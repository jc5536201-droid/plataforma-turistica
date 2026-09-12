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

VELOCIDAD_FALLBACK_KMH = 40

FACTOR_HOLGURA = float(os.environ.get("FACTOR_HOLGURA", "1.25"))

ATRACTIVOS_GOOGLE = {
    1: {"nombre": "Playa Santa Clara", "cod": "PSC", "tipo": "Playa",
        "lat": 8.37388, "lng": -80.10569,
        "descripcion": "Playa de arena blanca y aguas tranquilas"},
    2: {"nombre": "Playa Farallón", "cod": "PFA", "tipo": "Playa",
        "lat": 8.3613, "lng": -80.12977,
        "descripcion": "Playa con olas moderadas y arena dorada"},
    3: {"nombre": "Playa El Salado", "cod": "PES", "tipo": "Playa",
        "lat": 8.20159, "lng": -80.48353,
        "descripcion": "Playa tranquila cerca de Aguadulce"},
    4: {"nombre": "Playa Blanca", "cod": "PBL", "tipo": "Playa",
        "lat": 8.34595, "lng": -80.15175,
        "descripcion": "Hermosa playa de arena blanca"},
    5: {"nombre": "Playa Juan Hombrón", "cod": "PJH", "tipo": "Playa",
        "lat": 8.29827, "lng": -80.25338,
        "descripcion": "Playa con aguas cristalinas"},
    6: {"nombre": "Mercado Artesanía Valle Antón", "cod": "MAV", "tipo": "Cultural",
        "lat": 8.60408, "lng": -80.13115,
        "descripcion": "Mercado de artesanías típicas"},
    7: {"nombre": "Serpentario Maravillas Tropicales", "cod": "SMT", "tipo": "Naturaleza",
        "lat": 8.60162, "lng": -80.11503,
        "descripcion": "Exhibición de serpientes y reptiles"},
    8: {"nombre": "Museo Hermanos Arias Madrid", "cod": "MHA", "tipo": "Cultural/Hist.",
        "lat": 8.52497, "lng": -80.35677,
        "descripcion": "Museo histórico en Penonomé"},
    9: {"nombre": "P.N. Omar Torrijos", "cod": "PNT", "tipo": "Parque Nacional",
        "lat": 8.68788, "lng": -80.64378,
        "descripcion": "Parque Nacional con senderos ecológicos"},
    10: {"nombre": "Sitio Arqueológico El Caño", "cod": "SAC", "tipo": "Arqueológico",
         "lat": 8.3967, "lng": -80.50148,
         "descripcion": "Importante sitio arqueológico precolombino"},
    11: {"nombre": "Museo Regional Stella Sierra", "cod": "MSS", "tipo": "Cultural/Hist.",
         "lat": 8.24104, "lng": -80.5398,
         "descripcion": "Museo regional en Aguadulce"},
    12: {"nombre": "Iglesia San Juan Bautista", "cod": "ISJ", "tipo": "Histórico",
         "lat": 8.52188, "lng": -80.35936,
         "descripcion": "Iglesia histórica en Penonomé"},
    13: {"nombre": "El Chorro Las Yayas", "cod": "CLY", "tipo": "Cascada",
         "lat": 8.64588, "lng": -80.58997,
         "descripcion": "Hermosa cascada en La Pintada"},
    14: {"nombre": "Balneario Las Mendozas", "cod": "BLM", "tipo": "Balneario",
         "lat": 8.52654, "lng": -80.35536,
         "descripcion": "Balneario natural cerca de Penonomé"},
    15: {"nombre": "Penonomé", "cod": "PEN", "tipo": "Hub/Ciudad",
         "lat": 8.55029, "lng": -80.35474,
         "descripcion": "Capital de la provincia de Coclé"},
    16: {"nombre": "Aguadulce", "cod": "AGU", "tipo": "Hub/Ciudad",
         "lat": 8.23017, "lng": -80.55495,
         "descripcion": "Ciudad conocida por sus salinas"},
    17: {"nombre": "Antón", "cod": "ANT", "tipo": "Hub/Ciudad",
         "lat": 8.40186, "lng": -80.27115,
         "descripcion": "Ciudad cerca de las playas"},
    18: {"nombre": "La Pintada", "cod": "LAP", "tipo": "Hub/Ciudad",
         "lat": 8.59331, "lng": -80.44655,
         "descripcion": "Ciudad conocida por sus artesanías"},
    19: {"nombre": "Natá", "cod": "NAT", "tipo": "Hub/Ciudad",
         "lat": 8.30297, "lng": -80.43265,
         "descripcion": "Ciudad histórica con iglesia colonial"},
    20: {"nombre": "Parroquia Ntra. Sra. Candelaria", "cod": "PNC", "tipo": "Histórico",
         "lat": 8.59308, "lng": -80.44582,
         "descripcion": "Iglesia histórica en La Pintada"},
    21: {"nombre": "Cerro Gaital", "cod": "CGA", "tipo": "Montaña",
         "lat": 8.61666, "lng": -80.11666,
         "descripcion": "Cerro con vista panorámica"},
    22: {"nombre": "Museo de Penonomé", "cod": "MPE", "tipo": "Cultural",
         "lat": 8.51959, "lng": -80.36056,
         "descripcion": "Museo histórico en Penonomé"},
    23: {"nombre": "Mercado Artesanías La Pintada", "cod": "MLA", "tipo": "Cultural",
         "lat": 8.59702, "lng": -80.44881,
         "descripcion": "Mercado de artesanías en La Pintada"},
    24: {"nombre": "Balneario Los Algarrobos", "cod": "BAL", "tipo": "Naturaleza",
         "lat": 8.59377, "lng": -80.44295,
         "descripcion": "Balneario natural cerca de La Pintada"},
    25: {"nombre": "Iglesia Santiago Apóstol", "cod": "ISA", "tipo": "Histórico",
         "lat": 8.33215, "lng": -80.51524,
         "descripcion": "Iglesia colonial en Natá"},
    26: {"nombre": "Ecoparque Don Arcelio", "cod": "ECO", "tipo": "Naturaleza",
         "lat": 8.38084, "lng": -80.5289,
         "descripcion": "Parque ecológico cerca de Natá"},
    27: {"nombre": "Salinas de Aguadulce", "cod": "SAL", "tipo": "Naturaleza",
         "lat": 8.20203, "lng": -80.4962,
         "descripcion": "Salinas tradicionales"},
    28: {"nombre": "Mariposario", "cod": "MAR", "tipo": "Naturaleza",
         "lat": 8.60141, "lng": -80.12923,
         "descripcion": "Jardín de mariposas"},
    29: {"nombre": "Canopy Adventure", "cod": "CAN", "tipo": "Aventura",
         "lat": 8.62585, "lng": -80.1387,
         "descripcion": "Tirolesa y aventura en la selva"}
}

ATRACTIVOS_OSM = {
    1: {"nombre": "Playa Santa Clara", "cod": "PSC", "tipo": "Playa",
        "lat": 8.37571, "lng": -80.10372,
        "descripcion": "Playa de arena blanca y aguas tranquilas"},
    2: {"nombre": "Playa Farallón", "cod": "PFA", "tipo": "Playa",
        "lat": 8.35894, "lng": -80.13333,
        "descripcion": "Playa con olas moderadas y arena dorada"},
    3: {"nombre": "Playa El Salado", "cod": "PES", "tipo": "Playa",
        "lat": 8.202045, "lng": -80.483697,
        "descripcion": "Playa tranquila cerca de Aguadulce"},
    4: {"nombre": "Playa Blanca", "cod": "PBL", "tipo": "Playa",
        "lat": 8.34490, "lng": -80.15400,
        "descripcion": "Hermosa playa de arena blanca"},
    5: {"nombre": "Playa Juan Hombrón", "cod": "PJH", "tipo": "Playa",
        "lat": 8.319702725314118, "lng": -80.205259322496,
        "descripcion": "Playa con aguas cristalinas"},
    6: {"nombre": "Mercado Artesanía Valle Antón", "cod": "MAV", "tipo": "Cultural",
        "lat": 8.604108, "lng": -80.131198,
        "descripcion": "Mercado de artesanías típicas"},
    7: {"nombre": "Serpentario Maravillas Tropicales", "cod": "SMT", "tipo": "Naturaleza",
        "lat": 8.6011942, "lng": -80.1152153,
        "descripcion": "Exhibición de serpientes y reptiles"},
    8: {"nombre": "Museo Hermanos Arias Madrid", "cod": "MHA", "tipo": "Cultural/Hist.",
        "lat": 8.525075, "lng": -80.356665,
        "descripcion": "Museo histórico en Penonomé"},
    9: {"nombre": "P.N. Omar Torrijos", "cod": "PNT", "tipo": "Parque Nacional",
        "lat": 8.6554, "lng": -80.7008,
        "descripcion": "Parque Nacional con senderos ecológicos"},
    10: {"nombre": "Sitio Arqueológico El Caño", "cod": "SAC", "tipo": "Arqueológico",
         "lat": 8.396716, "lng": -80.501499,
         "descripcion": "Importante sitio arqueológico precolombino"},
    11: {"nombre": "Museo Regional Stella Sierra", "cod": "MSS", "tipo": "Cultural/Hist.",
         "lat": 8.241049, "lng": -80.539833,
         "descripcion": "Museo regional en Aguadulce"},
    12: {"nombre": "Iglesia San Juan Bautista", "cod": "ISJ", "tipo": "Histórico",
         "lat": 8.521929, "lng": -80.359489,
         "descripcion": "Iglesia histórica en Penonomé"},
    13: {"nombre": "El Chorro Las Yayas", "cod": "CLY", "tipo": "Cascada",
         "lat": 8.645952, "lng": -80.590030,
         "descripcion": "Hermosa cascada en La Pintada"},
    14: {"nombre": "Balneario Las Mendozas", "cod": "BLM", "tipo": "Balneario",
         "lat": 8.526422, "lng": -80.355455,
         "descripcion": "Balneario natural cerca de Penonomé"},
    15: {"nombre": "Penonomé", "cod": "PEN", "tipo": "Hub/Ciudad",
         "lat": 8.5260, "lng": -80.3616,
         "descripcion": "Capital de la provincia de Coclé"},
    16: {"nombre": "Aguadulce", "cod": "AGU", "tipo": "Hub/Ciudad",
         "lat": 8.24275, "lng": -80.53888,
         "descripcion": "Ciudad conocida por sus salinas"},
    17: {"nombre": "Antón", "cod": "ANT", "tipo": "Hub/Ciudad",
         "lat": 8.3944820, "lng": -80.2663470,
         "descripcion": "Ciudad cerca de las playas"},
    18: {"nombre": "La Pintada", "cod": "LAP", "tipo": "Hub/Ciudad",
         "lat": 8.5963, "lng": -80.4467,
         "descripcion": "Ciudad conocida por sus artesanías"},
    19: {"nombre": "Natá", "cod": "NAT", "tipo": "Hub/Ciudad",
         "lat": 8.33686, "lng": -80.51725,
         "descripcion": "Ciudad histórica con iglesia colonial"},
    20: {"nombre": "Parroquia Ntra. Sra. Candelaria", "cod": "PNC", "tipo": "Histórico",
         "lat": 8.593051, "lng": -80.445811,
         "descripcion": "Iglesia histórica en La Pintada"},
    21: {"nombre": "Cerro Gaital", "cod": "CGA", "tipo": "Montaña",
         "lat": 8.624607, "lng": -80.123500,
         "descripcion": "Cerro con vista panorámica"},
    22: {"nombre": "Museo de Penonomé", "cod": "MPE", "tipo": "Cultural",
         "lat": 8.519549, "lng": -80.360597,
         "descripcion": "Museo histórico en Penonomé"},
    23: {"nombre": "Mercado Artesanías La Pintada", "cod": "MLA", "tipo": "Cultural",
         "lat": 8.597083, "lng": -80.448927,
         "descripcion": "Mercado de artesanías en La Pintada"},
    24: {"nombre": "Balneario Los Algarrobos", "cod": "BAL", "tipo": "Naturaleza",
         "lat": 8.59850400964035, "lng": -80.44361114252906,
         "descripcion": "Balneario natural cerca de La Pintada"},
    25: {"nombre": "Iglesia Santiago Apóstol", "cod": "ISA", "tipo": "Histórico",
         "lat": 8.332057, "lng": -80.515256,
         "descripcion": "Iglesia colonial en Natá"},
    26: {"nombre": "Ecoparque Don Arcelio", "cod": "ECO", "tipo": "Naturaleza",
         "lat": 8.380838, "lng": -80.528935,
         "descripcion": "Parque ecológico cerca de Natá"},
    27: {"nombre": "Salinas de Aguadulce", "cod": "SAL", "tipo": "Naturaleza",
         "lat": 8.22279, "lng": -80.49906,
         "descripcion": "Salinas tradicionales"},
    28: {"nombre": "Mariposario", "cod": "MAR", "tipo": "Naturaleza",
         "lat": 8.600997663400143, "lng": -80.12844476076745,
         "descripcion": "Jardín de mariposas"},
    29: {"nombre": "Canopy Adventure", "cod": "CAN", "tipo": "Aventura",
         "lat": 8.625407314878048, "lng": -80.13892822612566,
         "descripcion": "Tirolesa y aventura en la selva"}
}

