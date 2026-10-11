"""
Plataforma de Rutas Turísticas - Provincia de Coclé, Panamá
Servidor Flask con OSRM + algoritmo de Dijkstra.

═══════════════════════════════════════════════════════════════════════════════
ARQUITECTURA (grafo + Dijkstra real)
═══════════════════════════════════════════════════════════════════════════════
• Grafo G = (V, E): V = los 29 atractivos turísticos.
  Aristas (no dirigidas):
    1) Cada atractivo se conecta con sus K vecinos más cercanos (Haversine).
    2) Se añade un árbol de expansión mínima (Prim) para garantizar que G sea
       conexo.
    3) Las ciudades-hub (Penonomé, Aguadulce, Antón, La Pintada, Natá) se
       conectan todas entre sí: son las "estaciones" naturales entre zonas y
       así ir de una ciudad a otra nunca obliga a un rodeo por atractivos.
    4) Reparación de desvíos (spanner voraz): se añade la arista directa a-b
       cuando el camino mínimo que ya existe entre a y b es más largo que
       FACTOR_DESVIO × la distancia directa por carretera. Así ningún camino
       del grafo supera ese desvío máximo (por defecto 1.3 = +30 %).
• Pesos de las aristas: distancia, tiempo y costo REALES por carretera,
  obtenidos de OSRM con una sola consulta (/table) por fuente de coordenadas.
• Camino mínimo entre dos atractivos: algoritmo de Dijkstra (cola de prioridad
  con heapq) sobre G, según el criterio oficial: DISTANCIA. El tiempo y el
  costo se reportan como métricas informativas del camino resultante.
• Orden de visita de cada día: se calcula la matriz de caminos mínimos entre
  las paradas (Dijkstra desde cada parada) y se resuelve el TSP de forma exacta
  por enumeración (máximo 6 paradas por día → 720 permutaciones).
• La geometría del mapa se dibuja con OSRM (/route) siguiendo los nodos del
  camino calculado por Dijkstra.
• Si OSRM no responde, los pesos se calculan con Haversine (línea recta).

═══════════════════════════════════════════════════════════════════════════════
FUENTE OFICIAL DE COORDENADAS
═══════════════════════════════════════════════════════════════════════════════
Fuente OFICIAL: Google Maps (ATRACTIVOS_GOOGLE).
Modo alternativo: OpenStreetMap (ATRACTIVOS_OSM) — análisis de sensibilidad.
═══════════════════════════════════════════════════════════════════════════════
"""

from flask import Flask, render_template, request, jsonify
import os
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

# Grafo: cada atractivo se conecta con sus K vecinos más cercanos
K_VECINOS = 4

# Máximo desvío permitido: ningún camino del grafo puede ser más largo que
# FACTOR_DESVIO × la distancia directa por carretera entre sus extremos.
FACTOR_DESVIO = float(os.environ.get("FACTOR_DESVIO", "1.3"))

# Conectar entre sí todas las ciudades-hub (tipo "Hub/Ciudad"). Poner la
# variable de entorno CONECTAR_HUBS=0 para desactivarlo (análisis de sensibilidad).
CONECTAR_HUBS = os.environ.get("CONECTAR_HUBS", "1") != "0"

# Nodo base de los itinerarios diarios (Penonomé)
BASE = 15

# Único criterio de optimización (oficial): DISTANCIA.
# El tiempo y el costo se reportan como métricas informativas.
CLAVE_PESO = {
    "distancia": "distancia_km",
}

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
# ITINERARIO DE 7 DÍAS
# ============================================================

DIAS = [
    {"dia": 1, "destinos": [1, 2, 4, 5, 17], "zona": "🌊 Playas de Antón"},
    {"dia": 2, "destinos": [8, 22, 12, 14, 15], "zona": "🏛️ Penonomé Histórico"},
    {"dia": 3, "destinos": [18, 20, 23, 24, 13, 9], "zona": "⛰️ La Pintada - Montaña"},
    {"dia": 4, "destinos": [10, 25, 26, 19], "zona": "🏺 Ruta Arqueológica de Natá"},
    {"dia": 5, "destinos": [6, 7, 28, 21, 29], "zona": "🌿 Naturaleza de Antón"},
    {"dia": 6, "destinos": [16, 3, 27, 11], "zona": "🌅 Tesoros de Aguadulce"},
    {"dia": 7, "destinos": [15, 18, 20, 23, 24], "zona": "🎯 Circuito Integrador"},
]


