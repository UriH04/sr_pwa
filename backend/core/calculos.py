from sqlalchemy import create_engine, text

# ==========================================================
# 1. Conexión a la base de datos
# ==========================================================

engine = create_engine("mysql+mysqlconnector://root:Mysqldb20@localhost/logistica")


# ==========================================================
# 2. FUNCIÓN PRINCIPAL: obtiene los datos y calcula todo
# ==========================================================

def calcular_pedido(id_pedido, distancia_km):
    """
    Recibe:
      - id_pedido: int   → pedido registrado en la base de datos
      - distancia_km: float → distancia calculada por Dijkstra (ahorita la ignoramos y la pasas manual)

    Regresa:
      - JSON con consumo, costo, emisiones, etc.
    """

    # --------------------------
    # 1) OBTENER DATOS DEL PEDIDO
    # --------------------------
    query_pedido = text("""
        SELECT id_vehiculo, peso_kg, volumen_m3
        FROM pedidos
        WHERE id_pedido = :id
    """)

    with engine.connect() as conn:
        pedido = conn.execute(query_pedido, {"id": id_pedido}).fetchone()

    if pedido is None:
        return {"error": "El pedido no existe"}

    id_vehiculo = pedido.id_vehiculo
    peso = float(pedido.peso_kg)
    volumen = float(pedido.volumen_m3)

    # --------------------------
    # 2) OBTENER DATOS DEL VEHÍCULO
    # --------------------------

    query_vehiculo = text("""
        SELECT tipo, rendimiento_gasolina, rendimiento_electrico,
               precio_gasolina, precio_kwh, factor_emisiones_gasolina,
               factor_emisiones_electrico, velocidad_promedio_kmh
        FROM vehiculos
        WHERE id_vehiculo = :id
    """)

    with engine.connect() as conn:
        vehiculo = conn.execute(query_vehiculo, {"id": id_vehiculo}).fetchone()

    if vehiculo is None:
        return {"error": "El vehículo asignado no existe"}

    tipo = vehiculo.tipo
    vel = vehiculo.velocidad_promedio_kmh

    # --------------------------
    # 3) CÁLCULOS DEPENDIENDO DEL VEHÍCULO
    # --------------------------

    if tipo == "gasolina":
        rendimiento = vehiculo.rendimiento_gasolina   # km por litro
        consumo = distancia_km / rendimiento
        costo = consumo * vehiculo.precio_gasolina
        emisiones = consumo * vehiculo.factor_emisiones_gasolina

    elif tipo == "hibrido":
        rendimiento = vehiculo.rendimiento_gasolina
        rendimiento_elec = vehiculo.rendimiento_electrico

        consumo_gas = distancia_km / rendimiento
        consumo_kwh = distancia_km / rendimiento_elec

        consumo = {"litros": consumo_gas, "kWh": consumo_kwh}

        costo = (consumo_gas * vehiculo.precio_gasolina) + \
                (consumo_kwh * vehiculo.precio_kwh)

        emisiones = (consumo_gas * vehiculo.factor_emisiones_gasolina) + \
                    (consumo_kwh * vehiculo.factor_emisiones_electrico)

    elif tipo == "electrico":
        rendimiento = vehiculo.rendimiento_electrico  # km/kWh
        consumo = distancia_km / rendimiento
        costo = consumo * vehiculo.precio_kwh
        emisiones = consumo * vehiculo.factor_emisiones_electrico

    else:
        return {"error": "Tipo de vehículo no válido"}

    # --------------------------
    # 4) CÁLCULO DE TIEMPO APROXIMADO
    # --------------------------
    tiempo_horas = distancia_km / vel
    tiempo_min = tiempo_horas * 60

    # --------------------------
    # 5) FORMAR EL JSON DE RESPUESTA
    # --------------------------

    resultado = {
        "pedido": id_pedido,
        "vehiculo": tipo,
        "distancia_km": distancia_km,
        "peso_kg": peso,
        "volumen_m3": volumen,
        "consumo": consumo,
        "costo_total": costo,
        "emisiones_kg": emisiones,
        "tiempo_estimado_min": tiempo_min
    }

    return resultado