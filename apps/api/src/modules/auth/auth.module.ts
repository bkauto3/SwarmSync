import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';

import { AuthController } from './auth.controller.js';
import { AuthService } from './auth.service.js';
import { JwtAuthGuard } from './guards/jwt-auth.guard.js';
import { ServiceAccountsController } from './service-accounts.controller.js';
import { ServiceAccountsService } from './service-accounts.service.js';
import { JwtStrategy } from './strategies/jwt.strategy.js';
import { DatabaseModule } from '../database/database.module.js';

@Module({
  imports: [
    ConfigModule,
    DatabaseModule,
    PassportModule.register({ defaultStrategy: 'jwt' }),
    JwtModule.registerAsync({
      global: true,
      inject: [ConfigService],
      useFactory: (configService: ConfigService) => ({
        secret: configService.get<string>('JWT_SECRET', 'development-secret'),
        signOptions: {
          expiresIn: '1h',
        },
      }),
    }),
  ],
  controllers: [AuthController, ServiceAccountsController],
  providers: [AuthService, JwtStrategy, ServiceAccountsService, JwtAuthGuard],
  exports: [AuthService, ServiceAccountsService, JwtAuthGuard],
})
export class AuthModule {}
