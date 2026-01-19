import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function assignAllAgentsToUser() {
  const userEmail = 'rainking6693@gmail.com';

  try {
    console.log('\n=== Assigning All Agents to User ===\n');

    // Find user
    const user = await prisma.user.findUnique({
      where: { email: userEmail },
    });

    if (!user) {
      console.error(`❌ User ${userEmail} not found!`);
      return;
    }

    console.log(`✓ Found user: ${user.displayName} (${user.id})\n`);

    // Get all agents (public marketplace agents)
    const allAgents = await prisma.agent.findMany({
      orderBy: {
        createdAt: 'desc',
      },
    });

    console.log(`Found ${allAgents.length} total agents in database\n`);

    // Find duplicates by slug (most reliable identifier)
    const slugMap = new Map<string, Array<{ id: string; name: string; slug: string; createdAt: Date }>>();
    
    for (const agent of allAgents) {
      if (!slugMap.has(agent.slug)) {
        slugMap.set(agent.slug, []);
      }
      slugMap.get(agent.slug)!.push({
        id: agent.id,
        name: agent.name,
        slug: agent.slug,
        createdAt: agent.createdAt,
      });
    }

    // Identify and delete duplicates (keep the oldest one)
    const duplicates: Array<{ keep: string; delete: string[] }> = [];
    let deletedCount = 0;

    for (const [slug, agents] of slugMap.entries()) {
      if (agents.length > 1) {
        // Sort by creation date, keep the oldest
        agents.sort((a, b) => a.createdAt.getTime() - b.createdAt.getTime());
        const keep = agents[0];
        const toDelete = agents.slice(1);

        duplicates.push({
          keep: keep.id,
          delete: toDelete.map(a => a.id),
        });

        console.log(`⚠️  Found ${agents.length} duplicates for "${keep.name}" (slug: ${slug})`);
        console.log(`   Keeping: ${keep.id} (created: ${keep.createdAt.toISOString()})`);
        
        for (const agentToDelete of toDelete) {
          console.log(`   Deleting: ${agentToDelete.id} (created: ${agentToDelete.createdAt.toISOString()})`);
          
          // Delete the duplicate agent
          await prisma.agent.delete({
            where: { id: agentToDelete.id },
          });
          deletedCount++;
        }
        console.log('');
      }
    }

    if (duplicates.length > 0) {
      console.log(`✓ Deleted ${deletedCount} duplicate agents\n`);
    } else {
      console.log('✓ No duplicates found\n');
    }

    // Get all remaining agents after duplicate removal
    const remainingAgents = await prisma.agent.findMany({
      orderBy: {
        createdAt: 'desc',
      },
    });

    console.log(`=== Assigning ${remainingAgents.length} agents to ${user.displayName} ===\n`);

    let assignedCount = 0;
    let alreadyAssignedCount = 0;

    for (const agent of remainingAgents) {
      if (agent.creatorId === user.id) {
        alreadyAssignedCount++;
      } else {
        // Update agent to assign to this user
        await prisma.agent.update({
          where: { id: agent.id },
          data: {
            creatorId: user.id,
          },
        });
        assignedCount++;
        console.log(`✓ Assigned: ${agent.name} (${agent.slug})`);
      }
    }

    console.log(`\n=== Summary ===`);
    console.log(`Total Agents: ${remainingAgents.length}`);
    console.log(`Newly Assigned: ${assignedCount}`);
    console.log(`Already Assigned: ${alreadyAssignedCount}`);
    console.log(`Duplicates Deleted: ${deletedCount}`);

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
      console.log(`   Trust Score: ${agent.trustScore}`);
      if (agent.categories.length > 0) {
        console.log(`   Categories: ${agent.categories.join(', ')}`);
      }
      if (agent.tags.length > 0) {
        console.log(`   Tags: ${agent.tags.join(', ')}`);
      }
      console.log('');
    });

    console.log('✓ Complete!\n');
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

assignAllAgentsToUser();

