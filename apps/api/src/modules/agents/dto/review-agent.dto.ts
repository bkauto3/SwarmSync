import { AgentStatus, ReviewStatus } from '@prisma/client';
import { IsEnum, IsOptional, IsString, IsUUID, MaxLength } from 'class-validator';

export class ReviewAgentDto {
  @IsUUID()
  reviewerId!: string;

  @IsEnum(ReviewStatus)
  reviewStatus!: ReviewStatus;

  @IsEnum(AgentStatus)
  targetStatus!: AgentStatus;

  @IsOptional()
  @IsString()
  @MaxLength(500)
  notes?: string;
}
