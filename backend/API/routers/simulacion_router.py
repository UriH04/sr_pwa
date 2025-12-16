from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv
import folium
import json
import math

from backend.core.dijkstra import (
    obtener_ruta_multiparada,
    obtener_incidencias_trafico
)
from backend.core.simulacion import traducir_detalles_trafico

router = APIRouter()
load_dotenv()

UES_NOMBRES = {
    'Km 2.5, Carretera al Ejido la Soledad, Ejido La Soledad, 50300 Villa de Acambay de Ruíz Castañeda, Méx.': 'UES Acambay',
    'Angel Castillo López S/N, A Santiago Oxtempan, 50600 El Oro de Hidalgo, Méx.': 'UES El Oro',
    'Ignacio Zaragoza, 50400 Temascalcingo de José María Velasco, Méx.': 'UES Temascalcingo',
    'Km. 7, Carretera Jilotepec-Chapa de Mota, Ejido de Jilotepec, 54240 Jilotepec de Molina Enríquez, Méx.': 'UES Jilotepec',
    'Camino Real S/N,, Barrio Primero, 50550 San Bartolo Morelos, Méx.': 'UES Morelos',
    'Domicilio Conocido S/N, Ixtlahuaca, 50740 Barrio de San Pedro la Cabecera, Méx.': 'UES Ixtlahuaca',
    'AVENIDA UNIVERSIDAD SN, 50660 Colonia Las Tinajas, Méx.': 'UES San José del Rincón',
    'Km.1, Carretera San Felipe Santiago, 50800 Méx.': 'UES Jiquipilco',
    'Km. 47 Carretera Federal Toluca-Zitácuaro, 50960 San Agustín Berros, Méx.': 'UES Villa Victoria',
    'Independencia 1, Sta Isabel Ixtapan, 56300 Santa Isabel Ixtapan, Méx.': 'UES Atenco',
    'Carr Federal México-Cuautla Km 14 s/n, La Candelaria tlapala, 56641 Chalco de Díaz Covarrubias, Méx.': 'UES Chalco',
    'Avenida Hacienda La Escondida 589, Geovillas Santa Barbara, 56630 Ixtapaluca, Méx.': 'UES Ixtapaluca',
    'S. Agustín S/N, El Pino, 56400 San Isidro, Méx.': 'UES La Paz',
    'De las Flores S/N, La Magdalena Chichicaspa, 52773 Huixquilucan de Degollado, Méx.': 'UES Huixquilucan',
    'Cto de la Industria Pte S/N, Isidro Fabela, 52004 Lerma de Villada, Méx.': 'UES Lerma',
    'Domicilio Conocido S/N, San Diego Alcalá, 50850 Temoaya, Méx.': 'UES Temoaya',
    'Los Hidalgos 233, Sin Nombre, 52316 Tenango de Arista, Méx.': 'UES Tenango del Valle',
    'Calle Colorines S/N,, Deportiva de Xalatlaco, 52680 Xalatlaco, Méx.': 'UES Xalatlaco',
    'Av Insurgentes, Fraccionamiento Las Americas, Las Américas, 55070 Ecatepec de Morelos, Méx.': 'UES Ecatepec',
    'Calle Blvrd Jardines Mz 66, Los Heroes Tecamac, 55764 Ojo de Agua, Méx.': 'UES Tecámac',
    'Calle Av. del Convento S/N, El Trebol, 54614 Tepotzotlán, Méx.': 'UES Tepotzotlán',
    'San Antonio s/n, Villa Esmeralda, 54910 Tultitlán de Mariano Escobedo, Méx.': 'UES Tultitlán',
    'Calle al Quemado S/N, Fracción I del Ex Ejido, 54980 San Pablo de las Salinas, Méx.': 'UES Tultepec',
    'Carretera Villa del Carbon, KM 34.5, 54300 Villa del Carbón, Méx.': 'UES Villa del Carbón',
    'Domicilio Conocido, Paraje la Chimenea, Comunidad Agua Fría, Paraje la Chimenea, 51860 Almoloya de Alquisiras, Méx.': 'UES Almoloya de Alquisiras',
    'Domicilio conocido, San Luis, 51700 Coatepec Harinas, Méx.': 'UES Coatepec Harinas',
    'Carretera Toluca–Sultepec, Libramiento Sultepec–La Goleta S/N,, Barrio Camino Nacional, 51600 Sultepec de Pedro Ascencio de Alquisiras, Méx.': 'UES Sultepec',
    'Domicilio Conocido, El Rodeo, Tejupilco de Hidalgo, 51400 Méx.': 'UES Tejupilco',
    'Carretera Los Cuervos-Arcelia km 35, San Pedro, Limón, 51585 Tlatlaya, Méx': 'UES Tlatlaya'
}

