from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum

class Token(BaseModel) :
    access_token : str
    token_type : str

class TokenData(BaseModel) :
    email : Optional[str] = None

class AccountType(str, Enum) :
    personal = "personal"
    business = "business"

class EmailRequest(BaseModel) :
    email : EmailStr

class VerifyRequest(BaseModel) :
    email : EmailStr
    otp : str

class UserCreate(BaseModel) :
    name : str
    email : EmailStr
    password : str
    # account_type : AccountType
    phone_number : str

class UserLogin(BaseModel) :
    email : EmailStr
    password : str

class PasswordResetRequest(BaseModel) :
    email : EmailStr

class PasswordResetConfirm(BaseModel) :
    token : str
    new_password : str