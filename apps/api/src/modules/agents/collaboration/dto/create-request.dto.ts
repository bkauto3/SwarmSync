import { IsObject, IsOptional, IsUUID } from 'class-validator';

export class CreateCollaborationRequestDto {
  @IsUUID()
  requesterAgentId!: string;

  @IsUUID()
  responderAgentId!: string;

  @IsOptional()
  @IsObject()
  payload?: Record<string, unknown>;
}
