import { IsOptional, IsString, IsUUID } from 'class-validator';

export class ReleaseEscrowDto {
  @IsUUID()
  escrowId!: string;

  @IsOptional()
  @IsString()
  memo?: string;
}
