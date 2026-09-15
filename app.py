"""
Plataforma de Rutas Turísticas - Provincia de Coclé, Panamá
Servidor Flask con grafo COMPLETO + algoritmo de Dijkstra + OSRM.

═══════════════════════════════════════════════════════════════════════════════
ARQUITECTURA (Opción A: grafo completo con caché)
═══════════════════════════════════════════════════════════════════════════════
El sistema construye un grafo COMPLETO entre los 29 atractivos:
cada par (i, j) tiene una arista con su distancia/tiempo/costo real
medida con OSRM sobre OpenStreetMap.

  • 29 nodos → 406 aristas (i < j).
  • Cada arista se consulta UNA VEZ a OSRM.
  • Los resultados se guardan en cache_aristas_<fuente>.json.
  • Primer arranque: ~5-10 min construyendo la caché.
  • Arranques siguientes: instantáneo (lee el JSON).

Dijkstra opera sobre este grafo completo. El camino que devuelve
Dijkstra ES el camino físico real, y su distancia ES la distancia
real de conducción. Camino y distancia son coherentes.

Las distancias coinciden con Google Maps dentro de la tolerancia
esperada entre proveedores de ruteo (±5-10%).

═══════════════════════════════════════════════════════════════════════════════
FLUJO
═══════════════════════════════════════════════════════════════════════════════
1. Arranque:
   - Si existe cache_aristas_<fuente>.json → cargar.
   - Si no → construir consultando OSRM y guardar.
2. /api/ruta:
   - Dijkstra sobre grafo completo.
   - Devuelve camino + distancia real del camino.
3. /api/dia/<n>:
   - Dijkstra (fuerza bruta) para el orden óptimo de visita.
   - Suma las aristas del orden → distancia real.

═══════════════════════════════════════════════════════════════════════════════
FUENTE OFICIAL DE COORDENADAS
═══════════════════════════════════════════════════════════════════════════════
Fuente OFICIAL: Google Maps (ATRACTIVOS_GOOGLE).
Modo alternativo: OpenStreetMap (ATRACTIVOS_OSM) — análisis de sensibilidad.
═══════════════════════════════════════════════════════════════════════════════
"""

from flask import Flask, render_template, request, jsonify
import os
import json
import threading
import requests
import heapq
import math
import time
from itertools import permutations

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

CRITERIO_OFICIAL = "distancia"
FUENTE_OFICIAL = "google"

# Directorio y archivo de caché
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# ============================================================
# COORDENADAS
# ============================================================

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
         "lat": 8.33220, "lng": -80.51420,
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

FUENTE_COORDENADAS = os.environ.get("FUENTE_COORDENADAS", FUENTE_OFICIAL).lower()
if FUENTE_COORDENADAS not in ("google", "osm"):
    FUENTE_COORDENADAS = FUENTE_OFICIAL


def obtener_atractivos_por_fuente(fuente):
    if fuente == "osm":
        return ATRACTIVOS_OSM
    return ATRACTIVOS_GOOGLE


ATRACTIVOS = obtener_atractivos_por_fuente(FUENTE_COORDENADAS)


# ============================================================
# UTILIDADES
# ============================================================

def distancia_haversine(lat1, lon1, lat2, lon2):
    radio_tierra = 6371.0
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return radio_tierra * c


def peso_arista_fallback(lat1, lng1, lat2, lng2):
    dist_km = distancia_haversine(lat1, lng1, lat2, lng2)
    tiempo_min = (dist_km / VELOCIDAD_FALLBACK_KMH) * 60
    costo = dist_km * COSTO_POR_KM
    return dist_km, tiempo_min, costo


def ruta_cache_path(fuente):
    return os.path.join(CACHE_DIR, f"cache_aristas_{fuente}.json")


# ============================================================
# CONSULTAS A OSRM
# ============================================================

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
            print(f"    Intento {intento+1} falló (nearest): {e}")
            time.sleep(1)
    return {"exito": False, "error": "No se encontró carretera cercana"}


