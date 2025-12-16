from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import folium
import json
from datetime import datetime

# Importamos solo las funciones necesarias de dijkstra
from backend.core.dijkstra import obtener_ruta_multiparada, construir_grafo_logico, obtener_incidencias_trafico
from backend.core.simulacion import traducir_detalles_trafico

router = APIRouter()
load_dotenv()

class SimulacionRequest(BaseModel):
    origen: str
    destino: str

def obtener_icono_y_color_por_tipo(tipo: int):
    """Obtiene icono y color según el tipo de evento de MapQuest"""
    iconos_map = {
        1: {"icon": "wrench", "color": "orange", "texto": "Construcción"},
        2: {"icon": "calendar", "color": "purple", "texto": "Evento"},
        3: {"icon": "exclamation-triangle", "color": "red", "texto": "Peligro"},
        4: {"icon": "traffic-light", "color": "darkred", "texto": "Congestión"},
        5: {"icon": "car-crash", "color": "black", "texto": "Accidente"},
        6: {"icon": "bus", "color": "blue", "texto": "Tránsito"},
        7: {"icon": "info-circle", "color": "gray", "texto": "Misceláneo"},
        8: {"icon": "newspaper", "color": "cadetblue", "texto": "Noticias"},
        9: {"icon": "clipboard-check", "color": "green", "texto": "Planificado"},
        10: {"icon": "road", "color": "darkgray", "texto": "Cierre"},
        11: {"icon": "cloud-rain", "color": "lightblue", "texto": "Clima"}
    }
    
    return iconos_map.get(tipo, {"icon": "exclamation-circle", "color": "gray", "texto": "Otro"})

def obtener_nivel_riesgo(severidad: int):
    """Determina el nivel de riesgo basado en la severidad"""
    if severidad >= 4:
        return "Alto"
    elif severidad >= 3:
        return "Moderado"
    else:
        return "Bajo"

def crear_popup_evento(evento_info: dict, desc_traducida: str):
    """Crea el HTML para el popup del evento"""
    tipo_info = obtener_icono_y_color_por_tipo(evento_info.get('type', 0))
    severidad = evento_info.get('severity', 1)
    
    popup_html = f"""
    <div style='font-family: Arial, sans-serif; width: 280px;'>
        <div style='background: var(--azul-medio); color: white; padding: 10px; border-radius: 5px 5px 0 0; margin: -10px -10px 10px -10px;'>
            <strong><i class='fas fa-{tipo_info["icon"]}'></i> {tipo_info["texto"]}</strong>
        </div>
        
        <div style='padding: 10px;'>
            <h5 style='margin: 10px 0; color: #333; font-size: 16px;'>
                {desc_traducida[:80]}{'...' if len(desc_traducida) > 80 else ''}
            </h5>
            
            <p style='margin-bottom: 12px; color: #555; font-size: 14px; line-height: 1.4;'>
                {desc_traducida}
            </p>
            
            <div style='background: #f5f5f5; padding: 10px; border-radius: 4px; border-left: 4px solid {tipo_info["color"]}; margin: 12px 0;'>
                <div style='margin-bottom: 5px;'>
                    <strong><i class='fas fa-map-marker-alt'></i> Ubicación:</strong> {evento_info.get('lat', 0):.4f}, {evento_info.get('lng', 0):.4f}
                </div>
                
                <div style='margin-bottom: 5px;'>
                    <strong><i class='fas fa-shield-alt'></i> Severidad:</strong> {severidad}/5
                </div>
            </div>
        </div>
    </div>
    """
    
    return popup_html

