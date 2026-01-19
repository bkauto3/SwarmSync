import { IsNumber, IsOptional, IsPositive, IsString } from 'class-validator';

export class FundWalletDto {
  @IsPositive()
  @IsNumber()
  amount!: number;

  @IsOptional()
  @IsString()
  reference?: string;
}
