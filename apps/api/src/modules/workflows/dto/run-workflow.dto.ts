import { IsUUID } from 'class-validator';

export class RunWorkflowDto {
  @IsUUID()
  initiatorUserId!: string;
}
