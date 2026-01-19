import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient({
  datasources: {
    db: {
      url: 'postgresql://neondb_owner:npg_v0RtJymP2rcw@ep-cold-butterfly-aenonb7s.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require',
    },
  },
});

async function main() {
  try {
    const email = 'seed-agent@example.com';
    const user = await prisma.user.findUnique({
      where: { email },
    });
    console.log('User found:', user);
  } catch (e) {
    console.error(e);
  } finally {
    // @ts-ignore
    await prisma.$disconnect();
  }
}

main();
