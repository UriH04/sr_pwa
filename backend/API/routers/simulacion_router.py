from fastapi import APIRouter, Depends
from pydantic import BaseModel
from core.simulacion import simular_movimiento  # Placeholder

router = APIRouter()

class SimulacionRequest(BaseModel):
    ruta: list[str]  # De /ruta

class SimulacionResponse(BaseModel):
    posiciones: list[dict]  # Lista de {"x": float, "y": float, "tiempo": float}

@router.post("/", response_model=SimulacionResponse)
def simular(request: SimulacionRequest):
    # Placeholder: Llama a simulator.py
    # posiciones = simular_movimiento(request.ruta)
    posiciones = simular_movimiento(request.ruta)
    return {"posiciones": posiciones}
