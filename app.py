from flask import Flask, render_template, request, jsonify
import os
import requests
import heapq
import math

app = Flask(__name__)

# ============================================================
# CONFIGURACIÓN
# ============================================================

OSRM_URL = os.environ.get("OSRM_URL", "https://router.project-osrm.org")
COSTO_POR_KM = 0.15

# ============================================================
# ATRACTIVOS TURÍSTICOS (CON COORDENADAS CORREGIDAS)
# ============================================================

ATRACTIVOS = {
    1: {"nombre": "Playa Santa Clara", "cod": "PSC", "tipo": "Playa", "lat": 8.3976, "lng": -80.1148},
    2: {"nombre": "Playa Farallón", "cod": "PFA", "tipo": "Playa", "lat": 8.3782, "lng": -80.1275},
    3: {"nombre": "Playa El Salado", "cod": "PES", "tipo": "Playa", "lat": 8.1990, "lng": -80.5460},
    4: {"nombre": "Playa Blanca", "cod": "PBL", "tipo": "Playa", "lat": 8.3480, "lng": -80.0875},
    5: {"nombre": "Playa Juan Hombrón", "cod": "PJH", "tipo": "Playa", "lat": 8.2985, "lng": -80.0670},
    6: {"nombre": "Mercado Artesanía Valle Antón", "cod": "MAV", "tipo": "Cultural", "lat": 8.6185, "lng": -80.1270},
    7: {"nombre": "Serpentario Maravillas Tropicales", "cod": "SMT", "tipo": "Naturaleza", "lat": 8.6280, "lng": -80.1370},
    8: {"nombre": "Museo Hermanos Arias Madrid", "cod": "MHA", "tipo": "Cultural/Hist.", "lat": 8.5185, "lng": -80.3575},
    9: {"nombre": "P.N. Omar Torrijos", "cod": "PNT", "tipo": "Parque Nacional", "lat": 8.5480, "lng": -80.5870},
    10: {"nombre": "Sitio Arqueológico El Caño", "cod": "SAC", "tipo": "Arqueológico", "lat": 8.3985, "lng": -80.5170},
    11: {"nombre": "Museo Regional Stella Sierra", "cod": "MSS", "tipo": "Cultural/Hist.", "lat": 8.2485, "lng": -80.5470},
    12: {"nombre": "Iglesia San Juan Bautista", "cod": "ISJ", "tipo": "Histórico", "lat": 8.5180, "lng": -80.3570},
    13: {"nombre": "El Chorro Las Yayas", "cod": "CLY", "tipo": "Cascada", "lat": 8.5485, "lng": -80.6770},
    14: {"nombre": "Balneario Las Mendozas", "cod": "BLM", "tipo": "Balneario", "lat": 8.5180, "lng": -80.3270},
    15: {"nombre": "Penonomé", "cod": "PEN", "tipo": "Hub/Ciudad", "lat": 8.5185, "lng": -80.3475},
    16: {"nombre": "Aguadulce", "cod": "AGU", "tipo": "Hub/Ciudad", "lat": 8.2385, "lng": -80.5470},
    17: {"nombre": "Antón", "cod": "ANT", "tipo": "Hub/Ciudad", "lat": 8.3985, "lng": -80.2575},
    18: {"nombre": "La Pintada", "cod": "LAP", "tipo": "Hub/Ciudad", "lat": 8.5985, "lng": -80.4370},
    19: {"nombre": "Natá", "cod": "NAT", "tipo": "Hub/Ciudad", "lat": 8.3285, "lng": -80.5170},
    20: {"nombre": "Parroquia Ntra. Sra. Candelaria", "cod": "PNC", "tipo": "Histórico", "lat": 8.5980, "lng": -80.4370},
    21: {"nombre": "Cerro Gaital", "cod": "CGA", "tipo": "Montaña", "lat": 8.6185, "lng": -80.1170},
    22: {"nombre": "Museo de Penonomé", "cod": "MPE", "tipo": "Cultural", "lat": 8.5180, "lng": -80.3470},
    23: {"nombre": "Mercado Artesanías La Pintada", "cod": "MLA", "tipo": "Cultural", "lat": 8.5985, "lng": -80.4375},
    24: {"nombre": "Balneario Los Algarrobos", "cod": "BAL", "tipo": "Naturaleza", "lat": 8.5980, "lng": -80.4370},
    25: {"nombre": "Iglesia Santiago Apóstol", "cod": "ISA", "tipo": "Histórico", "lat": 8.3280, "lng": -80.5175},
    26: {"nombre": "Ecoparque Don Arcelio", "cod": "ECO", "tipo": "Naturaleza", "lat": 8.3285, "lng": -80.5170},
    27: {"nombre": "Salinas de Aguadulce", "cod": "SAL", "tipo": "Naturaleza", "lat": 8.2380, "lng": -80.5475},
    28: {"nombre": "Mariposario", "cod": "MAR", "tipo": "Naturaleza", "lat": 8.3980, "lng": -80.2570},
    29: {"nombre": "Canopy Adventure", "cod": "CAN", "tipo": "Aventura", "lat": 8.3985, "lng": -80.2570},
}

# ============================================================
# DISTANCIA GEOGRÁFICA AUXILIAR
# ============================================================

def distancia_haversine(lat1, lon1, lat2, lon2):
    radio_tierra = 6371.0
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return radio_tierra * c

# ============================================================
# OBTENER PUNTO MÁS CERCANO A UNA CARRETERA
# ============================================================

def obtener_punto_carretera(lat, lng):
    url = f"{OSRM_URL}/nearest/v1/driving/{lng},{lat}"
    params = {"number": 1}
    try:
        respuesta = requests.get(url, params=params, timeout=30)
        data = respuesta.json()
        if respuesta.status_code == 200 and data.get("code") == "Ok":
            waypoint = data["waypoints"][0]
            coordenadas = waypoint["location"]
            return {
                "lng": coordenadas[0],
                "lat": coordenadas[1],
                "exito": True
            }
        return {"exito": False}
    except Exception as e:
        return {"exito": False}

# ============================================================
# AJUSTAR TODOS LOS NODOS A LA RED VIAL
# ============================================================

def ajustar_puntos_a_carreteras():
    puntos_ajustados = {}
    for nodo_id, atractivo in ATRACTIVOS.items():
        resultado = obtener_punto_carretera(atractivo["lat"], atractivo["lng"])
        if resultado["exito"]:
            puntos_ajustados[nodo_id] = {
                **atractivo,
                "lat_original": atractivo["lat"],
                "lng_original": atractivo["lng"],
                "lat": resultado["lat"],
                "lng": resultado["lng"]
            }
        else:
            puntos_ajustados[nodo_id] = {
                **atractivo,
                "lat_original": atractivo["lat"],
                "lng_original": atractivo["lng"]
            }
    return puntos_ajustados

# ============================================================
# OBTENER RUTA ENTRE DOS PUNTOS
# ============================================================

def obtener_ruta_osrm(origen_lat, origen_lng, destino_lat, destino_lng):
    url = f"{OSRM_URL}/route/v1/driving/{origen_lng},{origen_lat};{destino_lng},{destino_lat}"
    params = {"overview": "full", "geometries": "geojson", "steps": "true", "radiuses": "1000;1000"}
    try:
        respuesta = requests.get(url, params=params, timeout=30)
        data = respuesta.json()
        if respuesta.status_code != 200 or data.get("code") != "Ok":
            return {"exito": False, "error": data.get("message", "Error en OSRM")}
        ruta = data["routes"][0]
        distancia_km = ruta["distance"] / 1000
        tiempo_min = ruta["duration"] / 60
        costo = distancia_km * COSTO_POR_KM
        geometria = ruta["geometry"]["coordinates"]
        puntos_ruta = [[coord[1], coord[0]] for coord in geometria]
        instrucciones = []
        for tramo in ruta.get("legs", []):
            for paso in tramo.get("steps", []):
                instruction = paso.get("maneuver", {}).get("instruction")
                if instruction:
                    instrucciones.append(instruction)
        return {
            "distancia_km": round(distancia_km, 2),
            "tiempo_min": round(tiempo_min),
            "costo": round(costo, 2),
            "puntos_ruta": puntos_ruta,
            "instrucciones": instrucciones,
            "exito": True
        }
    except Exception as e:
        return {"exito": False, "error": str(e)}

# ============================================================
# CONSTRUIR MATRIZ DE DISTANCIAS Y TIEMPOS
# ============================================================

def construir_matriz_osrm(puntos):
    ids = list(puntos.keys())
    coordenadas = ";".join(f"{puntos[nodo]['lng']},{puntos[nodo]['lat']}" for nodo in ids)
    url = f"{OSRM_URL}/table/v1/driving/{coordenadas}"
    params = {"annotations": "duration,distance"}
    try:
        respuesta = requests.get(url, params=params, timeout=60)
        data = respuesta.json()
        if respuesta.status_code != 200 or data.get("code") != "Ok":
            return None, None, None
        return ids, data["distances"], data["durations"]
    except Exception as e:
        print("Error construyendo matriz:", e)
        return None, None, None

# ============================================================
# CONSTRUIR GRAFO
# ============================================================

def construir_grafo(puntos):
    ids, matriz_distancia, matriz_tiempo = construir_matriz_osrm(puntos)
    if ids is None:
        return {}
    grafo = {}
    for i, nodo_origen in enumerate(ids):
        grafo[nodo_origen] = {}
        for j, nodo_destino in enumerate(ids):
            if i == j:
                continue
            distancia_metros = matriz_distancia[i][j]
            tiempo_segundos = matriz_tiempo[i][j]
            if distancia_metros is None or tiempo_segundos is None:
                continue
            distancia_km = distancia_metros / 1000
            tiempo_min = tiempo_segundos / 60
            costo = distancia_km * COSTO_POR_KM
            grafo[nodo_origen][nodo_destino] = {
                "distancia_km": round(distancia_km, 2),
                "tiempo_min": round(tiempo_min, 2),
                "costo": round(costo, 2)
            }
    return grafo

# ============================================================
# PREPARAR GRAFO
# ============================================================

GRAFO = {}
PUNTOS_AJUSTADOS = {}

def preparar_grafo():
    global GRAFO, PUNTOS_AJUSTADOS
    print("Preparando red vial...")
    PUNTOS_AJUSTADOS = ajustar_puntos_a_carreteras()
    print("Construyendo matriz de rutas...")
    GRAFO = construir_grafo(PUNTOS_AJUSTADOS)
    print(f"Grafo construido con {len(GRAFO)} nodos.")

# ============================================================
# DIJKSTRA
# ============================================================

def dijkstra(grafo, origen, destino, criterio):
    pesos = {"distancia": "distancia_km", "tiempo": "tiempo_min", "costo": "costo"}
    if criterio not in pesos:
        criterio = "tiempo"
    campo_peso = pesos[criterio]
    distancias = {nodo: float("inf") for nodo in grafo}
    anteriores = {nodo: None for nodo in grafo}
    distancias[origen] = 0
    cola_prioridad = [(0, origen)]
    while cola_prioridad:
        distancia_actual, nodo_actual = heapq.heappop(cola_prioridad)
        if distancia_actual > distancias[nodo_actual]:
            continue
        if nodo_actual == destino:
            break
        for vecino, datos in grafo.get(nodo_actual, {}).items():
            peso = datos[campo_peso]
            nueva_distancia = distancia_actual + peso
            if nueva_distancia < distancias[vecino]:
                distancias[vecino] = nueva_distancia
                anteriores[vecino] = nodo_actual
                heapq.heappush(cola_prioridad, (nueva_distancia, vecino))
    if distancias.get(destino, float("inf")) == float("inf"):
        return None
    camino = []
    nodo = destino
    while nodo is not None:
        camino.append(nodo)
        nodo = anteriores[nodo]
    camino.reverse()
    return {
        "camino": camino,
        "peso_total": round(distancias[destino], 2),
        "criterio": criterio
    }

# ============================================================
# OBTENER GEOMETRÍA COMPLETA DEL CAMINO
# ============================================================

def obtener_geometria_camino(camino):
    if not camino or len(camino) < 2:
        return []
    coordenadas = ";".join(f"{PUNTOS_AJUSTADOS[nodo]['lng']},{PUNTOS_AJUSTADOS[nodo]['lat']}" for nodo in camino)
    url = f"{OSRM_URL}/route/v1/driving/{coordenadas}"
    params = {"overview": "full", "geometries": "geojson", "steps": "true"}
    try:
        respuesta = requests.get(url, params=params, timeout=60)
        data = respuesta.json()
        if respuesta.status_code != 200 or data.get("code") != "Ok":
            return []
        ruta = data["routes"][0]
        geometria = ruta["geometry"]["coordinates"]
        return [[coord[1], coord[0]] for coord in geometria]
    except Exception as e:
        print("Error obteniendo geometría:", e)
        return []

# ============================================================
# RUTAS DE LA PÁGINA WEB
# ============================================================

@app.route("/")
def index():
    return render_template("index.html", atractivos=ATRACTIVOS)