def obtener_nombre_ues(direccion):
    """Obtiene el nombre de la UES a partir de la dirección"""
    return UES_NOMBRES.get(direccion, direccion)


# =========================
# MODELOS
# =========================

class SimulacionRequest(BaseModel):
    origen: str
    destino: str

class SimulacionRequestMulti(BaseModel):
    origen: str
    destinos: List[str]

# =========================
# UTILIDADES Y PROCESAMIENTO
# =========================

def obtener_icono_y_color_por_tipo(tipo: int):
    iconos_map = {
        1: {"icon": "wrench", "color": "orange", "texto": "Construcción"},
        2: {"icon": "calendar", "color": "purple", "texto": "Evento"},
        3: {"icon": "exclamation-triangle", "color": "red", "texto": "Peligro"},
        4: {"icon": "traffic-light", "color": "red", "texto": "Congestión"},
        5: {"icon": "car-crash", "color": "black", "texto": "Accidente"},
        6: {"icon": "bus", "color": "blue", "texto": "Tránsito"},
        7: {"icon": "info-circle", "color": "gray", "texto": "Misceláneo"},
        8: {"icon": "newspaper", "color": "cadetblue", "texto": "Noticias"},
        9: {"icon": "clipboard-check", "color": "green", "texto": "Planificado"},
        10: {"icon": "road", "color": "darkgray", "texto": "Cierre"},
        11: {"icon": "cloud-rain", "color": "lightblue", "texto": "Clima"},
    }
    return iconos_map.get(tipo, {"icon": "exclamation-circle", "color": "gray", "texto": "Otro"})

def procesar_instrucciones_para_frontend(maniobras):
    """Procesa las maniobras para el frontend con instrucciones traducidas"""
    instrucciones = []
    
    for i, man in enumerate(maniobras):
        # Traducir la instrucción
        instruccion_traducida = traducir_detalles_trafico(man['narrative'])
        
        # Formatear distancia
        distancia_km = man.get('distance', 0)
        
        instrucciones.append({
            "orden": i + 1,
            "texto": instruccion_traducida,
            "distancia": f"{distancia_km:.2f} km",
            "distancia_km": distancia_km,
            "coordenadas": f"{man.get('startPoint', {}).get('lat', 0):.4f}, {man.get('startPoint', {}).get('lng', 0):.4f}"
        })
    
    return instrucciones

def procesar_eventos_para_frontend(incidentes, geometria):
    """Procesa eventos de tráfico para el frontend"""
    eventos_procesados = []
    
    for inc in incidentes:
        lat = inc.get('lat')
        lng = inc.get('lng')
        
        if not lat or not lng:
            continue
        
        tipo = inc.get('type', 0)
        tipo_info = obtener_icono_y_color_por_tipo(tipo)
        severidad = inc.get('severity', 1)
        desc_original = inc.get('fullDesc', inc.get('shortDesc', 'Sin detalles disponibles'))
        desc_traducida = traducir_detalles_trafico(desc_original)
        
        # Calcular distancia a la ruta
        distancia_a_ruta = calcular_distancia_a_ruta(lat, lng, geometria)
        
        eventos_procesados.append({
            "type": tipo_info["texto"].lower().replace(" ", "_"),
            "tipo_texto": tipo_info["texto"],
            "title": f"{tipo_info['texto']}: {desc_traducida[:50]}...",
            "description": desc_traducida,
            "location": f"{lat:.4f}, {lng:.4f}",
            "severidad": severidad,
            "icono": tipo_info["icon"],
            "color": tipo_info["color"],
            "distancia_a_ruta_km": round(distancia_a_ruta, 2) if distancia_a_ruta else None,
            "nivel_riesgo": "Alto" if severidad >= 4 else "Moderado" if severidad >= 3 else "Bajo"
        })
    
    return eventos_procesados

def calcular_distancia_a_ruta(lat, lng, geometria):
    """Calcula la distancia mínima de un punto a la ruta"""
    if not geometria:
        return None
    
    def haversine(lat1, lon1, lat2, lon2):
        """Fórmula de Haversine para calcular distancia entre dos puntos"""
        R = 6371.0  # Radio de la Tierra en km
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    # Encontrar la distancia mínima a cualquier punto de la geometría (muestreo simple)
    distancias = []
    # Optimizacion: Si la geometría es muy grande, muestrear cada X puntos para rendimiento
    paso = 1 if len(geometria) < 1000 else 5
    
    for i in range(0, len(geometria), paso):
        try:
            punto = geometria[i]
            punto_lat, punto_lng = punto
            distancia = haversine(lat, lng, punto_lat, punto_lng)
            distancias.append(distancia)
        except:
            continue
    
    return min(distancias) if distancias else None

# =========================
# ENDPOINT MULTIPARADA (HTML)
# =========================

@router.post("/render-multi", response_class=HTMLResponse)
def simular_ruta_multiparada_render(request: SimulacionRequestMulti):
    """
    Calcula ruta con múltiples destinos, obtiene tráfico, genera el mapa y
    inyecta los datos procesados (JSON) para que el frontend los consuma.
    """
    API_KEY = os.getenv("MAPQUEST_API_KEY", "0wSs0qcTStL21HNT4VhipGi7CDsjXnkw")
    
    # Construir lista de lugares: origen + todos los destinos
    lugares = [request.origen] + request.destinos
    
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

    # 3. Procesar datos para el frontend (Estadísticas e Instrucciones)
    instrucciones_procesadas = procesar_instrucciones_para_frontend(maniobras)
    eventos_procesados = procesar_eventos_para_frontend(incidentes, geometria)
    
    distancia_total = sum(man['distance'] for man in maniobras)
    tiempo_estimado = distancia_total * 1.5  # Estimación simple: 1.5 minutos por km
    
    # 4. Configurar el mapa base
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

    # 5. Añadir control de capas
    folium.LayerControl().add_to(m)

    # 6. Dibujar la Ruta Principal
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

    # 7. Dibujar Incidentes de Tráfico en el mapa (Visualización)
    print(f"Procesando {len(incidentes)} eventos de tráfico para {len(request.destinos)} destinos...")
    
    for inc in incidentes:
        lat = inc.get('lat')
        lng = inc.get('lng')
        
        if not lat or not lng:
            continue
        
        # Filtro geográfico simple
        if not (sw[0] < lat < ne[0] and sw[1] < lng < ne[1]):
            continue
        
        tipo = inc.get('type', 0)
        severidad = inc.get('severity', 1)
        desc_original = inc.get('fullDesc', inc.get('shortDesc', 'Sin detalles disponibles'))
        desc_traducida = traducir_detalles_trafico(desc_original)
        
        tipo_info = obtener_icono_y_color_por_tipo(tipo)
        
        # Popup HTML para el mapa
        popup_html = f"""
        <div style='font-family: Arial, sans-serif; width: 250px;'>
            <div style='background: var(--azul-medio, #2c3e50); color: white; padding: 8px; border-radius: 5px 5px 0 0;'>
                <strong><i class='fas fa-{tipo_info["icon"]}'></i> {tipo_info["texto"]}</strong>
            </div>
            <div style='padding: 10px;'>
                <p style='margin: 0 0 10px 0; color: #333; font-size: 14px;'>
                    {desc_traducida[:100]}{'...' if len(desc_traducida) > 100 else ''}
                </p>
                <div style='font-size: 12px; color: #666;'>
                    <div>Severidad: {severidad}/5</div>
                    <div>Ubicación: {lat:.4f}, {lng:.4f}</div>
                </div>
            </div>
        </div>
        """
        
        folium.Marker(
            location=(lat, lng),
            icon=folium.Icon(color=tipo_info["color"], icon=tipo_info["icon"], prefix='fa'),
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{tipo_info['texto']} - Severidad: {severidad}/5"
        ).add_to(m)
    
    # 8. Marcadores de Inicio y Destinos
    if orden:
        # Marcador de inicio (UMB)
        folium.Marker(
            location=orden[0]['pos'],
            popup=f"""
            <div style='font-family: Arial; width: 250px;'>
                <div style='background: #2ecc71; color: white; padding: 10px; border-radius: 5px 5px 0 0;'>
                    <strong><i class='fas fa-university'></i> ORIGEN</strong>
                </div>
                <div style='padding: 10px;'>
                    <h5 style='margin: 0 0 10px 0; color: #333;'>UMB Cuautitlán</h5>
                    <p style='margin: 0; color: #666;'>Manzana 005, Loma Bonita, 54879 Cuautitlán, Méx.</p>
                </div>
            </div>
            """,
            icon=folium.Icon(color='green', icon='university', prefix='fa'),
            tooltip="UMB Cuautitlán - Origen"
        ).add_to(m)
        
        # Marcadores de destinos (numerados)
        for i in range(1, len(orden)):
            direccion_destino = orden[i]['dir']
            nombre_ues = obtener_nombre_ues(direccion_destino)

            destino_icon = folium.DivIcon(
                html=f"""
                <div style="
                    background: #3498db;
                    color: white;
                    width: 30px;
                    height: 30px;
                    border-radius: 50%;
                    border: 2px solid white;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    font-size: 14px;
                ">
                    {i}
                </div>
                """,
                icon_size=(30, 30),
                icon_anchor=(15, 15)
            )
            
            folium.Marker(
                location=orden[i]['pos'],
                popup=f"""
                <div style='font-family: Arial; width: 250px;'>
                    <div style='background: #3498db; color: white; padding: 10px; border-radius: 5px 5px 0 0;'>
                        <strong><i class='fas fa-flag-checkered'></i> DESTINO {i}</strong>
                    </div>
                    <div style='padding: 10px;'>
                        <h5 style='margin: 0 0 10px 0; color: #333;'>{nombre_ues}</h5>
                        <p style='margin: 0; color: #666;'>{orden[i]['dir']}</p>
                    </div>
                </div>
                """,
                icon=destino_icon,
                tooltip=f"{nombre_ues} - Destino {i}"
            ).add_to(m)

    # 9. Añadir leyenda al mapa
    legend_html = '''
    <div style="
        position: fixed; 
        bottom: 20px; 
        right: 20px; 
        width: 190px;
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
                    background: #2ecc71; 
                    border: 1.5px solid rgba(255,255,255,0.8);
                    display: flex; align-items: center; justify-content: center; 
                    margin-right: 8px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
                ">
                    <i class="fas fa-university" style="color: white; font-size: 9px;"></i>
                </div>
                <span style="font-size: 11px; font-weight: 500;">Origen (UMB)</span>
            </div>
            
            <div style="display: flex; align-items: center; margin-bottom: 8px;">
                <div style="
                    width: 20px; height: 20px; 
                    border-radius: 50%; 
                    background: #3498db; 
                    border: 1.5px solid rgba(255,255,255,0.8);
                    display: flex; align-items: center; justify-content: center; 
                    margin-right: 8px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
                ">
                    <span style="color: white; font-size: 9px; font-weight: bold;">1</span>
                </div>
                <span style="font-size: 11px; font-weight: 500;">Destinos</span>
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
            
            <div style="display: flex; align-items: center; margin-bottom: 0;">
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
    
    # ==============================================================================
    # 10. INYECCIÓN DE DATOS PARA EL FRONTEND
    # ==============================================================================
    
    datos_frontend = {
        "instrucciones": instrucciones_procesadas[:10],  # Primeras 10 instrucciones para resumen
        "todas_instrucciones": instrucciones_procesadas, # Todas para el modal
        "eventos": eventos_procesados,
        "estadisticas": {
            "total_instrucciones": len(instrucciones_procesadas),
            "total_eventos": len(eventos_procesados),
            "distancia_total_km": round(distancia_total, 2),
            "tiempo_estimado_min": round(tiempo_estimado, 1),
            "destinos": len(request.destinos),
            "eventos_por_tipo": {}
        }
    }
    
    # Contar eventos por tipo
    for evento in eventos_procesados:
        tipo = evento["type"] # Usamos el key interno (traffic, accident, etc)
        datos_frontend["estadisticas"]["eventos_por_tipo"][tipo] = datos_frontend["estadisticas"]["eventos_por_tipo"].get(tipo, 0) + 1
    
    # Script para inyectar window.datosRuta en el HTML
    script_datos = f"""
    <script>
    // Datos de la ruta generados por el backend
    window.datosRuta = {json.dumps(datos_frontend, ensure_ascii=False)};
    
    // Log para depuración
    console.log('Datos de ruta cargados en window.datosRuta:', window.datosRuta);
    
    // Función helper para que el padre pueda centrar el mapa (si está en iframe)
    window.zoomToLocation = function(lat, lng) {{
        if (typeof map !== 'undefined') {{
            map.setView([lat, lng], 15);
            // Abrir popup si hay marcador cerca
            map.eachLayer(function(layer) {{
                if (layer instanceof L.Marker) {{
                    var layerLatLng = layer.getLatLng();
                    if (Math.abs(layerLatLng.lat - lat) < 0.001 && Math.abs(layerLatLng.lng - lng) < 0.001) {{
                        layer.openPopup();
                    }}
                }}
            }});
        }}
    }};

    // Guardar los datos de la ruta en localStorage para el GPS del repartidor
    const rutaData = {{
        origen: "{request.origen}",
        destinos: {json.dumps(request.destinos, ensure_ascii=False)},
        fecha_calculo: new Date().toISOString(),
        total_destinos: {len(request.destinos)},
        distancia_total: {distancia_total:.2f}
    }};
    
    localStorage.setItem('ultimaRutaMulti', JSON.stringify(rutaData));
    console.log('Ruta guardada en localStorage para GPS:', rutaData);
    
    // Notificar al padre si está en iframe
    if (window.parent !== window) {{
        window.parent.postMessage({{
            type: 'RUTA_CALCULADA',
            data: rutaData
        }}, '*');
    }}
    </script>
    """
    
    # Renderizar mapa a string HTML
    mapa_html = m.get_root().render()
    
    # Inyectar el script antes del cierre del body
    html_final = mapa_html.replace('</body>', f'{script_datos}</body>')
    
    return HTMLResponse(content=html_final)