# ============================================================
# UTILIDADES
# ============================================================

def distancia_haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


def peso_arista_fallback(lat1, lng1, lat2, lng2):
    dist_km = distancia_haversine(lat1, lng1, lat2, lng2)
    tiempo_min = (dist_km / VELOCIDAD_FALLBACK_KMH) * 60
    return dist_km, tiempo_min, dist_km * COSTO_POR_KM


# ============================================================
# CONSULTAS A OSRM
# ============================================================

def obtener_matrices_osrm(atractivos):
    """
    Una sola consulta al servicio /table de OSRM con TODOS los atractivos.
    Devuelve (ids, matriz_distancias_m, matriz_duraciones_s) o None si falla.
    """
    ids = sorted(atractivos)
    coord_str = ";".join(f"{atractivos[i]['lng']},{atractivos[i]['lat']}" for i in ids)
    url = f"{OSRM_URL}/table/v1/driving/{coord_str}"
    params = {"annotations": "duration,distance"}
    for intento in range(MAX_RETRIES):
        try:
            respuesta = requests.get(url, params=params, timeout=TIMEOUT)
            data = respuesta.json()
            if (respuesta.status_code == 200 and data.get("code") == "Ok"
                    and data.get("durations") and data.get("distances")):
                return ids, data["distances"], data["durations"]
            time.sleep(1)
        except Exception as e:
            print(f"  Intento {intento+1} OSRM table falló: {e}")
            time.sleep(1)
    return None


def obtener_ruta_multi_punto(puntos, con_geometria=True):
    """
    Consulta OSRM para un recorrido de varios puntos encadenados.
    puntos: lista de (lat, lng).
    """
    if len(puntos) < 2:
        return {"exito": False, "error": "Puntos insuficientes"}
    coord_str = ";".join(f"{lng},{lat}" for lat, lng in puntos)
    url = f"{OSRM_URL}/route/v1/driving/{coord_str}"
    params = {
        "overview": "full" if con_geometria else "false",
        "geometries": "geojson",
        "steps": "false"
    }
    for intento in range(MAX_RETRIES):
        try:
            respuesta = requests.get(url, params=params, timeout=60)
            data = respuesta.json()
            if respuesta.status_code == 200 and data.get("code") == "Ok":
                ruta = data["routes"][0]
                dist = ruta["distance"] / 1000.0
                tmin = ruta["duration"] / 60.0
                resultado = {
                    "distancia_km": dist,
                    "tiempo_min": tmin,
                    "costo": dist * COSTO_POR_KM,
                    "exito": True
                }
                if con_geometria:
                    geom = ruta["geometry"]["coordinates"]
                    resultado["puntos_ruta"] = [[c[1], c[0]] for c in geom]
                return resultado
            time.sleep(1)
        except Exception as e:
            print(f"  Intento {intento+1} OSRM multi falló: {e}")
            time.sleep(1)
    return {"exito": False, "error": "OSRM no respondió (multi-punto)"}


# ============================================================
# GRAFO
# ============================================================

