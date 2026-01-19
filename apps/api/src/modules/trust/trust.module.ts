import { Module } from '@nestjs/common';

import { TrustController } from './trust.controller.js';
import { TrustService } from './trust.service.js';

@Module({
  controllers: [TrustController],
  providers: [TrustService],
  exports: [TrustService],
})
export class TrustModule {}
