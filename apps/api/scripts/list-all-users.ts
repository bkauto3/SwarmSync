import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function listAllUsers() {
  try {
    const users = await prisma.user.findMany({
      include: {
        _count: {
          select: {
            agents: true,
          },
        },
      },
      orderBy: {
        createdAt: 'desc',
      },
    });

    console.log(`\n=== All Users in Database ===\n`);
    console.log(`Total Users: ${users.length}\n`);

    if (users.length === 0) {
      console.log('No users found in the database.\n');
      return;
    }

    users.forEach((user, index) => {
      console.log(`${index + 1}. ${user.displayName}`);
      console.log(`   Email: ${user.email}`);
      console.log(`   ID: ${user.id}`);
      console.log(`   Agents: ${user._count.agents}`);
      console.log(`   Created: ${user.createdAt.toISOString()}`);
      console.log('');
    });
  } catch (error) {
    console.error('Error listing users:', error);
  } finally {
    await prisma.$disconnect();
  }
}

listAllUsers();

