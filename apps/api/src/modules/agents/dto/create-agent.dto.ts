import { AgentVisibility } from '@prisma/client';
import {
  ArrayNotEmpty,
  IsArray,
  IsEnum,
  IsInt,
  IsObject,
  IsOptional,
  IsString,
  Length,
  Min,
} from 'class-validator';

export class CreateAgentDto {
  @IsString()
  @Length(3, 60)
  name!: string;

  @IsString()
  @Length(10, 500)
  description!: string;

  @IsArray()
  @ArrayNotEmpty()
  @IsString({ each: true })
  categories!: string[];

  @IsArray()
  @IsString({ each: true })
  tags: string[] = [];

  @IsString()
  @Length(3, 120)
  pricingModel!: string;

  @IsEnum(AgentVisibility)
  visibility: AgentVisibility = AgentVisibility.PUBLIC;

  @IsString()
  @Length(1, 64)
  creatorId!: string;

  @IsOptional()
  @IsInt()
  @Min(0)
  basePriceCents?: number;

  @IsOptional()
  @IsObject()
  inputSchema?: Record<string, unknown>;

  @IsOptional()
  @IsObject()
  outputSchema?: Record<string, unknown>;

  @IsOptional()
  @IsString()
  ap2Endpoint?: string;
}
