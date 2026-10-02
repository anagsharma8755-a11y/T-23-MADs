import hashlib, secrets
from datetime import datetime, timedelta, timezone
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select, delete
from sqlalchemy.orm import Session as DBSession
from .config import settings
from .db import get_db
from .models import Session, User

ph = PasswordHasher()
def hash_password(password: str) -> str: return ph.hash(password)
def verify_password(password: str, value: str) -> bool:
    try: return ph.verify(value, password)
    except VerifyMismatchError: return False
def digest(value: str) -> str: return hashlib.sha256(value.encode()).hexdigest()

def create_session(db: DBSession, user: User, response: Response):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours)
    db.add(Session(user_id=user.id, token_hash=digest(token), csrf_hash=digest(csrf), expires_at=expires)); db.commit()
    response.set_cookie("muletrace_session", token, httponly=True, secure=settings.cookie_secure, samesite="strict", max_age=settings.session_ttl_hours*3600, path="/")
    response.set_cookie("muletrace_csrf", csrf, httponly=False, secure=settings.cookie_secure, samesite="strict", max_age=settings.session_ttl_hours*3600, path="/")

def clear_session(db: DBSession, request: Request, response: Response):
    token=request.cookies.get("muletrace_session")
    if token: db.execute(delete(Session).where(Session.token_hash==digest(token))); db.commit()
    response.delete_cookie("muletrace_session",path="/"); response.delete_cookie("muletrace_csrf",path="/")

def current_user(request: Request, db: DBSession=Depends(get_db)) -> User:
    token=request.cookies.get("muletrace_session")
    if not token: raise HTTPException(401,"Authentication required")
    row=db.scalar(select(Session).where(Session.token_hash==digest(token)))
    expires = row.expires_at.replace(tzinfo=timezone.utc) if row and row.expires_at.tzinfo is None else (row.expires_at if row else None)
    if not row or expires <= datetime.now(timezone.utc): raise HTTPException(401,"Session expired")
    user=db.get(User,row.user_id)
    if not user or not user.active: raise HTTPException(401,"Account disabled")
    request.state.session=row
    return user

def require_csrf(request: Request, user: User=Depends(current_user)) -> User:
    if request.method not in {"GET","HEAD","OPTIONS"}:
        value=request.headers.get("X-CSRF-Token","")
        if not value or digest(value)!=request.state.session.csrf_hash: raise HTTPException(403,"Invalid CSRF token")
    return user
def supervisor(user: User=Depends(require_csrf)) -> User:
    if user.role!="supervisor": raise HTTPException(403,"Supervisor role required")
    return user

