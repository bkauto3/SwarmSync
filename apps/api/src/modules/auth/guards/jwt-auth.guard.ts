import { ExecutionContext, Injectable, UnauthorizedException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Reflector } from '@nestjs/core';
import { AuthGuard } from '@nestjs/passport';
import { firstValueFrom, isObservable } from 'rxjs';

import { IS_PUBLIC_KEY } from '../decorators/public.decorator.js';
import { ServiceAccountsService } from '../service-accounts.service.js';

import type { Request } from 'express';
import type { Observable } from 'rxjs';

@Injectable()
export class JwtAuthGuard extends AuthGuard('jwt') {
  constructor(
    private readonly configService: ConfigService,
    private readonly serviceAccounts: ServiceAccountsService,
    private readonly reflector: Reflector,
  ) {
    super();
  }

  async canActivate(context: ExecutionContext): Promise<boolean> {
    // Check if route is marked as public
    const isPublic = this.reflector.getAllAndOverride<boolean>(IS_PUBLIC_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);

    if (isPublic) {
      try {
        // Attempt to authenticate to populate user, but don't fail if invalid
        await super.canActivate(context);
      } catch {
        // Ignore auth errors on public routes
      }
      return true;
    }

    if (!this.isEnforced()) {
      return true;
    }
    const request = context.switchToHttp().getRequest<Request>();
    const apiKey = this.extractApiKey(request);

    if (apiKey) {
      const principal = await this.serviceAccounts.validateApiKey(apiKey);
      if (!principal) {
        throw new UnauthorizedException('Invalid API key');
      }
      request.user = principal;
      return true;
    }

    const result = super.canActivate(context) as boolean | Promise<boolean> | Observable<boolean>;
    return this.resolveGuardResult(result);
  }

  handleRequest<TUser = unknown>(
    err: unknown,
    user: TUser,
    _info?: unknown,
    _context?: ExecutionContext,
    _status?: unknown,
  ): TUser {
    if (!this.isEnforced()) {
      if (err) {
        throw err;
      }
      return (user ?? null) as TUser;
    }

    if (err || !user) {
      throw err || new UnauthorizedException();
    }

    return user;
  }

  private async resolveGuardResult(
    result: boolean | Promise<boolean> | Observable<boolean>,
  ): Promise<boolean> {
    if (typeof result === 'boolean') {
      return result;
    }
    if (isObservable(result)) {
      return firstValueFrom(result);
    }
    return result;
  }

  private isEnforced() {
    const flag = this.configService.get<string>('AP2_REQUIRE_AUTH', 'true');
    return flag?.toLowerCase() === 'true';
  }

  private extractApiKey(request: Request) {
    const headerKey = (request.headers['x-agent-api-key'] ??
      request.headers['x-api-key']) as string | string[] | undefined;
    if (typeof headerKey === 'string' && headerKey.trim().length > 0) {
      return headerKey.trim();
    }
    if (Array.isArray(headerKey)) {
      const first = headerKey.find((value) => value && value.trim().length > 0);
      if (first) {
        return first.trim();
      }
    }

    const authHeader = request.headers.authorization;
    if (typeof authHeader === 'string' && authHeader.startsWith('ApiKey ')) {
      return authHeader.slice('ApiKey '.length).trim();
    }

    return null;
  }
}
