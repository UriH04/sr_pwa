from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from jose import JWTError, jwt
from datetime import datetime, timedelta

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
def login(request: LoginRequest):
    # Placeholder: Verifica en BD (por ahora, mock)
    if request.username == "admin" and request.password == "pass":
        token = create_access_token({"sub": request.username, "role": "admin"})
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Credenciales inválidas")

def get_current_user(token: str = Depends(lambda: None)):  # Placeholder para dependencias
    # Aquí validarías el token JWT y devolverías el usuario
    return {"username": "admin", "role": "admin"}  # Mock