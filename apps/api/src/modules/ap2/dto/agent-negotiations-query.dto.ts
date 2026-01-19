import { IsOptional, IsUUID } from 'class-validator';

export class AgentNegotiationsQueryDto {
  @IsOptional()
  @IsUUID()
  agentId?: string;
}

