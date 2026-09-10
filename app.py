from flask import Flask, render_template, request, jsonify
import os
import json
import math
import heapq
import requests
import time

app = Flask(__name__)

# ============================================================
# CONFIGURACIÓN
# ============================================================
OSRM_URL = os.environ.get("OSRM_URL", "https://router.project-osrm.org")
COSTO_POR_KM = 0.15
TIMEOUT = 8                    # ⬅️ Timeout corto para no colgar
FACTOR_CARRETERA = 1.35        # Haversine → distancia por carretera
VELOCIDAD_PROMEDIO_KMH = 50
USAR_OSRM = os.environ.get("USAR_OSRM", "0") == "1"   # ⬅️ OFF por defecto
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

PUNTOS = {k: {**v, "lat_original": v["lat"], "lng_original": v["lng"]} for k, v in ATRACTIVOS.items()}


# ============================================================
# HAVERSINE
# ============================================================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ============================================================
# CONSTRUIR GRAFO (Haversine × 1.35 — siempre funciona, instantáneo)
# ============================================================
def construir_grafo_haversine():
    ids = list(PUNTOS.keys())
    n = len(ids)
    G = {}
    for i, a in enumerate(ids):
        G[a] = {}
        for j, b in enumerate(ids):
            if i == j:
                continue
            d = haversine(PUNTOS[a]["lat"], PUNTOS[a]["lng"],
                          PUNTOS[b]["lat"], PUNTOS[b]["lng"]) * FACTOR_CARRETERA
            G[a][b] = {
                "distancia_km": round(d, 2),
                "tiempo_min": round((d / VELOCIDAD_PROMEDIO_KMH) * 60, 2),
                "costo": round(d * COSTO_POR_KM, 2),
            }
    return G


# ============================================================
# INTENTO OPCIONAL CON OSRM (solo si USAR_OSRM=1 y hay caché)
# ============================================================
def intentar_osrm_table():
    """Intenta /table de OSRM (n<=25). Devuelve matriz o None."""
    ids = list(PUNTOS.keys())
    if len(ids) > 25:
        print("⚠️ Más de 25 nodos, /table no soportado")
        return None
    coords = ";".join(f"{PUNTOS[i]['lng']},{PUNTOS[i]['lat']}" for i in ids)
    url = f"{OSRM_URL}/table/v1/driving/{coords}"
    try:
        r = requests.get(url, params={"annotations": "distance,duration"}, timeout=TIMEOUT)
        if r.status_code != 200:
            print(f"⚠️ OSRM /table HTTP {r.status_code}")
            return None
        data = r.json()
        if data.get("code") != "Ok":
            print(f"⚠️ OSRM /table code={data.get('code')}")
            return None
        return data.get("distances"), data.get("durations")
    except Exception as e:
        print(f"⚠️ OSRM /table error: {e}")
        return None


