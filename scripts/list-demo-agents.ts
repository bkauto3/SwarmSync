import { PrismaClient, AgentStatus, AgentVisibility } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const agents = await prisma.agent.findMany({
    where: {
      status: AgentStatus.APPROVED,
      visibility: AgentVisibility.PUBLIC,
    },
    orderBy: { createdAt: 'asc' },
    take: 40,
  });

  const lines = agents.map((agent, index) => {
    return [
      `${index + 1}. ${agent.name} (${agent.slug})`,
      `   id=${agent.id}`,
      `   categories=${agent.categories.join(', ')}`,
    ].join('\n');
  });

  // eslint-disable-next-line no-console
  console.log(lines.join('\n'));
}

main()
  .catch((error) => {
    // eslint-disable-next-line no-console
    console.error('Error listing demo agents:', error);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });

