import { Body, Controller, Get, Param, Patch, Post, Put, Query } from '@nestjs/common';
import { Throttle } from '@nestjs/throttler';
import { AgentStatus, AgentVisibility } from '@prisma/client';

import { AgentsService } from './agents.service.js';
import { AgentDiscoveryQueryDto } from './dto/agent-discovery-query.dto.js';
import { CreateAgentDto } from './dto/create-agent.dto.js';
import { ExecuteAgentDto } from './dto/execute-agent.dto.js';
import { ReviewAgentDto } from './dto/review-agent.dto.js';
import { SubmitForReviewDto } from './dto/submit-for-review.dto.js';
import { UpdateAgentDto } from './dto/update-agent.dto.js';
import { UpdateAgentBudgetDto } from './dto/update-budget.dto.js';
import { AuthenticatedUser } from '../auth/auth.service.js';
import { CurrentUser } from '../auth/decorators/current-user.decorator.js';
import { Public } from '../auth/decorators/public.decorator.js';

@Controller('agents')
export class AgentsController {
  constructor(private readonly agentsService: AgentsService) { }

  // Public endpoints - rate limited
  @Public()
  @Get()
  @Throttle({ default: { limit: 20, ttl: 60000 } }) // 20 requests per minute
  findAll(
    @Query('status') status?: AgentStatus,
    @Query('visibility') visibility?: AgentVisibility,
    @Query('category') category?: string,
    @Query('tag') tag?: string,
    @Query('search') search?: string,
    @Query('verifiedOnly') verifiedOnly?: string,
    @Query('creatorId') creatorId?: string,
    @Query('showAll') showAll?: string,
    @CurrentUser() user?: AuthenticatedUser,
  ) {
    return this.agentsService.findAll({
      status,
      visibility,
      category,
      tag,
      search,
      verifiedOnly: (verifiedOnly ?? '').toLowerCase() === 'true',
      creatorId,
      showAll: (showAll ?? '').toLowerCase() === 'true',
      userId: user?.id,
      organizationId: user?.organizationId,
    });
  }

  @Public()
  @Get('discover')
  @Throttle({ default: { limit: 10, ttl: 60000 } }) // 10 requests per minute for discovery
  async discover(@Query() query: AgentDiscoveryQueryDto) {
    return this.agentsService.discover(query);
  }

  @Public()
  @Get('slug/:slug')
  @Throttle({ default: { limit: 20, ttl: 60000 } })
  async findBySlug(@Param('slug') slug: string) {
    return this.agentsService.findBySlug(slug);
  }

  @Public()
  @Get(':id')
  @Throttle({ default: { limit: 20, ttl: 60000 } })
  async findOne(@Param('id') id: string) {
    return this.agentsService.findOne(id);
  }

  @Public()
  @Get(':id/schema')
  @Throttle({ default: { limit: 20, ttl: 60000 } })
  getSchema(@Param('id') id: string) {
    return this.agentsService.getAgentSchema(id);
  }

  // Protected endpoints - rate limited
  @Post()
  @Throttle({ default: { limit: 10, ttl: 60000 } }) // 10 requests per minute for creation
  create(@Body() body: CreateAgentDto) {
    return this.agentsService.create(body);
  }

  @Put(':id')
  @Throttle({ default: { limit: 20, ttl: 60000 } })
  update(@Param('id') id: string, @Body() body: UpdateAgentDto) {
    return this.agentsService.update(id, body);
  }

  @Post(':id/submit')
  @Throttle({ default: { limit: 5, ttl: 60000 } }) // 5 requests per minute
  submit(@Param('id') id: string, @Body() body: SubmitForReviewDto) {
    return this.agentsService.submitForReview(id, body);
  }

  @Post(':id/review')
  @Throttle({ default: { limit: 10, ttl: 60000 } })
  review(@Param('id') id: string, @Body() body: ReviewAgentDto) {
    return this.agentsService.reviewAgent(id, body);
  }

  @Post(':id/execute')
  @Throttle({ default: { limit: 30, ttl: 60000 } }) // 30 requests per minute for execution
  execute(@Param('id') id: string, @Body() body: ExecuteAgentDto) {
    return this.agentsService.executeAgent(id, body);
  }

  @Get(':id/executions')
  @Throttle({ default: { limit: 20, ttl: 60000 } })
  executions(@Param('id') id: string) {
    return this.agentsService.listExecutions(id);
  }

  @Get(':id/reviews')
  @Throttle({ default: { limit: 20, ttl: 60000 } })
  reviews(@Param('id') id: string) {
    return this.agentsService.listReviews(id);
  }

  @Public()
  @Get(':id/budget')
  @Throttle({ default: { limit: 20, ttl: 60000 } })
  getBudget(@Param('id') id: string) {
    return this.agentsService.getAgentBudget(id);
  }

  @Patch(':id/budget')
  @Throttle({ default: { limit: 20, ttl: 60000 } })
  updateBudget(@Param('id') id: string, @Body() body: UpdateAgentBudgetDto) {
    return this.agentsService.updateAgentBudget(id, body);
  }

  @Get(':id/payment-history')
  @Throttle({ default: { limit: 20, ttl: 60000 } })
  getPaymentHistory(@Param('id') id: string) {
    return this.agentsService.getAgentPaymentHistory(id);
  }

  @Get(':id/a2a-transactions')
  @Throttle({ default: { limit: 20, ttl: 60000 } })
  listA2aTransactions(@Param('id') id: string) {
    return this.agentsService.listAgentA2aTransactions(id);
  }

  @Get(':id/network')
  @Throttle({ default: { limit: 20, ttl: 60000 } })
  getNetwork(@Param('id') id: string) {
    return this.agentsService.getAgentNetwork(id);
  }
}