def construir_grafo(atractivos):
    """
    Construye el grafo G = (V, E) de los atractivos.

    Aristas (no dirigidas):
      1) K vecinos más cercanos de cada nodo (Haversine).
      2) Árbol de expansión mínima (Prim) → G conexo.
      3) Todas las ciudades-hub conectadas entre sí (si CONECTAR_HUBS).
      4) Reparación de desvíos (spanner voraz): se añade la arista directa a-b
         si el camino mínimo actual entre a y b supera FACTOR_DESVIO × la
         distancia directa por carretera. Así ninguna ruta tiene un desvío
         absurdo (p. ej. Natá → Penonomé pasando por zonas intermedias lejanas).
    Pesos (dirigidos, a→b): distancia, tiempo y costo reales por carretera (OSRM).
    """
    ids = sorted(atractivos)

    def hav(a, b):
        return distancia_haversine(atractivos[a]["lat"], atractivos[a]["lng"],
                                   atractivos[b]["lat"], atractivos[b]["lng"])

    # 1) K vecinos más cercanos
    pares = set()
    for a in ids:
        vecinos = sorted((b for b in ids if b != a), key=lambda b: hav(a, b))
        for b in vecinos[:K_VECINOS]:
            pares.add((min(a, b), max(a, b)))

    # 2) Árbol de expansión mínima (Prim) para garantizar conectividad
    en_arbol = {ids[0]}
    while len(en_arbol) < len(ids):
        mejor = None
        for a in en_arbol:
            for b in ids:
                if b in en_arbol:
                    continue
                d = hav(a, b)
                if mejor is None or d < mejor[0]:
                    mejor = (d, a, b)
        en_arbol.add(mejor[2])
        pares.add((min(mejor[1], mejor[2]), max(mejor[1], mejor[2])))

    aristas_kmst = len(pares)

    # 3) Ciudades-hub conectadas entre sí
    if CONECTAR_HUBS:
        hubs = [n for n in ids if atractivos[n].get("tipo") == "Hub/Ciudad"]
        for i, a in enumerate(hubs):
            for b in hubs[i + 1:]:
                pares.add((min(a, b), max(a, b)))
    aristas_base = len(pares)

    # 4) Pesos reales de OSRM (una sola consulta)
    osrm = obtener_matrices_osrm(atractivos)
    indice = {n: i for i, n in enumerate(ids)}
    usados_fallback = 0

    def pesos(a, b, contar=True):
        nonlocal usados_fallback
        if osrm is not None:
            _, mat_d, mat_t = osrm
            d = mat_d[indice[a]][indice[b]]
            t = mat_t[indice[a]][indice[b]]
            if d is not None and t is not None:
                dist_km = d / 1000.0
                return {"distancia_km": dist_km,
                        "tiempo_min": t / 60.0,
                        "costo": dist_km * COSTO_POR_KM}
        if contar:
            usados_fallback += 1
        dist_km, tmin, costo = peso_arista_fallback(
            atractivos[a]["lat"], atractivos[a]["lng"],
            atractivos[b]["lat"], atractivos[b]["lng"])
        return {"distancia_km": dist_km, "tiempo_min": tmin, "costo": costo}

    ady = {n: {} for n in ids}
    for a, b in pares:
        ady[a][b] = pesos(a, b)
        ady[b][a] = pesos(b, a)

    # 5) Reparación de desvíos: se revisan los pares sin arista, del más
    #    cercano al más lejano (distancia directa por carretera).
    grafo_tmp = {"ady": ady}
    candidatos = sorted(
        (pesos(a, b, contar=False)["distancia_km"], a, b)
        for a in ids for b in ids
        if a < b and (a, b) not in pares
    )
    reparadas = []
    for _, a, b in candidatos:
        directo_ab = pesos(a, b, contar=False)["distancia_km"]
        directo_ba = pesos(b, a, contar=False)["distancia_km"]
        camino_ab = dijkstra(grafo_tmp, a, "distancia", b)[0][b]
        camino_ba = dijkstra(grafo_tmp, b, "distancia", a)[0][a]
        if (camino_ab > FACTOR_DESVIO * directo_ab
                or camino_ba > FACTOR_DESVIO * directo_ba):
            pares.add((a, b))
            ady[a][b] = pesos(a, b)
            ady[b][a] = pesos(b, a)
            reparadas.append((a, b))

    if osrm is None:
        fuente_pesos = "haversine"
    elif usados_fallback:
        fuente_pesos = "mixto"
    else:
        fuente_pesos = "osrm"

    return {
        "ids": ids,
        "atractivos": atractivos,
        "ady": ady,
        "num_aristas": len(pares),
        "aristas_kmst": aristas_kmst,
        "aristas_hubs": aristas_base - aristas_kmst,
        "aristas_base": aristas_base,
        "aristas_reparadas": len(reparadas),
        "reparadas": reparadas,
        "fuente_pesos": fuente_pesos,
    }


_GRAFOS = {}
_GRAFOS_LOCK = threading.Lock()


def obtener_grafo():
    """Devuelve el grafo de la fuente activa (se construye una vez por fuente)."""
    fuente = FUENTE_COORDENADAS
    with _GRAFOS_LOCK:
        if fuente in _GRAFOS:
            return _GRAFOS[fuente]
    grafo = construir_grafo(obtener_atractivos_por_fuente(fuente))
    if grafo["fuente_pesos"] == "osrm":
        with _GRAFOS_LOCK:
            _GRAFOS[fuente] = grafo
    return grafo


# ============================================================
# DIJKSTRA
# ============================================================

