import { Body, Controller, Post, UseGuards } from '@nestjs/common';

import { Ap2Service } from './ap2.service.js';
import { CompleteAp2PaymentDto } from './dto/complete-ap2.dto.js';
import { InitiateAp2PaymentDto } from './dto/initiate-ap2.dto.js';
import { ReleaseEscrowDto } from './dto/release-escrow.dto.js';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard.js';

@Controller('payments')
@UseGuards(JwtAuthGuard)
export class Ap2Controller {
  constructor(private readonly ap2Service: Ap2Service) {}

  @Post('ap2/initiate')
  initiate(@Body() body: InitiateAp2PaymentDto) {
    return this.ap2Service.initiate(body);
  }

  @Post('ap2/complete')
  complete(@Body() body: CompleteAp2PaymentDto) {
    return this.ap2Service.complete(body);
  }

  @Post('ap2/release')
  release(@Body() body: ReleaseEscrowDto) {
    return this.ap2Service.release(body.escrowId, body.memo);
  }
}
