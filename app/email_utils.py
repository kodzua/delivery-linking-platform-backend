from fastapi_mail import FastMail, MessageSchema
from app.email_config import conf

async def send_otp_email(email : str, otp : str) :
    message = MessageSchema(
        subject = "your verification code",
        recipients = [email],          
        body = f"your code is : {otp}",  
        subtype = "plain"          
    )
    fm = FastMail(conf)             
    await fm.send_message(message)  

async def send_reset_password_email(email : str, reset_link : str) :
    message = MessageSchema(
        subject = "reset your password",
        recipients = [email],
        body = f"click the link below to reset your password :\n\n{reset_link}\n\n this link expires in 15 minutes.",  
        subtype = "plain"
    )
    fm = FastMail(conf)
    await fm.send_message(message)