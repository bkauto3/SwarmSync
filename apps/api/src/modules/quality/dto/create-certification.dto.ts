import { IsOptional, IsString, IsUUID, MaxLength } from 'class-validator';

export class CreateCertificationDto {
  @IsUUID()
  agentId!: string;

  @IsOptional()
  @IsUUID()
  checklistId?: string;

  @IsOptional()
  evidence?: Record<string, unknown>;

  @IsOptional()
  @IsString()
  @MaxLength(2000)
  notes?: string;
}
