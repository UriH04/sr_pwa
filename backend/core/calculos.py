def calcular_metricas(distancia, vehiculo):
    tiempo = distancia / vehiculo.velocidad_promedio_km * 60
    costo = distancia * vehiculo.costo_mantenimiento_km
    energia = distancia / vehiculo.rendimiento_electrico if vehiculo.tipo == 'electrico' else 0
    return {"tiempo": tiempo, "costo": costo, "energia": energia}