def dijkstra(grafo, origen, criterio="distancia", destino=None):
    """
    Algoritmo de Dijkstra con cola de prioridad (heapq).
    Minimiza la suma del atributo de arista según el criterio.
    Si se indica destino, se detiene al fijar su distancia.
    Devuelve (dist, prev).
    """
    clave = CLAVE_PESO[criterio]
    ady = grafo["ady"]
    dist = {n: math.inf for n in ady}
    prev = {}
    dist[origen] = 0.0
    cola = [(0.0, origen)]
    while cola:
        d, u = heapq.heappop(cola)
        if d > dist[u]:
            continue
        if destino is not None and u == destino:
            break
        for v, arista in ady[u].items():
            nd = d + arista[clave]
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(cola, (nd, v))
    return dist, prev


def reconstruir_camino(prev, origen, destino):
    """Reconstruye el camino origen → destino a partir de los predecesores."""
    camino = [destino]
    while camino[-1] != origen:
        if camino[-1] not in prev:
            return None
        camino.append(prev[camino[-1]])
    camino.reverse()
    return camino


def metricas_camino(grafo, camino):
    """Suma distancia, tiempo y costo de las aristas del camino y detalla los tramos."""
    dist = tiempo = costo = 0.0
    segmentos = []
    for a, b in zip(camino, camino[1:]):
        ar = grafo["ady"][a][b]
        dist += ar["distancia_km"]
        tiempo += ar["tiempo_min"]
        costo += ar["costo"]
        segmentos.append({
            "origen": a, "destino": b,
            "distancia_km": round(ar["distancia_km"], 2),
            "tiempo_min": round(ar["tiempo_min"], 2),
            "costo": round(ar["costo"], 2),
        })
    return dist, tiempo, costo, segmentos


def orden_optimo_visita(grafo, destinos, criterio="distancia"):
    """
    Orden óptimo de visita de un día (sale y regresa a BASE).
    1) Dijkstra desde cada parada → matriz de caminos mínimos.
    2) TSP exacto por enumeración de permutaciones sobre esa matriz.
    Devuelve (orden, costo_total) o (None, inf) si no hay solución.
    """
    paradas = []
    for d in destinos:
        if d != BASE and d not in paradas:
            paradas.append(d)
    if not paradas:
        return [], 0.0

    nodos = [BASE] + paradas
    D = {}
    for a in nodos:
        dist, _ = dijkstra(grafo, a, criterio)
        for b in nodos:
            D[(a, b)] = dist[b]

    mejor_costo = math.inf
    mejor_orden = None
    for perm in permutations(paradas):
        secuencia = [BASE] + list(perm) + [BASE]
        total = 0.0
        for i in range(len(secuencia) - 1):
            total += D[(secuencia[i], secuencia[i + 1])]
        if total < mejor_costo:
            mejor_costo = total
            mejor_orden = list(perm)
    return mejor_orden, mejor_costo


def construir_nodos_ruta(atractivos, camino, paradas):
    """Nodos del camino; es_parada=False marca atractivos por los que solo se pasa."""
    return [{
        "id": n, **atractivos[n],
        "lat_carretera": atractivos[n]["lat"],
        "lng_carretera": atractivos[n]["lng"],
        "es_parada": n in paradas,
    } for n in camino]


