import { Body, Controller, HttpException, HttpStatus, Logger, Post } from '@nestjs/common';

import { AuthService } from './auth.service.js';
import { LoginDto } from './dto/login.dto.js';
import { RegisterUserDto } from './dto/register-user.dto.js';

@Controller('auth')
export class AuthController {
  private readonly logger = new Logger(AuthController.name);

  constructor(private readonly authService: AuthService) {}

  @Post('register')
  async register(@Body() body: RegisterUserDto) {
    try {
      this.logger.log(`Registration attempt for email: ${body.email}`);
      const result = await this.authService.register(body);
      this.logger.log(`Registration successful for email: ${body.email}`);
      return result;
    } catch (error) {
      this.logger.error(`Registration failed for email: ${body.email}`, error.stack);
      if (error instanceof HttpException) {
        throw error;
      }
      throw new HttpException(
        'Registration failed. Please try again.',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Post('login')
  async login(@Body() body: LoginDto) {
    try {
      this.logger.log(`Login attempt for email: ${body.email}`);
      const result = await this.authService.login(body);
      this.logger.log(`Login successful for email: ${body.email}`);
      return result;
    } catch (error) {
      this.logger.error(`Login failed for email: ${body.email}`, error.stack);
      if (error instanceof HttpException) {
        throw error;
      }
      throw new HttpException(
        'Login failed. Please try again.',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }
}