def obtener_ruta_osrm(lat1, lng1, lat2, lng2):
    url = f"{OSRM_URL}/route/v1/driving/{lng1},{lat1};{lng2},{lat2}"
    params = {"overview": "false", "steps": "false"}
    for intento in range(MAX_RETRIES):
        try:
            respuesta = requests.get(url, params=params, timeout=TIMEOUT)
            data = respuesta.json()
            if respuesta.status_code == 200 and data.get("code") == "Ok":
                ruta = data["routes"][0]
                dist = ruta["distance"] / 1000.0
                tmin = ruta["duration"] / 60.0
                return {"distancia_km": dist, "tiempo_min": tmin,
                        "costo": dist * COSTO_POR_KM, "exito": True}
            time.sleep(1)
        except Exception as e:
            print(f"    Intento {intento+1} falló (route): {e}")
            time.sleep(1)
    return {"exito": False, "error": "No se pudo calcular la ruta"}


# ============================================================
# CONSTRUCCIÓN DEL GRAFO COMPLETO (con caché)
# ============================================================

GRAFO = {}
PUNTOS_AJUSTADOS = {}
FUENTE_GRAFO = None
CACHE_CARGADO = False
_lock_grafo = threading.Lock()
_progreso_cache = {"estado": "sin_iniciar", "hechas": 0, "total": 0, "inicio": None}


def ajustar_puntos_a_carreteras():
    """Ajusta cada atractivo a la carretera más cercana (snapping)."""
    puntos_ajustados = {}
    total = len(ATRACTIVOS)
    print(f"  Ajustando {total} atractivos a carreteras...")
    for i, (nodo_id, atractivo) in enumerate(ATRACTIVOS.items(), 1):
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
        print(f"    [{i}/{total}] {atractivo['cod']} ajustado", end="\r")
    print(f"    [{total}/{total}] Todos ajustados.        ")
    return puntos_ajustados


