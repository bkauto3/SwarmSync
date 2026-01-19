import { IsEmail, IsNotEmpty, MinLength } from 'class-validator';

export class RegisterUserDto {
  @IsEmail()
  email!: string;

  @IsNotEmpty()
  @MinLength(3)
  displayName!: string;

  @IsNotEmpty()
  @MinLength(8)
  password!: string;
}
