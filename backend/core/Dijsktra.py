from ..API.models import ConexionMapa

def calcular_ruta(id_origen, id_destino, db):
    conexion = db.query(ConexionMapa).filter(
        ConexionMapa.id_nodo_origen == id_origen,
        ConexionMapa.id_nodo_destino == id_destino
    ).first()
    if conexion:
        return {"ruta": [id_origen, id_destino], "distancia": float(conexion.distancia_km)}
    return {"ruta": [], "distancia": 0.0}

#Prueba para Git