@router.post("/render", response_class=HTMLResponse)
def simular_ruta_render(request: SimulacionRequest):
    """
    Calcula ruta, obtiene tráfico y devuelve el HTML del mapa completo
    con TODOS los tipos de eventos de MapQuest.
    """
    API_KEY = os.getenv("MAPQUEST_API_KEY", "0wSs0qcTStL21HNT4VhipGi7CDsjXnkw")
    
    lugares = [request.origen, request.destino]
    
    # 1. Obtener datos de la ruta y el Bounding Box
    maniobras, geometria, bbox, orden = obtener_ruta_multiparada(API_KEY, lugares)
    
    if not maniobras:
        raise HTTPException(status_code=400, detail="No se pudo calcular la ruta.")
    
    # 2. Obtener datos de tráfico
    incidentes = []
    if bbox:
        try:
            incidentes = obtener_incidencias_trafico(API_KEY, bbox)
        except Exception as e:
            print(f"Advertencia: No se pudo obtener tráfico: {e}")

    # 3. Configurar el mapa base
    sw = [18.80, -100.20] 
    ne = [20.20, -98.80]
    centro = [(sw[0]+ne[0])/2, (sw[1]+ne[1])/2]
    
    m = folium.Map(
        location=centro, 
        zoom_start=11, 
        tiles='OpenStreetMap',
        min_zoom=9,
        max_bounds=True,
        min_lat=sw[0],
        max_lat=ne[0],
        min_lon=sw[1],
        max_lon=ne[1]
    )

    # 4. Añadir capa de control de capas
    folium.LayerControl().add_to(m)

    # 5. Dibujar la Ruta Principal
    if geometria:
        folium.PolyLine(
            geometria, 
            color="#0055FF", 
            weight=5, 
            opacity=0.7,
            popup="Ruta principal",
            tooltip="Ruta sugerida",
            name="Ruta Principal"
        ).add_to(m)

    # 6. Dibujar TODOS los Incidentes de Tráfico
    print(f"Procesando {len(incidentes)} eventos de tráfico...")
    
    # Contadores por tipo
    contadores_tipo = {}
    
    for inc in incidentes:
        lat = inc.get('lat')
        lng = inc.get('lng')
        
        if not lat or not lng:
            continue
        
        # Filtro geográfico
        if not (sw[0] < lat < ne[0] and sw[1] < lng < ne[1]):
            continue
        
        tipo = inc.get('type', 0)
        severidad = inc.get('severity', 1)
        desc_original = inc.get('fullDesc', inc.get('shortDesc', 'Sin detalles disponibles'))
        desc_traducida = traducir_detalles_trafico(desc_original)
        
        # Obtener información del tipo
        tipo_info = obtener_icono_y_color_por_tipo(tipo)
        
        # Contar por tipo
        contadores_tipo[tipo_info["texto"]] = contadores_tipo.get(tipo_info["texto"], 0) + 1
        
        # Crear popup
        popup_html = crear_popup_evento(inc, desc_traducida)
        
        # Dibujar según el tipo
        if tipo == 4:  # Congestión - círculo con radio proporcional a severidad
            radio = severidad * 150  # 150 metros por nivel de severidad
            folium.Circle(
                location=(lat, lng),
                radius=radio,
                color=tipo_info["color"],
                fill=True,
                fill_opacity=0.3,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{tipo_info['texto']} - Severidad: {severidad}/5",
                name=f"Congestión ({contadores_tipo[tipo_info['texto']]})"
            ).add_to(m)
            
            # También añadir marcador en el centro
            folium.Marker(
                location=(lat, lng),
                icon=folium.Icon(color=tipo_info["color"], icon=tipo_info["icon"], prefix='fa'),
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{tipo_info['texto']} - Centro"
            ).add_to(m)
            
        elif tipo == 10:  # Cierre de carretera - marcador especial
            # Icono personalizado para cierre
            closure_icon = folium.DivIcon(
                html=f"""
                <div style="
                    background: {tipo_info['color']};
                    color: white;
                    width: 30px;
                    height: 30px;
                    border-radius: 50%;
                    border: 3px solid white;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                ">
                    <i class="fas fa-{tipo_info['icon']}" style="font-size: 14px;"></i>
                </div>
                """,
                icon_size=(30, 30),
                icon_anchor=(15, 15)
            )
            
            folium.Marker(
                location=(lat, lng),
                icon=closure_icon,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"🚫 {tipo_info['texto']} - Severidad: {severidad}/5",
                name=f"Cierres ({contadores_tipo[tipo_info['texto']]})"
            ).add_to(m)
            
        elif tipo == 5:  # Accidente - marcador con animación
            # Icono parpadeante para accidentes graves
            if severidad >= 4:
                accident_icon = folium.DivIcon(
                    html=f"""
                    <div style="
                        background: {tipo_info['color']};
                        color: white;
                        width: 28px;
                        height: 28px;
                        border-radius: 50%;
                        border: 3px solid white;
                        box-shadow: 0 0 10px {tipo_info['color']};
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        animation: pulse 1.5s infinite;
                    ">
                        <i class="fas fa-{tipo_info['icon']}" style="font-size: 12px;"></i>
                    </div>
                    <style>
                        @keyframes pulse {{
                            0% {{ opacity: 1; transform: scale(1); }}
                            50% {{ opacity: 0.7; transform: scale(1.1); }}
                            100% {{ opacity: 1; transform: scale(1); }}
                        }}
                    </style>
                    """,
                    icon_size=(28, 28),
                    icon_anchor=(14, 14)
                )
            else:
                accident_icon = folium.Icon(
                    color=tipo_info["color"], 
                    icon=tipo_info["icon"], 
                    prefix='fa'
                )
            
            folium.Marker(
                location=(lat, lng),
                icon=accident_icon,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"⚠️ {tipo_info['texto']} - Severidad: {severidad}/5",
                name=f"Accidentes ({contadores_tipo[tipo_info['texto']]})"
            ).add_to(m)
            
        else:  # Otros tipos - marcadores estándar
            # Icono personalizado para mejor visibilidad
            custom_icon = folium.DivIcon(
                html=f"""
                <div style="
                    background: {tipo_info['color']};
                    color: white;
                    width: 26px;
                    height: 26px;
                    border-radius: 50%;
                    border: 2px solid white;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                ">
                    <i class="fas fa-{tipo_info['icon']}" style="font-size: 12px;"></i>
                </div>
                """,
                icon_size=(26, 26),
                icon_anchor=(13, 13)
            )
            
            folium.Marker(
                location=(lat, lng),
                icon=custom_icon,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{tipo_info['texto']} - Severidad: {severidad}/5",
                name=f"{tipo_info['texto']} ({contadores_tipo[tipo_info['texto']]})"
            ).add_to(m)
    
    # 7. Marcadores de Inicio y Fin
    if orden:
        # Marcador de inicio (UMB)
        folium.Marker(
            location=orden[0]['pos'],
            popup=f"""
            <div style='font-family: Arial; width: 250px;'>
                <div style='background: #2ecc71; color: white; padding: 10px; border-radius: 5px 5px 0 0;'>
                    <strong><i class='fas fa-university'></i> PUNTO DE ORIGEN</strong>
                </div>
                <div style='padding: 10px;'>
                    <h5 style='margin: 0 0 10px 0; color: #333;'>UMB Cuautitlán</h5>
                    <p style='margin: 0; color: #666;'>{orden[0]['dir']}</p>
                </div>
            </div>
            """,
            icon=folium.Icon(color='green', icon='university', prefix='fa'),
            tooltip="UMB Cuautitlán - Punto de origen",
            name="Origen"
        ).add_to(m)
        
        # Marcador de destino
        folium.Marker(
            location=orden[-1]['pos'],
            popup=f"""
            <div style='font-family: Arial; width: 250px;'>
                <div style='background: #3498db; color: white; padding: 10px; border-radius: 5px 5px 0 0;'>
                    <strong><i class='fas fa-flag-checkered'></i> PUNTO DE DESTINO</strong>
                </div>
                <div style='padding: 10px;'>
                    <h5 style='margin: 0 0 10px 0; color: #333;'>Destino</h5>
                    <p style='margin: 0; color: #666;'>{orden[-1]['dir']}</p>
                </div>
            </div>
            """,
            icon=folium.Icon(color='blue', icon='flag-checkered', prefix='fa'),
            tooltip="Destino final",
            name="Destino"
        ).add_to(m)

    # 8. Añadir leyenda al mapa con diseño mejorado (Estilo Header UMB)
    # 8. Añadir leyenda al mapa con diseño compactado
    legend_html = '''
    <div style="
        position: fixed; 
        bottom: 20px; 
        right: 20px; 
        width: 190px; /* Reducido de 260px a 190px */
        background: linear-gradient(135deg, #1c2e4a 0%, #274c77 100%);
        border: 1px solid #3a7ca5;
        border-radius: 10px; 
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        z-index: 9999;
        color: #ffffff;
        overflow: hidden;
        backdrop-filter: blur(4px);
    ">
        <div style="
            background: rgba(0, 0, 0, 0.2); 
            padding: 8px 12px; 
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            display: flex; 
            align-items: center; 
            gap: 8px;
        ">
            <i class="fas fa-layer-group" style="color: #3a7ca5; font-size: 12px;"></i>
            <h4 style="margin: 0; font-size: 13px; font-weight: 600; letter-spacing: 0.5px;">Simbología</h4>
        </div>
        
        <div style="padding: 10px;">
            <div style="display: flex; align-items: center; margin-bottom: 8px;">
                <div style="
                    width: 20px; height: 20px; 
                    border-radius: 50%; 
                    background: #ff0000; 
                    border: 1.5px solid rgba(255,255,255,0.8);
                    display: flex; align-items: center; justify-content: center; 
                    margin-right: 8px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
                ">
                    <i class="fas fa-exclamation-triangle" style="color: white; font-size: 9px;"></i>
                </div>
                <span style="font-size: 11px; font-weight: 500;">Peligro</span>
            </div>

            <div style="display: flex; align-items: center; margin-bottom: 8px;">
                <div style="
                    width: 20px; height: 20px; 
                    border-radius: 50%; 
                    background: #ff6b6b; 
                    border: 1.5px solid rgba(255,255,255,0.8);
                    display: flex; align-items: center; justify-content: center; 
                    margin-right: 8px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
                ">
                    <i class="fas fa-car-crash" style="color: white; font-size: 9px;"></i>
                </div>
                <span style="font-size: 11px; font-weight: 500;">Accidente</span>
            </div>
            
            <div style="display: flex; align-items: center; margin-bottom: 8px;">
                <div style="
                    width: 20px; height: 20px; 
                    border-radius: 50%; 
                    background: #ffa726; 
                    border: 1.5px solid rgba(255,255,255,0.8);
                    display: flex; align-items: center; justify-content: center; 
                    margin-right: 8px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
                ">
                    <i class="fas fa-wrench" style="color: white; font-size: 9px;"></i>
                </div>
                <span style="font-size: 11px; font-weight: 500;">Construcción</span>
            </div>
            
            <div style="display: flex; align-items: center; margin-bottom: 8px;">
                <div style="
                    width: 20px; height: 20px; 
                    border-radius: 50%; 
                    background: #f44336; 
                    border: 1.5px solid rgba(255,255,255,0.8);
                    display: flex; align-items: center; justify-content: center; 
                    margin-right: 8px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
                ">
                    <i class="fas fa-traffic-light" style="color: white; font-size: 9px;"></i>
                </div>
                <span style="font-size: 11px; font-weight: 500;">Congestión</span>
            </div>
            
            <div style="display: flex; align-items: center; margin-bottom: 8px;">
                <div style="
                    width: 20px; height: 20px; 
                    border-radius: 50%; 
                    background: #000000; 
                    border: 1.5px solid rgba(255,255,255,0.8);
                    display: flex; align-items: center; justify-content: center; 
                    margin-right: 8px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
                ">
                    <i class="fas fa-road" style="color: white; font-size: 9px;"></i>
                </div>
                <span style="font-size: 11px; font-weight: 500;">Cierre</span>
            </div>
            
            <div style="display: flex; align-items: center; margin-bottom: 0;">
                <div style="
                    width: 20px; height: 20px; 
                    border-radius: 50%; 
                    background: #3f51b5; 
                    border: 1.5px solid rgba(255,255,255,0.8);
                    display: flex; align-items: center; justify-content: center; 
                    margin-right: 8px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
                ">
                    <i class="fas fa-bus" style="color: white; font-size: 9px;"></i>
                </div>
                <span style="font-size: 11px; font-weight: 500;">Tránsito</span>
            </div>
        </div>
        
        <div style="
            padding: 5px 10px; 
            background: rgba(0,0,0,0.15); 
            font-size: 9px; 
            text-align: center; 
            color: rgba(255,255,255,0.6);
        ">
            <i class="fas fa-mouse-pointer"></i> Click en marcadores
        </div>
    </div>
    '''
    
    m.get_root().html.add_child(folium.Element(legend_html))

    m.fit_bounds([sw, ne])
    
    # 9. Generar estadísticas para el frontend
    distancia_total = sum(man['distance'] for man in maniobras) if maniobras else 0
    
    # Procesar instrucciones
    instrucciones = []
    for i, man in enumerate(maniobras):
        instrucciones.append({
            "orden": i + 1,
            "texto": man['narrative'],
            "distancia": f"{man['distance']:.1f} km",
            "distancia_km": man['distance']
        })
    
    # Procesar eventos para el frontend
    eventos_procesados = []
    for inc in incidentes:
        tipo = inc.get('type', 0)
        tipo_info = obtener_icono_y_color_por_tipo(tipo)
        
        eventos_procesados.append({
            "type": tipo_info["texto"].lower().replace(" ", "_"),
            "tipo_texto": tipo_info["texto"],
            "title": traducir_detalles_trafico(inc.get('fullDesc', 'Sin detalles'))[:60] + "...",
            "description": traducir_detalles_trafico(inc.get('fullDesc', 'Sin detalles disponibles')),
            "location": f"{inc.get('lat', 0):.4f}, {inc.get('lng', 0):.4f}",
            "severidad": inc.get('severity', 1),
            "icono": tipo_info["icon"],
            "color": tipo_info["color"]
        })
    
    # 10. Inyectar datos en el HTML
    datos_frontend = {
        "eventos": eventos_procesados,
        "estadisticas_eventos": contadores_tipo,
        "total_eventos": len(incidentes),
        "instrucciones": instrucciones[:5],
        "todas_instrucciones": instrucciones,
        "estadisticas": {
            "total_steps": len(instrucciones),
            "total_events": len(incidentes),
            "total_distance": f"{distancia_total:.1f} km",
            "distancia_km": distancia_total,
            "eventos_por_tipo": contadores_tipo
        },
        "ruta_info": {
            "origen": orden[0]['dir'] if orden else request.origen,
            "destino": orden[-1]['dir'] if orden else request.destino,
            "origen_coords": orden[0]['pos'] if orden else [19.667, -99.175],
            "destino_coords": orden[-1]['pos'] if orden else [19.667, -99.175]
        }
    }
    
    # Inyectar script con datos
    script_datos = f"""
    <script>
    // Datos de la ruta para el frontend
    window.datosRuta = {json.dumps(datos_frontend, ensure_ascii=False)};
    
    // Función para hacer zoom a un evento específico
    window.zoomToEvent = function(lat, lng) {{
        if (typeof map !== 'undefined') {{
            map.setView([lat, lng], 15);
            return true;
        }}
        return false;
    }};
    
    // Función para mostrar/ocultar tipos específicos de eventos
    window.filterEvents = function(tipo) {{
        if (typeof map !== 'undefined') {{
            // Implementación básica - en producción usaría capas
            alert('Filtrando eventos de tipo: ' + tipo);
        }}
    }};
    
    // Función para obtener estadísticas
    window.getEventStats = function() {{
        return {json.dumps(contadores_tipo, ensure_ascii=False)};
    }};
    
    console.log('Datos de ruta cargados:', window.datosRuta.estadisticas_eventos);
    </script>
    """
    
    # Insertar el script al final del body
    mapa_html = m.get_root().render()
    html_final = mapa_html.replace('</body>', f'{script_datos}</body>')
    
    print(f"✅ Mapa generado con {len(incidentes)} eventos de tráfico")
    print(f"📊 Estadísticas por tipo: {contadores_tipo}")
    
    return HTMLResponse(content=html_final)