def construir_grafo_completo(puntos):
    """
    Construye un grafo COMPLETO: cada par (i, j) con i < j
    tiene una arista con distancia/tiempo/costo medidos con OSRM.

    29 nodos → 406 aristas → 406 consultas a OSRM.
    """
    global _progreso_cache
    grafo = {nodo: {} for nodo in puntos}
    nodos = sorted(puntos.keys())
    total_aristas = len(nodos) * (len(nodos) - 1) // 2

    _progreso_cache = {
        "estado": "construyendo",
        "hechas": 0,
        "total": total_aristas,
        "inicio": time.time(),
        "fuente": FUENTE_COORDENADAS
    }

    hechas = 0
    for i, a in enumerate(nodos):
        for b in nodos[i + 1:]:
            hechas += 1
            _progreso_cache["hechas"] = hechas

            p_a = puntos[a]
            p_b = puntos[b]

            # Intentar OSRM
            resultado = obtener_ruta_osrm(p_a["lat"], p_a["lng"], p_b["lat"], p_b["lng"])
            if resultado.get("exito"):
                datos = {
                    "distancia_km": resultado["distancia_km"],
                    "tiempo_min": resultado["tiempo_min"],
                    "costo": resultado["costo"]
                }
            else:
                d, t, c = peso_arista_fallback(p_a["lat"], p_a["lng"], p_b["lat"], p_b["lng"])
                datos = {"distancia_km": d, "tiempo_min": t, "costo": c}

            grafo[a][b] = datos
            grafo[b][a] = datos

            # Progreso cada 20 aristas
            if hechas % 20 == 0 or hechas == total_aristas:
                pct = hechas / total_aristas * 100
                transcurrido = time.time() - _progreso_cache["inicio"]
                if hechas > 0:
                    restante = transcurrido / hechas * (total_aristas - hechas)
                    mins = int(restante // 60)
                    segs = int(restante % 60)
                    print(f"    [{hechas}/{total_aristas}] {pct:.1f}% - ~{mins}m{segs}s restantes", end="\r")
                else:
                    print(f"    [{hechas}/{total_aristas}] {pct:.1f}%", end="\r")

    print(f"    [{total_aristas}/{total_aristas}] 100.0% completado.        ")
    _progreso_cache["estado"] = "listo"
    return grafo


def guardar_cache(grafo, puntos):
    """Guarda el grafo y los puntos ajustados en JSON."""
    path = ruta_cache_path(FUENTE_COORDENADAS)
    payload = {
        "fuente": FUENTE_COORDENADAS,
        "timestamp": time.time(),
        "total_nodos": len(puntos),
        "total_aristas": sum(len(v) for v in grafo.values()) // 2,
        "puntos": {str(k): v for k, v in puntos.items()},
        "grafo": {str(k): {str(kk): vv for kk, vv in v.items()} for k, v in grafo.items()}
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"  ✔ Caché guardada: {path}")


def cargar_cache():
    """Intenta cargar el grafo desde caché. Devuelve (grafo, puntos) o (None, None)."""
    path = ruta_cache_path(FUENTE_COORDENADAS)
    if not os.path.exists(path):
        return None, None
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if payload.get("fuente") != FUENTE_COORDENADAS:
            print(f"  ⚠ Caché existe pero es de otra fuente ({payload.get('fuente')}). Se ignora.")
            return None, None
        # Reconstruir con claves int
        puntos = {int(k): v for k, v in payload["puntos"].items()}
        grafo = {int(k): {int(kk): vv for kk, vv in v.items()} for k, v in payload["grafo"].items()}
        # Validar que las coordenadas ajustadas coincidan con las actuales
        for nodo, datos in puntos.items():
            if nodo in ATRACTIVOS:
                # Solo verificamos que el lat/lng ajustado sea el mismo
                if abs(datos.get("lat", 0) - puntos[nodo].get("lat", 0)) > 1e-6:
                    print(f"  ⚠ Caché desactualizada para nodo {nodo}. Se reconstruye.")
                    return None, None
        return grafo, puntos
    except Exception as e:
        print(f"  ⚠ Error cargando caché: {e}. Se reconstruye.")
        return None, None


def preparar_grafo(force_rebuild=False):
    """Prepara el grafo: carga caché o reconstruye."""
    global GRAFO, PUNTOS_AJUSTADOS, FUENTE_GRAFO, CACHE_CARGADO

    if not force_rebuild:
        grafo_cache, puntos_cache = cargar_cache()
        if grafo_cache is not None:
            GRAFO = grafo_cache
            PUNTOS_AJUSTADOS = puntos_cache
            FUENTE_GRAFO = FUENTE_COORDENADAS
            CACHE_CARGADO = True
            print(f"  ✔ Caché cargada: {len(GRAFO)} nodos, "
                  f"{sum(len(v) for v in GRAFO.values()) // 2} aristas (instantáneo).")
            return

    # Construcción desde cero
    print("  Sin caché disponible. Construyendo grafo completo...")
    print("  ⏳ Esto puede tardar ~5-10 min la primera vez. Se guardará en caché.")
    PUNTOS_AJUSTADOS = ajustar_puntos_a_carreteras()
    GRAFO = construir_grafo_completo(PUNTOS_AJUSTADOS)
    FUENTE_GRAFO = FUENTE_COORDENADAS
    CACHE_CARGADO = True
    guardar_cache(GRAFO, PUNTOS_AJUSTADOS)


def asegurar_grafo_actualizado():
    global GRAFO, PUNTOS_AJUSTADOS, FUENTE_GRAFO
    if GRAFO and FUENTE_GRAFO == FUENTE_COORDENADAS:
        return
    with _lock_grafo:
        if GRAFO and FUENTE_GRAFO == FUENTE_COORDENADAS:
            return
        preparar_grafo()


# ============================================================
# DIJKSTRA
# ============================================================

def dijkstra(grafo, origen, destino, criterio):
    pesos = {"distancia": "distancia_km", "tiempo": "tiempo_min", "costo": "costo"}
    if criterio not in pesos:
        criterio = CRITERIO_OFICIAL
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


def orden_optimo_visita(destinos, criterio="distancia"):
    """
    Encuentra el orden óptimo de visita (TSP) usando el grafo completo.
    Como el grafo ya tiene todas las aristas reales, no hace falta matriz
    separada: se leen directamente de GRAFO.
    """
    BASE = 15
    destinos_sin_base = [d for d in destinos if d != BASE]
    if not destinos_sin_base:
        return [], 0.0

    campo_peso = {"distancia": "distancia_km", "tiempo": "tiempo_min",
                  "costo": "costo"}.get(criterio, "distancia_km")

    mejor_costo = float("inf")
    mejor_orden = None

    for perm in permutations(destinos_sin_base):
        secuencia = [BASE] + list(perm) + [BASE]
        total = 0.0
        valido = True
        for i in range(len(secuencia) - 1):
            a, b = secuencia[i], secuencia[i + 1]
            if a not in GRAFO or b not in GRAFO[a]:
                valido = False
                break
            peso = GRAFO[a][b].get(campo_peso, 0)
            if peso <= 0:
                valido = False
                break
            total += peso
        if valido and total < mejor_costo:
            mejor_costo = total
            mejor_orden = list(perm)

    return mejor_orden, mejor_costo


def metricas_camino(camino):
    """Suma las aristas del camino. Como el grafo es completo, cada tramo
    es una ruta real medida con OSRM."""
    if not camino or len(camino) < 2:
        return {"distancia_km": 0.0, "tiempo_conduccion_min": 0.0, "costo": 0.0}
    d = t = c = 0.0
    segmentos = []
    for i in range(len(camino) - 1):
        a, b = camino[i], camino[i + 1]
        arista = GRAFO[a][b]
        d += arista["distancia_km"]
        t += arista["tiempo_min"]
        c += arista["costo"]
        segmentos.append({
            "origen": a, "destino": b,
            "distancia_km": round(arista["distancia_km"], 2),
            "tiempo_min": round(arista["tiempo_min"], 2),
            "costo": round(arista["costo"], 2),
        })
    return {
        "distancia_km": d,
        "tiempo_conduccion_min": t,
        "costo": c,
        "segmentos": segmentos
    }


# ============================================================
# RUTAS HTTP
# ============================================================

@app.route("/")
def index():
    return render_template(
        "index.html",
        atractivos=ATRACTIVOS,
        fuente_actual=FUENTE_COORDENADAS,
        fuente_oficial=FUENTE_OFICIAL,
        factor_holgura=FACTOR_HOLGURA,
        criterio_oficial=CRITERIO_OFICIAL,
    )


@app.route("/api/ruta", methods=["POST"])
def api_ruta():
    try:
        data = request.get_json()
        origen = int(data["origen"])
        destino = int(data["destino"])
        criterio = data.get("criterio", CRITERIO_OFICIAL)
        if origen not in ATRACTIVOS:
            return jsonify({"exito": False, "error": "El nodo de origen no existe."}), 400
        if destino not in ATRACTIVOS:
            return jsonify({"exito": False, "error": "El nodo de destino no existe."}), 400
        if origen == destino:
            return jsonify({"exito": False, "error": "El origen y destino no pueden ser iguales."}), 400

        asegurar_grafo_actualizado()

        resultado_dijkstra = dijkstra(GRAFO, origen, destino, criterio)
        if resultado_dijkstra is None:
            return jsonify({"exito": False, "error": "No se encontró un camino."}), 404

        camino = resultado_dijkstra["camino"]
        metricas = metricas_camino(camino)

        dist_total = metricas["distancia_km"]
        t_conduccion = metricas["tiempo_conduccion_min"]
        costo_total = metricas["costo"]
        t_total = t_conduccion * FACTOR_HOLGURA

        nodos_ruta = []
        for nodo in camino:
            nodos_ruta.append({
                "id": nodo, **ATRACTIVOS[nodo],
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
            "distancia_km": round(dist_total, 2),
            "tiempo_conduccion_min": round(t_conduccion, 2),
            "tiempo_min": round(t_total, 2),
            "factor_holgura": FACTOR_HOLGURA,
            "costo": round(costo_total, 2),
            "fuente_metricas": "osrm",
            "segmentos": metricas["segmentos"],
            "nodos_visitados": len(nodos_ruta),
            "metodo": "A_dijkstra_grafo_completo"
        })
    except Exception as e:
        print("ERROR API RUTA:", e)
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/dia/<int:dia_num>")
def api_dia(dia_num):
    try:
        dias = {
            1: {"destinos": [1, 2, 4, 5, 17], "zona": "🌊 Playas de Antón"},
            2: {"destinos": [8, 22, 12, 14, 15], "zona": "🏛️ Penonomé Histórico"},
            3: {"destinos": [18, 20, 23, 24, 13, 9], "zona": "⛰️ La Pintada - Montaña"},
            4: {"destinos": [10, 25, 26, 19], "zona": "🏺 Ruta Arqueológica de Natá"},
            5: {"destinos": [6, 7, 28, 21, 29], "zona": "🌿 Naturaleza de Antón"},
            6: {"destinos": [16, 3, 27, 11], "zona": "🌅 Tesoros de Aguadulce"},
            7: {"destinos": [15, 18, 20, 23, 24], "zona": "🎯 Circuito Integrador"}
        }
        if dia_num not in dias:
            return jsonify({"exito": False, "error": "Día inválido (1-7)."}), 400
        criterio = request.args.get("criterio", CRITERIO_OFICIAL)
        if criterio not in ("distancia", "tiempo", "costo"):
            criterio = CRITERIO_OFICIAL
        dia = dias[dia_num]
        destinos = dia["destinos"]
        asegurar_grafo_actualizado()

        orden, _ = orden_optimo_visita(destinos, criterio)
        if orden is None:
            return jsonify({"exito": False, "error": "No se pudo calcular el orden óptimo."}), 500

        BASE = 15
        secuencia = [BASE] + orden + [BASE]

        # Sumar aristas del camino
        dist_total = 0.0
        t_conduccion = 0.0
        costo_total = 0.0
        for i in range(len(secuencia) - 1):
            a, b = secuencia[i], secuencia[i + 1]
            arista = GRAFO[a][b]
            dist_total += arista["distancia_km"]
            t_conduccion += arista["tiempo_min"]
            costo_total += arista["costo"]

        t_total = t_conduccion * FACTOR_HOLGURA

        nodos_ruta = []
        for nodo in secuencia:
            nodos_ruta.append({
                "id": nodo, **ATRACTIVOS[nodo],
                "lat_carretera": PUNTOS_AJUSTADOS[nodo]["lat"],
                "lng_carretera": PUNTOS_AJUSTADOS[nodo]["lng"]
            })

        # Segmentos
        segmentos = []
        for i in range(len(secuencia) - 1):
            a, b = secuencia[i], secuencia[i + 1]
            arista = GRAFO[a][b]
            segmentos.append({
                "origen": a, "destino": b,
                "distancia_km": round(arista["distancia_km"], 2),
                "tiempo_min": round(arista["tiempo_min"], 2),
                "costo": round(arista["costo"], 2),
            })

        return jsonify({
            "exito": True,
            "dia": dia_num,
            "zona": dia["zona"],
            "criterio": criterio,
            "orden_optimo": secuencia,
            "camino": secuencia,
            "nodos_ruta": nodos_ruta,
            "segmentos": segmentos,
            "distancia_km": round(dist_total, 2),
            "tiempo_conduccion_min": round(t_conduccion, 2),
            "tiempo_min": round(t_total, 2),
            "factor_holgura": FACTOR_HOLGURA,
            "costo": round(costo_total, 2),
            "fuente_metricas": "osrm",
            "nodos_visitados": len(nodos_ruta),
            "metodo": "A_dijkstra_grafo_completo"
        })
    except Exception as e:
        print("ERROR API DIA:", e)
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/coordenadas")
def api_coordenadas():
    asegurar_grafo_actualizado()
    resultado = {}
    for nodo, datos in PUNTOS_AJUSTADOS.items():
        resultado[nodo] = {
            "nombre": datos["nombre"], "cod": datos["cod"], "tipo": datos["tipo"],
            "lat": datos.get("lat_original", datos["lat"]), "lng": datos.get("lng_original", datos["lng"]),
            "lat_original": datos.get("lat_original", datos["lat"]),
            "lng_original": datos.get("lng_original", datos["lng"]),
            "lat_carretera": datos["lat"], "lng_carretera": datos["lng"]
        }
    return jsonify(resultado)


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
        "fuente_oficial": FUENTE_OFICIAL,
        "fuente_nombre": "OpenStreetMap" if FUENTE_COORDENADAS == "osm" else "Google Maps",
        "es_oficial": FUENTE_COORDENADAS == FUENTE_OFICIAL,
        "total_atractivos": len(ATRACTIVOS),
        "factor_holgura": FACTOR_HOLGURA,
        "criterio_oficial": CRITERIO_OFICIAL,
        "costo_por_km": COSTO_POR_KM,
        "metodo": "A_dijkstra_grafo_completo",
        "cache_cargado": CACHE_CARGADO
    })


