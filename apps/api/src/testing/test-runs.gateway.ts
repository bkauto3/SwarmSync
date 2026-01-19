import { Logger } from '@nestjs/common';
import {
  WebSocketGateway,
  WebSocketServer,
  SubscribeMessage,
  OnGatewayConnection,
  OnGatewayDisconnect,
} from '@nestjs/websockets';
import Redis from 'ioredis';
import { Server, Socket } from 'socket.io';

@WebSocketGateway({
  cors: {
    origin: process.env.WEB_URL || 'http://localhost:3000',
    credentials: true,
  },
  namespace: '/test-runs',
})
export class TestRunsGateway implements OnGatewayConnection, OnGatewayDisconnect {
  @WebSocketServer()
  server: Server;

  private readonly logger = new Logger(TestRunsGateway.name);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private redis: any;
  private subscribers: Map<string, Set<string>> = new Map(); // runId -> Set of socket IDs

  constructor() {
    // Initialize Redis subscriber only if Redis is configured
    // Railway provides REDIS_URL in format: redis://default:password@host:port or rediss://default:password@host:port (TLS)
    const redisUrl = process.env.REDIS_URL;
    let parsedRedisUrl: URL | null = null;
    if (redisUrl) {
      try {
        parsedRedisUrl = new URL(redisUrl);
        this.logger.log(`Parsed REDIS_URL: host=${parsedRedisUrl.hostname}, port=${parsedRedisUrl.port}, hasPassword=${!!parsedRedisUrl.password}`);
      } catch (error) {
        this.logger.warn(`Invalid REDIS_URL provided: ${error instanceof Error ? error.message : 'Unknown error'}, falling back to REDIS_HOST/PORT`);
      }
    }
    const redisHost = process.env.REDIS_HOST ?? parsedRedisUrl?.hostname;
    const redisPort = parseInt(process.env.REDIS_PORT ?? parsedRedisUrl?.port ?? '6379', 10);
    // Extract password from URL (Railway format: redis://default:password@host:port)
    // URL.password contains the password part after the colon
    const redisPassword = process.env.REDIS_PASSWORD ?? parsedRedisUrl?.password;
    
    // Log Redis configuration for debugging
    if (redisHost) {
      this.logger.log(`Redis configuration: host=${redisHost}, port=${redisPort}, hasPassword=${!!redisPassword}, fromUrl=${!!parsedRedisUrl}`);
    }
    if (redisHost) {
      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        this.redis = new (Redis as any)({
          host: redisHost,
          port: redisPort,
          password: redisPassword,
          retryStrategy: () => null, // Don't retry on connection failure
          maxRetriesPerRequest: null,
          lazyConnect: true,
        });

        // Handle connection errors gracefully
        this.redis.on('error', (err: Error) => {
          this.logger.warn(`Redis connection error (WebSocket gateway): ${err.message}`);
        });

        // Subscribe to all test-run channels
        this.redis
          .connect()
          .then(() => {
            this.redis.psubscribe('test-run:*');
            this.logger.log('Redis connected for test run WebSocket gateway');
          })
          .catch((err: Error) => {
            this.logger.warn(`Failed to connect to Redis (WebSocket gateway): ${err.message}`);
          });

        this.redis.on('pmessage', (pattern, channel, message) => {
          const runId = channel.replace('test-run:', '');
          const progress = JSON.parse(message);

          // Emit to all sockets subscribed to this run
          const socketIds = this.subscribers.get(runId);
          if (socketIds) {
            socketIds.forEach((socketId) => {
              this.server.to(socketId).emit('test-run-progress', progress);
            });
          }
        });
      } catch (err) {
        this.logger.warn(`Failed to initialize Redis (WebSocket gateway): ${err instanceof Error ? err.message : 'Unknown error'}`);
      }
    } else {
      this.logger.warn('Redis not configured - WebSocket test run updates will not work');
    }
  }

  handleConnection(client: Socket) {
    this.logger.log(`Client connected: ${client.id}`);
  }

  handleDisconnect(client: Socket) {
    this.logger.log(`Client disconnected: ${client.id}`);

    // Remove from all subscriptions
    for (const [runId, socketIds] of this.subscribers.entries()) {
      socketIds.delete(client.id);
      if (socketIds.size === 0) {
        this.subscribers.delete(runId);
      }
    }
  }

  @SubscribeMessage('subscribe')
  handleSubscribe(client: Socket, payload: { runId: string }) {
    const { runId } = payload;

    if (!this.subscribers.has(runId)) {
      this.subscribers.set(runId, new Set());
    }

    this.subscribers.get(runId)!.add(client.id);
    client.join(`test-run:${runId}`);

    this.logger.log(`Client ${client.id} subscribed to test run ${runId}`);
  }

  @SubscribeMessage('unsubscribe')
  handleUnsubscribe(client: Socket, payload: { runId: string }) {
    const { runId } = payload;

    const socketIds = this.subscribers.get(runId);
    if (socketIds) {
      socketIds.delete(client.id);
      if (socketIds.size === 0) {
        this.subscribers.delete(runId);
      }
    }

    client.leave(`test-run:${runId}`);
    this.logger.log(`Client ${client.id} unsubscribed from test run ${runId}`);
  }
}

