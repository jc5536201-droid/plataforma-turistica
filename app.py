from flask import Flask, render_template, request, jsonify
import os
import requests
import heapq
import math
import time

app = Flask(__name__)

# ============================================================
# CONFIGURACIÓN
# ============================================================

OSRM_URL = os.environ.get("OSRM_URL", "https://router.project-osrm.org")
COSTO_POR_KM = 0.15
TIMEOUT = 30
MAX_RETRIES = 3

# ============================================================
# ATRACTIVOS TURÍSTICOS
# ============================================================

ATRACTIVOS = {
    1: {"nombre": "Playa Santa Clara", "cod": "PSC", "tipo": "Playa", "lat": 8.37518, "lng": -80.10355},
    2: {"nombre": "Playa Farallón", "cod": "PFA", "tipo": "Playa", "lat": 8.35658264, "lng": -80.13722992},
    3: {"nombre": "Playa El Salado", "cod": "PES", "tipo": "Playa", "lat": 8.20197, "lng": -80.48368},
    4: {"nombre": "Playa Blanca", "cod": "PBL", "tipo": "Playa", "lat": 8.34535, "lng": -80.15234},
    5: {"nombre": "Playa Juan Hombrón", "cod": "PJH", "tipo": "Playa", "lat": 8.31682, "lng": -80.20536},
    6: {"nombre": "Mercado Artesanía Valle Antón", "cod": "MAV", "tipo": "Cultural", "lat": 8.60409, "lng": -80.13119},
    7: {"nombre": "Serpentario Maravillas Tropicales", "cod": "SMT", "tipo": "Naturaleza", "lat": 8.601521, "lng": -80.115128},
    8: {"nombre": "Museo Hermanos Arias Madrid", "cod": "MHA", "tipo": "Cultural/Hist.", "lat": 8.52508, "lng": -80.35666},
    9: {"nombre": "P.N. Omar Torrijos", "cod": "PNT", "tipo": "Parque Nacional", "lat": 8.6505, "lng": -80.7125},
    10: {"nombre": "Sitio Arqueológico El Caño", "cod": "SAC", "tipo": "Arqueológico", "lat": 8.39542, "lng": -80.50132},
    11: {"nombre": "Museo Regional Stella Sierra", "cod": "MSS", "tipo": "Cultural/Hist.", "lat": 8.24126389, "lng": -80.54030556},
    12: {"nombre": "Iglesia San Juan Bautista", "cod": "ISJ", "tipo": "Histórico", "lat": 8.52198, "lng": -80.35941},
    13: {"nombre": "El Chorro Las Yayas", "cod": "CLY", "tipo": "Cascada", "lat": 8.63911, "lng": -80.58982},
    14: {"nombre": "Balneario Las Mendozas", "cod": "BLM", "tipo": "Balneario", "lat": 8.52645, "lng": -80.35547},
    15: {"nombre": "Penonomé", "cod": "PEN", "tipo": "Hub/Ciudad", "lat": 8.5205, "lng": -80.35958},
    16: {"nombre": "Aguadulce", "cod": "AGU", "tipo": "Hub/Ciudad", "lat": 8.2421, "lng": -80.5391},
    17: {"nombre": "Antón", "cod": "ANT", "tipo": "Hub/Ciudad", "lat": 8.39448, "lng": -80.26635},
    18: {"nombre": "La Pintada", "cod": "LAP", "tipo": "Hub/Ciudad", "lat": 8.59597, "lng": -80.44647},
    19: {"nombre": "Natá", "cod": "NAT", "tipo": "Hub/Ciudad", "lat": 8.33695, "lng": -80.51771},
    20: {"nombre": "Parroquia Ntra. Sra. Candelaria", "cod": "PNC", "tipo": "Histórico", "lat": 8.59597, "lng": -80.44647},
    21: {"nombre": "Cerro Gaital", "cod": "CGA", "tipo": "Montaña", "lat": 8.6256, "lng": -80.13198},
    22: {"nombre": "Museo de Penonomé", "cod": "MPE", "tipo": "Cultural", "lat": 8.51956, "lng": -80.36061},
    23: {"nombre": "Mercado Artesanías La Pintada", "cod": "MLA", "tipo": "Cultural", "lat": 8.5875, "lng": -80.4425},
    24: {"nombre": "Balneario Los Algarrobos", "cod": "BAL", "tipo": "Naturaleza", "lat": 8.5925, "lng": -80.445},
    25: {"nombre": "Iglesia Santiago Apóstol", "cod": "ISA", "tipo": "Histórico", "lat": 8.33189, "lng": -80.51548},
    26: {"nombre": "Ecoparque Don Arcelio", "cod": "ECO", "tipo": "Naturaleza", "lat": 8.38339661, "lng": -80.52890658},
    27: {"nombre": "Salinas de Aguadulce", "cod": "SAL", "tipo": "Naturaleza", "lat": 8.25983, "lng": -80.49883},
    28: {"nombre": "Mariposario", "cod": "MAR", "tipo": "Naturaleza", "lat": 8.601134, "lng": -80.129326},
    29: {"nombre": "Canopy Adventure", "cod": "CAN", "tipo": "Aventura", "lat": 8.62598002, "lng": -80.1388213}
}