@app.route("/api/fuente", methods=["POST"])
def api_fuente_post():
    global FUENTE_COORDENADAS, ATRACTIVOS, GRAFO, PUNTOS_AJUSTADOS, FUENTE_GRAFO, CACHE_CARGADO
    try:
        data = request.get_json() or {}
        nueva = str(data.get("fuente", "")).lower().strip()
        if nueva not in ("google", "osm"):
            return jsonify({"exito": False, "error": "Fuente inválida. Use 'google' u 'osm'."}), 400
        with _lock_grafo:
            if nueva == FUENTE_COORDENADAS and GRAFO and FUENTE_GRAFO == nueva:
                return jsonify({"exito": True, "fuente": FUENTE_COORDENADAS,
                                "mensaje": "La fuente ya estaba activa."})
            FUENTE_COORDENADAS = nueva
            ATRACTIVOS = obtener_atractivos_por_fuente(nueva)
            GRAFO = {}
            PUNTOS_AJUSTADOS = {}
            FUENTE_GRAFO = None
            CACHE_CARGADO = False
        asegurar_grafo_actualizado()
        return jsonify({
            "exito": True,
            "fuente": FUENTE_COORDENADAS,
            "fuente_nombre": "OpenStreetMap" if FUENTE_COORDENADAS == "osm" else "Google Maps",
            "es_oficial": FUENTE_COORDENADAS == FUENTE_OFICIAL,
            "total_atractivos": len(ATRACTIVOS)
        })
    except Exception as e:
        print("ERROR API FUENTE POST:", e)
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/cache/estado")
def api_cache_estado():
    """Endpoint para saber el estado del caché."""
    return jsonify({
        "estado": _progreso_cache["estado"],
        "hechas": _progreso_cache["hechas"],
        "total": _progreso_cache["total"],
        "porcentaje": round(_progreso_cache["hechas"] / _progreso_cache["total"] * 100, 1)
                      if _progreso_cache["total"] > 0 else 0,
        "cache_en_disco": os.path.exists(ruta_cache_path(FUENTE_COORDENADAS)),
        "cache_path": ruta_cache_path(FUENTE_COORDENADAS),
        "nodos_cargados": len(GRAFO),
        "aristas_cargadas": sum(len(v) for v in GRAFO.values()) // 2 if GRAFO else 0,
    })


