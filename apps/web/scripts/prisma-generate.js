import { readdir, rm, access } from 'fs/promises';
import path from 'path';
import { spawn } from 'child_process';

const prismaDir = path.join(process.cwd(), 'node_modules', '.prisma', 'client');

const ENGINE_PATTERN = /^query_engine-.*\.node(?:\.tmp.*)?$/;

const shouldSkipGenerate = process.platform === 'win32';

if (shouldSkipGenerate) {
  console.warn(
    'Skipping Prisma generate on Windows to avoid query engine rename issues - run `npx prisma generate` manually if needed.'
  );
  process.exit(0);
}

// Removed WASM engine type enforcement - using binary engines for Netlify compatibility
// process.env.PRISMA_CLIENT_ENGINE_TYPE = process.env.PRISMA_CLIENT_ENGINE_TYPE || 'wasm';

const getSchemaPath = () => {
  const args = process.argv.slice(2);
  const schemaFlagIndex = args.findIndex((arg) => arg === '--schema');
  if (schemaFlagIndex !== -1 && args.length > schemaFlagIndex + 1) {
    return args[schemaFlagIndex + 1];
  }
  return './prisma/schema.prisma';
};

async function cleanupOldBinaries() {
  try {
    await access(prismaDir);
  } catch {
    return;
  }

  const files = await readdir(prismaDir);
  await Promise.all(
    files
      .filter((file) => ENGINE_PATTERN.test(file))
      .map(async (file) => {
        try {
          await rm(path.join(prismaDir, file), { force: true });
        } catch (error) {
          if (error && error.code !== 'ENOENT') {
            console.warn('Unable to remove', file, '-', error.message);
          }
        }
      })
  );
}

function runPrismaGenerate(schemaPath) {
  return new Promise((resolve, reject) => {
    const child = spawn('npx', ['prisma', 'generate', '--schema', schemaPath], {
      stdio: 'inherit',
      shell: true,
    });

    child.on('error', reject);
    child.on('exit', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`Prisma generate exited with code ${code}`));
      }
    });
  });
}

async function main() {
  const schemaPath = getSchemaPath();
  await cleanupOldBinaries();
  await runPrismaGenerate(schemaPath);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
