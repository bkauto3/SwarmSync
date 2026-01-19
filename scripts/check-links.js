#!/usr/bin/env node

/**
 * Link Checker Script for CI/CD
 * 
 * Crawls the site and checks for broken links.
 * Fails the build if broken internal links are found.
 */

import { SiteChecker } from 'broken-link-checker';

const baseUrl = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000';
let hasErrors = false;
const brokenLinks = [];

console.log(`\n🔍 Starting link check for: ${baseUrl}\n`);

const siteChecker = new SiteChecker(
    {
        excludeExternalLinks: false, // Check external links but don't fail on them
        filterLevel: 3, // Check everything
        honorRobotExclusions: false,
        maxSocketsPerHost: 10,
        userAgent: 'SwarmSync-LinkChecker/1.0',
    },
    {
        error: (error) => {
            console.error('❌ Crawler error:', error);
            hasErrors = true;
        },
        link: (result) => {
            if (result.broken) {
                const isInternal = result.url.resolved.startsWith(baseUrl);
                const severity = isInternal ? '🔴 CRITICAL' : '⚠️  WARNING';

                console.error(`${severity} Broken link found:`);
                console.error(`  URL: ${result.url.original}`);
                console.error(`  On page: ${result.base.original}`);
                console.error(`  Reason: ${result.brokenReason}`);
                console.error(`  HTTP Status: ${result.http.statusCode || 'N/A'}\n`);

                brokenLinks.push({
                    url: result.url.original,
                    page: result.base.original,
                    reason: result.brokenReason,
                    status: result.http.statusCode,
                    isInternal,
                });

                // Only fail build for internal broken links
                if (isInternal) {
                    hasErrors = true;
                }
            }
        },
        page: (error, pageUrl) => {
            if (error) {
                console.error(`❌ Error crawling page: ${pageUrl}`, error);
            } else {
                console.log(`✓ Checked: ${pageUrl}`);
            }
        },
        end: () => {
            console.log('\n📊 Link Check Summary\n');
            console.log('─'.repeat(60));

            if (brokenLinks.length === 0) {
                console.log('✅ No broken links found!');
                console.log('─'.repeat(60));
                process.exit(0);
            }

            const internalBroken = brokenLinks.filter(l => l.isInternal);
            const externalBroken = brokenLinks.filter(l => !l.isInternal);

            console.log(`Total broken links: ${brokenLinks.length}`);
            console.log(`  Internal (critical): ${internalBroken.length}`);
            console.log(`  External (warnings): ${externalBroken.length}`);
            console.log('─'.repeat(60));

            if (internalBroken.length > 0) {
                console.log('\n🔴 CRITICAL: Internal broken links found:\n');
                internalBroken.forEach((link, i) => {
                    console.log(`${i + 1}. ${link.url}`);
                    console.log(`   On: ${link.page}`);
                    console.log(`   Reason: ${link.reason}\n`);
                });
            }

            if (externalBroken.length > 0) {
                console.log('\n⚠️  External broken links (not failing build):\n');
                externalBroken.forEach((link, i) => {
                    console.log(`${i + 1}. ${link.url}`);
                    console.log(`   On: ${link.page}\n`);
                });
            }

            if (hasErrors) {
                console.log('\n❌ Build failed due to broken internal links\n');
                process.exit(1);
            } else {
                console.log('\n✅ No critical issues found\n');
                process.exit(0);
            }
        },
    }
);

// Start the crawl
siteChecker.enqueue(baseUrl);

// Handle process termination
process.on('SIGINT', () => {
    console.log('\n\n⚠️  Link check interrupted by user\n');
    process.exit(1);
});

process.on('uncaughtException', (error) => {
    console.error('\n❌ Uncaught exception:', error);
    process.exit(1);
});
