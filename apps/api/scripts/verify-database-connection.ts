import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function verifyConnection() {
  try {
    console.log('\n=== Database Connection Verification ===\n');
    
    const dbUrl = process.env.DATABASE_URL;
    if (!dbUrl) {
      console.error('❌ DATABASE_URL is not set!');
      return;
    }

    // Extract database info from URL (without exposing password)
    const urlMatch = dbUrl.match(/postgres(ql)?:\/\/([^:]+):([^@]+)@([^:]+):(\d+)\/([^?]+)/);
    if (urlMatch) {
      const [, , username, , host, port, database] = urlMatch;
      console.log('Database Host:', host);
      console.log('Database Port:', port);
      console.log('Database Name:', database);
      console.log('Database User:', username);
      console.log('Is Neon?', host.includes('neon.tech') || host.includes('neon') ? 'Yes ✓' : 'No');
    }

    // Test connection
    await prisma.$connect();
    console.log('\n✓ Connection successful\n');

    // Get database name from a query
    const result = await prisma.$queryRaw<Array<{ current_database: string }>>`
      SELECT current_database();
    `;
    console.log('Connected to database:', result[0]?.current_database);

    // Count tables
    const tableCount = await prisma.$queryRaw<Array<{ count: bigint }>>`
      SELECT COUNT(*) as count
      FROM information_schema.tables
      WHERE table_schema = 'public'
    `;
    console.log('Tables in database:', Number(tableCount[0]?.count || 0));

    // Count records
    const userCount = await prisma.user.count();
    const agentCount = await prisma.agent.count();
    
    console.log('\n=== Record Counts ===');
    console.log(`Users: ${userCount}`);
    console.log(`Agents: ${agentCount}`);

    if (userCount > 0) {
      console.log('\n=== Users ===');
      const users = await prisma.user.findMany({
        select: {
          id: true,
          email: true,
          displayName: true,
          createdAt: true,
        },
        orderBy: { createdAt: 'desc' },
        take: 5,
      });
      users.forEach((u) => {
        console.log(`  - ${u.displayName} (${u.email}) - Created: ${u.createdAt.toISOString()}`);
      });
    }

  } catch (error) {
    console.error('\n❌ Connection error:', error);
  } finally {
    await prisma.$disconnect();
  }
}

verifyConnection();

