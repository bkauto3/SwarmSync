import 'reflect-metadata';
import { ValidationPipe } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { NestFactory } from '@nestjs/core';
import express from 'express';
import helmet from 'helmet';

import { AppModule } from './modules/app.module.js';
import { PrismaService } from './modules/database/prisma.service.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule, {
    bufferLogs: true,
  });

  const configService = app.get(ConfigService);
  const port = configService.get<number>('PORT', 4000);
  const corsOrigins =
    configService.get<string>('CORS_ALLOWED_ORIGINS') ??
    configService.get<string>('WEB_URL', 'http://localhost:3000');
  const normalizeOrigin = (value: string) => value.trim().replace(/\/$/, '');

  const fallbackOrigins = [
    // Local development
    'http://localhost:3000',
    'http://localhost:3001',
    'http://127.0.0.1:3000',
    // Production marketing domains (always allow to prevent CORS regressions)
    'https://swarmsync.ai',
    'https://www.swarmsync.ai',
    'https://swarmsync.netlify.app', // Netlify deploy URL
    'https://swarmsync-api.up.railway.app',
  ];

  const allowedOrigins = [
    ...fallbackOrigins,
    ...corsOrigins.split(',').map(normalizeOrigin).filter(Boolean),
  ]
    .map(normalizeOrigin)
    .filter(Boolean);
  const uniqueAllowedOrigins = [...new Set(allowedOrigins)];

  // Log allowed origins for debugging
  // eslint-disable-next-line no-console
  console.log('CORS allowed origins:', uniqueAllowedOrigins);

  app.enableCors({
    origin: (origin, callback) => {
      // Allow requests with no origin (like mobile apps or curl requests)
      if (!origin) {
        callback(null, true);
        return;
      }
      const normalized = normalizeOrigin(origin);
      if (uniqueAllowedOrigins.includes(normalized)) {
        callback(null, true);
      } else {
        // eslint-disable-next-line no-console
        console.warn(`CORS blocked origin: ${origin} (normalized: ${normalized})`);
        callback(new Error(`Origin ${origin} not allowed by CORS`));
      }
    },
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization'],
    exposedHeaders: ['Content-Type', 'Authorization'],
    credentials: true,
    preflightContinue: false,
    optionsSuccessStatus: 204,
  });

  // Configure Helmet to not interfere with CORS
  app.use(
    helmet({
      crossOriginResourcePolicy: { policy: 'cross-origin' },
      crossOriginEmbedderPolicy: false,
    }),
  );
  // Global JSON body parser
  app.use(express.json());
  app.use('/stripe/webhook', express.raw({ type: '*/*' }));
  // X402 webhook uses JSON body but we need to preserve raw body for signature verification
  app.use('/webhooks/x402', express.json({ verify: (req: unknown, res: unknown, buf: Buffer) => { (req as Record<string, unknown>).rawBody = buf.toString('utf8'); } }));

  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      transform: true,
      forbidUnknownValues: true,
    }),
  );

  const prismaService = app.get(PrismaService);
  await prismaService.enableShutdownHooks(app);

  await app.listen(port, '0.0.0.0');
}

bootstrap().catch((error) => {
  // eslint-disable-next-line no-console
  console.error('Failed to bootstrap API', error);
  process.exit(1);
});
// Force restart
