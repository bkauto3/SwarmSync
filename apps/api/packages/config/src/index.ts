export interface ServiceConfig {
  nodeEnv: string;
  port: number;
  databaseUrl: string;
  redisUrl: string;
  stripeSecretKey: string;
}

export const loadServiceConfig = (): ServiceConfig => ({
  nodeEnv: process.env.NODE_ENV ?? 'development',
  port: Number.parseInt(process.env.PORT ?? '4000', 10),
  databaseUrl: process.env.DATABASE_URL ?? '',
  redisUrl: process.env.REDIS_URL ?? '',
  stripeSecretKey: process.env.STRIPE_SECRET_KEY ?? '',
});

export { billingPlanConfigs } from './billing.js';
