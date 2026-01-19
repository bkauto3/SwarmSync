import { PrismaClient, AgentStatus, AgentVisibility } from '@prisma/client';

const prisma = new PrismaClient();

async function create53Agents() {
  const userEmail = 'rainking6693@gmail.com';

  try {
    console.log('\n=== Creating 53 Agents ===\n');

    // Find user
    const user = await prisma.user.findUnique({
      where: { email: userEmail },
    });

    if (!user) {
      console.error(`❌ User ${userEmail} not found!`);
      return;
    }

    console.log(`✓ Found user: ${user.displayName} (${user.id})\n`);

    // Get current agent count
    const currentCount = await prisma.agent.count({
      where: { creatorId: user.id },
    });

    console.log(`Current agent count: ${currentCount}`);
    console.log(`Target: 53 agents\n`);

    if (currentCount >= 53) {
      console.log('✓ Already have 53+ agents. Checking for duplicates...\n');
    } else {
      const needed = 53 - currentCount;
      console.log(`Need to create ${needed} more agents\n`);
    }

    // Find duplicates by slug
    const allAgents = await prisma.agent.findMany({
      orderBy: { createdAt: 'asc' },
    });

    const slugMap = new Map<string, Array<{ id: string; name: string; createdAt: Date }>>();
    
    for (const agent of allAgents) {
      if (!slugMap.has(agent.slug)) {
        slugMap.set(agent.slug, []);
      }
      slugMap.get(agent.slug)!.push({
        id: agent.id,
        name: agent.name,
        createdAt: agent.createdAt,
      });
    }

    // Delete duplicates (keep oldest)
    let deletedCount = 0;
    for (const [, agents] of slugMap.entries()) {
      if (agents.length > 1) {
        agents.sort((a, b) => a.createdAt.getTime() - b.createdAt.getTime());
        const toDelete = agents.slice(1);
        
        for (const agentToDelete of toDelete) {
          console.log(`🗑️  Deleting duplicate: ${agentToDelete.name} (${agentToDelete.id})`);
          await prisma.agent.delete({
            where: { id: agentToDelete.id },
          });
          deletedCount++;
        }
      }
    }

    if (deletedCount > 0) {
      console.log(`\n✓ Deleted ${deletedCount} duplicate agents\n`);
    }

    // Get remaining agents
    const remainingAgents = await prisma.agent.findMany();
    const userAgentCount = remainingAgents.filter(a => a.creatorId === user.id).length;

    console.log(`Total agents in database: ${remainingAgents.length}`);
    console.log(`Your agents: ${userAgentCount}`);
    console.log(`Need to assign: ${remainingAgents.length - userAgentCount}\n`);

    // Assign all remaining agents to user
    let assignedCount = 0;
    for (const agent of remainingAgents) {
      if (agent.creatorId !== user.id) {
        await prisma.agent.update({
          where: { id: agent.id },
          data: { creatorId: user.id },
        });
        assignedCount++;
      }
    }

    console.log(`✓ Assigned ${assignedCount} agents to ${user.displayName}\n`);

    // If we still need more agents, create them
    const finalCount = await prisma.agent.count({
      where: { creatorId: user.id },
    });

    if (finalCount < 53) {
      const toCreate = 53 - finalCount;
      console.log(`Creating ${toCreate} additional agents...\n`);

      for (let i = 1; i <= toCreate; i++) {
        const agentName = `Agent ${finalCount + i}`;
        
        await prisma.agent.create({
          data: {
            slug: `agent-${finalCount + i}-${Date.now()}-${i}`,
            name: agentName,
            description: `AI agent #${finalCount + i} for ${user.displayName}`,
            categories: ['general'],
            tags: ['agent'],
            pricingModel: 'pay_per_use',
            status: AgentStatus.APPROVED,
            visibility: AgentVisibility.PUBLIC,
            creatorId: user.id,
            trustScore: 50 + Math.floor(Math.random() * 50), // Random trust score 50-100
          },
        });
        console.log(`✓ Created: ${agentName}`);
      }
    }

    // Final summary
    const finalAgents = await prisma.agent.findMany({
      where: { creatorId: user.id },
      orderBy: { createdAt: 'desc' },
    });

    console.log(`\n=== Final Summary ===`);
    console.log(`Your Total Agents: ${finalAgents.length}`);
    console.log(`Duplicates Deleted: ${deletedCount}`);
    console.log(`Newly Assigned: ${assignedCount}`);

    if (finalAgents.length >= 53) {
      console.log(`\n✓ Success! You now have ${finalAgents.length} agents assigned to your account.\n`);
    } else {
      console.log(`\n⚠️  You have ${finalAgents.length} agents, but target was 53.`);
      console.log(`   This might mean some agents exist elsewhere or need to be created manually.\n`);
    }

  } catch (error) {
    console.error('\n❌ Error:', error);
    if (error instanceof Error) {
      console.error('Message:', error.message);
    }
  } finally {
    await prisma.$disconnect();
  }
}

create53Agents();

