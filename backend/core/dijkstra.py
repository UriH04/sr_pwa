# NOMBRE DEL ARCHIVO: dijkstra.py
import requests
import networkx as nx

def obtener_datos_ruta(api_key, origen, destino):
    url = "http://www.mapquestapi.com/directions/v2/route"
    params = {
        "key": api_key,
        "from": origen,
        "to": destino,
        "routeType": "fastest",
        "fullShape": "true",
        "drivingStyle": "normal",
        # --- PARÁMETROS DE IDIOMA Y UNIDAD ---
        "unit": "k",        # 'k' = Kilómetros (Por defecto viene en 'm' = Millas)
        "locale": "es_MX"   # Español de México (Traduce la narrativa)
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data["info"]["statuscode"] != 0:
            return [], [], None
            
        maniobras = data["route"]["legs"][0]["maneuvers"]
        shape_points_raw = data["route"]["shape"]["shapePoints"]
        ruta_precisa = list(zip(shape_points_raw[0::2], shape_points_raw[1::2]))
        
        # Obtenemos la caja delimitadora (Bounding Box) de la ruta
        # Formato MapQuest: lat_max, lng_max, lat_min, lng_min
        bbox = data["route"]["boundingBox"]
        boundingBox_str = f"{bbox['ul']['lat']},{bbox['ul']['lng']},{bbox['lr']['lat']},{bbox['lr']['lng']}"
        
        return maniobras, ruta_precisa, boundingBox_str

    except Exception as e:
        print(f"Error en ruta: {e}")
        return [], [], None

def obtener_incidencias_trafico(api_key, bounding_box):
    """
    Consulta la API de Tráfico para obtener accidentes, obras y congestión
    dentro del área de la ruta.
    """
    if not bounding_box:
        return []

    url = "http://www.mapquestapi.com/traffic/v2/incidents"
    params = {
        "key": api_key,
        "boundingBox": bounding_box,
        "filters": "construction,incidents,congestion" # Qué queremos ver
    }
    
    try:
        print("   -> Consultando estado del tráfico en tiempo real...")
        response = requests.get(url, params=params)
        data = response.json()
        
        if "incidents" in data:
            return data["incidents"]
        else:
            return []
            
    except Exception as e:
        print(f"Error obteniendo tráfico: {e}")
        return []

def construir_grafo_logico(maniobras):
    """Construye el grafo lógico (sin cambios)."""
    G = nx.DiGraph()
    for i in range(len(maniobras) - 1):
        actual = maniobras[i]
        siguiente = maniobras[i+1]
        id_actual = i
        id_siguiente = i + 1
        
        pos_actual = (actual['startPoint']['lat'], actual['startPoint']['lng'])
        pos_siguiente = (siguiente['startPoint']['lat'], siguiente['startPoint']['lng'])
        
        G.add_node(id_actual, pos=pos_actual, desc=actual['narrative'])
        if i == len(maniobras) - 2:
             G.add_node(id_siguiente, pos=pos_siguiente, desc=siguiente['narrative'])

        distancia = actual['distance']
        G.add_edge(id_actual, id_siguiente, weight=distancia)
    return G