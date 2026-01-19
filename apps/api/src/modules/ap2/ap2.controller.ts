import {
  Body,
  Controller,
  Get,
  Param,
  ParseUUIDPipe,
  Patch,
  Post,
  Query,
  UseGuards,
} from '@nestjs/common';
import { Throttle } from '@nestjs/throttler';

import { AP2Service } from './ap2.service.js';
import { AgentNegotiationsQueryDto } from './dto/agent-negotiations-query.dto.js';
import { NegotiationRequestDto } from './dto/negotiation-request.dto.js';
import { RespondNegotiationDto } from './dto/respond-negotiation.dto.js';
import { ServiceDeliveryDto } from './dto/service-delivery.dto.js';
import { AgentTransactionsQueryDto } from './dto/transactions-query.dto.js';
import { CurrentUser } from '../auth/decorators/current-user.decorator.js';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard.js';

import type { AuthenticatedUser } from '../auth/types.js';

@Controller('ap2')
@UseGuards(JwtAuthGuard)
export class AP2Controller {
  constructor(private readonly ap2Service: AP2Service) { }

  // Raise limits for negotiation traffic to reduce 429s during agent-to-agent flows
  @Throttle({ default: { limit: 500, ttl: 60000 } })
  @Post('negotiate')
  initiateNegotiation(
    @CurrentUser() user: AuthenticatedUser | null,
    @Body() body: NegotiationRequestDto,
  ) {
    return this.ap2Service.initiateNegotiation({
      ...body,
      initiatedByUserId: user?.id,
    });
  }

  @Post('respond')
  respondToNegotiation(
    @CurrentUser() _user: AuthenticatedUser | null,
    @Body() body: RespondNegotiationDto,
  ) {
    return this.ap2Service.respondToNegotiation(body);
  }

  @Post('deliver')
  deliverService(@CurrentUser() user: AuthenticatedUser | null, @Body() body: ServiceDeliveryDto) {
    return this.ap2Service.deliverService({
      ...body,
      deliveredByUserId: user?.id,
    });
  }

  @Get('negotiations/:id')
  getNegotiation(@Param('id', new ParseUUIDPipe()) id: string) {
    return this.ap2Service.getNegotiation(id);
  }

  @Throttle({ default: { limit: 500, ttl: 60000 } })
  @Get('negotiations/my')
  listNegotiations(@Query() query: AgentNegotiationsQueryDto) {
    return this.ap2Service.getAgentNegotiations(query.agentId);
  }

  @Patch('negotiations/:id/cancel')
  cancelNegotiation(@Param('id', new ParseUUIDPipe()) id: string) {
    return this.ap2Service.cancelNegotiation(id);
  }

  @Get('transactions/:id')
  getTransaction(@Param('id', new ParseUUIDPipe()) id: string) {
    return this.ap2Service.getTransactionStatus(id);
  }

  @Get('transactions/my')
  listTransactions(@Query() query: AgentTransactionsQueryDto) {
    return this.ap2Service.listTransactionsForAgent(query.agentId);
  }
}
