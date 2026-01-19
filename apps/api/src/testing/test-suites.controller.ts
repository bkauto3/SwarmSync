import { Controller, Get, Query, UseGuards } from '@nestjs/common';

import { TestRunService } from './test-run.service.js';
import { JwtAuthGuard } from '../modules/auth/guards/jwt-auth.guard.js';

@Controller('api/v1/test-suites')
@UseGuards(JwtAuthGuard)
export class TestSuitesController {
  constructor(private readonly testRunService: TestRunService) { }

  @Get()
  async listSuites(
    @Query('category') category?: string,
    @Query('recommended') recommended?: string,
  ) {
    return this.testRunService.listSuites({
      category,
      recommended: recommended === 'true' ? true : recommended === 'false' ? false : undefined,
    });
  }

  @Get('recommended')
  async getRecommendedSuites() {
    return this.testRunService.getRecommendedSuites();
  }
  @Get('individual')
  async listIndividualTests() {
    return this.testRunService.listIndividualTests();
  }
}

