import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function listUserAgents() {
  const userEmail = 'rainking6693@gmail.com';

  try {
    // Find user by email
    const user = await prisma.user.findUnique({
      where: { email: userEmail },
      include: {
        agents: {
          orderBy: {
            createdAt: 'desc',
          },
        },
      },
    });

    if (!user) {
      console.log(`User with email ${userEmail} not found.`);
      return;
    }

    console.log(`\n=== Agents for ${user.displayName} (${user.email}) ===\n`);
    console.log(`User ID: ${user.id}`);
    console.log(`Total Agents: ${user.agents.length}\n`);

    if (user.agents.length === 0) {
      console.log('No agents found for this user.\n');
      return;
    }

    // Display each agent
    user.agents.forEach((agent, index) => {
      console.log(`${index + 1}. ${agent.name}`);
      console.log(`   ID: ${agent.id}`);
      console.log(`   Slug: ${agent.slug}`);
      console.log(`   Status: ${agent.status}`);
      console.log(`   Visibility: ${agent.visibility}`);
      console.log(`   Trust Score: ${agent.trustScore}`);
      console.log(`   Categories: ${agent.categories.join(', ') || 'None'}`);
      console.log(`   Tags: ${agent.tags.join(', ') || 'None'}`);
      console.log(`   Pricing Model: ${agent.pricingModel}`);
      if (agent.basePriceCents) {
        console.log(`   Base Price: $${(agent.basePriceCents / 100).toFixed(2)}`);
      }
      console.log(`   Created: ${agent.createdAt.toISOString()}`);
      console.log(`   Updated: ${agent.updatedAt.toISOString()}`);
      if (agent.ap2Endpoint) {
        console.log(`   AP2 Endpoint: ${agent.ap2Endpoint}`);
      }
      console.log('');
    });

    // Summary
    console.log('\n=== Summary ===');
    const statusCounts = user.agents.reduce((acc, agent) => {
      acc[agent.status] = (acc[agent.status] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    
    console.log('By Status:');
    Object.entries(statusCounts).forEach(([status, count]) => {
      console.log(`  ${status}: ${count}`);
    });

    const visibilityCounts = user.agents.reduce((acc, agent) => {
      acc[agent.visibility] = (acc[agent.visibility] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    
    console.log('\nBy Visibility:');
    Object.entries(visibilityCounts).forEach(([visibility, count]) => {
      console.log(`  ${visibility}: ${count}`);
    });
  } catch (error) {
    console.error('Error listing user agents:', error);
  } finally {
    await prisma.$disconnect();
  }
}

listUserAgents();

