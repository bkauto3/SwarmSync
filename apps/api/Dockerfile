# Multi-stage build for NestJS backend in monorepo

# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app

# Copy package files from root and workspace
COPY package*.json ./
COPY packages/sdk/package*.json ./packages/sdk/
COPY apps/api/package*.json ./apps/api/

# Install dependencies for entire monorepo
RUN npm ci

# Stage 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app

# Copy dependencies from deps stage
# In npm workspaces, all dependencies are hoisted to root node_modules
COPY --from=deps /app/node_modules ./node_modules

# Copy entire monorepo (needed for workspace structure)
COPY . .

# Build SDK first (api depends on it)
RUN npm run build --workspace @agent-market/sdk

# Build API
ENV NODE_ENV=production
RUN npm run build --workspace @agent-market/api

# Stage 3: Runner
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nestjs

# Copy necessary files
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules

# Copy SDK build output
COPY --from=builder /app/packages/sdk/dist ./packages/sdk/dist
COPY --from=builder /app/packages/sdk/package*.json ./packages/sdk/

# Copy API build output
COPY --from=builder /app/apps/api/dist ./apps/api/dist
COPY --from=builder /app/apps/api/package*.json ./apps/api/
# Note: node_modules are already copied from root, no need for workspace-specific copies

USER nestjs

EXPOSE 4000

ENV PORT=4000

# Start NestJS
CMD ["node", "apps/api/dist/main.js"]
