# Multi-stage build for Next.js frontend in monorepo

# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app

# Copy package files from root and workspace
COPY package*.json ./
COPY packages/sdk/package*.json ./packages/sdk/
COPY apps/web/package*.json ./apps/web/

# Install dependencies for entire monorepo
RUN npm ci

# Stage 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/packages/sdk/node_modules ./packages/sdk/node_modules
COPY --from=deps /app/apps/web/node_modules ./apps/web/node_modules

# Copy entire monorepo (needed for workspace structure)
COPY . .

# Build SDK first (web depends on it)
RUN npm run build --workspace @agent-market/sdk

# Build web app with production environment variables available
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Build Next.js
RUN npm run build --workspace @agent-market/web

# Stage 3: Runner
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy necessary files from builder
COPY --from=builder /app/apps/web/next.config.mjs ./
COPY --from=builder /app/apps/web/package*.json ./

# Copy Next.js standalone output
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/public ./apps/web/public

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Start Next.js
CMD ["node", "apps/web/server.js"]
