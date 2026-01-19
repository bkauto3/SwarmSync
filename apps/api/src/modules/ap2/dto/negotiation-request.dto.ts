import {
  IsNumber,
  IsObject,
  IsOptional,
  IsPositive,
  IsString,
  IsUUID,
} from 'class-validator';

export class NegotiationRequestDto {
  @IsUUID()
  requesterAgentId!: string;

  @IsUUID()
  responderAgentId!: string;

  @IsString()
  requestedService!: string;

  @IsNumber()
  @IsPositive()
  budget!: number;

  @IsOptional()
  @IsObject()
  requirements?: Record<string, unknown>;

  @IsOptional()
  @IsString()
  notes?: string;
}