def geometria_camino(atractivos, camino):
    """Geometría por carretera (OSRM) siguiendo los nodos del camino de Dijkstra."""
    puntos = [(atractivos[n]["lat"], atractivos[n]["lng"]) for n in camino]
    if len(puntos) >= 2:
        r = obtener_ruta_multi_punto(puntos, con_geometria=True)
        if r.get("exito") and len(r.get("puntos_ruta", [])) >= 2:
            return r["puntos_ruta"]
    return [[lat, lng] for lat, lng in puntos]


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
    """
    Camino mínimo entre dos atractivos con Dijkstra sobre el grafo.
    Devuelve distancia, tiempo, costo, geometría, camino y tramos.
    """
    try:
        data = request.get_json(silent=True) or {}
        try:
            origen = int(data["origen"])
            destino = int(data["destino"])
        except (KeyError, TypeError, ValueError):
            return jsonify({"exito": False,
                            "error": "Debes enviar 'origen' y 'destino' (números)."}), 400
        criterio = data.get("criterio", CRITERIO_OFICIAL)
        if criterio not in CLAVE_PESO:
            criterio = CRITERIO_OFICIAL

        grafo = obtener_grafo()
        atractivos = grafo["atractivos"]

        if origen not in atractivos:
            return jsonify({"exito": False, "error": "Origen no existe."}), 400
        if destino not in atractivos:
            return jsonify({"exito": False, "error": "Destino no existe."}), 400
        if origen == destino:
            return jsonify({"exito": False, "error": "Origen y destino no pueden ser iguales."}), 400

        # Dijkstra
        _, prev = dijkstra(grafo, origen, criterio, destino)
        camino = reconstruir_camino(prev, origen, destino)
        if camino is None:
            return jsonify({"exito": False, "error": "No existe camino entre los nodos."}), 404

        dist_total, t_conduccion, costo_total, segmentos = metricas_camino(grafo, camino)
        t_total = t_conduccion * FACTOR_HOLGURA
        puntos_ruta = geometria_camino(atractivos, camino)
        nodos_ruta = construir_nodos_ruta(atractivos, camino, {origen, destino})

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
            "fuente_metricas": grafo["fuente_pesos"],
            "puntos_ruta": puntos_ruta,
            "segmentos": segmentos,
            "nodos_visitados": len(camino),
            "metodo": "dijkstra_grafo"
        })
    except Exception as e:
        print("ERROR API RUTA:", e)
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/dia/<int:dia_num>")
def api_dia(dia_num):
    """
    Itinerario óptimo de un día:
    1) Dijkstra desde cada parada + TSP exacto deciden el orden de visita.
    2) Cada tramo entre paradas es un camino mínimo de Dijkstra sobre el grafo.
    3) Las métricas son la suma de las aristas del recorrido completo.
    """
    try:
        dia = next((d for d in DIAS if d["dia"] == dia_num), None)
        if dia is None:
            return jsonify({"exito": False, "error": "Día inválido (1-7)."}), 400
        criterio = request.args.get("criterio", CRITERIO_OFICIAL)
        if criterio not in CLAVE_PESO:
            criterio = CRITERIO_OFICIAL

        grafo = obtener_grafo()
        atractivos = grafo["atractivos"]

        # 1) Orden óptimo de visita
        orden, _ = orden_optimo_visita(grafo, dia["destinos"], criterio)
        if orden is None:
            return jsonify({"exito": False, "error": "No se pudo calcular el orden óptimo."}), 500
        secuencia = [BASE] + orden + [BASE]

        # 2) Camino mínimo (Dijkstra) entre paradas consecutivas
        camino = [BASE]
        for a, b in zip(secuencia, secuencia[1:]):
            _, prev = dijkstra(grafo, a, criterio, b)
            tramo = reconstruir_camino(prev, a, b)
            if tramo is None:
                return jsonify({"exito": False, "error": "No existe camino entre paradas."}), 500
            camino.extend(tramo[1:])

        # 3) Métricas y geometría
        dist_total, t_conduccion, costo_total, segmentos = metricas_camino(grafo, camino)
        t_total = t_conduccion * FACTOR_HOLGURA
        puntos_ruta = geometria_camino(atractivos, camino)
        nodos_ruta = construir_nodos_ruta(atractivos, camino, set(secuencia))

        return jsonify({
            "exito": True,
            "dia": dia_num,
            "zona": dia["zona"],
            "criterio": criterio,
            "orden_optimo": secuencia,
            "camino": camino,
            "nodos_ruta": nodos_ruta,
            "puntos_ruta": puntos_ruta,
            "segmentos": segmentos,
            "distancia_km": round(dist_total, 2),
            "tiempo_conduccion_min": round(t_conduccion, 2),
            "tiempo_min": round(t_total, 2),
            "factor_holgura": FACTOR_HOLGURA,
            "costo": round(costo_total, 2),
            "fuente_metricas": grafo["fuente_pesos"],
            "nodos_visitados": len(nodos_ruta),
            "metodo": "dijkstra_grafo"
        })
    except Exception as e:
        print("ERROR API DIA:", e)
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/geometria", methods=["POST"])
def api_geometria():
    """Geometría por carretera (OSRM) para un camino dado (lista de ids de nodos)."""
    try:
        data = request.get_json(silent=True) or {}
        camino = data.get("camino")
        atractivos = ATRACTIVOS
        if (not isinstance(camino, list) or len(camino) < 2
                or any(not isinstance(n, int) or n not in atractivos for n in camino)):
            return jsonify({"exito": False, "error": "Camino inválido."}), 400
        return jsonify({"exito": True,
                        "puntos_ruta": geometria_camino(atractivos, camino)})
    except Exception as e:
        print("ERROR API GEOMETRIA:", e)
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/grafo")
def api_grafo():
    """
    Estadísticas del grafo (útil para la tesis): número de aristas del K-NN + MST,
    aristas añadidas por la reparación de desvíos y lista de esas aristas.
    """
    try:
        grafo = obtener_grafo()
        atractivos = grafo["atractivos"]
        return jsonify({
            "exito": True,
            "fuente": FUENTE_COORDENADAS,
            "fuente_pesos": grafo["fuente_pesos"],
            "nodos": len(grafo["ids"]),
            "k_vecinos": K_VECINOS,
            "factor_desvio": FACTOR_DESVIO,
            "num_aristas": grafo["num_aristas"],
            "conectar_hubs": CONECTAR_HUBS,
            "aristas_kmst": grafo["aristas_kmst"],
            "aristas_hubs": grafo["aristas_hubs"],
            "aristas_reparadas": grafo["aristas_reparadas"],
            "lista_reparadas": [
                {"a": a, "b": b,
                 "nombre_a": atractivos[a]["nombre"],
                 "nombre_b": atractivos[b]["nombre"],
                 "distancia_km": round(grafo["ady"][a][b]["distancia_km"], 2)}
                for a, b in grafo["reparadas"]
            ],
        })
    except Exception as e:
        print("ERROR API GRAFO:", e)
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/coordenadas")
def api_coordenadas():
    resultado = {}
    for nodo, datos in ATRACTIVOS.items():
        resultado[nodo] = {
            "nombre": datos["nombre"], "cod": datos["cod"], "tipo": datos["tipo"],
            "lat": datos["lat"], "lng": datos["lng"],
            "lat_carretera": datos["lat"], "lng_carretera": datos["lng"]
        }
    return jsonify(resultado)


