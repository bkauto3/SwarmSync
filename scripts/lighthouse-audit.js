#!/usr/bin/env node

/**
 * Lighthouse Audit Script
 * 
 * Runs Lighthouse audits on key pages for performance, accessibility, SEO, and best practices.
 * 
 * Usage:
 *   npm run lighthouse:audit
 *   npm run lighthouse:audit -- --url=http://localhost:3000
 * 
 * Requires: npm install -g lighthouse
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const BASE_URL = process.env.AUDIT_URL || 'http://localhost:3000';
const PAGES = [
  '/',
  '/pricing',
  '/agents',
  '/demo/workflows',
  '/register',
];

const OUTPUT_DIR = path.join(process.cwd(), 'lighthouse-reports');

// Ensure output directory exists
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

console.log('🔍 Running Lighthouse audits...\n');
console.log(`Base URL: ${BASE_URL}\n`);

PAGES.forEach((page, index) => {
  const url = `${BASE_URL}${page}`;
  const slug = page === '/' ? 'homepage' : page.replace(/\//g, '-').replace(/^-/, '');
  const outputPath = path.join(OUTPUT_DIR, `lighthouse-${slug}.html`);
  
  console.log(`[${index + 1}/${PAGES.length}] Auditing ${url}...`);
  
  try {
    execSync(
      `lighthouse "${url}" --output=html --output-path="${outputPath}" --chrome-flags="--headless" --quiet`,
      { stdio: 'inherit' }
    );
    console.log(`✅ Report saved: ${outputPath}\n`);
  } catch (error) {
    console.error(`❌ Failed to audit ${url}`);
    console.error(error.message);
    console.log('');
  }
});

console.log('📊 All audits complete!');
console.log(`Reports saved in: ${OUTPUT_DIR}`);
console.log('\nTo view reports, open the HTML files in your browser.');
console.log('\nRecommended thresholds:');
console.log('  Performance: > 90');
console.log('  Accessibility: > 95');
console.log('  Best Practices: > 90');
console.log('  SEO: > 95');

