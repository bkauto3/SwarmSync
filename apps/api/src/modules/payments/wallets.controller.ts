import { Body, Controller, Get, Param, Post } from '@nestjs/common';

import { CreateWalletDto } from './dto/create-wallet.dto.js';
import { FundWalletDto } from './dto/fund-wallet.dto.js';
import { WalletsService } from './wallets.service.js';

@Controller('wallets')
export class WalletsController {
  constructor(private readonly walletsService: WalletsService) {}

  @Post()
  create(@Body() body: CreateWalletDto) {
    return this.walletsService.createWallet(body);
  }

  @Get('agent/:agentId')
  getAgentWallet(@Param('agentId') agentId: string) {
    return this.walletsService.ensureAgentWallet(agentId);
  }

  @Get('user/:userId')
  getUserWallet(@Param('userId') userId: string) {
    return this.walletsService.ensureUserWallet(userId);
  }

  @Get('org/:slug')
  getOrganizationWallet(@Param('slug') slug: string) {
    return this.walletsService.ensureOrganizationWalletBySlug(slug);
  }

  @Get(':id')
  get(@Param('id') id: string) {
    return this.walletsService.getWallet(id);
  }

  @Post(':id/fund')
  fund(@Param('id') id: string, @Body() body: FundWalletDto) {
    return this.walletsService.fundWallet(id, body);
  }
}
