import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function checkDatabase() {
  try {
    console.log('\n=== Database Check ===\n');
    console.log('Database URL:', process.env.DATABASE_URL ? 'Set (hidden)' : 'Not set');
    
    // Test connection
    await prisma.$connect();
    console.log('✓ Database connection successful\n');

    // Count records
    const userCount = await prisma.user.count();
    const agentCount = await prisma.agent.count();
    
    console.log(`Users: ${userCount}`);
    console.log(`Agents: ${agentCount}\n`);

    if (agentCount > 0) {
      console.log('=== Sample Agents (first 5) ===\n');
      const agents = await prisma.agent.findMany({
        take: 5,
        include: {
          creator: {
            select: {
              email: true,
              displayName: true,
            },
          },
        },
        orderBy: {
          createdAt: 'desc',
        },
      });

      agents.forEach((agent, index) => {
        console.log(`${index + 1}. ${agent.name}`);
        console.log(`   Created by: ${agent.creator.displayName} (${agent.creator.email})`);
        console.log(`   Status: ${agent.status}`);
        console.log(`   Slug: ${agent.slug}`);
        console.log('');
      });
    }
  } catch (error) {
    console.error('Error checking database:', error);
  } finally {
    await prisma.$disconnect();
  }
}

checkDatabase();