@app.route("/api/dias")
def api_dias():
    return jsonify(DIAS)


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
        "k_vecinos": K_VECINOS,
        "factor_desvio": FACTOR_DESVIO,
        "metodo": "dijkstra_grafo"
    })


@app.route("/api/fuente", methods=["POST"])
def api_fuente_post():
    global FUENTE_COORDENADAS, ATRACTIVOS
    try:
        data = request.get_json() or {}
        nueva = str(data.get("fuente", "")).lower().strip()
        if nueva not in ("google", "osm"):
            return jsonify({"exito": False, "error": "Fuente inválida."}), 400
        FUENTE_COORDENADAS = nueva
        ATRACTIVOS = obtener_atractivos_por_fuente(nueva)
        return jsonify({
            "exito": True,
            "fuente": FUENTE_COORDENADAS,
            "fuente_nombre": "OpenStreetMap" if FUENTE_COORDENADAS == "osm" else "Google Maps",
            "es_oficial": FUENTE_COORDENADAS == FUENTE_OFICIAL,
            "total_atractivos": len(ATRACTIVOS)
        })
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("==========================================")
    print(" RUTAS TURÍSTICAS DE COCLÉ")
    print(" Método: Grafo + Dijkstra (heapq)")
    print(" Pesos reales por carretera: OSRM /table")
    print("==========================================")
    print(f"Atractivos registrados: {len(ATRACTIVOS)}")
    print(f"Fuente oficial: {FUENTE_OFICIAL.upper()}")
    print(f"Fuente activa: {FUENTE_COORDENADAS.upper()}")
    print(f"Criterio oficial: {CRITERIO_OFICIAL.upper()}")
    print(f"Vecinos por nodo (K): {K_VECINOS}")
    print(f"Ciudades-hub conectadas entre sí: {'SÍ' if CONECTAR_HUBS else 'NO'}")
    print(f"Desvío máximo permitido: {FACTOR_DESVIO} (+{round((FACTOR_DESVIO - 1) * 100)}%)")
    print(f"Factor de holgura: {FACTOR_HOLGURA} (+{round((FACTOR_HOLGURA - 1) * 100)}%)")
    print("\nServidor iniciado.")
    print("==========================================\n")

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("FLASK_DEBUG", "0") == "1")
