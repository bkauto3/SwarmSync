import { CollaborationStatus } from '@prisma/client';
import { IsEnum, IsObject, IsOptional, IsUUID } from 'class-validator';

export class RespondCollaborationRequestDto {
  @IsUUID()
  requestId!: string;

  @IsEnum(CollaborationStatus)
  status!: CollaborationStatus;

  @IsOptional()
  @IsObject()
  counterPayload?: Record<string, unknown>;
}
