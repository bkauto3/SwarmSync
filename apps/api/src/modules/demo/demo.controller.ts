import { Controller, Get, Param, Post, Body, Req, HttpCode, HttpStatus } from '@nestjs/common';
import { Throttle } from '@nestjs/throttler';
import { Request } from 'express';

import { DemoService } from './demo.service.js';
import { Public } from '../auth/decorators/public.decorator.js';

interface RunDemoA2ADto {
  requesterAgentId: string;
  responderAgentId: string;
  service: string;
  budget: number;
  price: number;
}

@Controller('demo/a2a')
@Public() // No authentication required
export class DemoController {
  constructor(private readonly demoService: DemoService) {}

  @Get('agents')
  @Throttle({ default: { limit: 10, ttl: 60000 } }) // 10 requests per minute
  async getDemoAgents() {
    return this.demoService.getDemoAgents();
  }

  @Post('run')
  @HttpCode(HttpStatus.CREATED)
  @Throttle({ default: { limit: 5, ttl: 60000 } }) // 5 runs per minute per IP
  async runDemoA2A(@Body() dto: RunDemoA2ADto, @Req() req: Request) {
    // Get IP address for demo session tracking
    const ipAddress = req.ip || req.socket.remoteAddress || 'unknown';

    // Get or create demo session
    const session = await this.demoService.getOrCreateDemoSession(ipAddress);

    // Run demo A2A negotiation
    const result = await this.demoService.runDemoA2A({
      ...dto,
      userId: session.userId,
    });

    return {
      runId: result.runId,
      negotiationId: result.negotiationId,
      expiresAt: session.expiresAt,
    };
  }

  @Get('run/:runId/logs')
  @Throttle({ default: { limit: 30, ttl: 60000 } }) // 30 requests per minute for polling
  async getDemoRunLogs(@Param('runId') runId: string) {
    return this.demoService.getDemoRunLogs(runId);
  }
}

