from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..dependencies import get_db  # Conexión a BD 
from..models import NodoMapa, Vehiculo, RutaOptimizada
from ...core.Dijsktra import calcular_ruta  # Placeholder: importa tu función real
from ...core.calculos import calcular_metricas

router = APIRouter()

class RutaRequest(BaseModel):
    origen: str  # Ej: "A"
    destino: str  # Ej: "B"
    vehiculo: str  # "gasolina", "hibrido", "electrico"

class RutaResponse(BaseModel):
    ruta: list[str]  # Lista de nodos: ["A", "C", "B"]
    distancia: float
    tiempo: float
    costo: float
    energia: float

@router.post("/", response_model=RutaResponse, dependencies=[Depends(get_current_user)])
def generar_ruta(request: RutaRequest, db=Depends(get_db)):
    origen = db.query(NodoMapa).filter(NodoMapa.nombre == request.origen).first()
    destino = db.query(NodoMapa).filter(NodoMapa.nombre == request.destino).first()
    vehiculo = db.query(Vehiculo).filter(Vehiculo.tipo == request.vehiculo).first()
    
    if not origen or not destino or not vehiculo:
        raise HTTPException(status_code=404, detail="Datos no encontrados")
    
    ruta_result = calcular_ruta(origen.id_nodo, destino.id_nodo, db)
    metricas = calcular_metricas(ruta_result["distancia"], vehiculo)
    
    nueva_ruta = RutaOptimizada(
        id_pedido=1, id_usuario=1, id_vehiculo=vehiculo.id_vehiculo,
        origen_lat=origen.latitud, origen_lng=origen.longitud,
        ruta_calculada=ruta_result["ruta"], distancia_km=ruta_result["distancia"],
        tiempo_estimado_min=metricas["tiempo"], costo_estimado=metricas["costo"],
        energia_usada_kwh=metricas["energia"], modo="simulacion"
    )
    db.add(nueva_ruta)
    db.commit()
    
    return {
        "ruta": ruta_result["ruta"],
        "distancia": ruta_result["distancia"],
        "tiempo": metricas["tiempo"],
        "costo": metricas["costo"],
        "energia": metricas["energia"]
    }