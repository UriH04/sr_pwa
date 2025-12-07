from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from jose import JWTError, jwt
from datetime import datetime, timedelta
from ..dependencies import det_db
from ..models import Usuario

router = APIRouter()

# Modelo para login
class LoginRequest(BaseModel):
    username: str
    password: str

# Modelo para response
class TokenResponse(BaseModel):
    access_token: str
    token_type: str

SECRET_KEY = "tu_clave_secreta_aqui"  # Cambia en producción
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db=Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.email == request.email).first()
    if not user or user.password_hash != request.password:  # Placeholder: hashea passwords en producción
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    token = create_access_token({"sub": user.email, "rol": user.rol})
    return {"access_token": token, "token_type": "bearer"}

def get_current_user(token: str = Depends(lambda: None)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return{"email": payload.get("sub"), "rol": payload.get("rol")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")
    