FUENTE_COORDENADAS = os.environ.get("FUENTE_COORDENADAS", "google").lower()
if FUENTE_COORDENADAS not in ("google", "osm"):
    FUENTE_COORDENADAS = "google"


def obtener_atractivos_por_fuente(fuente):
    if fuente == "osm":
        return ATRACTIVOS_OSM
    return ATRACTIVOS_GOOGLE


ATRACTIVOS = obtener_atractivos_por_fuente(FUENTE_COORDENADAS)

HUBS = {15, 16, 17, 18, 19}

ASIGNACION_HUB = {
    12: 15, 8: 15, 14: 15, 22: 15,
    5: 17, 4: 17, 2: 17, 1: 17,
    6: 17, 7: 17, 21: 17, 28: 17, 29: 17,
    11: 16, 27: 16, 3: 16,
    23: 18, 20: 18, 24: 18, 13: 18, 9: 18,
    25: 19, 26: 19, 10: 19,
}


def edges_topologia():
    aristas = []
    for nodo, hub in ASIGNACION_HUB.items():
        aristas.append((nodo, hub))
    hubs_lista = sorted(HUBS)
    for i in range(len(hubs_lista)):
        for j in range(i + 1, len(hubs_lista)):
            aristas.append((hubs_lista[i], hubs_lista[j]))
    return aristas


