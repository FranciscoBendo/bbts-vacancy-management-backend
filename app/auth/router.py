from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.auth.schemas import RegisterRequest, LoginRequest, TokenResponse, UserOut
from app.auth.service import create_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=TokenResponse, status_code=201, summary="Cadastrar novo usuário")
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    user = User(name=body.name, email=body.email, password_hash=hash_password(body.password), role=body.role)
    db.add(user); db.commit(); db.refresh(user)
    return TokenResponse(access_token=create_token(user.id), user_id=user.id, name=user.name, role=user.role)

@router.post("/login", response_model=TokenResponse, summary="Login com email e senha")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    return TokenResponse(access_token=create_token(user.id), user_id=user.id, name=user.name, role=user.role)

@router.get("/me", response_model=UserOut, summary="Usuário autenticado")
def me(current_user: User = Depends(get_current_user)):
    return current_user