def construir_grafo():
    """Construye grafo: intenta OSRM (si activado) → fallback Haversine."""
    ids = list(PUNTOS.keys())
    n = len(ids)

    # 1) Caché
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                G = json.load(f)
            G = {int(k): {int(k2): v2 for k2, v2 in v.items()} for k, v in G.items()}
            print(f"✅ Grafo cargado desde caché ({len(G)} nodos)")
            return G
        except Exception as e:
            print(f"⚠️ Caché inválida: {e}")

    # 2) Si USAR_OSRM=1, intentar /table
    if USAR_OSRM:
        print("🌐 Intentando OSRM /table...")
        res = intentar_osrm_table()
        if res:
            dist_m, dur_s = res
            G = {}
            for i, a in enumerate(ids):
                G[a] = {}
                for j, b in enumerate(ids):
                    if i == j:
                        continue
                    d_km = (dist_m[i][j] or 0) / 1000
                    t_min = (dur_s[i][j] or 0) / 60
                    if d_km <= 0:
                        # fallback para este par
                        d_km = haversine(PUNTOS[a]["lat"], PUNTOS[a]["lng"],
                                         PUNTOS[b]["lat"], PUNTOS[b]["lng"]) * FACTOR_CARRETERA
                        t_min = (d_km / VELOCIDAD_PROMEDIO_KMH) * 60
                    G[a][b] = {
                        "distancia_km": round(d_km, 2),
                        "tiempo_min": round(t_min, 2),
                        "costo": round(d_km * COSTO_POR_KM, 2),
                    }
            try:
                with open(CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump({str(k): {str(k2): v2 for k2, v2 in v.items()} for k, v in G.items()},
                              f, ensure_ascii=False)
                print(f"💾 Caché OSRM guardada")
            except Exception:
                pass
            return G

    # 3) Fallback Haversine (siempre funciona, instantáneo)
    print("📐 Usando Haversine × 1.35 (sin OSRM)")
    G = construir_grafo_haversine()
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({str(k): {str(k2): v2 for k2, v2 in v.items()} for k, v in G.items()},
                      f, ensure_ascii=False)
        print(f"💾 Caché guardada en {CACHE_FILE}")
    except Exception as e:
        print(f"⚠️ No se pudo guardar caché: {e}")
    return G


# ============================================================
# ESTADO GLOBAL
# ============================================================
GRAFO = None


def asegurar_grafo():
    global GRAFO
    if GRAFO is None:
        GRAFO = construir_grafo()
    return GRAFO


# ============================================================
# DIJKSTRA
# ============================================================
def dijkstra(grafo, origen, destino, criterio):
    pesos = {"distancia": "distancia_km", "tiempo": "tiempo_min", "costo": "costo"}
    campo = pesos.get(criterio, "tiempo")

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
# GEOMETRÍA DE LA RUTA (línea recta entre nodos — sin OSRM)
# ============================================================
def geometria_simple(camino):
    """Genera puntos interpolados entre cada par de nodos (línea recta)."""
    puntos = []
    for i in range(len(camino) - 1):
        a, b = camino[i], camino[i + 1]
        pa, pb = PUNTOS[a], PUNTOS[b]
        # interpolar 15 puntos por segmento para que se vea suave
        for k in range(15):
            t = k / 15
            lat = pa["lat"] + (pb["lat"] - pa["lat"]) * t
            lng = pa["lng"] + (pb["lng"] - pa["lng"]) * t
            puntos.append([lat, lng])
        puntos.append([pb["lat"], pb["lng"]])
    return puntos


# ============================================================
# API
# ============================================================
@app.route("/")
def index():
    return render_template("index.html", atractivos=ATRACTIVOS)


@app.route("/api/estado")
def api_estado():
    return jsonify({
        "grafo_listo": GRAFO is not None,
        "nodos": len(GRAFO) if GRAFO else 0,
        "usar_osrm": USAR_OSRM,
    })


@app.route("/api/coordenadas")
def api_coordenadas():
    out = {}
    for nodo, d in PUNTOS.items():
        out[nodo] = {
            "nombre": d["nombre"], "cod": d["cod"], "tipo": d["tipo"],
            "lat": d["lat"], "lng": d["lng"], "descripcion": d["descripcion"],
        }
    return jsonify(out)


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

        grafo = asegurar_grafo()

        res = dijkstra(grafo, origen, destino, criterio)
        if res is None:
            return jsonify({"exito": False, "error": "No hay camino entre esos nodos"}), 404

        camino = res["camino"]

        dist_total = 0.0
        tiempo_total = 0.0
        segmentos = []
        for i in range(len(camino) - 1):
            a, b = camino[i], camino[i + 1]
            seg = grafo[a][b]
            dist_total += seg["distancia_km"]
            tiempo_total += seg["tiempo_min"]
            segmentos.append({"origen": a, "destino": b, **seg})

        nodos_ruta = [{
            "id": n,
            "nombre": ATRACTIVOS[n]["nombre"],
            "cod": ATRACTIVOS[n]["cod"],
            "tipo": ATRACTIVOS[n]["tipo"],
            "descripcion": ATRACTIVOS[n]["descripcion"],
            "lat": PUNTOS[n]["lat"],
            "lng": PUNTOS[n]["lng"],
        } for n in camino]

        return jsonify({
            "exito": True,
            "origen": origen, "destino": destino, "criterio": criterio,
            "camino": camino, "nodos_ruta": nodos_ruta,
            "distancia_km": round(dist_total, 2),
            "tiempo_min": round(tiempo_total, 2),
            "costo": round(dist_total * COSTO_POR_KM, 2),
            "puntos_ruta": geometria_simple(camino),
            "segmentos": segmentos,
            "instrucciones": [],
            "nodos_visitados": len(camino),
            "aproximado": True,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"exito": False, "error": str(e)}), 500


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


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print(" RUTAS TURÍSTICAS DE COCLÉ")
    print(f" Modo: {'OSRM + Haversine' if USAR_OSRM else 'Haversine × 1.35'}")
    print("=" * 50)

    # Precargar grafo (instantáneo porque es Haversine)
    asegurar_grafo()
    print(f"✅ Grafo listo: {len(GRAFO)} nodos")

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
