// Test if Prisma can connect to the database
const { PrismaClient } = require('@prisma/client');

const DATABASE_URL = 'postgresql://neondb_owner:npg_v0RtJymP2rcw@ep-cold-butterfly-a3nonb7s.us-east-2.aws.neon.tech/neondb?sslmode=require';

async function testConnection() {
    console.log('Testing Prisma connection...');

    const prisma = new PrismaClient({
        datasources: {
            db: {
                url: DATABASE_URL
            }
        }
    });

    try {
        // Try to query the database
        const userCount = await prisma.user.count();
        console.log(`✓ Connected successfully. User count: ${userCount}`);

        // Try to find a specific user
        const testUser = await prisma.user.findFirst({
            where: {
                email: {
                    contains: '@'
                }
            }
        });

        if (testUser) {
            console.log(`✓ Found user: ${testUser.email}`);
        }

        await prisma.$disconnect();
        console.log('✓ Disconnected successfully');
    } catch (error) {
        console.error('❌ ERROR:', error.message);
        console.error(error);
        await prisma.$disconnect();
    }
}

testConnection();
