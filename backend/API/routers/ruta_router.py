from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from ..dependencies import get_db
from backend.API.models import Vehiculo, Pedido
from backend.core.dijkstra import obtener_ruta_multiparada, obtener_incidencias_trafico, construir_grafo_logico
from backend.core.calculos import calcular_pedido
from backend.core.simulacion import generar_mapa_visual

router = APIRouter()
load_dotenv()

class RutaRequest(BaseModel):
    origen: str  # Ej: "UMB Cuautitlán"
    destino: str  # Ej: "Zócalo CDMX"
    pedido_id: Optional[int] = None  # Opcional

class RutaResponse(BaseModel):
    distancia_km: float
    tiempo_estimado_min: float
    costo_total: float
    emisiones_kg: float
    incidentes_trafico: int
    pasos: list[Dict[str, Any]]
    mapa_html: str = "mapa_generado.html"
    mensaje: str

@router.post("/calcular", response_model=RutaResponse)
async def calcular_ruta_optimizada(
    request: RutaRequest, 
    db: Session = Depends(get_db)
):
    """
    Endpoint principal que integra:
    1. MapQuest API para ruta
    2. Dijkstra para grafo lógico
    3. Cálculos de costo/consumo
    4. Generación de mapa
    """
    
    # 1. Obtener API Key de MapQuest
    MAPQUEST_API_KEY = os.getenv("MAPQUEST_API_KEY")
    if not MAPQUEST_API_KEY or MAPQUEST_API_KEY == "TU_API_KEY_MAPQUEST_AQUI":
        raise HTTPException(
            status_code=500, 
            detail="Configura la API Key de MapQuest en el archivo .env"
        )
    
    # 2. Obtener ruta de MapQuest
    print(f"Calculando ruta: {request.origen} -> {request.destino}")
    maniobras, geometria, bbox = obtener_datos_ruta(
        MAPQUEST_API_KEY, 
        request.origen, 
        request.destino
    )
    
    if not maniobras:
        raise HTTPException(
            status_code=400, 
            detail="No se pudo calcular la ruta. Verifica las direcciones."
        )
    
    # 3. Obtener incidentes de tráfico
    incidentes = obtener_incidencias_trafico(MAPQUEST_API_KEY, bbox)
    
    # 4. Construir grafo lógico con Dijkstra
    grafo = construir_grafo_logico(maniobras)
    
    # 5. Calcular distancia total
    distancia_total = sum(grafo[u][v]['weight'] for u, v in grafo.edges())
    
    # 6. Preparar lista de pasos para respuesta
    pasos = []
    for node_id in grafo.nodes():
        node_data = grafo.nodes[node_id]
        pasos.append({
            "orden": node_id,
            "descripcion": node_data['desc'],
            "coordenadas": node_data['pos']
        })
    
    # 7. Si hay pedido_id, calcular métricas detalladas
    costo_total = 0
    emisiones_kg = 0
    tiempo_estimado_min = (distancia_total / 40) * 60  # Default 40 km/h
    
    if request.pedido_id:
        try:
            resultado = calcular_pedido(request.pedido_id, distancia_total)
            
            if "error" in resultado:
                mensaje = f"Pedido: {resultado['error']}. Mostrando solo ruta."
            else:
                costo_total = resultado["costo_total"]
                emisiones_kg = resultado["emisiones_kg"]
                tiempo_estimado_min = resultado["tiempo_estimado_min"]
                mensaje = f"Ruta calculada para pedido #{request.pedido_id}"
        except Exception as e:
            mensaje = f"Error en cálculo de pedido: {str(e)}"
    else:
        mensaje = "Ruta calculada exitosamente (sin pedido asociado)"
    
    # 8. Generar mapa visual
    try:
        generar_mapa_visual(grafo, geometria, incidentes, "mapa_generado.html")
        mapa_msg = "Mapa generado: mapa_generado.html"
    except Exception as e:
        mapa_msg = f"Error generando mapa: {str(e)}"
    
    # 9. Retornar respuesta estructurada
    return {
        "distancia_km": round(distancia_total, 2),
        "tiempo_estimado_min": round(tiempo_estimado_min, 1),
        "costo_total": round(costo_total, 2),
        "emisiones_kg": round(emisiones_kg, 2),
        "incidentes_trafico": len(incidentes),
        "pasos": pasos,
        "mapa_html": "mapa_generado.html",
        "mensaje": f"{mensaje} | {mapa_msg}"
    }

@router.get("/pedido/{pedido_id}")
def obtener_calculos_pedido(
    pedido_id: int, 
    distancia_km: float
):
    """Endpoint separado solo para cálculos de pedido"""
    resultado = calcular_pedido(pedido_id, distancia_km)
    return resultado