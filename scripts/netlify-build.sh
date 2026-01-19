#!/bin/bash
set -e

# Build SDK dependency first
echo "Building SDK..."
npm run build --workspace @agent-market/sdk

# Build Next.js app
echo "Building Next.js app..."
cd apps/web
next build