def distancia_haversine(lat1, lon1, lat2, lon2):
    radio_tierra = 6371.0
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return radio_tierra * c


def obtener_punto_carretera(lat, lng):
    url = f"{OSRM_URL}/nearest/v1/driving/{lng},{lat}"
    params = {"number": 1}
    for intento in range(MAX_RETRIES):
        try:
            respuesta = requests.get(url, params=params, timeout=TIMEOUT)
            data = respuesta.json()
            if respuesta.status_code == 200 and data.get("code") == "Ok":
                waypoint = data["waypoints"][0]
                coordenadas = waypoint["location"]
                return {"lng": coordenadas[0], "lat": coordenadas[1], "exito": True}
            time.sleep(1)
        except Exception as e:
            print(f"Intento {intento+1} falló: {e}")
            time.sleep(1)
    return {"exito": False, "error": "No se encontró carretera cercana"}


def obtener_ruta_osrm(origen_lat, origen_lng, destino_lat, destino_lng):
    url = f"{OSRM_URL}/route/v1/driving/{origen_lng},{origen_lat};{destino_lng},{destino_lat}"
    params = {"overview": "full", "geometries": "geojson", "steps": "false"}
    for intento in range(MAX_RETRIES):
        try:
            respuesta = requests.get(url, params=params, timeout=TIMEOUT)
            data = respuesta.json()
            if respuesta.status_code == 200 and data.get("code") == "Ok":
                ruta = data["routes"][0]
                distancia_km = ruta["distance"] / 1000
                tiempo_min = ruta["duration"] / 60
                costo = distancia_km * COSTO_POR_KM
                return {
                    "distancia_km": distancia_km,
                    "tiempo_min": tiempo_min,
                    "costo": costo,
                    "exito": True
                }
            time.sleep(1)
        except Exception as e:
            print(f"Intento {intento+1} falló: {e}")
            time.sleep(1)
    return {"exito": False, "error": "No se pudo calcular la ruta"}


