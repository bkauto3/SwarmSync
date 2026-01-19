import { Injectable, Optional } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';

import { AuthenticatedUser } from '../auth.service.js';

interface JwtPayload {
  sub: string;
  email: string;
  displayName: string;
  kind?: 'user' | 'service_account';
}

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor(@Optional() configService?: ConfigService) {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey:
        configService?.get<string>('JWT_SECRET', 'development-secret') ??
        process.env.JWT_SECRET ??
        'development-secret',
    });
  }

  async validate(payload: JwtPayload): Promise<AuthenticatedUser> {
    return {
      id: payload.sub,
      email: payload.email,
      displayName: payload.displayName,
      kind: payload.kind ?? 'user',
    };
  }
}

