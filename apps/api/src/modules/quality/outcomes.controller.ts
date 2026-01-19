import { Body, Controller, Get, Param, Post } from '@nestjs/common';

import { CreateServiceAgreementDto } from './dto/create-service-agreement.dto.js';
import { RecordOutcomeVerificationDto } from './dto/record-verification.dto.js';
import { OutcomesService } from './outcomes.service.js';

@Controller('quality/outcomes')
export class OutcomesController {
  constructor(private readonly outcomesService: OutcomesService) {}

  @Post('agreements')
  createAgreement(@Body() body: CreateServiceAgreementDto) {
    return this.outcomesService.createAgreement(body);
  }

  @Get('agreements/agent/:agentId')
  listAgreements(@Param('agentId') agentId: string) {
    return this.outcomesService.listAgreements(agentId);
  }

  @Post('agreements/:id/verify')
  verifyOutcome(@Param('id') id: string, @Body() body: RecordOutcomeVerificationDto) {
    return this.outcomesService.recordVerification(id, body);
  }
}
