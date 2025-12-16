from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
from datetime import datetime  # Importamos datetime
import math  # Para la función haversine
from pydantic import BaseModel
from typing import List, Optional

from ..dependencies import get_db
from backend.API.models import Vehiculo, Pedido
from backend.core.dijkstra import obtener_ruta_multiparada, obtener_incidencias_trafico, construir_grafo_logico
from backend.core.calculos import calcular_pedido
from backend.core.simulacion import generar_mapa_visual, traducir_detalles_trafico

router = APIRouter()
load_dotenv()

# --- MODELOS ---

class RutaRequest(BaseModel):
    origen: str  # Ej: "UMB Cuautitlán"
    destino: str  # Ej: "Zócalo CDMX"
    pedido_id: Optional[int] = None  # Opcional



class RutaMultiparadaRequest(BaseModel):
    lugares: List[str]
    optimizar: Optional[bool] = True

class EventoTrafico(BaseModel):
    type: str  # Tipo interno: construction, event, hazard, etc.
    tipo_texto: str  # Texto descriptivo: Construcción, Evento, Peligro, etc.
    title: str  # Título corto
    description: str  # Descripción completa
    location: str  # Coordenadas
    severidad: int  # 1-5
    icono: str = "exclamation-circle"  # Icono de FontAwesome
    color: str = "gray"  # Color para visualización
    nivel_riesgo: str = "bajo"  # bajo, medio, alto
    hora_inicio: Optional[str] = None
    hora_fin: Optional[str] = None
    impacto: int = 0  # Número de vehículos afectados
    distancia_a_ruta: Optional[float] = None  # Distancia a la ruta principal en km

class InstruccionRuta(BaseModel):
    orden: int
    descripcion: str
    distancia: str
    distancia_km: float
    coordenadas: tuple

class RutaResponse(BaseModel):
    distancia_km: float
    tiempo_estimado_min: float
    costo_total: float
    emisiones_kg: float
    incidentes_trafico: int
    eventos_trafico: List[EventoTrafico]
    instrucciones: List[InstruccionRuta]
    pasos: List[Dict[str, Any]]
    mapa_html: str = "mapa_generado.html"
    mensaje: str
    estadisticas: Dict[str, Any]

