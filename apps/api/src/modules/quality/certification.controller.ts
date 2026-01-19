import { Body, Controller, Get, Param, Post } from '@nestjs/common';

import { CertificationService } from './certification.service.js';
import { CreateCertificationDto } from './dto/create-certification.dto.js';
import { UpdateCertificationStatusDto } from './dto/update-certification-status.dto.js';
import { Public } from '../auth/decorators/public.decorator.js';

@Controller('quality/certifications')
export class CertificationController {
  constructor(private readonly certificationService: CertificationService) {}

  @Public()
  @Post()
  create(@Body() body: CreateCertificationDto) {
    return this.certificationService.createCertification(body);
  }

  @Public()
  @Post(':id/advance')
  advance(@Param('id') id: string, @Body() body: UpdateCertificationStatusDto) {
    return this.certificationService.advanceCertification(id, body);
  }

  @Public()
  @Get('agent/:agentId')
  listByAgent(@Param('agentId') agentId: string) {
    return this.certificationService.listForAgent(agentId);
  }
}
