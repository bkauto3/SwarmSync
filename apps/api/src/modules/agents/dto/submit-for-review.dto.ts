import { IsOptional, IsString, IsUUID, MaxLength } from 'class-validator';

export class SubmitForReviewDto {
  @IsUUID()
  reviewerId!: string;

  @IsOptional()
  @IsString()
  @MaxLength(500)
  notes?: string;
}
