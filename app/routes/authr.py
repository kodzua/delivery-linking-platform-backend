from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime, timezone
from app import models, schemas, security
from app.database import get_db
from app.email_utils import send_otp_email, send_reset_password_email
from app.security import create_access_token, get_password_hash
import random
import secrets
import os

router = APIRouter(
    prefix = "/auth",
    tags = ["authentication"]
)

VERIFICATION_WINDOW_HOURS = 48

def _is_deactivated(user) -> bool :
    if user.is_verified :
        return False
    if user.created_at is None :
        return False
    created_at = user.created_at
    if created_at.tzinfo is None :
        created_at = created_at.replace(tzinfo = timezone.utc)
    return (datetime.now(timezone.utc) - created_at) > timedelta(hours = VERIFICATION_WINDOW_HOURS)

def _verification_deadline_iso(user) -> str | None :
    if user.created_at is None :
        return None
    created_at = user.created_at
    if created_at.tzinfo is None :
        created_at = created_at.replace(tzinfo = timezone.utc)
    return (created_at + timedelta(hours = VERIFICATION_WINDOW_HOURS)).isoformat()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user : schemas.UserCreate, db : Session = Depends(get_db)) :
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing :
        if not existing.is_verified :
            if _is_deactivated(existing) :
                otp_code = random.randint(100000, 999999)
                existing.otp_code = otp_code
                existing.otp_expires = datetime.now(timezone.utc) + timedelta(minutes=5)
                db.commit()
                try :
                    await send_otp_email(existing.email, str(otp_code))
                except Exception as e :
                    print("email error :", e)
                raise HTTPException(status_code = status.HTTP_403_FORBIDDEN, detail = "account_deactivated")
            else :
                raise HTTPException(status_code = status.HTTP_400_BAD_REQUEST, detail = "email is already registered but not yet verified. please check your inbox.")
        else :
            raise HTTPException(status_code = status.HTTP_400_BAD_REQUEST, detail = "email is already registered")
    hashed_password = security.get_password_hash(user.password)
    new_user = models.User(
        name = user.name,
        email = user.email,
        password_hash = hashed_password,
        phone_number = user.phone_number
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    otp_code = random.randint(100000, 999999)
    new_user.otp_code = otp_code
    new_user.otp_expires = datetime.now(timezone.utc) + timedelta(minutes=5)
    db.commit()
    try :
        await send_otp_email(new_user.email, str(otp_code))
    except Exception as e :
        print("email error :", e)
    access_token = security.create_access_token(data = {"user_id" : new_user.id})
    return {
        "status" : "success",
        "message" : "account created. please verify your email within 48 hours.",
        "access_token" : access_token,
        "token_type" : "bearer",
        "name" : new_user.name,
        "is_verified" : False,
        "verification_deadline" : _verification_deadline_iso(new_user)
    }

@router.post("/login")
def login(form_data : OAuth2PasswordRequestForm = Depends(), db : Session = Depends(get_db)) :
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user :
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail = "invalid credentials")
    if not security.verify_password(form_data.password, user.password_hash) :
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail = "invalid credentials")
    if not user.is_verified :
        if _is_deactivated(user) :
            raise HTTPException(status_code = status.HTTP_403_FORBIDDEN, detail = "account_deactivated")
        access_token = security.create_access_token(data = {"user_id" : user.id})
        return {
            "access_token" : access_token,
            "token_type" : "bearer",
            "name" : user.name,
            "is_verified" : False,
            "verification_deadline" : _verification_deadline_iso(user)
        }
    access_token = security.create_access_token(data = {"user_id" : user.id})
    return {
        "access_token" : access_token,
        "token_type" : "bearer",
        "name" : user.name,
        "is_verified" : True,
        "verification_deadline" : None
    }

@router.post("/send-otp")
async def send_otp(request : schemas.EmailRequest, db : Session = Depends(get_db)) :
    user = db.query(models.User).filter(models.User.email == request.email).first()
    if not user :
        raise HTTPException(status_code = 404, detail = "user not found")
    otp_code = random.randint(100000, 999999)
    user.otp_code = otp_code
    user.otp_expires = datetime.now(timezone.utc) + timedelta(minutes=5)
    db.commit()
    try :
        await send_otp_email(user.email, str(otp_code))
    except Exception as e :
        print("email error :", e)
        raise HTTPException(status_code = 500, detail = str(e))
    return {"message" : "otp sent to your email"}

@router.post("/verify-otp")
def verify_otp(data : schemas.VerifyRequest, db : Session = Depends(get_db)) :
    user = db.query(models.User).filter(models.User.email == data.email).first()
    if not user:
        raise HTTPException(status_code = 404, detail = "user not found")
    if user.otp_code is None:
        raise HTTPException(status_code = 400, detail = "no otp has been requested for this email")
    if str(user.otp_code) != str(data.otp):
        raise HTTPException(status_code = 400, detail = "the code you entered is incorrect")
    if user.otp_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code = 400, detail = "otp expired")
    user.otp_code = None
    user.is_verified = True
    db.commit()
    access_token = create_access_token(data = {"user_id" : user.id})
    return {
        "message" : "email verified successfully",
        "access_token" : access_token,
        "token_type" : "bearer",
        "name" : user.name,
        "is_verified" : True
    }

@router.post("/forgot-password")
async def forgot_password(request : schemas.PasswordResetRequest, db : Session = Depends(get_db)) :
    user = db.query(models.User).filter(models.User.email == request.email).first()
    if not user :
        raise HTTPException(status_code = 404, detail = "user not found")
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(minutes = 15)
    db.commit()
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    reset_link = f"{frontend_url}/reset-password?token={token}"
    try :
        await send_reset_password_email(user.email, reset_link)
    except Exception as e :
        raise HTTPException(status_code = 500, detail = "failed to send email")
    return {"message" : "reset link sent to your email!"}

@router.post("/reset-password")
async def reset_password(request: schemas.PasswordResetConfirm, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.reset_token == request.token).first()
    if not user:
        raise HTTPException(status_code=400, detail="invalid token")
    if user.reset_token_expires:
        expires = user.reset_token_expires.replace(tzinfo=timezone.utc)
    else:
        expires = None
    if not expires or expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="token expired")
    if len(request.new_password) < 8:
        raise HTTPException(status_code=400, detail="password too weak")
    hashed_password = get_password_hash(request.new_password)
    user.password_hash = hashed_password
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    return {"message": "password reset successful"}