@router.post("/datos-ruta")
def obtener_datos_ruta(request: SimulacionRequest):
    """
    Endpoint alternativo que devuelve solo los datos de la ruta en JSON
    con todos los tipos de eventos de MapQuest.
    """
    API_KEY = os.getenv("MAPQUEST_API_KEY", "0wSs0qcTStL21HNT4VhipGi7CDsjXnkw")
    
    lugares = [request.origen, request.destino]
    
    # 1. Obtener datos de la ruta
    maniobras, geometria, bbox, orden = obtener_ruta_multiparada(API_KEY, lugares)
    
    if not maniobras:
        raise HTTPException(status_code=400, detail="No se pudo calcular la ruta.")
    
    # 2. Obtener datos de tráfico
    incidentes = []
    if bbox:
        try:
            incidentes = obtener_incidencias_trafico(API_KEY, bbox)
        except Exception as e:
            print(f"Advertencia: No se pudo obtener tráfico: {e}")
    
    # 3. Procesar datos para respuesta
    instrucciones = []
    for i, man in enumerate(maniobras):
        instrucciones.append({
            "orden": i + 1,
            "texto": man['narrative'],
            "distancia": f"{man['distance']:.1f} km",
            "distancia_km": man['distance']
        })
    
    distancia_total = sum(man['distance'] for man in maniobras)
    
    # 4. Procesar incidentes con todos los tipos
    eventos_procesados = []
    contadores_tipo = {}
    
    for inc in incidentes:
        tipo = inc.get('type', 0)
        tipo_info = obtener_icono_y_color_por_tipo(tipo)
        severidad = inc.get('severity', 1)
        
        # Contar por tipo
        contadores_tipo[tipo_info["texto"]] = contadores_tipo.get(tipo_info["texto"], 0) + 1
        
        # Traducir descripción
        desc = traducir_detalles_trafico(inc.get('fullDesc', 'Sin detalles disponibles'))
        
        eventos_procesados.append({
            "type": tipo_info["texto"].lower().replace(" ", "_"),
            "tipo_texto": tipo_info["texto"],
            "title": desc[:50] + "..." if len(desc) > 50 else desc,
            "description": desc,
            "location": f"{inc.get('lat', 0):.4f}, {inc.get('lng', 0):.4f}",
            "severidad": severidad,
            "nivel_riesgo": obtener_nivel_riesgo(severidad),
            "icono": tipo_info["icon"],
            "color": tipo_info["color"],
            "hora_inicio": inc.get('startTime'),
            "hora_fin": inc.get('endTime'),
            "impacto": inc.get('impacting', 0)
        })
    
    return {
        "eventos": eventos_procesados,
        "instrucciones": instrucciones,
        "estadisticas": {
            "total_steps": len(instrucciones),
            "total_events": len(eventos_procesados),
            "total_distance": f"{distancia_total:.1f} km",
            "distancia_km": distancia_total,
            "eventos_por_tipo": contadores_tipo,
            "eventos_alto_riesgo": len([e for e in eventos_procesados if e["nivel_riesgo"] == "Alto"])
        },
        "ruta_info": {
            "origen": orden[0]['dir'] if orden else request.origen,
            "destino": orden[-1]['dir'] if orden else request.destino,
            "origen_coords": orden[0]['pos'] if orden else None,
            "destino_coords": orden[-1]['pos'] if orden else None
        }
    }