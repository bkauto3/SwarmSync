import { Body, Controller, Get, Param, Post } from '@nestjs/common';

import { CollaborationService } from './collaboration.service.js';
import { CreateCollaborationRequestDto } from './dto/create-request.dto.js';
import { RespondCollaborationRequestDto } from './dto/respond-request.dto.js';

@Controller('agents/a2a')
export class CollaborationController {
  constructor(private readonly collaborationService: CollaborationService) {}

  @Post()
  create(@Body() body: CreateCollaborationRequestDto) {
    return this.collaborationService.create(body);
  }

  @Post('respond')
  respond(@Body() body: RespondCollaborationRequestDto) {
    return this.collaborationService.respond(body);
  }

  @Get(':agentId')
  list(@Param('agentId') agentId: string) {
    return this.collaborationService.listForAgent(agentId);
  }
}
