import { Type } from 'class-transformer';
import {
  IsEnum,
  IsNumber,
  IsObject,
  IsOptional,
  IsPositive,
  IsString,
  IsUUID,
  ValidateNested,
} from 'class-validator';

export enum NegotiationResponseStatus {
  ACCEPTED = 'ACCEPTED',
  REJECTED = 'REJECTED',
  COUNTERED = 'COUNTERED',
}

class NegotiationTermsDto {
  [key: string]: unknown;
}

export class RespondNegotiationDto {
  @IsUUID()
  negotiationId!: string;

  @IsUUID()
  responderAgentId!: string;

  @IsEnum(NegotiationResponseStatus)
  status!: NegotiationResponseStatus;

  @IsOptional()
  @IsNumber()
  @IsPositive()
  price?: number;

  @IsOptional()
  @IsString()
  estimatedDelivery?: string;

  @IsOptional()
  @IsObject()
  @ValidateNested()
  @Type(() => NegotiationTermsDto)
  terms?: Record<string, unknown>;

  @IsOptional()
  @IsString()
  notes?: string;
}

