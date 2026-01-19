import { Module } from '@nestjs/common';

import { DemoController } from './demo.controller.js';
import { DemoService } from './demo.service.js';
import { AgentsModule } from '../agents/agents.module.js';
import { AP2Module } from '../ap2/ap2.module.js';
import { DatabaseModule } from '../database/database.module.js';
import { PaymentsModule } from '../payments/payments.module.js';

@Module({
  imports: [DatabaseModule, AgentsModule, AP2Module, PaymentsModule],
  controllers: [DemoController],
  providers: [DemoService],
  exports: [DemoService],
})
export class DemoModule {}

