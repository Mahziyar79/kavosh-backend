# main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session as DBSession
from contextlib import asynccontextmanager
from sqlalchemy import func
from typing import List
from database import Base, engine, get_db
from models import User,Session as ChatSession,Message
from schemas import LoginRequest, RegisterRequest, Token, SessionCreate, SessionOut,MessageCreate, MessageOut,SessionUpdate
from auth import verify_password, hash_password, create_access_token, get_current_user

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


@app.post("/auth/register", response_model=Token, status_code=201)
def register(payload: RegisterRequest, db: DBSession = Depends(get_db)):
    email = payload.email.strip()
    exists = db.query(User).filter(func.lower(User.email) == email.lower()).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(subject=str(user.id))
    return Token(access_token=token)

@app.post("/auth/login", response_model=Token)
def login(payload: LoginRequest, db: DBSession = Depends(get_db)):
    email = payload.email.strip()
    user = db.query(User).filter(func.lower(User.email) == email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(subject=str(user.id))
    return Token(access_token=token)


@app.get("/auth/me")
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}


@app.post("/sessions", response_model=SessionOut, status_code=201)
def create_session(
    payload: SessionCreate,
    db: DBSession  = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    s = ChatSession(title=payload.title, user_id=current_user.id)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@app.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    db: DBSession  = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rows = (db.query(ChatSession)
              .filter(ChatSession.user_id == current_user.id)
              .order_by(ChatSession.created_at.desc())
              .all())
    return rows


@app.patch("/sessions/{session_id}", response_model=SessionOut)
def update_session_title(
    session_id: int,
    payload: SessionUpdate,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    selectedSession = (db.query(ChatSession)
           .filter(ChatSession.id == session_id,
                   ChatSession.user_id == current_user.id)
           .first())
    if not selectedSession:
        raise HTTPException(status_code=404, detail="Session not found")

    if payload.title is None:
        raise HTTPException(status_code=400, detail="Nothing to update")

    new_title = payload.title.strip()
    if new_title == "":
        raise HTTPException(status_code=422, detail="Title cannot be empty")

    selectedSession.title = new_title
    db.add(selectedSession)
    db.commit()
    db.refresh(selectedSession)
    return selectedSession

@app.post("/sessions/{session_id}/messages", response_model=MessageOut, status_code=201)
def add_message(
    session_id: int,
    payload: MessageCreate,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # user_id فقط برای role=user ست می‌شود
    msg = Message(
        session_id=session.id,
        role=payload.role,
        user_id=current_user.id if payload.role == "user" else None,
        content=payload.content
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg

@app.get("/sessions/{session_id}/messages", response_model=List[MessageOut])
def list_messages(
    session_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
):
    # ensure the session belongs to the current user
    exists = db.query(ChatSession.id).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Session not found")

    rows = (db.query(Message)
              .filter(Message.session_id == session_id)
              .order_by(Message.created_at.asc())
              .limit(limit)
              .offset(offset)
              .all())
    return rows

@app.delete("/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # بررسی مالکیت
    s = (db.query(ChatSession)
            .filter(ChatSession.id == session_id,
                    ChatSession.user_id == current_user.id)
            .first())

    if not s:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(s)
    db.commit()

    return 

# uvicorn main:app --host 127.0.0.1 --port 9000 --reload  اجرای مستقیم روی همین ماشین با پورت 9000
# docker run -d --name kavosh-backend -p 9000:9000 --env-file .env.docker --restart unless-stopped kavosh-backend ساخت ایمیج
# login : {
#     "email": "admin@SteelAlborz.com",
#     "password": "123456"
# }
