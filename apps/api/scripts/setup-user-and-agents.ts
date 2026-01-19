import { PrismaClient } from '@prisma/client';
import { hash } from 'argon2';

const prisma = new PrismaClient();

async function setupUserAndAgents() {
  const userEmail = 'rainking6693@gmail.com';
  const userPassword = 'Chartres6693!';
  const userDisplayName = 'Ben Stone';

  try {
    console.log('\n=== Setting up User and Agents ===\n');
    console.log('Database URL:', process.env.DATABASE_URL ? 'Set (hidden)' : 'NOT SET - This is a problem!');
    
    if (!process.env.DATABASE_URL) {
      console.error('\n❌ ERROR: DATABASE_URL environment variable is not set!');
      console.error('Please set DATABASE_URL to your Neon database connection string.');
      return;
    }

    // Test connection
    await prisma.$connect();
    console.log('✓ Database connection successful\n');

    // Check if user already exists
    let user = await prisma.user.findUnique({
      where: { email: userEmail },
      include: {
        agents: true,
      },
    });

    if (user) {
      console.log(`User ${userEmail} already exists.`);
      console.log(`User ID: ${user.id}`);
      console.log(`Display Name: ${user.displayName}`);
      console.log(`Current Agents: ${user.agents.length}\n`);
      
      // Update password if needed
      const passwordHash = await hash(userPassword);
      user = await prisma.user.update({
        where: { id: user.id },
        data: {
          password: passwordHash,
          displayName: userDisplayName,
        },
        include: {
          agents: true,
        },
      });
      console.log('✓ Password and display name updated\n');
    } else {
      // Create new user
      const passwordHash = await hash(userPassword);
      user = await prisma.user.create({
        data: {
          email: userEmail,
          displayName: userDisplayName,
          password: passwordHash,
        },
        include: {
          agents: true,
        },
      });
      console.log(`✓ User created: ${userDisplayName} (${userEmail})`);
      console.log(`User ID: ${user.id}\n`);
    }

    // Get all existing agents
    const allAgents = await prisma.agent.findMany({
      orderBy: {
        createdAt: 'desc',
      },
    });

    console.log(`\n=== Found ${allAgents.length} agents in database ===\n`);

    if (allAgents.length === 0) {
      console.log('No agents found. You may need to create agents through the UI first.\n');
      return;
    }

    // Assign agents to user
    let assignedCount = 0;
    let alreadyAssignedCount = 0;

    for (const agent of allAgents) {
      if (agent.creatorId === user.id) {
        alreadyAssignedCount++;
        console.log(`✓ ${agent.name} - Already assigned to ${userDisplayName}`);
      } else {
        // Update agent to assign to this user
        await prisma.agent.update({
          where: { id: agent.id },
          data: {
            creatorId: user.id,
          },
        });
        assignedCount++;
        console.log(`✓ ${agent.name} - Assigned to ${userDisplayName}`);
      }
    }

    console.log(`\n=== Summary ===`);
    console.log(`Total Agents: ${allAgents.length}`);
    console.log(`Newly Assigned: ${assignedCount}`);
    console.log(`Already Assigned: ${alreadyAssignedCount}`);

    // List all agents for this user
    const userAgents = await prisma.agent.findMany({
      where: {
        creatorId: user.id,
      },
      orderBy: {
        createdAt: 'desc',
      },
    });

    console.log(`\n=== Your Agents (${userAgents.length}) ===\n`);
    userAgents.forEach((agent, index) => {
      console.log(`${index + 1}. ${agent.name}`);
      console.log(`   ID: ${agent.id}`);
      console.log(`   Slug: ${agent.slug}`);
      console.log(`   Status: ${agent.status}`);
      console.log(`   Visibility: ${agent.visibility}`);
      console.log(`   Created: ${agent.createdAt.toISOString()}`);
      console.log('');
    });

    console.log('✓ Setup complete!\n');
  } catch (error) {
    console.error('\n❌ Error:', error);
    if (error instanceof Error) {
      console.error('Message:', error.message);
      console.error('Stack:', error.stack);
    }
  } finally {
    await prisma.$disconnect();
  }
}

setupUserAndAgents();

