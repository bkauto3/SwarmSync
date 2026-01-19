import { PrismaClient, WalletOwnerType } from '@prisma/client';

const prisma = new PrismaClient();

const DEFAULT_ORG_SLUG = process.env.DEFAULT_ORG_SLUG ?? 'genesis';

async function main() {
  // Create or update the default organization
  const organization = await prisma.organization.upsert({
    where: { slug: DEFAULT_ORG_SLUG },
    update: {
      name: 'Genesis Organization',
    },
    create: {
      slug: DEFAULT_ORG_SLUG,
      name: 'Genesis Organization',
    },
  });

  console.log(`Ensured organization exists: ${organization.slug} (${organization.id})`);

  // Ensure the organization has a wallet
  const walletId = `org-wallet-${organization.id}`;
  await prisma.wallet.upsert({
    where: { id: walletId },
    update: {},
    create: {
      id: walletId,
      ownerType: WalletOwnerType.ORGANIZATION,
      organizationId: organization.id,
      currency: 'USD',
      status: 'ACTIVE',
    },
  });

  console.log(`Ensured organization wallet exists: ${walletId}`);
}

main()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
