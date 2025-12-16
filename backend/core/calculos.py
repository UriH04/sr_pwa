import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ==========================================================
# 1. Conexión a la base de datos (usando pymysql)
# ==========================================================

# Obtener configuración desde variables de entorno
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "simpwadb")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "mysqlumb")

# Usar pymysql en lugar de mysqlconnector
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)


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

    # Si no hay motor de base de datos, usar valores por defecto
    if engine is None:
        return {
            "pedido": id_pedido,
            "vehiculo": "gasolina",
            "distancia_km": distancia_km,
            "peso_kg": 10.0,
            "volumen_m3": 1.0,
            "consumo": distancia_km / 12,  # 12 km por litro
            "costo_total": distancia_km / 12 * 22.5,  # $22.5 por litro
            "emisiones_kg": distancia_km / 12 * 2.31,
            "tiempo_estimado_min": (distancia_km / 40) * 60,
            "mensaje": "Usando valores por defecto (BD no disponible)"
        }

    # --------------------------
    # 1) OBTENER DATOS DEL PEDIDO
    # --------------------------
    query_pedido = text("""
        SELECT id_vehiculo, peso_kg, volumen_m3
        FROM pedidos
        WHERE id_pedido = :id
    """)

    try:
        with engine.connect() as conn:
            pedido = conn.execute(query_pedido, {"id": id_pedido}).fetchone()
    except Exception as e:
        print(f"Error consultando pedido: {e}")
        return {"error": f"Error de base de datos: {str(e)}"}

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

    try:
        with engine.connect() as conn:
            vehiculo = conn.execute(query_vehiculo, {"id": id_vehiculo}).fetchone()
    except Exception as e:
        print(f"Error consultando vehículo: {e}")
        return {"error": f"Error de base de datos: {str(e)}"}

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