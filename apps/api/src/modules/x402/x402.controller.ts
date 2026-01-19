import { Body, Controller, Get, Inject, Param, Post } from '@nestjs/common';

import { X402Service } from './x402.service.js';

interface VerifyPaymentBody {
  agentId: string;
  txHash: string;
  buyerAddress: string;
  amount: number;
}

interface ExecutePaymentBody extends VerifyPaymentBody {
  task: Record<string, unknown>;
}

@Controller('x402')
export class X402Controller {
  constructor(@Inject(X402Service) private readonly x402Service: X402Service) {}

  @Get('agents/:agentId/payment-methods')
  getPaymentMethods(@Param('agentId') agentId: string) {
    return this.x402Service.getPaymentMethods(agentId);
  }

  @Post('verify')
  verifyPayment(@Body() body: VerifyPaymentBody) {
    return this.x402Service.verifyPayment(body);
  }

  @Post('execute')
  executeWithX402(@Body() body: ExecutePaymentBody) {
    return this.x402Service.executeWithX402({
      ...body,
      task: body.task ?? {},
    });
  }
}

