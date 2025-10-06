# main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from sqlalchemy import func
from database import Base, engine, get_db
from models import User
from schemas import LoginRequest, Token
from auth import verify_password, create_access_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(title="Kavosh API", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/auth/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.strip()
    user = db.query(User).filter(func.lower(User.email) == email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(subject=str(user.id))
    return Token(access_token=token)


# run app uvicorn main:app --host 127.0.0.1 --port 9000 --reload  اجرای مستقیم روی همین ماشین با پورت 9000
# docker run -d --name kavosh-backend -p 9000:9000 --env-file .env.docker --restart unless-stopped kavosh-backend ساخت ایمیج
# login : {
#     "email": "admin@SteelAlborz.com",
#     "password": "123456"
# }
