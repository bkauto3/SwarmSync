import { Body, Controller, Get, Param, Post } from '@nestjs/common';

import { RunEvaluationDto } from './dto/run-evaluation.dto.js';
import { EvaluationService } from './evaluation.service.js';
import { Public } from '../auth/decorators/public.decorator.js';

@Controller('quality/evaluations')
export class EvaluationController {
  constructor(private readonly evaluationService: EvaluationService) {}

  @Public()
  @Post('run')
  run(@Body() body: RunEvaluationDto) {
    return this.evaluationService.runScenario(body);
  }

  @Public()
  @Get('agent/:agentId')
  listAgentResults(@Param('agentId') agentId: string) {
    return this.evaluationService.listResults(agentId);
  }
}
