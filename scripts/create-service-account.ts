#!/usr/bin/env tsx
import 'dotenv/config';
import { createHash, randomBytes } from 'node:crypto';
import process from 'node:process';

import { PrismaClient } from '@prisma/client';

interface CliOptions {
  name?: string;
  description?: string;
  organization?: string;
  agent?: string;
  scopes?: string[];
}

function parseArgs(): CliOptions {
  const args = process.argv.slice(2);
  const options: CliOptions = {};

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    switch (arg) {
      case '--name':
      case '-n':
        options.name = args[++i];
        break;
      case '--description':
      case '-d':
        options.description = args[++i];
        break;
      case '--organization':
      case '-o':
        options.organization = args[++i];
        break;
      case '--agent':
      case '-a':
        options.agent = args[++i];
        break;
      case '--scopes':
        options.scopes = (args[++i] ?? '')
          .split(',')
          .map((value) => value.trim())
          .filter(Boolean);
        break;
      default:
        break;
    }
  }

  return options;
}

async function main() {
  const prisma = new PrismaClient();
  const options = parseArgs();

  if (!options.name) {
    throw new Error('Missing required --name for the service account.');
  }

  let organizationId: string | undefined;
  if (options.organization) {
    const organization = await prisma.organization.findFirst({
      where: {
        OR: [{ id: options.organization }, { slug: options.organization }],
      },
    });
    if (!organization) {
      throw new Error(`Organization not found for identifier: ${options.organization}`);
    }
    organizationId = organization.id;
  }

  let agentId: string | undefined;
  if (options.agent) {
    const agent = await prisma.agent.findFirst({
      where: {
        OR: [{ id: options.agent }, { slug: options.agent }],
      },
      select: { id: true },
    });
    if (!agent) {
      throw new Error(`Agent not found for identifier: ${options.agent}`);
    }
    agentId = agent.id;
  }

  const token = `sa_${randomBytes(24).toString('hex')}`;
  const apiKeyHash = createHash('sha256').update(token).digest('hex');

  const account = await prisma.serviceAccount.create({
    data: {
      name: options.name,
      description: options.description,
      organizationId,
      agentId,
      scopes: options.scopes ?? [],
      apiKeyHash,
    },
  });

  // eslint-disable-next-line no-console
  console.log('Created service account:', account.id);
  // eslint-disable-next-line no-console
  console.log('API KEY (copy this now):', token);

  await prisma.$disconnect();
}

main().catch((error) => {
  // eslint-disable-next-line no-console
  console.error(error);
  process.exit(1);
});