# --- FUNCIONES AUXILIARES ---

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calcula distancia entre dos puntos en km usando fórmula de Haversine"""
    # Radio de la Tierra en km
    R = 6371.0
    
    # Convertir a radianes
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Diferencia de coordenadas
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    
    # Fórmula de Haversine
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def procesar_incidentes_trafico(incidentes: List[Dict]) -> List[EventoTrafico]:
    """Procesa los incidentes de tráfico para la respuesta de la API"""
    eventos_procesados = []
    
    # Mapeo completo de tipos de MapQuest
    TIPOS_EVENTOS = {
        1: {"type": "construction", "texto": "Construcción", "icono": "wrench", "color": "orange"},
        2: {"type": "event", "texto": "Evento", "icono": "calendar", "color": "purple"},
        3: {"type": "hazard", "texto": "Peligro", "icono": "exclamation-triangle", "color": "red"},
        4: {"type": "congestion", "texto": "Congestión", "icono": "traffic-light", "color": "red"},
        5: {"type": "accident", "texto": "Accidente", "icono": "car-crash", "color": "darkred"},
        6: {"type": "transit", "texto": "Tránsito", "icono": "bus", "color": "blue"},
        7: {"type": "misc", "texto": "Misceláneo", "icono": "info-circle", "color": "gray"},
        8: {"type": "news", "texto": "Noticias", "icono": "newspaper", "color": "cadetblue"},
        9: {"type": "planned", "texto": "Planificado", "icono": "clipboard-check", "color": "green"},
        10: {"type": "closure", "texto": "Cierre", "icono": "road", "color": "black"},
        11: {"type": "weather", "texto": "Clima", "icono": "cloud-rain", "color": "lightblue"}
    }
    
    for inc in incidentes:
        lat = inc.get('lat', 0)
        lng = inc.get('lng', 0)
        tipo_num = inc.get('type', 0)
        severidad = inc.get('severity', 1)
        impacto = inc.get('impacting', 0)  # Número de vehículos afectados
        hora_inicio = inc.get('startTime', '')
        hora_fin = inc.get('endTime', '')
        
        # Obtener información del tipo
        tipo_info = TIPOS_EVENTOS.get(tipo_num, {
            "type": "other", 
            "texto": "Otro", 
            "icono": "question-circle", 
            "color": "gray"
        })
        
        # Traducir descripción
        desc_original = inc.get('fullDesc', inc.get('shortDesc', 'Sin detalles disponibles'))
        desc_traducida = traducir_detalles_trafico(desc_original)
        
        # Crear título y descripción detallada
        titulo = f"{tipo_info['texto']}: {desc_traducida[:60]}..." if len(desc_traducida) > 60 else f"{tipo_info['texto']}: {desc_traducida}"
        
        # Información adicional
        info_adicional = []
        if hora_inicio:
            info_adicional.append(f"Inicio: {hora_inicio}")
        if hora_fin:
            info_adicional.append(f"Fin estimado: {hora_fin}")
        if impacto and impacto > 0:
            info_adicional.append(f"Vehículos afectados: {impacto}")
        
        descripcion_completa = desc_traducida
        if info_adicional:
            descripcion_completa += f"\n\n{chr(10).join(info_adicional)}"
        
        # Calcular nivel de riesgo basado en severidad e impacto
        nivel_riesgo = "bajo"
        if severidad >= 3:
            nivel_riesgo = "alto" if severidad >= 4 else "medio"
        
        eventos_procesados.append(EventoTrafico(
            type=tipo_info['type'],
            tipo_texto=tipo_info['texto'],
            title=titulo,
            description=descripcion_completa,
            location=f"{lat:.4f}, {lng:.4f}",
            severidad=severidad,
            icono=tipo_info['icono'],
            color=tipo_info['color'],
            nivel_riesgo=nivel_riesgo,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            impacto=impacto
        ))
    
    return eventos_procesados

def procesar_maniobras_instrucciones(maniobras: List[Dict]) -> List[InstruccionRuta]:
    """Procesa las maniobras de la ruta para crear instrucciones detalladas"""
    instrucciones = []
    
    for i, man in enumerate(maniobras):
        descripcion = man.get('narrative', 'Continuar')
        distancia_km = man.get('distance', 0)
        distancia_formateada = f"{distancia_km:.1f} km"
        
        # Obtener coordenadas si están disponibles
        start_point = man.get('startPoint', {})
        coordenadas = (start_point.get('lat', 0), start_point.get('lng', 0))
        
        instrucciones.append(InstruccionRuta(
            orden=i + 1,
            descripcion=descripcion,
            distancia=distancia_formateada,
            distancia_km=distancia_km,
            coordenadas=coordenadas
        ))
    
    return instrucciones

def obtener_estadisticas_eventos(eventos: List[EventoTrafico]) -> Dict[str, Any]:
    """Genera estadísticas detalladas sobre los eventos de tráfico"""
    if not eventos:
        return {}
    
    # Conteo por tipo
    conteo_por_tipo = {}
    severidad_promedio = 0
    eventos_alto_riesgo = 0
    
    for evento in eventos:
        # Contar por tipo
        tipo = evento.tipo_texto
        conteo_por_tipo[tipo] = conteo_por_tipo.get(tipo, 0) + 1
        
        # Sumar severidad para promedio
        severidad_promedio += evento.severidad
        
        # Contar eventos de alto riesgo
        if evento.nivel_riesgo == "alto":
            eventos_alto_riesgo += 1
    
    severidad_promedio = round(severidad_promedio / len(eventos), 1) if eventos else 0
    
    return {
        "total": len(eventos),
        "por_tipo": conteo_por_tipo,
        "severidad_promedio": severidad_promedio,
        "eventos_alto_riesgo": eventos_alto_riesgo,
        "tipos_diferentes": len(conteo_por_tipo),
        "impacto_total": sum(e.impacto for e in eventos if e.impacto)
    }

# --- ENDPOINTS ---

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
    5. Procesamiento de eventos de tráfico
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
    maniobras, geometria, bbox, orden = obtener_ruta_multiparada(
        MAPQUEST_API_KEY, 
        [request.origen, request.destino]
    )
    
    if not maniobras:
        raise HTTPException(
            status_code=400, 
            detail="No se pudo calcular la ruta. Verifica las direcciones."
        )
    
    # 3. Obtener incidentes de tráfico
    incidentes = []
    if bbox:
        try:
            incidentes = obtener_incidencias_trafico(MAPQUEST_API_KEY, bbox)
        except Exception as e:
            print(f"Advertencia al obtener tráfico: {e}")
    
    # 4. Procesar eventos de tráfico
    eventos_procesados = procesar_incidentes_trafico(incidentes)
    
    # 5. Procesar instrucciones de la ruta
    instrucciones = procesar_maniobras_instrucciones(maniobras)
    
    # 6. Construir grafo lógico con Dijkstra
    grafo = construir_grafo_logico(maniobras)
    
    # 7. Calcular distancia total
    distancia_total = sum(man['distance'] for man in maniobras)
    
    # 8. Preparar lista de pasos para respuesta (compatible con versión anterior)
    pasos = []
    for node_id in grafo.nodes():
        node_data = grafo.nodes[node_id]
        pasos.append({
            "orden": node_id,
            "descripcion": node_data.get('desc', 'Sin descripción'),
            "coordenadas": node_data.get('pos', (0, 0))
        })
    
    # 9. Si hay pedido_id, calcular métricas detalladas
    costo_total = 0
    emisiones_kg = 0
    tiempo_estimado_min = (distancia_total / 40) * 60  # Default 40 km/h
    
    if request.pedido_id:
        try:
            resultado = calcular_pedido(request.pedido_id, distancia_total)
            
            if "error" in resultado:
                mensaje = f"Pedido: {resultado['error']}. Mostrando solo ruta."
            else:
                costo_total = resultado.get("costo_total", 0)
                emisiones_kg = resultado.get("emisiones_kg", 0)
                tiempo_estimado_min = resultado.get("tiempo_estimado_min", tiempo_estimado_min)
                mensaje = f"Ruta calculada para pedido #{request.pedido_id}"
        except Exception as e:
            mensaje = f"Error en cálculo de pedido: {str(e)}"
    else:
        mensaje = "Ruta calculada exitosamente (sin pedido asociado)"
    
    # 10. Generar mapa visual
    try:
        generar_mapa_visual(grafo, geometria, incidentes, orden, "mapa_generado.html")
        mapa_msg = "Mapa generado: mapa_generado.html"
    except Exception as e:
        mapa_msg = f"Error generando mapa: {str(e)}"
    
    # 11. Preparar estadísticas
    estadisticas_eventos = obtener_estadisticas_eventos(eventos_procesados)
    
    estadisticas = {
        "total_steps": len(instrucciones),
        "total_events": len(eventos_procesados),
        "total_distance": f"{distancia_total:.1f} km",
        "distancia_km": distancia_total,
        "tiempo_estimado_min": tiempo_estimado_min,
        "eventos_por_tipo": {
            "traffic": len([e for e in eventos_procesados if e.type in ["congestion", "accident", "hazard"]]),
            "construction": len([e for e in eventos_procesados if e.type == "construction"]),
            "other": len([e for e in eventos_procesados if e.type not in ["congestion", "accident", "hazard", "construction"]])
        },
        **estadisticas_eventos
    }
    
    # 12. Retornar respuesta estructurada
    return RutaResponse(
        distancia_km=round(distancia_total, 2),
        tiempo_estimado_min=round(tiempo_estimado_min, 1),
        costo_total=round(costo_total, 2),
        emisiones_kg=round(emisiones_kg, 2),
        incidentes_trafico=len(eventos_procesados),
        eventos_trafico=eventos_procesados,
        instrucciones=instrucciones,
        pasos=pasos,
        mapa_html="mapa_generado.html",
        mensaje=f"{mensaje} | {mapa_msg}",
        estadisticas=estadisticas
    )

@router.get("/pedido/{pedido_id}")
def obtener_calculos_pedido(
    pedido_id: int, 
    distancia_km: float
):
    """Endpoint separado solo para cálculos de pedido"""
    resultado = calcular_pedido(pedido_id, distancia_km)
    return resultado

@router.get("/eventos/{lat}/{lng}/{radio}")
def obtener_eventos_cercanos(
    lat: float,
    lng: float,
    radio: int = 10  # Radio en kilómetros
):
    """
    Obtiene eventos de tráfico cercanos a una ubicación específica
    Útil para visualizaciones en tiempo real
    """
    MAPQUEST_API_KEY = os.getenv("MAPQUEST_API_KEY")
    if not MAPQUEST_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="API Key no configurada"
        )
    
    # Crear bounding box aproximado basado en radio
    # Aproximación: 1 grado ≈ 111 km
    radio_grados = radio / 111.0
    
    sw_lat = lat - radio_grados
    sw_lng = lng - radio_grados
    ne_lat = lat + radio_grados
    ne_lng = lng + radio_grados
    
    bbox_str = f"{sw_lat},{sw_lng},{ne_lat},{ne_lng}"
    
    try:
        incidentes = obtener_incidencias_trafico(MAPQUEST_API_KEY, bbox_str)
        eventos_procesados = procesar_incidentes_trafico(incidentes)
        
        return {
            "ubicacion": {"lat": lat, "lng": lng},
            "radio_km": radio,
            "total_eventos": len(eventos_procesados),
            "eventos": eventos_procesados
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener eventos: {str(e)}"
        )

@router.post("/analisis-trafico")
def analisis_detallado_trafico(
    request: RutaRequest,
    radio_km: int = 5,
    db: Session = Depends(get_db)
):
    """
    Análisis detallado de tráfico en una ruta específica
    Incluye predicciones, alternativas y recomendaciones
    """
    MAPQUEST_API_KEY = os.getenv("MAPQUEST_API_KEY")
    if not MAPQUEST_API_KEY:
        raise HTTPException(status_code=500, detail="API Key no configurada")
    
    try:
        # Obtener ruta
        maniobras, geometria, bbox, orden = obtener_ruta_multiparada(
            MAPQUEST_API_KEY, 
            [request.origen, request.destino]
        )
        
        if not maniobras:
            raise HTTPException(status_code=400, detail="No se pudo calcular la ruta")
        
        # Obtener incidentes
        incidentes = []
        if bbox:
            incidentes = obtener_incidencias_trafico(MAPQUEST_API_KEY, bbox)
        
        # Procesar eventos
        eventos_procesados = procesar_incidentes_trafico(incidentes)
        
        # Calcular distancia de cada evento a la ruta
        ruta_puntos = [(p[0], p[1]) for p in geometria] if geometria else []
        
        for evento in eventos_procesados:
            try:
                # Extraer coordenadas del evento
                lat_str, lng_str = evento.location.split(',')
                evento_lat = float(lat_str.strip())
                evento_lng = float(lng_str.strip())
                
                # Calcular distancia mínima a la ruta
                if ruta_puntos:
                    distancias = []
                    for punto in ruta_puntos:
                        dist = haversine_distance(
                            evento_lat, evento_lng, 
                            punto[0], punto[1]
                        )
                        distancias.append(dist)
                    
                    if distancias:
                        evento.distancia_a_ruta = min(distancias)
            except:
                evento.distancia_a_ruta = None
        
        # Filtrar eventos cercanos a la ruta
        eventos_cercanos = [
            e for e in eventos_procesados 
            if e.distancia_a_ruta is not None and e.distancia_a_ruta <= radio_km
        ]
        
        # Estadísticas detalladas
        estadisticas = obtener_estadisticas_eventos(eventos_cercanos)
        
        # Calcular tiempo adicional por eventos
        tiempo_base = (sum(m['distance'] for m in maniobras) / 40) * 60  # 40 km/h
        tiempo_adicional = 0
        
        for evento in eventos_cercanos:
            # Cada evento agrega tiempo basado en severidad y tipo
            tiempo_evento = 0
            
            if evento.severidad >= 4:
                tiempo_evento = 10  # 10 minutos por evento severo
            elif evento.severidad >= 2:
                tiempo_evento = 5   # 5 minutos por evento moderado
            
            # Eventos de construcción o cierre añaden más tiempo
            if evento.type in ["construction", "closure"]:
                tiempo_evento *= 1.5
            
            tiempo_adicional += tiempo_evento
        
        tiempo_total = tiempo_base + tiempo_adicional
        
        # Generar recomendaciones
        recomendaciones = []
        if eventos_cercanos:
            if estadisticas.get("eventos_alto_riesgo", 0) > 3:
                recomendaciones.append("Considerar ruta alterna debido a múltiples incidentes graves")
            
            eventos_construccion = [e for e in eventos_cercanos if e.type == "construction"]
            if eventos_construccion:
                recomendaciones.append(f"Hay {len(eventos_construccion)} zonas de construcción en la ruta")
            
            eventos_accidentes = [e for e in eventos_cercanos if e.type == "accident"]
            if eventos_accidentes:
                recomendaciones.append("Precaución: hay accidentes reportados en la ruta")
        
        if not eventos_cercanos:
            recomendaciones.append("Ruta libre de incidentes reportados")
        
        return {
            "ruta": {
                "origen": request.origen,
                "destino": request.destino,
                "distancia_km": round(sum(m['distance'] for m in maniobras), 2),
                "tiempo_base_min": round(tiempo_base, 1),
                "tiempo_adicional_min": round(tiempo_adicional, 1),
                "tiempo_total_min": round(tiempo_total, 1)
            },
            "eventos": {
                "totales": len(eventos_procesados),
                "cercanos": len(eventos_cercanos),
                "detalles": eventos_cercanos,
                "estadisticas": estadisticas
            },
            "recomendaciones": recomendaciones,
            "resumen_riesgo": "Alto" if estadisticas.get("eventos_alto_riesgo", 0) > 2 else 
                             "Moderado" if estadisticas.get("eventos_alto_riesgo", 0) > 0 else 
                             "Bajo"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis: {str(e)}")

@router.get("/trafico-tiempo-real/{lat}/{lng}")
def trafico_tiempo_real(
    lat: float,
    lng: float,
    radio_km: int = 10,
    tipos: str = "all"  # all, accidents, construction, congestion
):
    """
    Obtiene tráfico en tiempo real alrededor de una ubicación
    """
    MAPQUEST_API_KEY = os.getenv("MAPQUEST_API_KEY")
    if not MAPQUEST_API_KEY:
        raise HTTPException(status_code=500, detail="API Key no configurada")
    
    # Calcular bounding box
    radio_grados = radio_km / 111.0  # Aprox. 111 km por grado
    bbox_str = f"{lat - radio_grados},{lng - radio_grados},{lat + radio_grados},{lng + radio_grados}"
    
    try:
        # Obtener incidentes
        incidentes = obtener_incidencias_trafico(MAPQUEST_API_KEY, bbox_str)
        
        # Filtrar por tipo si es necesario
        if tipos != "all":
            tipo_map = {
                "accidents": [5],
                "construction": [1],
                "congestion": [4],
                "closures": [10],
                "weather": [11]
            }
            
            tipos_numeros = tipo_map.get(tipos, [])
            if tipos_numeros:
                incidentes = [i for i in incidentes if i.get('type', 0) in tipos_numeros]
        
        # Procesar eventos
        eventos = procesar_incidentes_trafico(incidentes)
        
        # Ordenar por distancia a la ubicación central
        for evento in eventos:
            try:
                lat_str, lng_str = evento.location.split(',')
                evento_lat = float(lat_str.strip())
                evento_lng = float(lng_str.strip())
                
                # Calcular distancia
                evento.distancia_km = haversine_distance(lat, lng, evento_lat, evento_lng)
            except:
                evento.distancia_km = float('inf')
        
        eventos.sort(key=lambda x: x.distancia_km)
        
        return {
            "ubicacion": {"lat": lat, "lng": lng},
            "radio_km": radio_km,
            "total_eventos": len(eventos),
            "eventos_cercanos": [e for e in eventos if e.distancia_km <= 5],
            "eventos_todos": eventos[:20],  # Limitar a 20 eventos
            "ultima_actualizacion": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo tráfico: {str(e)}")

@router.post("/prediccion-trafico")
def prediccion_trafico(
    request: RutaRequest,
    hora_salida: str = None,
    db: Session = Depends(get_db)
):
    """
    Predice condiciones de tráfico basado en hora y día
    """
    # Si no se especifica hora, usar hora actual
    if not hora_salida:
        hora_salida = datetime.now().isoformat()
    
    try:
        hora_dt = datetime.fromisoformat(hora_salida.replace('Z', '+00:00'))
        dia_semana = hora_dt.weekday()  # 0=Lunes, 6=Domingo
        hora_dia = hora_dt.hour
        
        # Patrones de tráfico típicos (simplificado)
        # Determinar factor de tráfico
        factor_trafico = 1.0  # Base
        
        if 7 <= hora_dia <= 9:
            factor_trafico = 1.5  # Hora pico mañana
        elif 17 <= hora_dia <= 19:
            factor_trafico = 1.8  # Hora pico tarde
        elif dia_semana in [4, 5]:  # Viernes, Sábado
            if 20 <= hora_dia <= 23:
                factor_trafico = 1.3  # Tráfico nocturno fin de semana
        elif dia_semana == 6:  # Domingo
            if 17 <= hora_dia <= 21:
                factor_trafico = 1.2  # Regreso dominical
        
        # Calcular ruta normal
        MAPQUEST_API_KEY = os.getenv("MAPQUEST_API_KEY")
        maniobras, geometria, bbox, orden = obtener_ruta_multiparada(
            MAPQUEST_API_KEY, 
            [request.origen, request.destino]
        )
        
        if not maniobras:
            raise HTTPException(status_code=400, detail="No se pudo calcular la ruta")
        
        distancia = sum(m['distance'] for m in maniobras)
        tiempo_normal = (distancia / 40) * 60  # 40 km/h base
        
        # Aplicar factor de tráfico
        tiempo_predicho = tiempo_normal * factor_trafico
        
        # Obtener eventos históricos/actuales para la zona
        incidentes = []
        if bbox:
            incidentes = obtener_incidencias_trafico(MAPQUEST_API_KEY, bbox)
        
        eventos_procesados = procesar_incidentes_trafico(incidentes)
        
        # Añadir tiempo por eventos actuales
        tiempo_eventos = sum(min(e.severidad * 2, 10) for e in eventos_procesados)
        tiempo_predicho += tiempo_eventos
        
        return {
            "prediccion": {
                "hora_salida": hora_salida,
                "dia_semana": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][dia_semana],
                "hora_dia": hora_dia,
                "factor_trafico": factor_trafico,
                "nivel_trafico": "Alto" if factor_trafico >= 1.5 else 
                                "Moderado" if factor_trafico >= 1.2 else 
                                "Bajo"
            },
            "tiempos": {
                "normal_min": round(tiempo_normal, 1),
                "predicho_min": round(tiempo_predicho, 1),
                "adicional_eventos_min": round(tiempo_eventos, 1),
                "incremento_porcentaje": round(((tiempo_predicho - tiempo_normal) / tiempo_normal) * 100, 1)
            },
            "recomendacion_hora": "Evitar" if factor_trafico >= 1.5 else 
                                 "Considerar" if factor_trafico >= 1.2 else 
                                 "Ideal",
            "eventos_actuales": len(eventos_procesados)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en predicción: {str(e)}")

@router.post("/ruta-multiparada")
def calcular_ruta_multiparada(request: RutaMultiparadaRequest):
    """
    Calcula ruta con múltiples paradas (problema del viajante)
    """
    MAPQUEST_API_KEY = os.getenv("MAPQUEST_API_KEY")
    if not MAPQUEST_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="API Key no configurada"
        )
    
    if len(request.lugares) < 2:
        raise HTTPException(
            status_code=400,
            detail="Se requieren al menos 2 ubicaciones"
        )
    
    try:
        maniobras, geometria, bbox, orden = obtener_ruta_multiparada(
            MAPQUEST_API_KEY, 
            request.lugares, 
            request.optimizar
        )
        
        if not maniobras:
            raise HTTPException(
                status_code=400,
                detail="No se pudo calcular la ruta multiparada"
            )
        
        # Procesar incidentes
        incidentes = []
        if bbox:
            incidentes = obtener_incidencias_trafico(MAPQUEST_API_KEY, bbox)
        
        eventos_procesados = procesar_incidentes_trafico(incidentes)
        instrucciones = procesar_maniobras_instrucciones(maniobras)
        distancia_total = sum(man['distance'] for man in maniobras)
        
        # Generar mapa
        grafo = construir_grafo_logico(maniobras)
        generar_mapa_visual(grafo, geometria, incidentes, orden, "ruta_multiparada.html")
        
        return {
            "paradas": len(request.lugares),
            "distancia_total_km": round(distancia_total, 2),
            "eventos_trafico": len(eventos_procesados),
            "instrucciones": len(instrucciones),
            "orden_optimizado": [p['dir'] for p in orden] if orden else request.lugares,
            "mapa_html": "ruta_multiparada.html",
            "estadisticas": {
                "total_stops": len(request.lugares) - 1,  # Restamos 1 porque el origen está incluido
                "total_events": len(eventos_procesados),
                "total_distance_km": round(distancia_total, 2),
                "estimated_time_min": round(distancia_total * 1.5, 1)  # Estimación: 1.5 min/km
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculando ruta multiparada: {str(e)}"
        )