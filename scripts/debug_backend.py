#!/usr/bin/env python3
"""
DEBUG COMPLETO DEL BACKEND - Simulador de Rutas PWA

"""

import sys
import os
from pathlib import Path

def print_section(title, char="="):
    line = char * 60
    print(f"\n{line}")
    print(f" {title}")
    print(f"{line}")

def main():
    print_section("DIAGNOSTICO COMPLETO DEL BACKEND")
    
    current_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(current_dir))
    
    # 1. ESTRUCTURA
    print_section("1. ESTRUCTURA DE CARPETAS", "-")
    
    folders = [
        ("backend", "Backend principal"),
        ("backend/core", "Logica core"),
        ("backend/API", "API FastAPI"),
        ("backend/API/routers", "Routers"),
        ("database", "Base de datos"),
        ("frontend", "Frontend"),
    ]
    
    for folder, desc in folders:
        path = current_dir / folder
        print(f"[{'OK' if path.exists() else 'ERROR'}] {desc}: {folder}")
    
    # 2. ARCHIVOS
    print_section("2. ARCHIVOS CRITICOS", "-")
    
    files = [
        (".env", "Variables entorno"),
        ("requirements.txt", "Dependencias"),
        ("backend/core/dijkstra.py", "Logica Dijkstra"),
        ("backend/core/calculos.py", "Calculos logisticos"),
        ("backend/core/simulacion.py", "Generacion mapas"),
        ("backend/API/main.py", "API FastAPI"),
        ("backend/API/dependencies.py", "Conexion BD"),
        ("database/schema_mysql.sql", "Esquema BD"),
    ]
    
    for file_path, desc in files:
        full_path = current_dir / file_path
        if full_path.exists():
            size = full_path.stat().st_size
            print(f"[OK]  {desc:25} ({size} bytes)")
        else:
            print(f"[ERROR] {desc:25} NO ENCONTRADO")
    
    # 3. DEPENDENCIAS
    print_section("3. DEPENDENCIAS PYTHON", "-")
    
    modules = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("sqlalchemy", "SQLAlchemy"),
        ("requests", "Requests"),
        ("networkx", "NetworkX"),
        ("folium", "Folium"),
        ("pydantic", "Pydantic"),
        ("pymysql", "PyMySQL"),
        ("dotenv", "python-dotenv"),
    ]
    
    for mod, name in modules:
        try:
            __import__(mod)
            print(f"[OK]  {name:15} instalado")
        except ImportError:
            print(f"[ERROR] {name:15} FALTA")
    
    # 4. IMPORTS PROPIOS
    print_section("4. IMPORTS DE MODULOS", "-")
    
    try:
        from backend.core.dijkstra import obtener_ruta_multiparada
        print("[OK]  backend.core.dijkstra")
    except Exception as e:
        print(f"[ERROR] dijkstra: {str(e)[:50]}")
    
    try:
        from backend.core.calculos import calcular_pedido
        print("[OK]  backend.core.calculos")
    except Exception as e:
        print(f"[ERROR] calculos: {str(e)[:50]}")
    
    try:
        from backend.API.main import app
        print(f"[OK]  backend.API.main: {app.title}")
    except Exception as e:
        print(f"[ERROR] main.py: {str(e)[:50]}")
    
    # 5. VARIABLES ENTORNO
    print_section("5. VARIABLES DE ENTORNO", "-")
    
    env_file = current_dir / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_file)
        
        key = os.getenv("MAPQUEST_API_KEY")
        db = os.getenv("DB_NAME")
        
        if key:
            print(f"MAPQUEST_API_KEY: [OK] ({len(key)} caracteres)")
        else:
            print(f"MAPQUEST_API_KEY: [ERROR] NO DEFINIDA")
        
        if db:
            print(f"DB_NAME: [OK] {db}")
        else:
            print(f"DB_NAME: [ERROR] NO DEFINIDA")
    else:
        print("[ERROR] Archivo .env no encontrado")
    
    # 6. RESUMEN
    print_section("RESUMEN", "=")
    print("SI TODO OK, INICIA API CON:")
    print("   uvicorn backend.API.main:app --reload --port 8000")
    print("")
    print("DOCUMENTACION: http://localhost:8000/docs")
    print("")
    print("ENDPOINT PRINCIPAL: POST /ruta/calcular")

if __name__ == "__main__":
    main()
