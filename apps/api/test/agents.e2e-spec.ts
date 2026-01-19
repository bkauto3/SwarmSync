import { INestApplication } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { Test } from '@nestjs/testing';
import request from 'supertest';

import { AuthModule } from '../src/modules/auth/auth.module.js';

describe('Auth endpoints (e2e)', () => {
  let app: INestApplication;

  beforeAll(async () => {
    process.env.JWT_SECRET ??= 'test-secret';

    const moduleRef = await Test.createTestingModule({
      imports: [
        ConfigModule.forRoot({
          isGlobal: true,
          ignoreEnvFile: true,
        }),
        AuthModule,
      ],
    }).compile();

    app = moduleRef.createNestApplication();
    await app.init();
  });

  afterAll(async () => {
    await app?.close();
  });

  it('registers and logs in a user', async () => {
    const payload = {
      email: 'qa@example.com',
      password: 'StrongPass123!',
      displayName: 'QA Agent',
    };

    const registerResponse = await request(app.getHttpServer())
      .post('/auth/register')
      .send(payload)
      .expect(201);

    expect(registerResponse.body).toMatchObject({
      user: {
        email: payload.email,
        displayName: payload.displayName,
      },
      accessToken: expect.any(String),
      expiresIn: 3600,
    });

    const loginResponse = await request(app.getHttpServer())
      .post('/auth/login')
      .send({ email: payload.email, password: payload.password })
      .expect(201);

    expect(loginResponse.body).toMatchObject({
      user: {
        email: payload.email,
        displayName: payload.displayName,
      },
      accessToken: expect.any(String),
      expiresIn: 3600,
    });
  });
});