def peso_arista_fallback(lat1, lng1, lat2, lng2):
    dist_km = distancia_haversine(lat1, lng1, lat2, lng2)
    tiempo_min = (dist_km / VELOCIDAD_FALLBACK_KMH) * 60
    costo = dist_km * COSTO_POR_KM
    return dist_km, tiempo_min, costo


def construir_grafo_hub(puntos):
    grafo = {nodo: {} for nodo in puntos}
    for a, b in edges_topologia():
        if a not in puntos or b not in puntos:
            continue
        resultado = obtener_ruta_osrm(
            puntos[a]["lat"], puntos[a]["lng"],
            puntos[b]["lat"], puntos[b]["lng"]
        )
        if resultado.get("exito"):
            distancia_km = resultado["distancia_km"]
            tiempo_min = resultado["tiempo_min"]
            costo = resultado["costo"]
        else:
            distancia_km, tiempo_min, costo = peso_arista_fallback(
                puntos[a]["lat"], puntos[a]["lng"],
                puntos[b]["lat"], puntos[b]["lng"]
            )
        datos_arista = {
            "distancia_km": distancia_km,
            "tiempo_min": tiempo_min,
            "costo": costo
        }
        grafo[a][b] = datos_arista
        grafo[b][a] = datos_arista
    return grafo


GRAFO = {}
PUNTOS_AJUSTADOS = {}
FUENTE_GRAFO = None


def preparar_grafo():
    global GRAFO, PUNTOS_AJUSTADOS, FUENTE_GRAFO
    PUNTOS_AJUSTADOS = ajustar_puntos_a_carreteras()
    GRAFO = construir_grafo_hub(PUNTOS_AJUSTADOS)
    FUENTE_GRAFO = FUENTE_COORDENADAS


def asegurar_grafo_actualizado():
    if not GRAFO or FUENTE_GRAFO != FUENTE_COORDENADAS:
        preparar_grafo()


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


def dijkstra(grafo, origen, destino, criterio):
    pesos = {"distancia": "distancia_km", "tiempo": "tiempo_min", "costo": "costo"}
    if criterio not in pesos:
        criterio = "tiempo"
    campo_peso = pesos[criterio]
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
    camino = []
    nodo = destino
    while nodo is not None:
        camino.append(nodo)
        nodo = anteriores[nodo]
    camino.reverse()
    return {"camino": camino, "peso_total": distancias[destino], "criterio": criterio}


