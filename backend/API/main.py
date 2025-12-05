from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import ruta_router, simulacion_router, auth_router  # Importa routers (ver abajo)

app = FastAPI(title="Simulador de Rutas API", version="1.0.0")

# CORS para conectar con React (ajusta origins si es necesario)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Puerto típico de React
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra routers
app.include_router(auth_router, prefix="/auth", tags=["Autenticación"])
app.include_router(ruta_router, prefix="/ruta", tags=["Rutas"])
app.include_router(simulacion_router, prefix="/simulacion", tags=["Simulación"])

@app.get("/")
def root():
    return {"message": "API del Simulador de Rutas funcionando"}