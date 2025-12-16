from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from jose import JWTError, jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..dependencies import get_db
from ..models import Usuario

router = APIRouter()

# Modelo para login
class LoginRequest(BaseModel):
    email: str
    password: str

# Modelo para response
class TokenResponse(BaseModel):
    access_token: str
    token_type: str

# Usa una clave secreta más segura en producción
SECRET_KEY = "colocar_llave_aquí"
ALGORITHM = "HS256"

def create_access_token(data: dict):
    """Crea token JWT"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Endpoint de login"""
    user = db.query(Usuario).filter(Usuario.email == request.email).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    # NOTA: En producción, usa hashing real (bcrypt, argon2)
    if user.password_hash != request.password:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    token = create_access_token({"sub": user.email, "rol": user.rol})
    return {"access_token": token, "token_type": "bearer"}