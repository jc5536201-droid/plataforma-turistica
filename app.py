from flask import Flask, render_template, request, jsonify
import os
import requests
import heapq
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

# ============================================================
# CONFIGURACIÓN
# ============================================================

OSRM_URL = os.environ.get("OSRM_URL", "https://router.project-osrm.org")
COSTO_POR_KM = 0.15
TIMEOUT = 30
MAX_RETRIES = 3
FACTOR_CARRETERA = 1.35          # Corrección Haversine → carretera
VELOCIDAD_PROMEDIO_KMH = 50      # Para estimar tiempo si no hay OSRM
MAX_WORKERS = 8                  # Hilos paralelos para consultas OSRM

# ============================================================
# ATRACTIVOS TURÍSTICOS
# ============================================================

ATRACTIVOS = {
    1:  {"nombre": "Playa Santa Clara", "cod": "PSC", "tipo": "Playa",
         "lat": 8.37571,  "lng": -80.10372, "descripcion": "Playa de arena blanca y aguas tranquilas"},
    2:  {"nombre": "Playa Farallón", "cod": "PFA", "tipo": "Playa",
         "lat": 8.35894,  "lng": -80.13333, "descripcion": "Playa con olas moderadas y arena dorada"},
    3:  {"nombre": "Playa El Salado", "cod": "PES", "tipo": "Playa",
         "lat": 8.202045, "lng": -80.483697, "descripcion": "Playa tranquila cerca de Aguadulce"},
    4:  {"nombre": "Playa Blanca", "cod": "PBL", "tipo": "Playa",
         "lat": 8.34490,  "lng": -80.15400, "descripcion": "Hermosa playa de arena blanca"},
    5:  {"nombre": "Playa Juan Hombrón", "cod": "PJH", "tipo": "Playa",
         "lat": 8.317049, "lng": -80.205259, "descripcion": "Playa con aguas cristalinas"},
    6:  {"nombre": "Mercado Artesanía Valle Antón", "cod": "MAV", "tipo": "Cultural",
         "lat": 8.604108, "lng": -80.131198, "descripcion": "Mercado de artesanías típicas"},
    7:  {"nombre": "Serpentario Maravillas Tropicales", "cod": "SMT", "tipo": "Naturaleza",
         "lat": 8.601194, "lng": -80.115215, "descripcion": "Exhibición de serpientes y reptiles"},
    8:  {"nombre": "Museo Hermanos Arias Madrid", "cod": "MHA", "tipo": "Cultural/Hist.",
         "lat": 8.525075, "lng": -80.356665, "descripcion": "Museo histórico en Penonomé"},
    9:  {"nombre": "P.N. Omar Torrijos", "cod": "PNT", "tipo": "Parque Nacional",
         "lat": 8.6801,   "lng": -80.7042,   "descripcion": "Parque Nacional con senderos ecológicos"},
    10: {"nombre": "Sitio Arqueológico El Caño", "cod": "SAC", "tipo": "Arqueológico",
         "lat": 8.396716, "lng": -80.501499, "descripcion": "Importante sitio arqueológico precolombino"},
    11: {"nombre": "Museo Regional Stella Sierra", "cod": "MSS", "tipo": "Cultural/Hist.",
         "lat": 8.241049, "lng": -80.539833, "descripcion": "Museo regional en Aguadulce"},
    12: {"nombre": "Iglesia San Juan Bautista", "cod": "ISJ", "tipo": "Histórico",
         "lat": 8.521929, "lng": -80.359489, "descripcion": "Iglesia histórica en Penonomé"},
    13: {"nombre": "El Chorro Las Yayas", "cod": "CLY", "tipo": "Cascada",
         "lat": 8.645952, "lng": -80.590030, "descripcion": "Hermosa cascada en La Pintada"},
    14: {"nombre": "Balneario Las Mendozas", "cod": "BLM", "tipo": "Balneario",
         "lat": 8.526422, "lng": -80.355455, "descripcion": "Balneario natural cerca de Penonomé"},
    15: {"nombre": "Penonomé", "cod": "PEN", "tipo": "Hub/Ciudad",
         "lat": 8.5260,   "lng": -80.3616,   "descripcion": "Capital de la provincia de Coclé"},
    16: {"nombre": "Aguadulce", "cod": "AGU", "tipo": "Hub/Ciudad",
         "lat": 8.24275,  "lng": -80.53888,  "descripcion": "Ciudad conocida por sus salinas"},
    17: {"nombre": "Antón", "cod": "ANT", "tipo": "Hub/Ciudad",
         "lat": 8.394482, "lng": -80.266347, "descripcion": "Ciudad cerca de las playas"},
    18: {"nombre": "La Pintada", "cod": "LAP", "tipo": "Hub/Ciudad",
         "lat": 8.5963,   "lng": -80.4467,   "descripcion": "Ciudad conocida por sus artesanías"},
    19: {"nombre": "Natá", "cod": "NAT", "tipo": "Hub/Ciudad",
         "lat": 8.33686,  "lng": -80.51725,  "descripcion": "Ciudad histórica con iglesia colonial"},
    20: {"nombre": "Parroquia Ntra. Sra. Candelaria", "cod": "PNC", "tipo": "Histórico",
         "lat": 8.593051, "lng": -80.445811, "descripcion": "Iglesia histórica en La Pintada"},
    21: {"nombre": "Cerro Gaital", "cod": "CGA", "tipo": "Montaña",
         "lat": 8.624607, "lng": -80.123500, "descripcion": "Cerro con vista panorámica"},
    22: {"nombre": "Museo de Penonomé", "cod": "MPE", "tipo": "Cultural",
         "lat": 8.519549, "lng": -80.360597, "descripcion": "Museo histórico en Penonomé"},
    23: {"nombre": "Mercado Artesanías La Pintada", "cod": "MLA", "tipo": "Cultural",
         "lat": 8.597083, "lng": -80.448927, "descripcion": "Mercado de artesanías en La Pintada"},
    24: {"nombre": "Balneario Los Algarrobos", "cod": "BAL", "tipo": "Naturaleza",
         "lat": 8.598504, "lng": -80.443611, "descripcion": "Balneario natural cerca de La Pintada"},
    25: {"nombre": "Iglesia Santiago Apóstol", "cod": "ISA", "tipo": "Histórico",
         "lat": 8.332057, "lng": -80.515256, "descripcion": "Iglesia colonial en Natá"},
    26: {"nombre": "Ecoparque Don Arcelio", "cod": "ECO", "tipo": "Naturaleza",
         "lat": 8.380838, "lng": -80.528935, "descripcion": "Parque ecológico cerca de Natá"},
    27: {"nombre": "Salinas de Aguadulce", "cod": "SAL", "tipo": "Naturaleza",
         "lat": 8.22279,  "lng": -80.49906,  "descripcion": "Salinas tradicionales"},
    28: {"nombre": "Mariposario", "cod": "MAR", "tipo": "Naturaleza",
         "lat": 8.600998, "lng": -80.128445, "descripcion": "Jardín de mariposas"},
    29: {"nombre": "Canopy Adventure", "cod": "CAN", "tipo": "Aventura",
         "lat": 8.625407, "lng": -80.138928, "descripcion": "Tirolesa y aventura en la selva"},
}

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def distancia_haversine(lat1, lon1, lat2, lon2):
    """Distancia en línea recta (km) usando Haversine."""
    radio_tierra = 6371.0
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (math.sin(dlat / 2) ** 2
         + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radio_tierra * c


def construir_instruccion(paso):
    """OSRM NO devuelve texto 'instruction'; hay que construirlo."""
    maneuver = paso.get("maneuver", {})
    tipo = maneuver.get("type", "")
    modificador = maneuver.get("modifier", "")
    nombre_via = paso.get("name", "") or "vía sin nombre"

    mapa = {
        "turn":        f"Gire {modificador}",
        "new name":    f"Continúe por {nombre_via}",
        "depart":      f"Salga por {nombre_via}",
        "arrive":      "Llegue a su destino",
        "merge":       f"Incorpórese {modificador}",
        "on ramp":     f"Tome la rampa {modificador}",
        "off ramp":    f"Tome la salida {modificador}",
        "fork":        f"En la bifurcación, tome {modificador}",
        "roundabout":  f"En la rotonda, tome la salida",
        "continue":    f"Continúe {modificador} por {nombre_via}",
        "end of road": f"Al final de la vía, gire {modificador}",
    }

    texto = mapa.get(tipo, f"Continúe por {nombre_via}")
    if nombre_via and nombre_via != "vía sin nombre" and tipo in ("turn", "merge", "fork"):
        texto += f" en {nombre_via}"
    return texto


def obtener_ruta_osrm(lat1, lng1, lat2, lng2):
    """
    Obtiene ruta real por carretera entre 2 puntos con /route.
    Devuelve distancia_km, tiempo_min, puntos_ruta, instrucciones.
    """
    url = f"{OSRM_URL}/route/v1/driving/{lng1},{lat1};{lng2},{lat2}"
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "true",
    }

    for intento in range(MAX_RETRIES):
        try:
            r = requests.get(url, params=params, timeout=TIMEOUT)
            data = r.json()
            if r.status_code == 200 and data.get("code") == "Ok":
                ruta = data["routes"][0]
                distancia_km = ruta["distance"] / 1000
                tiempo_min = ruta["duration"] / 60

                geometria = ruta["geometry"]["coordinates"]
                puntos_ruta = [[c[1], c[0]] for c in geometria]

                instrucciones = []
                for leg in ruta.get("legs", []):
                    for paso in leg.get("steps", []):
                        instrucciones.append(construir_instruccion(paso))

                return {
                    "exito": True,
                    "distancia_km": round(distancia_km, 2),
                    "tiempo_min": round(tiempo_min, 2),
                    "puntos_ruta": puntos_ruta,
                    "instrucciones": instrucciones,
                }
            time.sleep(0.5)
        except Exception as e:
            print(f"[OSRM] Intento {intento + 1} falló: {e}")
            time.sleep(0.5)

    return {"exito": False}


def distancia_carretera_fallback(lat1, lng1, lat2, lng2):
    """Fallback: Haversine × factor de corrección por carretera."""
    d = distancia_haversine(lat1, lng1, lat2, lng2) * FACTOR_CARRETERA
    return {
        "exito": True,
        "distancia_km": round(d, 2),
        "tiempo_min": round((d / VELOCIDAD_PROMEDIO_KMH) * 60, 2),
        "puntos_ruta": [[lat1, lng1], [lat2, lng2]],
        "instrucciones": [],
        "aproximado": True,
    }


# ============================================================
# MATRIZ DE DISTANCIAS REALES (POR PARES CON /route)
# ============================================================

def _consultar_par(args):
    """Helper para ThreadPoolExecutor."""
    i, j, id_i, id_j, p_i, p_j = args
    ruta = obtener_ruta_osrm(p_i["lat"], p_i["lng"], p_j["lat"], p_j["lng"])
    if not ruta["exito"]:
        ruta = distancia_carretera_fallback(p_i["lat"], p_i["lng"], p_j["lat"], p_j["lng"])
        ruta["aproximado"] = True
    return i, j, ruta


def construir_matriz_osrm(puntos):
    """
    Construye la matriz de distancias/tiempos consultando OSRM /route
    para CADA PAR de puntos en paralelo.
    Esto da distancias reales por carretera (como Google Maps).
    """
    ids = list(puntos.keys())
    n = len(ids)

    print(f"🔍 Construyendo matriz {n}×{n} con OSRM /route (paralelo)...")

    matriz_distancia = [[0.0] * n for _ in range(n)]
    matriz_tiempo = [[0.0] * n for _ in range(n)]
    matriz_aproximada = [[False] * n for _ in range(n)]

    tareas = []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            tareas.append((i, j, ids[i], ids[j], puntos[ids[i]], puntos[ids[j]]))

    exitos = 0
    fallbacks = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futuros = [pool.submit(_consultar_par, t) for t in tareas]
        for fut in as_completed(futuros):
            try:
                i, j, ruta = fut.result()
                matriz_distancia[i][j] = ruta["distancia_km"] * 1000  # metros
                matriz_tiempo[i][j] = ruta["tiempo_min"] * 60          # segundos
                matriz_aproximada[i][j] = ruta.get("aproximado", False)
                if ruta.get("aproximado"):
                    fallbacks += 1
                else:
                    exitos += 1
            except Exception as e:
                print(f"Error en par: {e}")

    print(f"✅ Matriz lista: {exitos} reales, {fallbacks} aproximadas (fallback)")
    return ids, matriz_distancia, matriz_tiempo, matriz_aproximada


def construir_matriz_aproximada(puntos):
    """Fallback completo: Haversine × factor carretera."""
    ids = list(puntos.keys())
    n = len(ids)

    matriz_distancia = [[0.0] * n for _ in range(n)]
    matriz_tiempo = [[0.0] * n for _ in range(n)]
    matriz_aproximada = [[True] * n for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i != j:
                d = distancia_haversine(
                    puntos[ids[i]]["lat"], puntos[ids[i]]["lng"],
                    puntos[ids[j]]["lat"], puntos[ids[j]]["lng"]
                ) * FACTOR_CARRETERA
                matriz_distancia[i][j] = d * 1000
                matriz_tiempo[i][j] = (d / VELOCIDAD_PROMEDIO_KMH) * 3600

    return ids, matriz_distancia, matriz_tiempo, matriz_aproximada


def construir_grafo(puntos):
    """Construye el grafo con pesos reales (OSRM /route por pares)."""
    try:
        ids, m_dist, m_tiempo, m_aprox = construir_matriz_osrm(puntos)
    except Exception as e:
        print(f"❌ Error construyendo matriz OSRM: {e}")
        print("   → Usando Haversine aproximado")
        ids, m_dist, m_tiempo, m_aprox = construir_matriz_aproximada(puntos)

    grafo = {}
    for i, nodo_o in enumerate(ids):
        grafo[nodo_o] = {}
        for j, nodo_d in enumerate(ids):
            if i == j:
                continue

            distancia_km = m_dist[i][j] / 1000
            tiempo_min = m_tiempo[i][j] / 60
            costo = distancia_km * COSTO_POR_KM

            grafo[nodo_o][nodo_d] = {
                "distancia_km": round(distancia_km, 2),
                "tiempo_min": round(tiempo_min, 2),
                "costo": round(costo, 2),
                "aproximado": m_aprox[i][j],
            }
    return grafo


# ============================================================
# ESTADO GLOBAL
# ============================================================

GRAFO = {}
PUNTOS_AJUSTADOS = {}


def preparar_grafo():
    """
    Prepara el grafo usando las coordenadas ORIGINALES de los atractivos
    (sin snap a carretera, para no distorsionar distancias).
    """
    global GRAFO, PUNTOS_AJUSTADOS

    print("=" * 50)
    print("Preparando red de rutas...")
    # NO hacemos snap: usamos coordenadas exactas
    PUNTOS_AJUSTADOS = {
        k: {**v, "lat_original": v["lat"], "lng_original": v["lng"]}
        for k, v in ATRACTIVOS.items()
    }

    GRAFO = construir_grafo(PUNTOS_AJUSTADOS)
    print(f"✅ Grafo construido con {len(GRAFO)} nodos.")
    print("=" * 50)


# ============================================================
# DIJKSTRA
# ============================================================

def dijkstra(grafo, origen, destino, criterio):
    """Dijkstra clásico (correcto, no se toca)."""
    pesos = {
        "distancia": "distancia_km",
        "tiempo": "tiempo_min",
        "costo": "costo",
    }
    if criterio not in pesos:
        criterio = "tiempo"
    campo = pesos[criterio]

    if origen not in grafo or destino not in grafo:
        return None

    distancias = {n: float("inf") for n in grafo}
    anteriores = {n: None for n in grafo}
    distancias[origen] = 0
    cola = [(0, origen)]

    while cola:
        d_actual, nodo = heapq.heappop(cola)
        if d_actual > distancias[nodo]:
            continue
        if nodo == destino:
            break
        for vecino, datos in grafo.get(nodo, {}).items():
            peso = datos.get(campo, 0)
            if peso <= 0:
                continue
            nueva = d_actual + peso
            if nueva < distancias[vecino]:
                distancias[vecino] = nueva
                anteriores[vecino] = nodo
                heapq.heappush(cola, (nueva, vecino))

    if distancias.get(destino, float("inf")) == float("inf"):
        return None

    camino = []
    n = destino
    while n is not None:
        camino.append(n)
        n = anteriores[n]
    camino.reverse()

    return {"camino": camino, "peso_total": round(distancias[destino], 2), "criterio": criterio}


def obtener_geometria_camino(camino):
    """
    Obtiene la geometría REAL de la ruta con TODOS los waypoints intermedios
    usando OSRM /route. Esto es lo que hace Google Maps.
    """
    if not camino or len(camino) < 2:
        return [], None

    coords = ";".join(
        f"{PUNTOS_AJUSTADOS[n]['lng']},{PUNTOS_AJUSTADOS[n]['lat']}"
        for n in camino
    )
    url = f"{OSRM_URL}/route/v1/driving/{coords}"
    params = {"overview": "full", "geometries": "geojson", "steps": "true"}

    for intento in range(MAX_RETRIES):
        try:
            r = requests.get(url, params=params, timeout=60)
            data = r.json()
            if r.status_code == 200 and data.get("code") == "Ok":
                ruta = data["routes"][0]
                geometria = ruta["geometry"]["coordinates"]
                puntos = [[c[1], c[0]] for c in geometria]

                instrucciones = []
                for leg in ruta.get("legs", []):
                    for paso in leg.get("steps", []):
                        instrucciones.append(construir_instruccion(paso))

                return puntos, {
                    "distancia_km": round(ruta["distance"] / 1000, 2),
                    "tiempo_min": round(ruta["duration"] / 60, 2),
                    "instrucciones": instrucciones,
                }
            time.sleep(0.5)
        except Exception as e:
            print(f"[Geometría] Intento {intento + 1} falló: {e}")
            time.sleep(0.5)

    # Fallback: líneas rectas entre nodos
    puntos = []
    for n in camino:
        puntos.append([PUNTOS_AJUSTADOS[n]["lat"], PUNTOS_AJUSTADOS[n]["lng"]])
    return puntos, None


# ============================================================
# RUTAS DE LA API
# ============================================================

@app.route("/")
def index():
    return render_template("index.html", atractivos=ATRACTIVOS)


@app.route("/api/ruta", methods=["POST"])
def api_ruta():
    """Calcula la ruta óptima con Dijkstra y devuelve la geometría REAL."""
    try:
        data = request.get_json()
        origen = int(data["origen"])
        destino = int(data["destino"])
        criterio = data.get("criterio", "tiempo")

        if origen not in ATRACTIVOS:
            return jsonify({"exito": False, "error": "Origen no existe."}), 400
        if destino not in ATRACTIVOS:
            return jsonify({"exito": False, "error": "Destino no existe."}), 400
        if origen == destino:
            return jsonify({"exito": False, "error": "Origen y destino iguales."}), 400

        if not GRAFO:
            preparar_grafo()

        # 1) Dijkstra decide el camino óptimo según el criterio
        resultado = dijkstra(GRAFO, origen, destino, criterio)
        if resultado is None:
            return jsonify({"exito": False, "error": "No hay camino."}), 404

        camino = resultado["camino"]

        # 2) Geometría REAL con todos los waypoints (como Google Maps)
        puntos_ruta, resumen_real = obtener_geometria_camino(camino)

        # 3) Suma de segmentos desde el grafo (para detalle por tramo)
        distancia_total = 0.0
        tiempo_total = 0.0
        costo_total = 0.0
        segmentos = []
        algun_aproximado = False

        for i in range(len(camino) - 1):
            a, b = camino[i], camino[i + 1]
            seg = GRAFO[a][b]
            distancia_total += seg["distancia_km"]
            tiempo_total += seg["tiempo_min"]
            costo_total += seg["costo"]
            if seg.get("aproximado"):
                algun_aproximado = True
            segmentos.append({
                "origen": a, "destino": b,
                "distancia_km": seg["distancia_km"],
                "tiempo_min": seg["tiempo_min"],
                "costo": seg["costo"],
                "aproximado": seg.get("aproximado", False),
            })

        # 4) Si OSRM devolvió resumen real, tiene prioridad
        if resumen_real:
            distancia_final = resumen_real["distancia_km"]
            tiempo_final = resumen_real["tiempo_min"]
        else:
            distancia_final = round(distancia_total, 2)
            tiempo_final = round(tiempo_total, 2)

        costo_final = round(distancia_final * COSTO_POR_KM, 2)

        nodos_ruta = []
        for nodo in camino:
            nodos_ruta.append({
                "id": nodo,
                **ATRACTIVOS[nodo],
                "lat_ruta": PUNTOS_AJUSTADOS[nodo]["lat"],
                "lng_ruta": PUNTOS_AJUSTADOS[nodo]["lng"],
                "lat_carretera": PUNTOS_AJUSTADOS[nodo]["lat"],
                "lng_carretera": PUNTOS_AJUSTADOS[nodo]["lng"],
            })

        return jsonify({
            "exito": True,
            "origen": origen,
            "destino": destino,
            "criterio": criterio,
            "camino": camino,
            "nodos_ruta": nodos_ruta,
            "distancia_km": distancia_final,
            "tiempo_min": tiempo_final,
            "costo": costo_final,
            "puntos_ruta": puntos_ruta,
            "segmentos": segmentos,
            "instrucciones": resumen_real["instrucciones"] if resumen_real else [],
            "nodos_visitados": len(camino),
            "aproximado": algun_aproximado and resumen_real is None,
        })

    except Exception as e:
        print("ERROR API RUTA:", e)
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/coordenadas")
def api_coordenadas():
    if not PUNTOS_AJUSTADOS:
        preparar_grafo()
    out = {}
    for nodo, d in PUNTOS_AJUSTADOS.items():
        out[nodo] = {
            "nombre": d["nombre"],
            "cod": d["cod"],
            "tipo": d["tipo"],
            "lat": d.get("lat_original", d["lat"]),
            "lng": d.get("lng_original", d["lng"]),
            "lat_original": d.get("lat_original", d["lat"]),
            "lng_original": d.get("lng_original", d["lng"]),
            "lat_carretera": d["lat"],
            "lng_carretera": d["lng"],
        }
    return jsonify(out)


@app.route("/api/grafo")
def api_grafo():
    if not GRAFO:
        preparar_grafo()
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
        {"dia": 7, "destinos": [15, 18, 20, 23, 24], "zona": "🎯 Circuito Integrador"},
    ]
    return jsonify(dias)


# ============================================================
# INICIO
# ============================================================

if __name__ == "__main__":
    print("==========================================")
    print(" RUTAS TURÍSTICAS DE COCLÉ")
    print(" Dijkstra + OSRM /route (por pares)")
    print("==========================================")
    print(f"Atractivos: {len(ATRACTIVOS)}")

    # Pre-calentar el grafo al iniciar (opcional pero recomendado)
    preparar_grafo()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
    )
