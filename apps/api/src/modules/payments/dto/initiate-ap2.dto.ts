import {
  IsEnum,
  IsNumber,
  IsObject,
  IsOptional,
  IsPositive,
  IsString,
  IsUUID,
} from 'class-validator';

export enum Ap2PaymentPurpose {
  AGENT_HIRE = 'AGENT_HIRE',
  SERVICE_FEE = 'SERVICE_FEE',
  REFUND = 'REFUND',
}

export class InitiateAp2PaymentDto {
  @IsUUID()
  sourceWalletId!: string;

  @IsUUID()
  destinationWalletId!: string;

  @IsPositive()
  @IsNumber()
  amount!: number;

  @IsEnum(Ap2PaymentPurpose)
  purpose!: Ap2PaymentPurpose;

  @IsOptional()
  @IsString()
  memo?: string;

  @IsOptional()
  @IsObject()
  metadata?: Record<string, unknown>;
}
