import { IsOptional, IsString, IsUUID } from 'class-validator';

export class ServiceDeliveryDto {
  @IsUUID()
  negotiationId!: string;

  @IsUUID()
  responderAgentId!: string;

  @IsOptional()
  result?: Record<string, unknown>;

  @IsOptional()
  evidence?: Record<string, unknown>;

  @IsOptional()
  @IsString()
  notes?: string;
}

