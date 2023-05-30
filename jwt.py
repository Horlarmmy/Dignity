from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta
import models
from db import SessionLocal
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Change this as per your requirement



class TokenManager:
    def __init__(self, secret_key, algorithm):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_token(self, username: str, expires_delta: timedelta = None):
        to_encode = {"sub": str(username)}
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def decode_token(self, token: str):
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload["sub"]
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")


token_manager = TokenManager(SECRET_KEY, ALGORITHM)


def create_tok(user):
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = token_manager.create_token(user.id, expires_delta=access_token_expires)
    return access_token

def decode_t(token):
    user_id = token_manager.decode_token(token)
    return user_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