# ============================================================
# DISTANCIA GEOGRÁFICA AUXILIAR
# ============================================================

def distancia_haversine(lat1, lon1, lat2, lon2):
    """Calcula la distancia aproximada entre dos coordenadas usando Haversine."""
    radio_tierra = 6371.0
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return radio_tierra * c

# ============================================================
# OBTENER PUNTO MÁS CERCANO A UNA CARRETERA
# ============================================================

def obtener_punto_carretera(lat, lng):
    """Obtiene el punto más cercano en la red vial."""
    url = f"{OSRM_URL}/nearest/v1/driving/{lng},{lat}"
    params = {"number": 1}
    
    for intento in range(MAX_RETRIES):
        try:
            respuesta = requests.get(url, params=params, timeout=TIMEOUT)
            data = respuesta.json()
            
            if respuesta.status_code == 200 and data.get("code") == "Ok":
                waypoint = data["waypoints"][0]
                coordenadas = waypoint["location"]
                return {
                    "lng": coordenadas[0],
                    "lat": coordenadas[1],
                    "exito": True
                }
            time.sleep(1)
        except Exception as e:
            print(f"Intento {intento+1} falló: {e}")
            time.sleep(1)
    
    return {"exito": False, "error": "No se encontró carretera cercana"}

# ============================================================
# AJUSTAR TODOS LOS NODOS A LA RED VIAL
# ============================================================

def ajustar_puntos_a_carreteras():
    """Ajusta todos los puntos turísticos a la red vial."""
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
    """Obtiene la ruta entre dos puntos usando OSRM."""
    url = f"{OSRM_URL}/route/v1/driving/{origen_lng},{origen_lat};{destino_lng},{destino_lat}"
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "true"
    }
    
    for intento in range(MAX_RETRIES):
        try:
            respuesta = requests.get(url, params=params, timeout=TIMEOUT)
            data = respuesta.json()
            
            if respuesta.status_code == 200 and data.get("code") == "Ok":
                ruta = data["routes"][0]
                distancia_km = ruta["distance"] / 1000
                tiempo_min = ruta["duration"] / 60
                costo = distancia_km * COSTO_POR_KM
                
                geometria = ruta["geometry"]["coordinates"]
                puntos_ruta = [[coord[1], coord[0]] for coord in geometria]
                
                instrucciones = []
                for tramo in ruta.get("legs", []):
                    for paso in tramo.get("steps", []):
                        maneuver = paso.get("maneuver", {})
                        instruction = maneuver.get("instruction")
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
            
            time.sleep(1)
        except Exception as e:
            print(f"Intento {intento+1} falló: {e}")
            time.sleep(1)
    
    return {"exito": False, "error": "No se pudo calcular la ruta"}

# ============================================================
# CONSTRUIR MATRIZ DE DISTANCIAS Y TIEMPOS
# ============================================================

def construir_matriz_osrm(puntos):
    """Construye la matriz de distancias y tiempos usando OSRM."""
    ids = list(puntos.keys())
    
    if len(ids) > 25:
        return construir_matriz_aproximada(puntos)
    
    coordenadas = ";".join(
        f"{puntos[nodo]['lng']},{puntos[nodo]['lat']}"
        for nodo in ids
    )
    
    url = f"{OSRM_URL}/table/v1/driving/{coordenadas}"
    params = {"annotations": "duration,distance"}
    
    try:
        respuesta = requests.get(url, params=params, timeout=60)
        data = respuesta.json()
        
        if respuesta.status_code == 200 and data.get("code") == "Ok":
            matriz_distancia = data["distances"]
            matriz_tiempo = data["durations"]
            
            # Limpiar valores nulos
            n = len(ids)
            for i in range(n):
                for j in range(n):
                    if matriz_distancia[i][j] is None or matriz_distancia[i][j] == 0:
                        if i != j:
                            dist = distancia_haversine(
                                puntos[ids[i]]["lat"], puntos[ids[i]]["lng"],
                                puntos[ids[j]]["lat"], puntos[ids[j]]["lng"]
                            )
                            matriz_distancia[i][j] = dist * 1000
                            matriz_tiempo[i][j] = (dist / 40) * 3600
            
            return ids, matriz_distancia, matriz_tiempo
        
        return construir_matriz_aproximada(puntos)
        
    except Exception as e:
        print("Error construyendo matriz:", e)
        return construir_matriz_aproximada(puntos)

