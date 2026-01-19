import { Module } from '@nestjs/common';

import { X402WebhookController } from './x402-webhook.controller.js';
import { X402Controller } from './x402.controller.js';
import { X402Service } from './x402.service.js';

@Module({
  controllers: [X402Controller, X402WebhookController],
  providers: [X402Service],
  exports: [X402Service],
})
export class X402Module {}