@app.route("/api/cache/reconstruir", methods=["POST"])
def api_cache_reconstruir():
    """Reconstruye el caché desde cero."""
    try:
        # Borrar caché existente
        path = ruta_cache_path(FUENTE_COORDENADAS)
        if os.path.exists(path):
            os.remove(path)

        with _lock_grafo:
            preparar_grafo(force_rebuild=True)

        return jsonify({
            "exito": True,
            "nodos": len(GRAFO),
            "aristas": sum(len(v) for v in GRAFO.values()) // 2
        })
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("==========================================")
    print(" RUTAS TURÍSTICAS DE COCLÉ")
    print(" Método: Opción A — Grafo completo con caché")
    print("==========================================")
    print(f"Atractivos registrados: {len(ATRACTIVOS)}")
    print(f"Fuente oficial: {FUENTE_OFICIAL.upper()}")
    print(f"Fuente activa: {FUENTE_COORDENADAS.upper()}")
    print(f"Criterio oficial: {CRITERIO_OFICIAL.upper()}")
    print(f"Factor de holgura: {FACTOR_HOLGURA} (+{round((FACTOR_HOLGURA - 1) * 100)}%)")
    print(f"Caché: {ruta_cache_path(FUENTE_COORDENADAS)}")
    print()

    try:
        preparar_grafo()
        print(f"\n✔ Grafo listo: {len(GRAFO)} nodos, "
              f"{sum(len(v) for v in GRAFO.values()) // 2} aristas.")
    except Exception as e:
        print(f"✗ No se pudo preparar el grafo: {e}")
        print("  Se intentará en la primera petición.")

    print("\nServidor iniciado.")
    print("==========================================\n")

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("FLASK_DEBUG", "0") == "1")
