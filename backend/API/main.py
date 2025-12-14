from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth_router, ruta_router, simulacion_router



# Crear app FastAPI
app = FastAPI(title="Simulador de Rutas API", version="1.0")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, restringe esto
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear tablas en BD (si no existen)
try:
    from .dependencies import create_tables
    create_tables()
    print("✅ Tablas creadas/verificadas")
except Exception as e:
    print(f"⚠️  Error al crear tablas: {e}")

# Registra routers
app.include_router(auth_router.router, prefix="/auth", tags=["Autenticación"])
app.include_router(ruta_router.router, prefix="/ruta", tags=["Rutas"])
app.include_router(simulacion_router.router, prefix="/simulacion", tags=["Simulación"])

@app.get("/")
def root():
    return {"message": "Sistema de Rutas UMB API", "status": "activo"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0"}