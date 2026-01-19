import { PrismaClient, AgentVisibility, WalletOwnerType } from '@prisma/client';
import { hash } from 'argon2';

const prisma = new PrismaClient();

async function main() {
  const userEmail = 'seed-agent@example.com';
  // Hash the password before storing
  const passwordHash = await hash('temporary-password');
  const user = await prisma.user.upsert({
    where: { email: userEmail },
    update: {
      // If user exists, update password if it's not hashed
      password: passwordHash,
    },
    create: {
      email: userEmail,
      displayName: 'Seed Agent Owner',
      password: passwordHash,
    },
  });

  const agent = await prisma.agent.upsert({
    where: { slug: 'test-agent' },
    update: {
      name: 'Test Agent',
      description: 'Seeded agent for automated Stripe smoke tests.',
      categories: ['general'],
      tags: ['demo', 'test'],
      pricingModel: 'pay_per_use',
      priceAmount: 10,
      visibility: AgentVisibility.PUBLIC,
      creatorId: user.id,
      x402Enabled: true,
      x402WalletAddress: '0x0000000000000000000000000000000000000000',
      x402Network: 'base-mainnet',
    },
    create: {
      slug: 'test-agent',
      name: 'Test Agent',
      description: 'Seeded agent for automated Stripe smoke tests.',
      categories: ['general'],
      tags: ['demo', 'test'],
      pricingModel: 'pay_per_use',
      priceAmount: 10,
      creatorId: user.id,
      visibility: AgentVisibility.PUBLIC,
      x402Enabled: true,
      x402WalletAddress: '0x0000000000000000000000000000000000000000',
      x402Network: 'base-mainnet',
    },
  });

  const walletId = `wallet-${agent.id}`;
  await prisma.wallet.upsert({
    where: { id: walletId },
    update: {},
    create: {
      id: walletId,
      ownerType: WalletOwnerType.AGENT,
      ownerAgentId: agent.id,
      currency: 'USD',
      status: 'ACTIVE',
    },
  });

  // eslint-disable-next-line no-console
  console.log(`Seeded agent ${agent.slug} with creator ${user.email}`);
}

main()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
