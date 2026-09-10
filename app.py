from flask import Flask, render_template, request, jsonify
import os
import json
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
TIMEOUT = 20
MAX_RETRIES = 2
FACTOR_CARRETERA = 1.35
VELOCIDAD_PROMEDIO_KMH = 50
MAX_WORKERS = 6
CACHE_FILE = "grafo_cache.json"

# ============================================================
# ATRACTIVOS
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
# UTILIDADES
# ============================================================

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def construir_instruccion(paso):
    m = paso.get("maneuver", {})
    tipo = m.get("type", "")
    mod = m.get("modifier", "")
    via = paso.get("name", "") or "vía sin nombre"
    mapa = {
        "turn": f"Gire {mod}",
        "new name": f"Continúe por {via}",
        "depart": f"Salga por {via}",
        "arrive": "Llegue a su destino",
        "merge": f"Incorpórese {mod}",
        "on ramp": f"Tome la rampa {mod}",
        "off ramp": f"Tome la salida {mod}",
        "fork": f"En la bifurcación, tome {mod}",
        "roundabout": "En la rotonda, tome la salida",
        "continue": f"Continúe {mod} por {via}",
        "end of road": f"Al final de la vía, gire {mod}",
    }
    txt = mapa.get(tipo, f"Continúe por {via}")
    if via and via != "vía sin nombre" and tipo in ("turn", "merge", "fork"):
        txt += f" en {via}"
    return txt


# ============================================================
# OSRM
# ============================================================

def osrm_route_par(lat1, lng1, lat2, lng2):
    """Consulta /route para UN par. Devuelve dict o None."""
    url = f"{OSRM_URL}/route/v1/driving/{lng1},{lat1};{lng2},{lat2}"
    params = {"overview": "false", "steps": "false"}
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("code") != "Ok":
            return None
        ruta = data["routes"][0]
        return {
            "distancia_km": round(ruta["distance"] / 1000, 2),
            "tiempo_min": round(ruta["duration"] / 60, 2),
        }
    except Exception:
        return None


def osrm_table(ids, puntos):
    """Intenta /table con n<=25. Devuelve (dist_km, tiempo_min) o (None, None)."""
    if len(ids) > 25:
        return None, None
    coords = ";".join(f"{puntos[i]['lng']},{puntos[i]['lat']}" for i in ids)
    url = f"{OSRM_URL}/table/v1/driving/{coords}"
    params = {"annotations": "distance,duration"}
    try:
        r = requests.get(url, params=params, timeout=60)
        if r.status_code != 200:
            return None, None
        data = r.json()
        if data.get("code") != "Ok":
            return None, None
        return data.get("distances"), data.get("durations")
    except Exception:
        return None, None


# ============================================================
# GRAFO
# ============================================================

GRAFO = None
PUNTOS = {k: {**v, "lat_original": v["lat"], "lng_original": v["lng"]} for k, v in ATRACTIVOS.items()}


