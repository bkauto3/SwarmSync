import { IsBoolean, IsNumber, IsOptional, IsString, IsUUID, MaxLength } from 'class-validator';

export class RunEvaluationDto {
  @IsUUID()
  agentId!: string;

  @IsOptional()
  @IsUUID()
  scenarioId?: string;

  @IsOptional()
  @IsString()
  @MaxLength(200)
  scenarioName?: string;

  @IsOptional()
  @IsString()
  @MaxLength(120)
  vertical?: string;

  @IsOptional()
  input?: Record<string, unknown>;

  @IsOptional()
  expected?: Record<string, unknown>;

  @IsOptional()
  tolerances?: Record<string, unknown>;

  @IsOptional()
  @IsBoolean()
  passed?: boolean;

  @IsOptional()
  @IsNumber()
  latencyMs?: number;

  @IsOptional()
  @IsNumber()
  cost?: number;

  @IsOptional()
  logs?: Record<string, unknown>;

  @IsOptional()
  @IsUUID()
  certificationId?: string;
}