# ============================================================
# MATRIZ APROXIMADA (FALLBACK)
# ============================================================

def construir_matriz_aproximada(puntos):
    """Construye una matriz aproximada usando distancia Haversine."""
    ids = list(puntos.keys())
    n = len(ids)
    
    matriz_distancia = [[0.0] * n for _ in range(n)]
    matriz_tiempo = [[0.0] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(n):
            if i != j:
                dist = distancia_haversine(
                    puntos[ids[i]]["lat"], puntos[ids[i]]["lng"],
                    puntos[ids[j]]["lat"], puntos[ids[j]]["lng"]
                )
                matriz_distancia[i][j] = dist * 1000  # metros
                matriz_tiempo[i][j] = (dist / 40) * 3600  # 40 km/h
    
    return ids, matriz_distancia, matriz_tiempo

# ============================================================
# CONSTRUIR GRAFO
# ============================================================

def construir_grafo(puntos):
    """Construye el grafo de rutas entre todos los puntos."""
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
    """Prepara el grafo con todos los puntos ajustados a la red vial."""
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
    """Algoritmo de Dijkstra para encontrar la ruta óptima."""
    pesos = {
        "distancia": "distancia_km",
        "tiempo": "tiempo_min",
        "costo": "costo"
    }
    
    if criterio not in pesos:
        criterio = "tiempo"
    
    campo_peso = pesos[criterio]
    
    # Verificar si origen y destino están en el grafo
    if origen not in grafo or destino not in grafo:
        return None
    
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
        
        vecinos = grafo.get(nodo_actual, {})
        for vecino, datos in vecinos.items():
            peso = datos.get(campo_peso, 0)
            if peso <= 0:
                continue
            
            nueva_distancia = distancia_actual + peso
            
            if nueva_distancia < distancias[vecino]:
                distancias[vecino] = nueva_distancia
                anteriores[vecino] = nodo_actual
                heapq.heappush(cola_prioridad, (nueva_distancia, vecino))
    
    if distancias.get(destino, float("inf")) == float("inf"):
        return None
    
    # Reconstruir camino
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
    """Obtiene la geometría completa del camino con todos los puntos intermedios."""
    if not camino or len(camino) < 2:
        return []
    
    # Construir puntos para la ruta
    puntos = []
    for nodo in camino:
        if nodo in PUNTOS_AJUSTADOS:
            puntos.append({
                "lat": PUNTOS_AJUSTADOS[nodo]["lat"],
                "lng": PUNTOS_AJUSTADOS[nodo]["lng"]
            })
        elif nodo in ATRACTIVOS:
            puntos.append({
                "lat": ATRACTIVOS[nodo]["lat"],
                "lng": ATRACTIVOS[nodo]["lng"]
            })
    
    # Si tenemos más de 2 puntos, unirlos en una ruta
    if len(puntos) >= 2:
        coord_str = ";".join(f"{p['lng']},{p['lat']}" for p in puntos)
        url = f"{OSRM_URL}/route/v1/driving/{coord_str}"
        params = {"overview": "full", "geometries": "geojson", "steps": "true"}
        
        try:
            respuesta = requests.get(url, params=params, timeout=60)
            data = respuesta.json()
            
            if respuesta.status_code == 200 and data.get("code") == "Ok":
                ruta = data["routes"][0]
                geometria = ruta["geometry"]["coordinates"]
                return [[coord[1], coord[0]] for coord in geometria]
        except:
            pass
        
        # Fallback: puntos rectos entre los nodos
        puntos_ruta = []
        for i in range(len(puntos) - 1):
            inicio = puntos[i]
            fin = puntos[i + 1]
            num_puntos = 20
            for j in range(num_puntos):
                t = j / num_puntos
                lat = inicio["lat"] + (fin["lat"] - inicio["lat"]) * t
                lng = inicio["lng"] + (fin["lng"] - inicio["lng"]) * t
                puntos_ruta.append([lat, lng])
            puntos_ruta.append([fin["lat"], fin["lng"]])
        
        return puntos_ruta
    
    return []

# ============================================================
# RUTAS DE LA API
# ============================================================

@app.route("/")
def index():
    """Página principal."""
    return render_template("index.html", atractivos=ATRACTIVOS)

@app.route("/api/ruta", methods=["POST"])
def api_ruta():
    """API para calcular la ruta óptima usando Dijkstra."""
    try:
        data = request.get_json()
        origen = int(data["origen"])
        destino = int(data["destino"])
        criterio = data.get("criterio", "tiempo")
        
        # Validar nodos
        if origen not in ATRACTIVOS:
            return jsonify({"exito": False, "error": "El nodo de origen no existe."}), 400
        
        if destino not in ATRACTIVOS:
            return jsonify({"exito": False, "error": "El nodo de destino no existe."}), 400
        
        if origen == destino:
            return jsonify({"exito": False, "error": "El origen y destino no pueden ser iguales."}), 400
        
        # Asegurar que el grafo esté preparado
        if not GRAFO:
            preparar_grafo()
        
        # Ejecutar Dijkstra
        resultado_dijkstra = dijkstra(GRAFO, origen, destino, criterio)
        
        if resultado_dijkstra is None:
            return jsonify({
                "exito": False,
                "error": "No se encontró un camino entre los nodos seleccionados."
            }), 404
        
        camino = resultado_dijkstra["camino"]
        
        # Obtener geometría de la ruta
        puntos_ruta = obtener_geometria_camino(camino)
        
        # Calcular datos totales
        distancia_total = 0
        tiempo_total = 0
        costo_total = 0
        segmentos = []
        
        for i in range(len(camino) - 1):
            nodo_a = camino[i]
            nodo_b = camino[i + 1]
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
        
        # Nodos del camino
        nodos_ruta = []
        for nodo in camino:
            nodos_ruta.append({
                "id": nodo,
                **ATRACTIVOS[nodo],
                "lat_ruta": PUNTOS_AJUSTADOS[nodo]["lat"],
                "lng_ruta": PUNTOS_AJUSTADOS[nodo]["lng"],
                "lat_carretera": PUNTOS_AJUSTADOS[nodo]["lat"],
                "lng_carretera": PUNTOS_AJUSTADOS[nodo]["lng"]
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

@app.route("/api/coordenadas")
def api_coordenadas():
    """API para obtener todas las coordenadas de los atractivos."""
    if not PUNTOS_AJUSTADOS:
        preparar_grafo()
    
    resultado = {}
    for nodo, datos in PUNTOS_AJUSTADOS.items():
        resultado[nodo] = {
            "nombre": datos["nombre"],
            "cod": datos["cod"],
            "tipo": datos["tipo"],
            "lat": datos.get("lat_original", datos["lat"]),
            "lng": datos.get("lng_original", datos["lng"]),
            "lat_original": datos.get("lat_original", datos["lat"]),
            "lng_original": datos.get("lng_original", datos["lng"]),
            "lat_carretera": datos["lat"],
            "lng_carretera": datos["lng"]
        }
    
    return jsonify(resultado)

@app.route("/api/grafo")
def api_grafo():
    """API para obtener el grafo completo."""
    if not GRAFO:
        preparar_grafo()
    return jsonify(GRAFO)

@app.route("/api/verificacion")
def api_verificacion():
    """Devuelve coordenadas originales y ajustadas a la red vial."""
    if not PUNTOS_AJUSTADOS:
        preparar_grafo()
    
    resultado = {}
    for nodo, atractivo in ATRACTIVOS.items():
        ajustado = PUNTOS_AJUSTADOS.get(nodo, {})
        resultado[nodo] = {
            "nombre": atractivo["nombre"],
            "lat_original": atractivo["lat"],
            "lng_original": atractivo["lng"],
            "lat_carretera": ajustado.get("lat", atractivo["lat"]),
            "lng_carretera": ajustado.get("lng", atractivo["lng"]),
        }
    return jsonify(resultado)

@app.route("/api/dias")
def api_dias():
    """Itinerarios de 7 días."""
    dias = [
        {"dia": 1, "destinos": [1, 2, 4, 5, 17], "zona": "🌊 Playas de Antón"},
        {"dia": 2, "destinos": [8, 22, 12, 14, 15], "zona": "🏛️ Penonomé Histórico"},
        {"dia": 3, "destinos": [18, 20, 23, 24, 13, 9], "zona": "⛰️ La Pintada - Montaña"},
        {"dia": 4, "destinos": [10, 25, 26, 19], "zona": "🏺 Ruta Arqueológica de Natá"},
        {"dia": 5, "destinos": [6, 7, 28, 21, 29], "zona": "🌿 Naturaleza de Antón"},
        {"dia": 6, "destinos": [16, 3, 27, 11], "zona": "🌅 Tesoros de Aguadulce"},
        {"dia": 7, "destinos": [15, 18, 20, 23, 24], "zona": "🎯 Circuito Integrador"}
    ]
    return jsonify(dias)

# ============================================================
# INICIO DE LA APLICACIÓN
# ============================================================

if __name__ == "__main__":
    print("==========================================")
    print(" RUTAS TURÍSTICAS DE COCLÉ")
    print(" Optimización mediante Dijkstra")
    print("==========================================")
    print(f"Atractivos registrados: {len(ATRACTIVOS)}")
    print("Servidor iniciado.")
    
    # Preparar el grafo al inicio (opcional)
    # preparar_grafo()
    
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1"
    )
