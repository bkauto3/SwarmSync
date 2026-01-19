import { randomUUID } from 'node:crypto';
import { performance } from 'node:perf_hooks';
import { setTimeout as delay } from 'node:timers/promises';

type HttpMethod = 'GET' | 'POST';

type Payload = Record<string, unknown>;

interface Endpoint {
  path: string;
  method: HttpMethod;
  payload?: Payload | (() => Payload);
}

const baseUrl = process.env.API_BASE_URL ?? 'http://localhost:4000';
const parallelism = Number(process.env.SMOKE_PARALLELISM ?? 5);
const iterations = Number(process.env.SMOKE_ITERATIONS ?? 10);
const jitterMs = Number(process.env.SMOKE_JITTER_MS ?? 200);

const endpoints: Endpoint[] = [
  { path: '/health', method: 'GET' },
  {
    path: '/auth/register',
    method: 'POST',
    payload: () => {
      const id = randomUUID();
      return {
        email: `smoke-${id}@example.com`,
        password: 'LoadSmokePass!234',
        displayName: `Smoke Tester ${id.slice(0, 6)}`,
      };
    },
  },
  {
    path: '/auth/login',
    method: 'POST',
    payload: {
      email: 'smoke-user@example.com',
      password: 'LoadSmokePass!234',
    },
  },
] as const;

type EndpointConfig = (typeof endpoints)[number];

const metrics = {
  total: 0,
  success: 0,
  failure: 0,
  latencies: [] as number[],
};

function resolvePayload(endpoint: EndpointConfig) {
  if (typeof endpoint.payload === 'function') {
    return endpoint.payload();
  }
  return endpoint.payload;
}

async function ensureBaselineUser() {
  const loginConfig = endpoints.find((endpoint) => endpoint.path === '/auth/login');
  if (!loginConfig) {
    return;
  }

  const registerPayload = {
    email: 'smoke-user@example.com',
    password: 'LoadSmokePass!234',
    displayName: 'Load Smoke User',
  };

  await fetch(`${baseUrl}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(registerPayload),
  }).catch(() => {
    /* ignore duplicate errors */
  });
}

async function hitEndpoint(endpoint: EndpointConfig) {
  const url = new URL(endpoint.path, baseUrl).toString();
  const payload = resolvePayload(endpoint);
  const started = performance.now();

  try {
    const response = await fetch(url, {
      method: endpoint.method,
      headers:
        endpoint.method === 'POST'
          ? {
              'Content-Type': 'application/json',
            }
          : undefined,
      body: payload ? JSON.stringify(payload) : undefined,
    });

    const latency = performance.now() - started;
    metrics.total += 1;
    metrics.latencies.push(latency);

    if (response.ok) {
      metrics.success += 1;
    } else {
      metrics.failure += 1;
      console.warn(`⚠️  ${endpoint.method} ${endpoint.path} responded with ${response.status}`);
    }
  } catch (error) {
    metrics.total += 1;
    metrics.failure += 1;
    console.error(`⛔️  ${endpoint.method} ${endpoint.path} failed`, error);
  }
}

async function runWorker(workerId: number) {
  for (let i = 0; i < iterations; i += 1) {
    for (const endpoint of endpoints) {
      await hitEndpoint(endpoint);
      if (jitterMs > 0) {
        await delay(Math.random() * jitterMs);
      }
    }
  }

  console.log(`Worker ${workerId} finished ${iterations * endpoints.length} requests.`);
}

function percentile(p: number, values: number[]) {
  if (values.length === 0) {
    return 0;
  }

  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.ceil((p / 100) * sorted.length) - 1;
  return sorted[Math.max(index, 0)];
}

async function main() {
  console.log(`🔥 Load smoke against ${baseUrl}`);
  console.log(
    `Running ${parallelism} workers • ${iterations} iterations • ${endpoints.length} endpoints`,
  );

  await ensureBaselineUser();

  const workers = Array.from({ length: parallelism }, (_, index) => runWorker(index + 1));
  await Promise.all(workers);

  const avgLatency =
    metrics.latencies.reduce((sum, latency) => sum + latency, 0) / metrics.latencies.length || 0;

  console.log('✅ Load smoke completed');
  console.table({
    total: metrics.total,
    success: metrics.success,
    failure: metrics.failure,
    'p95 latency (ms)': percentile(95, metrics.latencies).toFixed(2),
    'avg latency (ms)': avgLatency.toFixed(2),
  });

  if (metrics.failure > 0) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error('Unexpected load smoke failure', error);
  process.exitCode = 1;
});