def obtener_metricas_camino_completo(camino):
    if not camino or len(camino) < 2:
        return {"puntos_ruta": [], "distancia_km": 0.0, "tiempo_conduccion_min": 0.0,
                "costo": 0.0, "fuente": "vacio", "exito": False}
    puntos = []
    for nodo in camino:
        if nodo in PUNTOS_AJUSTADOS:
            puntos.append({"lat": PUNTOS_AJUSTADOS[nodo]["lat"], "lng": PUNTOS_AJUSTADOS[nodo]["lng"]})
        elif nodo in ATRACTIVOS:
            puntos.append({"lat": ATRACTIVOS[nodo]["lat"], "lng": ATRACTIVOS[nodo]["lng"]})
    if len(puntos) < 2:
        return {"puntos_ruta": [], "distancia_km": 0.0, "tiempo_conduccion_min": 0.0,
                "costo": 0.0, "fuente": "vacio", "exito": False}
    coord_str = ";".join(f"{p['lng']},{p['lat']}" for p in puntos)
    url = f"{OSRM_URL}/route/v1/driving/{coord_str}"
    params = {"overview": "full", "geometries": "geojson", "steps": "false"}
    for intento in range(MAX_RETRIES):
        try:
            respuesta = requests.get(url, params=params, timeout=60)
            data = respuesta.json()
            if respuesta.status_code == 200 and data.get("code") == "Ok":
                ruta = data["routes"][0]
                dist = ruta["distance"] / 1000.0
                tmin = ruta["duration"] / 60.0
                geometria = ruta["geometry"]["coordinates"]
                return {"puntos_ruta": [[c[1], c[0]] for c in geometria], "distancia_km": dist,
                        "tiempo_conduccion_min": tmin, "costo": dist * COSTO_POR_KM,
                        "fuente": "osrm", "exito": True}
            time.sleep(1)
        except Exception as e:
            print(f"Intento {intento+1} falló (camino completo): {e}")
            time.sleep(1)
    dist_total = 0.0
    puntos_ruta = []
    for i in range(len(puntos) - 1):
        a = puntos[i]
        b = puntos[i + 1]
        dist_total += distancia_haversine(a["lat"], a["lng"], b["lat"], b["lng"])
        if i == 0:
            puntos_ruta.append([a["lat"], a["lng"]])
        puntos_ruta.append([b["lat"], b["lng"]])
    tmin = (dist_total / VELOCIDAD_FALLBACK_KMH) * 60
    return {"puntos_ruta": puntos_ruta, "distancia_km": dist_total, "tiempo_conduccion_min": tmin,
            "costo": dist_total * COSTO_POR_KM, "fuente": "haversine", "exito": False}


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
        if origen not in ATRACTIVOS:
            return jsonify({"exito": False, "error": "El nodo de origen no existe."}), 400
        if destino not in ATRACTIVOS:
            return jsonify({"exito": False, "error": "El nodo de destino no existe."}), 400
        if origen == destino:
            return jsonify({"exito": False, "error": "El origen y destino no pueden ser iguales."}), 400
        asegurar_grafo_actualizado()
        resultado_dijkstra = dijkstra(GRAFO, origen, destino, criterio)
        if resultado_dijkstra is None:
            return jsonify({"exito": False, "error": "No se encontró un camino entre los nodos seleccionados."}), 404
        camino = resultado_dijkstra["camino"]
        metricas = obtener_metricas_camino_completo(camino)
        puntos_ruta = metricas["puntos_ruta"]
        distancia_total = metricas["distancia_km"]
        tiempo_conduccion = metricas["tiempo_conduccion_min"]
        costo_total = metricas["costo"]
        tiempo_total = tiempo_conduccion * FACTOR_HOLGURA
        segmentos = []
        for i in range(len(camino) - 1):
            a = camino[i]
            b = camino[i + 1]
            d = GRAFO[a][b]
            segmentos.append({"origen": a, "destino": b,
                               "distancia_km": round(d["distancia_km"], 2),
                               "tiempo_min": round(d["tiempo_min"], 2),
                               "costo": round(d["costo"], 2)})
        nodos_ruta = []
        for nodo in camino:
            nodos_ruta.append({
                "id": nodo, **ATRACTIVOS[nodo],
                "lat_ruta": PUNTOS_AJUSTADOS[nodo]["lat"], "lng_ruta": PUNTOS_AJUSTADOS[nodo]["lng"],
                "lat_carretera": PUNTOS_AJUSTADOS[nodo]["lat"], "lng_carretera": PUNTOS_AJUSTADOS[nodo]["lng"]
            })
        return jsonify({
            "exito": True, "origen": origen, "destino": destino, "criterio": criterio,
            "camino": camino, "nodos_ruta": nodos_ruta, "distancia_km": round(distancia_total, 2),
            "tiempo_conduccion_min": round(tiempo_conduccion, 2), "tiempo_min": round(tiempo_total, 2),
            "factor_holgura": FACTOR_HOLGURA, "costo": round(costo_total, 2),
            "fuente_metricas": metricas["fuente"], "puntos_ruta": puntos_ruta,
            "segmentos": segmentos, "nodos_visitados": len(camino)
        })
    except Exception as e:
        print("ERROR API RUTA:", e)
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/coordenadas")
def api_coordenadas():
    asegurar_grafo_actualizado()
    resultado = {}
    for nodo, datos in PUNTOS_AJUSTADOS.items():
        resultado[nodo] = {
            "nombre": datos["nombre"], "cod": datos["cod"], "tipo": datos["tipo"],
            "lat": datos.get("lat_original", datos["lat"]), "lng": datos.get("lng_original", datos["lng"]),
            "lat_original": datos.get("lat_original", datos["lat"]), "lng_original": datos.get("lng_original", datos["lng"]),
            "lat_carretera": datos["lat"], "lng_carretera": datos["lng"]
        }
    return jsonify(resultado)


