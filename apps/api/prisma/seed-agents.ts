import { PrismaClient, AgentStatus, AgentVisibility, VerificationStatus } from '@prisma/client';

const prisma = new PrismaClient();

const demoAgents = [
  // Lead Generation Agents
  {
    name: 'B2B Lead Generator Pro',
    slug: 'b2b-lead-generator-pro',
    description: 'Generates qualified B2B leads with verified emails, job titles, and company information. Perfect for sales teams targeting enterprise clients.',
    categories: ['lead-generation', 'sales'],
    tags: ['b2b', 'leads', 'sales-prospecting', 'enterprise'],
    pricingModel: 'per_execution',
    basePriceCents: 3500, // $35 per 100 leads
    status: AgentStatus.APPROVED,
    visibility: AgentVisibility.PUBLIC,
    verificationStatus: VerificationStatus.VERIFIED,
    trustScore: 85,
    successCount: 142,
    failureCount: 8,
  },
  {
    name: 'LinkedIn Profile Scraper',
    slug: 'linkedin-profile-scraper',
    description: 'Extracts professional profiles from LinkedIn including contact information, work history, and skills. Ideal for recruitment and networking.',
    categories: ['lead-generation', 'data-collection'],
    tags: ['linkedin', 'scraping', 'recruitment', 'networking'],
    pricingModel: 'per_execution',
    basePriceCents: 1000, // $10 per 100 profiles
    status: AgentStatus.APPROVED,
    visibility: AgentVisibility.PUBLIC,
    verificationStatus: VerificationStatus.VERIFIED,
    trustScore: 78,
    successCount: 89,
    failureCount: 5,
  },

  // Content Creation Agents
  {
    name: 'SEO Blog Writer',
    slug: 'seo-blog-writer',
    description: 'Creates SEO-optimized blog posts with keyword research, meta descriptions, and internal linking suggestions. Drives organic traffic.',
    categories: ['content-creation', 'marketing'],
    tags: ['seo', 'blogging', 'content-marketing', 'copywriting'],
    pricingModel: 'per_execution',
    basePriceCents: 1500, // $15 per post
    status: AgentStatus.APPROVED,
    visibility: AgentVisibility.PUBLIC,
    verificationStatus: VerificationStatus.VERIFIED,
    trustScore: 92,
    successCount: 234,
    failureCount: 3,
  },
  {
    name: 'Social Media Content Creator',
    slug: 'social-media-content-creator',
    description: 'Generates engaging social media posts for Twitter, LinkedIn, and Facebook with hashtags and optimal posting times.',
    categories: ['content-creation', 'social-media'],
    tags: ['social-media', 'twitter', 'linkedin', 'facebook'],
    pricingModel: 'per_execution',
    basePriceCents: 800, // $8 per batch (10 posts)
    status: AgentStatus.APPROVED,
    visibility: AgentVisibility.PUBLIC,
    verificationStatus: VerificationStatus.VERIFIED,
    trustScore: 88,
    successCount: 312,
    failureCount: 12,
  },
  {
    name: 'Technical Documentation Writer',
    slug: 'technical-documentation-writer',
    description: 'Creates comprehensive technical documentation including API docs, user guides, and developer tutorials with code examples.',
    categories: ['content-creation', 'development'],
    tags: ['documentation', 'technical-writing', 'api-docs'],
    pricingModel: 'per_execution',
    basePriceCents: 7500, // $75 per document
    status: AgentStatus.APPROVED,
    visibility: AgentVisibility.PUBLIC,
    verificationStatus: VerificationStatus.VERIFIED,
    trustScore: 95,
    successCount: 67,
    failureCount: 1,
  },

  // Data Analysis Agents
  {
    name: 'Sales Trend Analyzer',
    slug: 'sales-trend-analyzer',
    description: 'Analyzes sales data to identify trends, patterns, and opportunities. Provides actionable insights with visualizations.',
    categories: ['data-analysis', 'sales'],
    tags: ['analytics', 'sales', 'trends', 'insights'],
    pricingModel: 'per_execution',
    basePriceCents: 8000, // $80 per report
    status: AgentStatus.APPROVED,
    visibility: AgentVisibility.PUBLIC,
    verificationStatus: VerificationStatus.VERIFIED,
    trustScore: 90,
    successCount: 156,
    failureCount: 7,
  },
  {
    name: 'Customer Segmentation Engine',
    slug: 'customer-segmentation-engine',
    description: 'Segments customers based on behavior, demographics, and purchase history. Enables targeted marketing campaigns.',
    categories: ['data-analysis', 'marketing'],
    tags: ['segmentation', 'customer-analysis', 'marketing'],
    pricingModel: 'per_execution',
    basePriceCents: 12000, // $120 per analysis
    status: AgentStatus.APPROVED,
    visibility: AgentVisibility.PUBLIC,
    verificationStatus: VerificationStatus.VERIFIED,
    trustScore: 87,
    successCount: 98,
    failureCount: 4,
  },

  // Customer Support Agents
  {
    name: 'Smart FAQ Bot',
    slug: 'smart-faq-bot',
    description: 'Answers common customer questions instantly with context-aware responses. Reduces support ticket volume by 60%.',
    categories: ['customer-support', 'automation'],
    tags: ['faq', 'chatbot', 'support', 'automation'],
    pricingModel: 'per_execution',
    basePriceCents: 15, // $0.15 per conversation
    status: AgentStatus.APPROVED,
    visibility: AgentVisibility.PUBLIC,
    verificationStatus: VerificationStatus.VERIFIED,
    trustScore: 82,
    successCount: 1847,
    failureCount: 53,
  },
  {
    name: 'Ticket Routing Assistant',
    slug: 'ticket-routing-assistant',
    description: 'Intelligently categorizes and routes support tickets to the right team. Includes priority scoring and SLA tracking.',
    categories: ['customer-support', 'automation'],
    tags: ['ticketing', 'routing', 'support', 'triage'],
    pricingModel: 'per_execution',
    basePriceCents: 10, // $0.10 per ticket
    status: AgentStatus.APPROVED,
    visibility: AgentVisibility.PUBLIC,
    verificationStatus: VerificationStatus.VERIFIED,
    trustScore: 91,
    successCount: 2341,
    failureCount: 29,
  },

  // Development Agents
  {
    name: 'Code Review Assistant',
    slug: 'code-review-assistant',
    description: 'Reviews pull requests for code quality, security issues, and best practices. Provides detailed feedback and suggestions.',
    categories: ['development', 'quality-assurance'],
    tags: ['code-review', 'security', 'quality', 'best-practices'],
    pricingModel: 'per_execution',
    basePriceCents: 2000, // $20 per review
    status: AgentStatus.APPROVED,
    visibility: AgentVisibility.PUBLIC,
    verificationStatus: VerificationStatus.VERIFIED,
    trustScore: 93,
    successCount: 187,
    failureCount: 6,
  },
  {
    name: 'Unit Test Generator',
    slug: 'unit-test-generator',
    description: 'Automatically generates comprehensive unit tests for your code with edge cases and mocking. Supports TypeScript, Python, and Java.',
    categories: ['development', 'testing'],
    tags: ['testing', 'unit-tests', 'automation', 'quality'],
    pricingModel: 'per_execution',
    basePriceCents: 3500, // $35 per test suite
    status: AgentStatus.APPROVED,
    visibility: AgentVisibility.PUBLIC,
    verificationStatus: VerificationStatus.VERIFIED,
    trustScore: 89,
    successCount: 124,
    failureCount: 8,
  },

  // Marketing Agents
  {
    name: 'SEO Keyword Researcher',
    slug: 'seo-keyword-researcher',
    description: 'Discovers high-value keywords with search volume, competition analysis, and ranking difficulty. Includes long-tail keyword suggestions.',
    categories: ['marketing', 'seo'],
    tags: ['seo', 'keywords', 'research', 'content-strategy'],
    pricingModel: 'per_execution',
    basePriceCents: 2500, // $25 per research report
    status: AgentStatus.APPROVED,
    visibility: AgentVisibility.PUBLIC,
    verificationStatus: VerificationStatus.VERIFIED,
    trustScore: 86,
    successCount: 203,
    failureCount: 11,
  },
  {
    name: 'Email Campaign Generator',
    slug: 'email-campaign-generator',
    description: 'Creates complete email drip campaigns with subject lines, body copy, and CTAs. Optimized for conversions and engagement.',
    categories: ['marketing', 'email'],
    tags: ['email-marketing', 'campaigns', 'copywriting', 'automation'],
    pricingModel: 'per_execution',
    basePriceCents: 4500, // $45 per campaign
    status: AgentStatus.APPROVED,
    visibility: AgentVisibility.PUBLIC,
    verificationStatus: VerificationStatus.VERIFIED,
    trustScore: 91,
    successCount: 167,
    failureCount: 5,
  },
  {
    name: 'Competitor Analysis Bot',
    slug: 'competitor-analysis-bot',
    description: 'Analyzes competitor websites, pricing, features, and marketing strategies. Provides actionable competitive intelligence.',
    categories: ['marketing', 'research'],
    tags: ['competitor-analysis', 'market-research', 'intelligence'],
    pricingModel: 'per_execution',
    basePriceCents: 9500, // $95 per report
    status: AgentStatus.APPROVED,
    visibility: AgentVisibility.PUBLIC,
    verificationStatus: VerificationStatus.VERIFIED,
    trustScore: 88,
    successCount: 78,
    failureCount: 3,
  },

  // Research Agents
  {
    name: 'Market Research Analyst',
    slug: 'market-research-analyst',
    description: 'Conducts comprehensive market research including TAM/SAM/SOM analysis, trends, and growth opportunities.',
    categories: ['research', 'business'],
    tags: ['market-research', 'analysis', 'trends', 'business-intelligence'],
    pricingModel: 'per_execution',
    basePriceCents: 15000, // $150 per report
    status: AgentStatus.APPROVED,
    visibility: AgentVisibility.PUBLIC,
    verificationStatus: VerificationStatus.VERIFIED,
    trustScore: 94,
    successCount: 56,
    failureCount: 2,
  },
  {
    name: 'Academic Paper Summarizer',
    slug: 'academic-paper-summarizer',
    description: 'Summarizes academic papers and research articles with key findings, methodology, and citations. Perfect for literature reviews.',
    categories: ['research', 'education'],
    tags: ['academic', 'research', 'summarization', 'education'],
    pricingModel: 'per_execution',
    basePriceCents: 500, // $5 per paper
    status: AgentStatus.APPROVED,
    visibility: AgentVisibility.PUBLIC,
    verificationStatus: VerificationStatus.VERIFIED,
    trustScore: 90,
    successCount: 412,
    failureCount: 18,
  },

  // Automation Agents
  {
    name: 'Data Entry Automator',
    slug: 'data-entry-automator',
    description: 'Automates repetitive data entry tasks across multiple platforms. Supports CSV, Excel, Google Sheets, and databases.',
    categories: ['automation', 'productivity'],
    tags: ['data-entry', 'automation', 'productivity', 'rpa'],
    pricingModel: 'per_execution',
    basePriceCents: 1500, // $15 per batch
    status: AgentStatus.APPROVED,
    visibility: AgentVisibility.PUBLIC,
    verificationStatus: VerificationStatus.VERIFIED,
    trustScore: 84,
    successCount: 267,
    failureCount: 14,
  },
  {
    name: 'Invoice Processing Agent',
    slug: 'invoice-processing-agent',
    description: 'Extracts data from invoices, validates information, and updates accounting systems. Handles PDF, images, and scanned documents.',
    categories: ['automation', 'finance'],
    tags: ['invoicing', 'ocr', 'accounting', 'automation'],
    pricingModel: 'per_execution',
    basePriceCents: 250, // $2.50 per invoice
    status: AgentStatus.APPROVED,
    visibility: AgentVisibility.PUBLIC,
    verificationStatus: VerificationStatus.VERIFIED,
    trustScore: 87,
    successCount: 534,
    failureCount: 21,
  },
];

async function main() {
  console.log('🌱 Seeding database with demo agents...');

  // Create a default user to own these agents
  let defaultUser = await prisma.user.findFirst({
    where: { email: 'demo@swarmsync.ai' },
  });

  if (!defaultUser) {
    console.log('Creating default user...');
    defaultUser = await prisma.user.create({
      data: {
        email: 'demo@swarmsync.ai',
        displayName: 'SwarmSync Demo',
        emailVerified: new Date(),
      },
    });
  }

  console.log(`✅ Default user: ${defaultUser.email} (${defaultUser.id})`);

  // Create agents
  for (const agentData of demoAgents) {
    const existing = await prisma.agent.findUnique({
      where: { slug: agentData.slug },
    });

    if (existing) {
      console.log(`⏭️  Agent already exists: ${agentData.name}`);
      continue;
    }

    const agent = await prisma.agent.create({
      data: {
        ...agentData,
        creatorId: defaultUser.id,
      },
    });

    console.log(`✅ Created agent: ${agent.name} (${agent.slug})`);
  }

  console.log('\n🎉 Database seeding complete!');
  console.log(`📊 Total agents: ${demoAgents.length}`);
}

main()
  .catch((e) => {
    console.error('❌ Error seeding database:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });

