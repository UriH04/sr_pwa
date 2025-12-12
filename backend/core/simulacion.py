import folium
import dijkstra

def generar_mapa_visual(G, ruta_geometria, incidentes, nombre_archivo="mapa.html"):
    if not G or not ruta_geometria:
        return

    # 1. Centrar Mapa
    primer_nodo = list(G.nodes())[0]
    centro_mapa = G.nodes[primer_nodo]['pos']
    mapa = folium.Map(location=centro_mapa, zoom_start=13, tiles='OpenStreetMap')

    # 2. Dibujar la Ruta (Azul)
    folium.PolyLine(
        ruta_geometria, color="#0055FF", weight=6, opacity=0.7, tooltip="Ruta Sugerida"
    ).add_to(mapa)

    # 3. Dibujar ZONAS DE TRÁFICO (Círculos y Alertas)
    print(f"   -> Procesando {len(incidentes)} eventos de tráfico...")
    for inc in incidentes:
        lat = inc['lat']
        lng = inc['lng']
        tipo = inc['type']
        descripcion = inc['fullDesc']
        severidad = inc['severity']

        if tipo == 4: # CONGESTIÓN
            folium.Circle(
                location=(lat, lng),
                radius=200 + (severidad * 50), 
                color='red', fill=True, fill_opacity=0.3,
                popup=f"Tráfico: {descripcion}"
            ).add_to(mapa)
        elif tipo == 1: # OBRAS
            folium.Marker(
                location=(lat, lng),
                popup=f"Obras: {descripcion}",
                icon=folium.Icon(color='orange', icon='wrench', prefix='fa')
            ).add_to(mapa)
        elif tipo == 3: # ACCIDENTE
            folium.Marker(
                location=(lat, lng),
                popup=f"Accidente: {descripcion}",
                icon=folium.Icon(color='red', icon='exclamation-triangle', prefix='fa')
            ).add_to(mapa)

    # 4. DIBUJAR INICIO Y FIN (DISEÑO PERSONALIZADO MAPQUEST)
    # URLs oficiales de los assets de MapQuest
    # Nota: Usamos 'marker-start' para el verde y 'marker-end' para el rojo.
    icon_url_inicio = "https://assets.mapquestapi.com/icon/v2/marker-start.png" 
    icon_url_fin = "https://assets.mapquestapi.com/icon/v2/marker-end.png"

    total_nodos = len(G.nodes())

    for i, node_id in enumerate(G.nodes()):
        datos_nodo = G.nodes[node_id]
        coord = datos_nodo['pos']
        narrativa = datos_nodo['desc']
        
        distancia_texto = ""
        if i < total_nodos - 1:
            # Buscamos la arista que conecta este nodo con el siguiente
            dist_km = G[i][i+1]['weight']
            if dist_km < 1.0:
                # Si es menos de 1 km, lo mostramos en metros
                distancia_texto = f"<br><b>Distancia:</b> {int(dist_km * 1000)} mts"
            else:
                distancia_texto = f"<br><b>Distancia:</b> {dist_km:.2f} km"

        # Contenido del Popup (Globo de texto)
        html_popup = f"""
        <div style="font-family: Arial; width: 200px;">
            <b>Paso {node_id}:</b><br>
            {narrativa}
            {distancia_texto}
        </div>
        """

        # LOGICA DE ICONOS
        if i == 0:
            # --- PUNTO DE INICIO (MapQuest Green Marker) ---
            icono_mq = folium.CustomIcon(
                icon_url_inicio,
                icon_size=(35, 35), # Tamaño en pixeles
                icon_anchor=(17, 35), # El punto del pin está abajo al centro
                popup_anchor=(0, -35)
            )
            folium.Marker(
                location=coord,
                popup=f"<b>INICIO:</b> {narrativa}",
                icon=icono_mq
            ).add_to(mapa)

        elif i == total_nodos - 1:
            # --- PUNTO DE DESTINO (MapQuest Red Marker) ---
            icono_mq = folium.CustomIcon(
                icon_url_fin,
                icon_size=(35, 35),
                icon_anchor=(17, 35),
                popup_anchor=(0, -35)
            )
            folium.Marker(
                location=coord,
                popup=f"<b>LLEGADA:</b> {narrativa}",
                icon=icono_mq
            ).add_to(mapa)
            
        else:
            # --- Puntos intermedios (Pequeños puntos azules para no estorbar) ---
            folium.CircleMarker(
                location=coord,
                radius=4,
                color='blue',
                fill=True,
                fill_color='white',
                popup=folium.Popup(html_popup, max_width=300)
            ).add_to(mapa)

    mapa.save(nombre_archivo)
    print(f"\nMapa PRO generado: {nombre_archivo}")

# --- EJECUCIÓN ---
if __name__ == "__main__":
    API_KEY = "0wSs0qcTStL21HNT4VhipGi7CDsjXnkw"
    
    # Ruta de Prueba
    ORIGEN = "UMB Unidad de Estudios Superiores Cuautitlán, Méx."
    DESTINO = "Zocalo, Ciudad de México"
    
    print("1. Obteniendo datos (Dijkstra + API)...")
    maniobras, geometria, bbox = dijkstra.obtener_datos_ruta(API_KEY, ORIGEN, DESTINO)
    
    if maniobras:
        print("2. Analizando tráfico...")
        incidentes = dijkstra.obtener_incidencias_trafico(API_KEY, bbox)
        
        print("3. Construyendo grafo...")
        grafo_ruta = dijkstra.construir_grafo_logico(maniobras)
        
        print("4. Renderizando mapa con diseño MapQuest...")
        generar_mapa_visual(grafo_ruta, geometria, incidentes)
    else:
        print("Error al calcular la ruta.")