import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';

import { AgentsModule } from './agents/agents.module.js';
import { AnalyticsModule } from './analytics/analytics.module.js';
import { AP2Module } from './ap2/ap2.module.js';
import { AuthModule } from './auth/auth.module.js';
import { BillingModule } from './billing/billing.module.js';
import { DatabaseModule } from './database/database.module.js';
import { HealthModule } from './health/health.module.js';
import { NotificationsModule } from './notifications/notifications.module.js';
import { OrganizationsModule } from './organizations/organizations.module.js';
import { PaymentsModule } from './payments/payments.module.js';
import { QualityModule } from './quality/quality.module.js';
import { RateLimitingModule } from './rate-limiting/rate-limiting.module.js';
import { TrustModule } from './trust/trust.module.js';
import { WorkflowsModule } from './workflows/workflows.module.js';
import { X402Module } from './x402/x402.module.js';
import { TestingModule } from '../testing/testing.module.js';
import { DemoModule } from './demo/demo.module.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
// From apps/api/src/modules/app.module.ts, go up 4 levels to reach root
const rootEnvPath = join(__dirname, '..', '..', '..', '..', '.env');

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: [rootEnvPath, '../../.env', '.env', 'env.example'],
    }),
    DatabaseModule,
    RateLimitingModule,
    AgentsModule,
    AnalyticsModule,
    BillingModule,
    PaymentsModule,
    AP2Module,
    TrustModule,
    WorkflowsModule,
    QualityModule,
    OrganizationsModule,
    AuthModule,
    HealthModule,
    X402Module,
    TestingModule,
    NotificationsModule,
    DemoModule,
  ],
})
export class AppModule {}