@app.route("/api/ruta", methods=["POST"])
def api_ruta():
    try:
        data = request.get_json()
        origen = int(data["origen"])
        destino = int(data["destino"])
        criterio = data.get("criterio", "tiempo")
        
        if origen not in ATRACTIVOS or destino not in ATRACTIVOS:
            return jsonify({"exito": False, "error": "Nodo no existe"}), 400
        if origen == destino:
            return jsonify({"exito": False, "error": "Origen y destino iguales"}), 400
        
        if not GRAFO:
            preparar_grafo()
        
        resultado_dijkstra = dijkstra(GRAFO, origen, destino, criterio)
        if resultado_dijkstra is None:
            return jsonify({"exito": False, "error": "No se encontró camino"}), 404
        
        camino = resultado_dijkstra["camino"]
        puntos_ruta = obtener_geometria_camino(camino)
        
        distancia_total = 0
        tiempo_total = 0
        costo_total = 0
        segmentos = []
        
        for i in range(len(camino) - 1):
            nodo_a = camino[i]
            nodo_b = camino[i+1]
            datos_segmento = GRAFO[nodo_a][nodo_b]
            distancia_total += datos_segmento["distancia_km"]
            tiempo_total += datos_segmento["tiempo_min"]
            costo_total += datos_segmento["costo"]
            segmentos.append({
                "origen": nodo_a,
                "destino": nodo_b,
                "distancia_km": datos_segmento["distancia_km"],
                "tiempo_min": datos_segmento["tiempo_min"],
                "costo": datos_segmento["costo"]
            })
        
        # ====================================================
        # NODOS DEL CAMINO CON COORDENADAS AJUSTADAS
        # ====================================================
        nodos_ruta = []
        for nodo in camino:
            ajustado = PUNTOS_AJUSTADOS[nodo]
            nodos_ruta.append({
                "id": nodo,
                "nombre": ATRACTIVOS[nodo]["nombre"],
                "cod": ATRACTIVOS[nodo]["cod"],
                "tipo": ATRACTIVOS[nodo]["tipo"],
                # Coordenadas ORIGINALES (donde está el atractivo)
                "lat": ATRACTIVOS[nodo]["lat"],
                "lng": ATRACTIVOS[nodo]["lng"],
                # Coordenadas en CARRETERA (donde va la ruta)
                "lat_carretera": ajustado.get("lat", ATRACTIVOS[nodo]["lat"]),
                "lng_carretera": ajustado.get("lng", ATRACTIVOS[nodo]["lng"])
            })
        
        return jsonify({
            "exito": True,
            "origen": origen,
            "destino": destino,
            "criterio": criterio,
            "camino": camino,
            "nodos_ruta": nodos_ruta,
            "distancia_km": round(distancia_total, 2),
            "tiempo_min": round(tiempo_total),
            "costo": round(costo_total, 2),
            "puntos_ruta": puntos_ruta,
            "segmentos": segmentos,
            "nodos_visitados": len(camino)
        })
    except Exception as e:
        print("ERROR API RUTA:", e)
        return jsonify({"exito": False, "error": str(e)}), 500

@app.route("/api/dias")
def api_dias():
    dias = [
        {"dia": 1, "destinos": [1, 2, 4, 5, 17], "zona": "🌊 Playas de Antón"},
        {"dia": 2, "destinos": [8, 22, 12, 14, 15], "zona": "🏛️ Penonomé Histórico"},
        {"dia": 3, "destinos": [18, 20, 23, 24, 13, 9], "zona": "⛰️ La Pintada - Montaña"},
        {"dia": 4, "destinos": [10, 25, 26, 19], "zona": "🏺 Ruta Arqueológica de Natá"},
        {"dia": 5, "destinos": [6, 7, 28, 21, 29], "zona": "🌿 Naturaleza de Antón"},
        {"dia": 6, "destinos": [16, 3, 27, 11], "zona": "🌅 Tesoros de Aguadulce"},
        {"dia": 7, "destinos": [15, 18, 20, 23, 24], "zona": "🎯 Circuito Integrador"},
    ]
    return jsonify(dias)

if __name__ == "__main__":
    print("==========================================")
    print(" RUTAS TURÍSTICAS DE COCLÉ")
    print(" Optimización mediante Dijkstra")
    print("==========================================")
    print(f"Atractivos registrados: {len(ATRACTIVOS)}")
    print("Servidor iniciado.")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
