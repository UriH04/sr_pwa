#!/usr/bin/env python3
"""
VERIFICACION RAPIDA - 30 segundos
"""

import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(current_dir))

print("VERIFICACION RAPIDA DEL BACKEND")
print("-" * 40)

# 1. Archivos esenciales
files = [
    (".env", "Variables entorno"),
    ("backend/API/main.py", "API principal"),
    ("backend/core/dijkstra.py", "Logica rutas"),
    ("backend/API/dependencies.py", "Conexion BD"),
]

all_ok = True
for file_path, desc in files:
    full_path = current_dir / file_path
    if full_path.exists():
        print(f"[OK]  {desc}")
    else:
        print(f"[ERROR] {desc} - FALTANTE")
        all_ok = False

# 2. Imports
print("\nVERIFICANDO IMPORTS...")
try:
    from backend.API.main import app
    print(f"[OK]  FastAPI: {app.title}")
except Exception as e:
    print(f"[ERROR] FastAPI: {e}")
    all_ok = False

#try:
 #   from backend.core.dijkstra import obtener_datos_ruta
 #   print("[OK]  Modulo dijkstra")
#except Exception as e:
 #   print(f"[ERROR] Dijkstra: {e}")
 #   all_ok = False

# 3. Resultado
print("\n" + "="*40)
if all_ok:
    print("[OK]  BACKEND LISTO")
    print("Comando para iniciar:")
    print("uvicorn backend.API.main:app --reload --port 8000")
else:
    print("[ERROR] PROBLEMAS DETECTADOS")
    print("Ejecuta debug_backend.py para diagnostico completo")
