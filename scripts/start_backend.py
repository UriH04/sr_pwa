#!/usr/bin/env python3
"""
Script para iniciar el backend fácilmente
"""
import subprocess
import sys
import os

def main():
    print("🚀 Iniciando Sistema de Rutas UMB API")
    print("=" * 50)
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists("backend/API/main.py"):
        print("❌ Error: No se encuentra backend/API/main.py")
        print("   Ejecuta desde el directorio raíz del proyecto")
        return 1
    
    # Comando para iniciar uvicorn
    cmd = [
        sys.executable, "-m", "uvicorn",
        "backend.API.main:app",
        "--reload",
        "--port", "8000",
        "--host", "0.0.0.0"
    ]
    
    print(f"📡 API disponible en: http://localhost:8000")
    print(f"📚 Documentación: http://localhost:8000/docs")
    print("=" * 50)
    print("Presiona Ctrl+C para detener")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Servidor detenido")
    return 0

if __name__ == "__main__":
    sys.exit(main())