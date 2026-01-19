import { IsEnum, IsOptional, IsString, IsUUID } from 'class-validator';

export enum Ap2CompletionStatus {
  AUTHORIZED = 'AUTHORIZED',
  SETTLED = 'SETTLED',
  FAILED = 'FAILED',
}

export class CompleteAp2PaymentDto {
  @IsUUID()
  escrowId!: string;

  @IsEnum(Ap2CompletionStatus)
  status!: Ap2CompletionStatus;

  @IsOptional()
  @IsString()
  failureReason?: string;
}
