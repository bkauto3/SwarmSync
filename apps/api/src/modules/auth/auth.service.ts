import { Injectable, InternalServerErrorException, Logger, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { hash, verify } from 'argon2';

import { PrismaService } from '../database/prisma.service.js';
import { LoginDto } from './dto/login.dto.js';
import { RegisterUserDto } from './dto/register-user.dto.js';

export interface AuthenticatedUser {
  id: string;
  email: string;
  displayName: string;
  kind?: 'user' | 'service_account';
  serviceAccountId?: string;
  organizationId?: string;
  agentId?: string;
  scopes?: string[];
}

@Injectable()
export class AuthService {
  private readonly logger = new Logger(AuthService.name);
  private schemaChecked = false; // Cache schema check result

  constructor(
    private readonly jwtService: JwtService,
    private readonly prisma: PrismaService,
  ) {}

  async register(data: RegisterUserDto) {
    const { email, password, displayName } = data;

    try {
      await this.ensureUserSchema();

      // Check if user already exists
      const existing = await this.prisma.user.findUnique({
        where: { email },
      });

      if (existing) {
        throw new UnauthorizedException('Email already registered');
      }

      // Hash password and create user
      const passwordHash = await hash(password);
      const dbUser = await this.prisma.user.create({
        data: {
          email,
          displayName,
          password: passwordHash,
        },
      });

      const user = this.dbUserToAuthUser(dbUser);
      return this.buildAuthResponse(user);
    } catch (error) {
      if (error instanceof UnauthorizedException) {
        throw error;
      }
      this.logger.error(`Registration error for email: ${email}`, error.stack);
      throw new InternalServerErrorException('Registration failed. Please try again.');
    }
  }

  async login(data: LoginDto) {
    try {
      await this.ensureUserSchema();

      const dbUser = await this.prisma.user.findUnique({
        where: { email: data.email },
      select: {
        id: true,
        email: true,
        displayName: true,
        password: true,
      },
      });

      if (!dbUser) {
        throw new UnauthorizedException('Invalid credentials');
      }

      // Check if password is in PHC format (starts with $)
      // If not, it's likely a plain text password from old seed data
      const isHashed = dbUser.password.startsWith('$');

      let passwordValid: boolean;
      if (isHashed) {
        // Normal verification for hashed passwords
        passwordValid = await verify(dbUser.password, data.password);
      } else {
        // For backward compatibility: if password is plain text, compare directly
        // Then re-hash it for future logins
        passwordValid = dbUser.password === data.password;
        if (passwordValid) {
          // Re-hash the password and update the database
          const passwordHash = await hash(data.password);
          await this.prisma.user.update({
            where: { id: dbUser.id },
            data: { password: passwordHash },
          });
          this.logger.log(`Re-hashed password for user: ${data.email}`);
        }
      }

      if (!passwordValid) {
        throw new UnauthorizedException('Invalid credentials');
      }

      const user = this.dbUserToAuthUser(dbUser);
      return this.buildAuthResponse(user);
    } catch (error) {
      if (error instanceof UnauthorizedException) {
        throw error;
      }
      this.logger.error(`Login error for email: ${data.email}`, error.stack);
      throw new InternalServerErrorException('Login failed. Please try again.');
    }
  }

  private dbUserToAuthUser(dbUser: { id: string; email: string; displayName: string }): AuthenticatedUser {
    return {
      id: dbUser.id,
      email: dbUser.email,
      displayName: dbUser.displayName,
      kind: 'user',
    };
  }

  private buildAuthResponse(
    user: AuthenticatedUser,
    additionalClaims?: {
      role?: string;
      betaAccess?: boolean;
      providerBeta?: boolean;
    },
  ) {
    try {
      const payload = {
        sub: user.id,
        email: user.email,
        displayName: user.displayName,
        kind: user.kind ?? 'user',
        ...additionalClaims,
      };

      const accessToken = this.jwtService.sign(payload);

      return {
        user,
        accessToken,
        expiresIn: 3600,
      };
    } catch (error) {
      this.logger.error('Failed to build auth response', error.stack);
      throw new InternalServerErrorException('Failed to generate authentication token');
    }
  }

  /**
   * Ensure critical user columns exist in legacy databases.
   * Cached to avoid running on every request.
   */
  private async ensureUserSchema() {
    // Only check once per service instance (cached for the lifetime of the service)
    if (this.schemaChecked) {
      return;
    }

    try {
      // Quick feature check on the metadata table; if it fails, attempt to add missing columns.
      await this.prisma.$queryRawUnsafe('SELECT "emailVerified" FROM "User" LIMIT 1;');
      this.schemaChecked = true; // Mark as checked if query succeeds
    } catch (error) {
      const message = error instanceof Error ? error.message : '';
      if (message.includes('emailVerified')) {
        this.logger.warn('Missing User.emailVerified column detected. Attempting to add it.');
        try {
          await this.prisma.$executeRawUnsafe(
            'ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "emailVerified" TIMESTAMP;',
          );
          this.schemaChecked = true; // Mark as checked after successful migration
        } catch (migrateError) {
          this.logger.error('Failed to auto-add User.emailVerified column', migrateError);
          // Keep going; the next calls will still surface the original error if unresolved.
        }
      } else {
        // If error is not about emailVerified, schema is likely fine, mark as checked
        this.schemaChecked = true;
      }
    }
  }
}
