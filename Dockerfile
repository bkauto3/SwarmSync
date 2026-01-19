# syntax = docker/dockerfile:1

ARG NODE_VERSION=20.18.1
FROM node:${NODE_VERSION}-slim AS base

LABEL fly_launch_runtime="Node.js"

WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED="1"
ENV HUSKY="0"


FROM base AS deps

RUN apt-get update -qq \
  && apt-get install --no-install-recommends -y build-essential python-is-python3 pkg-config \
  && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json ./
COPY apps/api/package.json apps/api/package.json
COPY apps/web/package.json apps/web/package.json
COPY packages/sdk/package.json packages/sdk/package.json
COPY packages/config/package.json packages/config/package.json
COPY apps/api/prisma apps/api/prisma

RUN npm ci


FROM deps AS builder

# Accept build args for Next.js public env vars
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_APP_URL
ARG NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY

# Set them as env vars for the build
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_APP_URL=${NEXT_PUBLIC_APP_URL}
ENV NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=${NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY}

COPY . .

RUN npm run build --workspace @agent-market/sdk \
  && npm run build --workspace @agent-market/web


FROM base AS runner

RUN addgroup --system --gid 1001 nodejs \
  && adduser --system --uid 1001 nextjs

WORKDIR /app

COPY --from=builder /app/apps/web/.next/standalone ./standalone
COPY --from=builder /app/apps/web/.next/static ./standalone/apps/web/.next/static
COPY --from=builder /app/apps/web/public ./standalone/apps/web/public

ENV NODE_ENV="production"
USER nextjs
WORKDIR /app/standalone/apps/web

EXPOSE 3000
CMD ["node", "server.js"]
