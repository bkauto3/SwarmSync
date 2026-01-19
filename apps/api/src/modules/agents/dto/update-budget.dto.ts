import { BudgetApprovalMode } from '@prisma/client';
import { IsBoolean, IsEnum, IsNumber, IsOptional, Min, ValidateIf } from 'class-validator';

export class UpdateAgentBudgetDto {
  @IsOptional()
  @IsNumber()
  @Min(0)
  monthlyLimit?: number;

  @IsOptional()
  @ValidateIf((_, value) => value !== null)
  @IsNumber()
  @Min(0)
  perTransactionLimit?: number | null;

  @IsOptional()
  @ValidateIf((_, value) => value !== null)
  @IsNumber()
  @Min(0)
  approvalThreshold?: number | null;

  @IsOptional()
  @IsEnum(BudgetApprovalMode)
  approvalMode?: BudgetApprovalMode;

  @IsOptional()
  @IsBoolean()
  autoReload?: boolean;
}
