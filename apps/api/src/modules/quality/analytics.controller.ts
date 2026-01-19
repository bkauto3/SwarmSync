import { Controller, Get, Param, Query } from '@nestjs/common';

import { QualityAnalyticsService } from './analytics.service.js';
import { Public } from '../auth/decorators/public.decorator.js';

@Controller('quality/analytics')
export class QualityAnalyticsController {
  constructor(private readonly analyticsService: QualityAnalyticsService) {}

  @Public()
  @Get('agents/:agentId')
  getAgentAnalytics(@Param('agentId') agentId: string) {
    return this.analyticsService.getAgentSummary(agentId);
  }

  @Public()
  @Get('agents/:agentId/timeseries')
  getAgentTimeseries(
    @Param('agentId') agentId: string,
    @Query('days') days?: string,
  ) {
    const parsedDays = days ? Number.parseInt(days, 10) : undefined;
    return this.analyticsService.getAgentRoiTimeseries(agentId, parsedDays);
  }
}
