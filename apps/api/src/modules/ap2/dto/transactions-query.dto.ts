import { IsUUID } from 'class-validator';

export class AgentTransactionsQueryDto {
  @IsUUID()
  agentId!: string;
}

