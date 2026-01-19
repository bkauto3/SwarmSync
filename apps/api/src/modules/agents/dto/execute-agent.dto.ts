import { InitiatorType } from '@prisma/client';
import { IsEnum, IsJSON, IsNumber, IsOptional, IsPositive, IsUUID, MaxLength } from 'class-validator';

export class ExecuteAgentDto {
  @IsUUID()
  initiatorId!: string;

  @IsOptional()
  @IsEnum(InitiatorType)
  initiatorType?: InitiatorType;

  @IsOptional()
  @IsUUID()
  initiatorAgentId?: string;

  @IsOptional()
  @IsUUID()
  sourceWalletId?: string;

  @IsOptional()
  @IsJSON()
  input: string = '{}';

  @IsOptional()
  @MaxLength(200)
  jobReference?: string;

  @IsOptional()
  @IsPositive()
  @IsNumber()
  budget?: number;
}
