import { OutcomeVerificationStatus } from '@prisma/client';
import { IsEnum, IsOptional, IsString, IsUUID, MaxLength } from 'class-validator';

export class RecordOutcomeVerificationDto {
  @IsEnum(OutcomeVerificationStatus)
  status!: OutcomeVerificationStatus;

  @IsOptional()
  @IsUUID()
  escrowId?: string;

  @IsOptional()
  evidence?: Record<string, unknown>;

  @IsOptional()
  @IsString()
  @MaxLength(2000)
  notes?: string;

  @IsOptional()
  @IsUUID()
  reviewerId?: string;
}
