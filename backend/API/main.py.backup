from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth_router, ruta_router, simulacion_router
from .dependencies import create_tables

app = FastAPI(title="Simulador de Rutas API", version="1.0.0")

# CORS para React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crea tablas si no existen (opcional, ya que usas schema.sql)
create_tables()

# Registra routers
app.include_router(auth_router, prefix="/auth", tags=["Autenticación"])
app.include_router(ruta_router, prefix="/ruta", tags=["Rutas"])
app.include_router(simulacion_router, prefix="/simulacion", tags=["Simulación"])

@app.get("/")
def root():
    return {"message": "API del Simulador de Rutas funcionando"}