from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext

SECRET_KEY = "my-super-secret-key-this-is-tot-rand-123-321" # we should remember not to hardcode this
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # a week

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password) :
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password) :
    return pwd_context.hash(password[:72])

def create_access_token(data : dict) :
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes = ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm = ALGORITHM)
    return encoded_jwt

def decode_access_token(token : str) :
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload