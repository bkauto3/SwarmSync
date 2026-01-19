import { OutcomeType } from '@prisma/client';
import { IsEnum, IsOptional, IsString, IsUUID, MaxLength } from 'class-validator';

export class CreateServiceAgreementDto {
  @IsUUID()
  agentId!: string;

  @IsOptional()
  @IsUUID()
  buyerId?: string;

  @IsOptional()
  @IsUUID()
  workflowId?: string;

  @IsOptional()
  @IsUUID()
  escrowId?: string;

  @IsEnum(OutcomeType)
  outcomeType!: OutcomeType;

  @IsString()
  @MaxLength(500)
  targetDescription!: string;
}
