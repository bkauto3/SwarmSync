import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient({
  datasources: {
    db: {
      url: 'postgresql://neondb_owner:npg_v0RtJymP2rcw@ep-cold-butterfly-aenonb7s.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require',
    },
  },
});

async function testConnection() {
  try {
    console.log('Connecting to database...');
    // @ts-ignore
    await prisma.$connect();
    console.log('Connected successfully!');

    console.log('Checking User table...');
    const count = await prisma.user.count();
    console.log('User count:', count);

    const user = await prisma.user.findFirst();
    console.log('Sample user:', user ? user.email : 'No users found');

  } catch (e) {
    console.error('Connection failed:', e);
  } finally {
    // @ts-ignore
    await prisma.$disconnect();
  }
}

testConnection();
