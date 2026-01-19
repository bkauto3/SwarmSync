import { Module } from '@nestjs/common';

import { AP2Controller } from './ap2.controller.js';
import { AP2Service } from './ap2.service.js';
import { AgentsModule } from '../agents/agents.module.js';
import { AuthModule } from '../auth/auth.module.js';
import { DatabaseModule } from '../database/database.module.js';
import { PaymentsModule } from '../payments/payments.module.js';
import { QualityModule } from '../quality/quality.module.js';

@Module({
  imports: [DatabaseModule, PaymentsModule, QualityModule, AgentsModule, AuthModule],
  controllers: [AP2Controller],
  providers: [AP2Service],
  exports: [AP2Service],
})
export class AP2Module {}
