import { Type } from 'class-transformer';
import {
  ArrayNotEmpty,
  IsArray,
  IsNumber,
  IsOptional,
  IsPositive,
  IsString,
  IsUUID,
  MaxLength,
  ValidateNested,
} from 'class-validator';

class WorkflowStepDto {
  @IsUUID()
  agentId!: string;

  @IsOptional()
  @IsString()
  jobReference?: string;

  @IsOptional()
  @IsNumber()
  @IsPositive()
  budget?: number;

  @IsOptional()
  input?: Record<string, unknown>;
}

export class CreateWorkflowDto {
  @IsString()
  @MaxLength(120)
  name!: string;

  @IsOptional()
  @IsString()
  @MaxLength(500)
  description?: string;

  @IsUUID()
  creatorId!: string;

  @IsNumber()
  @IsPositive()
  budget!: number;

  @IsArray()
  @ArrayNotEmpty()
  @ValidateNested({ each: true })
  @Type(() => WorkflowStepDto)
  steps!: WorkflowStepDto[];
}

export type WorkflowStepInput = WorkflowStepDto;
