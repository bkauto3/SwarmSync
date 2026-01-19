import { VerificationStatus } from '@prisma/client';
import { IsEnum, IsOptional, IsString, IsUUID, MaxLength } from 'class-validator';

export class UpdateVerificationDto {
  @IsUUID()
  agentId!: string;

  @IsUUID()
  reviewerId!: string;

  @IsEnum(VerificationStatus)
  status!: VerificationStatus;

  @IsOptional()
  @IsString()
  @MaxLength(500)
  notes?: string;
}
