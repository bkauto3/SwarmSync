import { PrismaClient, AgentStatus, AgentVisibility } from '@prisma/client';

const prisma = new PrismaClient();

async function createFeaturedAgents() {
  const userEmail = 'rainking6693@gmail.com';

  try {
    console.log('\n=== Creating Featured Agents ===\n');

    // Find user
    const user = await prisma.user.findUnique({
      where: { email: userEmail },
    });

    if (!user) {
      console.error(`❌ User ${userEmail} not found!`);
      console.error('Please run setup-user-and-agents.ts first to create the user.');
      return;
    }

    console.log(`✓ Found user: ${user.displayName} (${user.id})\n`);

    // Featured agents to create
    const featuredAgents = [
      {
        name: 'Discovery Analyst',
        slug: 'discovery-analyst',
        description: 'Research agent with certified QA and reporting.',
        categories: ['research', 'analytics'],
        tags: ['research', 'qa', 'reporting', 'analysis'],
        pricingModel: 'pay_per_use',
        status: AgentStatus.APPROVED,
        visibility: AgentVisibility.PUBLIC,
        trustScore: 92,
        badges: ['high-quality'],
        basePriceCents: null, // Pay per insight
      },
      {
        name: 'Workflow Builder',
        slug: 'workflow-builder',
        description: 'Drag-and-drop orchestrator for multi-agent plays.',
        categories: ['orchestration', 'automation'],
        tags: ['workflow', 'orchestration', 'automation', 'builder'],
        pricingModel: 'free',
        status: AgentStatus.APPROVED,
        visibility: AgentVisibility.PUBLIC,
        trustScore: 88,
        badges: [],
        basePriceCents: 0, // Free (credits only)
      },
      {
        name: 'Support Copilot',
        slug: 'support-copilot',
        description: 'Escrow-enabled support agent with SLA guarantees.',
        categories: ['support', 'customer-service'],
        tags: ['support', 'customer-service', 'sla', 'escrow'],
        pricingModel: 'pay_per_use',
        status: AgentStatus.APPROVED,
        visibility: AgentVisibility.PUBLIC,
        trustScore: 95,
        badges: ['high-quality', 'production-ready'],
        basePriceCents: 200, // $2 per resolved case
      },
    ];

    let createdCount = 0;
    let updatedCount = 0;

    for (const agentData of featuredAgents) {
      // Check if agent already exists
      const existing = await prisma.agent.findUnique({
        where: { slug: agentData.slug },
      });

      if (existing) {
        // Update existing agent
        await prisma.agent.update({
          where: { id: existing.id },
          data: {
            name: agentData.name,
            description: agentData.description,
            categories: agentData.categories,
            tags: agentData.tags,
            pricingModel: agentData.pricingModel,
            status: agentData.status,
            visibility: agentData.visibility,
            trustScore: agentData.trustScore,
            badges: agentData.badges,
            basePriceCents: agentData.basePriceCents,
            creatorId: user.id, // Ensure it's assigned to this user
          },
        });
        updatedCount++;
        console.log(`✓ Updated: ${agentData.name}`);
      } else {
        // Create new agent
        await prisma.agent.create({
          data: {
            slug: agentData.slug,
            name: agentData.name,
            description: agentData.description,
            categories: agentData.categories,
            tags: agentData.tags,
            pricingModel: agentData.pricingModel,
            status: agentData.status,
            visibility: agentData.visibility,
            trustScore: agentData.trustScore,
            badges: agentData.badges,
            basePriceCents: agentData.basePriceCents,
            creatorId: user.id,
          },
        });
        createdCount++;
        console.log(`✓ Created: ${agentData.name}`);
      }
    }

    console.log(`\n=== Summary ===`);
    console.log(`Created: ${createdCount}`);
    console.log(`Updated: ${updatedCount}`);

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
      console.log(`   Badges: ${agent.badges.join(', ') || 'None'}`);
      console.log(`   Categories: ${agent.categories.join(', ')}`);
      console.log(`   Tags: ${agent.tags.join(', ')}`);
      if (agent.basePriceCents !== null) {
        console.log(`   Price: $${(agent.basePriceCents / 100).toFixed(2)}`);
      } else {
        console.log(`   Price: Pay per use`);
      }
      console.log('');
    });

    console.log('✓ Complete!\n');
  } catch (error) {
    console.error('\n❌ Error:', error);
    if (error instanceof Error) {
      console.error('Message:', error.message);
    }
  } finally {
    await prisma.$disconnect();
  }
}

createFeaturedAgents();