@app.route("/api/grafo")
def api_grafo():
    asegurar_grafo_actualizado()
    return jsonify(GRAFO)


@app.route("/api/dias")
def api_dias():
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


@app.route("/api/fuente", methods=["GET"])
def api_fuente_get():
    return jsonify({
        "fuente": FUENTE_COORDENADAS,
        "fuente_nombre": "OpenStreetMap" if FUENTE_COORDENADAS == "osm" else "Google Maps",
        "total_atractivos": len(ATRACTIVOS),
        "factor_holgura": FACTOR_HOLGURA
    })


@app.route("/api/fuente", methods=["POST"])
def api_fuente_post():
    global FUENTE_COORDENADAS, ATRACTIVOS, GRAFO, PUNTOS_AJUSTADOS, FUENTE_GRAFO
    try:
        data = request.get_json() or {}
        nueva = str(data.get("fuente", "")).lower().strip()
        if nueva not in ("google", "osm"):
            return jsonify({"exito": False, "error": "Fuente inválida. Use 'google' u 'osm'."}), 400
        if nueva == FUENTE_COORDENADAS and GRAFO and FUENTE_GRAFO == nueva:
            return jsonify({"exito": True, "fuente": FUENTE_COORDENADAS, "mensaje": "La fuente ya estaba activa."})
        FUENTE_COORDENADAS = nueva
        ATRACTIVOS = obtener_atractivos_por_fuente(nueva)
        GRAFO = {}
        PUNTOS_AJUSTADOS = {}
        FUENTE_GRAFO = None
        asegurar_grafo_actualizado()
        return jsonify({"exito": True, "fuente": FUENTE_COORDENADAS,
                        "fuente_nombre": "OpenStreetMap" if FUENTE_COORDENADAS == "osm" else "Google Maps",
                        "total_atractivos": len(ATRACTIVOS)})
    except Exception as e:
        print("ERROR API FUENTE POST:", e)
        return jsonify({"exito": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("FLASK_DEBUG", "0") == "1")
