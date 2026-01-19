import { Body, Controller, Get, Param, Post } from '@nestjs/common';

import { UpdateVerificationDto } from './dto/update-verification.dto.js';
import { TrustService } from './trust.service.js';

@Controller('trust')
export class TrustController {
  constructor(private readonly trustService: TrustService) {}

  @Post('verify')
  verify(@Body() body: UpdateVerificationDto) {
    return this.trustService.updateVerification(body);
  }

  @Get('agents/:agentId')
  metrics(@Param('agentId') agentId: string) {
    return this.trustService.getAgentTrust(agentId);
  }
}
