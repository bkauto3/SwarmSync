import { createParamDecorator, ExecutionContext } from '@nestjs/common';

import { AuthenticatedUser } from '../auth.service.js';

export const CurrentUser = createParamDecorator<
  unknown,
  ExecutionContext,
  AuthenticatedUser | null
>((_data, ctx) => {
  const request = ctx.switchToHttp().getRequest();
  return request.user ?? null;
});

