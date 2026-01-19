import { Controller, Get, Query } from '@nestjs/common';

import { AnalyticsService } from './analytics.service.js';

@Controller('admin/analytics')
export class AnalyticsController {
  constructor(private readonly analyticsService: AnalyticsService) {}

  @Get('agents/top-buyers')
  async getTopBuyingAgents(
    @Query('limit') limit?: string,
    @Query('startDate') startDate?: string,
    @Query('endDate') endDate?: string,
  ) {
    return this.analyticsService.getTopBuyingAgents({
      limit: limit ? parseInt(limit, 10) : 100,
      startDate: startDate ? new Date(startDate) : undefined,
      endDate: endDate ? new Date(endDate) : undefined,
    });
  }

  @Get('agents/churned')
  async getChurnedAgents(@Query('daysInactive') daysInactive?: string) {
    return this.analyticsService.getChurnedAgents(
      daysInactive ? parseInt(daysInactive, 10) : 30,
    );
  }

  @Get('agents/whales')
  async getWhaleAgents(
    @Query('minSpend') minSpend?: string,
    @Query('startDate') startDate?: string,
    @Query('endDate') endDate?: string,
  ) {
    return this.analyticsService.getWhaleAgents({
      minSpend: minSpend ? parseFloat(minSpend) : 1000,
      startDate: startDate ? new Date(startDate) : undefined,
      endDate: endDate ? new Date(endDate) : undefined,
    });
  }

  @Get('agents/network-graph')
  async getAgentNetworkGraph(@Query('agentId') agentId?: string) {
    return this.analyticsService.getAgentNetworkGraph(agentId);
  }

  @Get('overview')
  async getOverview(
    @Query('startDate') startDate?: string,
    @Query('endDate') endDate?: string,
  ) {
    return this.analyticsService.getOverview({
      startDate: startDate ? new Date(startDate) : undefined,
      endDate: endDate ? new Date(endDate) : undefined,
    });
  }
}

