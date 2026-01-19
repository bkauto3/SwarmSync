import { Module } from '@nestjs/common';
import { ScheduleModule } from '@nestjs/schedule';

import { NotificationSchedulerService } from './notification-scheduler.service.js';
import { DatabaseModule } from '../database/database.module.js';

@Module({
  imports: [DatabaseModule, ScheduleModule.forRoot()],
  providers: [NotificationSchedulerService],
  exports: [NotificationSchedulerService],
})
export class NotificationsModule {}

