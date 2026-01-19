import { CertificationStatus } from '@prisma/client';
import { IsEnum, IsOptional, IsString, IsUUID, MaxLength } from 'class-validator';

export class UpdateCertificationStatusDto {
  @IsOptional()
  @IsEnum(CertificationStatus)
  status?: CertificationStatus;

  @IsOptional()
  @IsUUID()
  reviewerId?: string;

  @IsOptional()
  evidence?: Record<string, unknown>;

  @IsOptional()
  @IsString()
  @MaxLength(2000)
  notes?: string;

  @IsOptional()
  expiresAt?: Date;
}