def construir_grafo():
    """Construye grafo. Intenta caché → OSRM /table → OSRM /route por pares → Haversine."""
    global GRAFO

    # 1) Caché
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                GRAFO = json.load(f)
                # JSON convierte claves a string
                GRAFO = {int(k): {int(k2): v2 for k2, v2 in v.items()} for k, v in GRAFO.items()}
            print(f"✅ Grafo cargado desde caché ({len(GRAFO)} nodos)")
            return
        except Exception as e:
            print(f"⚠️ Caché inválida: {e}")

    ids = list(PUNTOS.keys())
    n = len(ids)
    print(f"🔨 Construyendo grafo para {n} nodos...")

    matriz_dist = [[None] * n for _ in range(n)]
    matriz_tiempo = [[None] * n for _ in range(n)]

    # 2) Intentar /table (solo si n<=25)
    if n <= 25:
        print("   Probando /table...")
        d, t = osrm_table(ids, PUNTOS)
        if d and t:
            matriz_dist, matriz_tiempo = d, t
            print("   ✅ /table OK")

    # 3) Si faltan valores, usar /route por pares en paralelo
    faltantes = [(i, j) for i in range(n) for j in range(n)
                 if i != j and (matriz_dist[i][j] is None or matriz_dist[i][j] == 0)]

    if faltantes:
        print(f"   Consultando {len(faltantes)} pares con /route...")

        def worker(t):
            i, j = t
            r = osrm_route_par(PUNTOS[ids[i]]["lat"], PUNTOS[ids[i]]["lng"],
                               PUNTOS[ids[j]]["lat"], PUNTOS[ids[j]]["lng"])
            return i, j, r

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            for fut in as_completed([pool.submit(worker, t) for t in faltantes]):
                try:
                    i, j, r = fut.result()
                    if r:
                        matriz_dist[i][j] = r["distancia_km"] * 1000
                        matriz_tiempo[i][j] = r["tiempo_min"] * 60
                except Exception:
                    pass

    # 4) Rellenar faltantes con Haversine × factor
    aproximados = 0
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if matriz_dist[i][j] is None or matriz_dist[i][j] == 0:
                d = haversine(PUNTOS[ids[i]]["lat"], PUNTOS[ids[i]]["lng"],
                              PUNTOS[ids[j]]["lat"], PUNTOS[ids[j]]["lng"]) * FACTOR_CARRETERA
                matriz_dist[i][j] = d * 1000
                matriz_tiempo[i][j] = (d / VELOCIDAD_PROMEDIO_KMH) * 3600
                aproximados += 1

    print(f"   ⚠️ {aproximados} pares aproximados con Haversine")

    # 5) Construir grafo
    GRAFO = {}
    for i, a in enumerate(ids):
        GRAFO[a] = {}
        for j, b in enumerate(ids):
            if i == j:
                continue
            d_km = matriz_dist[i][j] / 1000
            t_min = matriz_tiempo[i][j] / 60
            GRAFO[a][b] = {
                "distancia_km": round(d_km, 2),
                "tiempo_min": round(t_min, 2),
                "costo": round(d_km * COSTO_POR_KM, 2),
            }

    # 6) Guardar caché
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({str(k): {str(k2): v2 for k2, v2 in v.items()} for k, v in GRAFO.items()},
                      f, ensure_ascii=False)
        print(f"💾 Caché guardada en {CACHE_FILE}")
    except Exception as e:
        print(f"⚠️ No se pudo guardar caché: {e}")

    print(f"✅ Grafo listo: {len(GRAFO)} nodos")


def asegurar_grafo():
    global GRAFO
    if GRAFO is None:
        construir_grafo()


# ============================================================
# DIJKSTRA
# ============================================================

def dijkstra(grafo, origen, destino, criterio):
    pesos = {"distancia": "distancia_km", "tiempo": "tiempo_min", "costo": "costo"}
    if criterio not in pesos:
        criterio = "tiempo"
    campo = pesos[criterio]

    if origen not in grafo or destino not in grafo:
        return None

    dist = {n: float("inf") for n in grafo}
    ant = {n: None for n in grafo}
    dist[origen] = 0
    cola = [(0, origen)]

    while cola:
        d, u = heapq.heappop(cola)
        if d > dist[u]:
            continue
        if u == destino:
            break
        for v, datos in grafo.get(u, {}).items():
            w = datos.get(campo, 0)
            if w <= 0:
                continue
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                ant[v] = u
                heapq.heappush(cola, (nd, v))

    if dist.get(destino, float("inf")) == float("inf"):
        return None

    camino = []
    n = destino
    while n is not None:
        camino.append(n)
        n = ant[n]
    camino.reverse()
    return {"camino": camino, "peso_total": round(dist[destino], 2), "criterio": criterio}


# ============================================================
# GEOMETRÍA REAL DE LA RUTA
# ============================================================

def geometria_real(camino):
    """Llama a /route con todos los waypoints. Devuelve (puntos, resumen, instrucciones)."""
    if len(camino) < 2:
        return [], None, []

    coords = ";".join(f"{PUNTOS[n]['lng']},{PUNTOS[n]['lat']}" for n in camino)
    url = f"{OSRM_URL}/route/v1/driving/{coords}"
    params = {"overview": "full", "geometries": "geojson", "steps": "true"}

    try:
        r = requests.get(url, params=params, timeout=60)
        if r.status_code != 200:
            return [], None, []
        data = r.json()
        if data.get("code") != "Ok":
            return [], None, []
        ruta = data["routes"][0]
        puntos = [[c[1], c[0]] for c in ruta["geometry"]["coordinates"]]
        resumen = {
            "distancia_km": round(ruta["distance"] / 1000, 2),
            "tiempo_min": round(ruta["duration"] / 60, 2),
        }
        instrucciones = []
        for leg in ruta.get("legs", []):
            for paso in leg.get("steps", []):
                instrucciones.append(construir_instruccion(paso))
        return puntos, resumen, instrucciones
    except Exception as e:
        print(f"[Geometría] Error: {e}")
        return [], None, []


# ============================================================
# API
# ============================================================

@app.route("/")
def index():
    return render_template("index.html", atractivos=ATRACTIVOS)


@app.route("/api/ruta", methods=["POST"])
def api_ruta():
    try:
        data = request.get_json(silent=True) or {}
        if "origen" not in data or "destino" not in data:
            return jsonify({"exito": False, "error": "Faltan origen/destino"}), 400

        origen = int(data["origen"])
        destino = int(data["destino"])
        criterio = data.get("criterio", "tiempo")

        if origen not in ATRACTIVOS or destino not in ATRACTIVOS:
            return jsonify({"exito": False, "error": "Nodo inexistente"}), 400
        if origen == destino:
            return jsonify({"exito": False, "error": "Origen y destino iguales"}), 400

        asegurar_grafo()

        res = dijkstra(GRAFO, origen, destino, criterio)
        if res is None:
            return jsonify({"exito": False, "error": "No hay camino entre esos nodos"}), 404

        camino = res["camino"]

        # Suma desde el grafo (para segmentos)
        dist_total = 0.0
        tiempo_total = 0.0
        segmentos = []
        for i in range(len(camino) - 1):
            a, b = camino[i], camino[i + 1]
            seg = GRAFO[a][b]
            dist_total += seg["distancia_km"]
            tiempo_total += seg["tiempo_min"]
            segmentos.append({"origen": a, "destino": b, **seg})

        # Geometría real (tiene prioridad)
        puntos_ruta, resumen, instrucciones = geometria_real(camino)

        dist_final = resumen["distancia_km"] if resumen else round(dist_total, 2)
        tiempo_final = resumen["tiempo_min"] if resumen else round(tiempo_total, 2)
        costo_final = round(dist_final * COSTO_POR_KM, 2)

        nodos_ruta = []
        for nodo in camino:
            nodos_ruta.append({
                "id": nodo,
                "nombre": ATRACTIVOS[nodo]["nombre"],
                "cod": ATRACTIVOS[nodo]["cod"],
                "tipo": ATRACTIVOS[nodo]["tipo"],
                "descripcion": ATRACTIVOS[nodo]["descripcion"],
                "lat": PUNTOS[nodo]["lat"],
                "lng": PUNTOS[nodo]["lng"],
            })

        return jsonify({
            "exito": True,
            "origen": origen,
            "destino": destino,
            "criterio": criterio,
            "camino": camino,
            "nodos_ruta": nodos_ruta,
            "distancia_km": dist_final,
            "tiempo_min": tiempo_final,
            "costo": costo_final,
            "puntos_ruta": puntos_ruta,
            "segmentos": segmentos,
            "instrucciones": instrucciones,
            "nodos_visitados": len(camino),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/coordenadas")
def api_coordenadas():
    out = {}
    for nodo, d in PUNTOS.items():
        out[nodo] = {
            "nombre": d["nombre"],
            "cod": d["cod"],
            "tipo": d["tipo"],
            "lat": d["lat"],
            "lng": d["lng"],
            "descripcion": d["descripcion"],
        }
    return jsonify(out)


@app.route("/api/dias")
def api_dias():
    return jsonify([
        {"dia": 1, "destinos": [1, 2, 4, 5, 17], "zona": "🌊 Playas de Antón"},
        {"dia": 2, "destinos": [8, 22, 12, 14, 15], "zona": "🏛️ Penonomé Histórico"},
        {"dia": 3, "destinos": [18, 20, 23, 24, 13, 9], "zona": "⛰️ La Pintada - Montaña"},
        {"dia": 4, "destinos": [10, 25, 26, 19], "zona": "🏺 Ruta Arqueológica de Natá"},
        {"dia": 5, "destinos": [6, 7, 28, 21, 29], "zona": "🌿 Naturaleza de Antón"},
        {"dia": 6, "destinos": [16, 3, 27, 11], "zona": "🌅 Tesoros de Aguadulce"},
        {"dia": 7, "destinos": [15, 18, 20, 23, 24], "zona": "🎯 Circuito Integrador"},
    ])


@app.route("/api/estado")
def api_estado():
    return jsonify({"grafo_listo": GRAFO is not None, "nodos": len(GRAFO) if GRAFO else 0})


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print(" RUTAS TURÍSTICAS DE COCLÉ")
    print("=" * 50)
    # NO pre-cargamos el grafo al inicio: se construye en el primer /api/ruta
    # o puedes forzarlo aquí descomentando:
    # construir_grafo()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
