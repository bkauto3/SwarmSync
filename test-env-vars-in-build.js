// Test script to check if env vars are actually accessible at runtime
console.log('='.repeat(80));
console.log('ENVIRONMENT VARIABLES CHECK');
console.log('='.repeat(80));
console.log();

const vars = [
  'NEXTAUTH_SECRET',
  'NEXTAUTH_URL',
  'GOOGLE_CLIENT_ID',
  'GOOGLE_CLIENT_SECRET',
  'GITHUB_CLIENT_ID',
  'GITHUB_CLIENT_SECRET',
  'DATABASE_URL',
  'NEXT_PUBLIC_GOOGLE_CLIENT_ID',
  'NEXT_PUBLIC_GITHUB_CLIENT_ID'
];

vars.forEach(varName => {
  const value = process.env[varName];
  if (value) {
    // Show first 20 chars for secrets
    const display = varName.includes('SECRET') || varName.includes('DATABASE')
      ? value.substring(0, 20) + '...'
      : value;
    console.log(`✓ ${varName}: ${display}`);
  } else {
    console.log(`❌ ${varName}: NOT SET`);
  }
});

console.log();
console.log('='.repeat(80));
