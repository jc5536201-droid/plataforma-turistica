# -*- coding: utf-8 -*-
"""
Plataforma de Rutas Turísticas - Provincia de Coclé, Panamá
Servidor Flask + algoritmo de Dijkstra (+ OSRM para dibujar el trazado).

═══════════════════════════════════════════════════════════════════════════════
ARQUITECTURA
═══════════════════════════════════════════════════════════════════════════════
• CRITERIO OFICIAL DE EVALUACIÓN: DISTANCIA (km). Tiempo y costo se reportan
  solo como valores de REFERENCIA.
• Fuente OFICIAL "google": grafo de 29 nodos y 57 aristas medidas en Google Maps
  (km y minutos), idéntico al del script rutas_cocle_dijkstra.py. Así, la
  plataforma y el script producen exactamente los mismos resultados.
• Fuente "osm" (solo análisis de sensibilidad): grafo generado con K vecinos
  más cercanos + árbol de expansión mínima + hubs + reparación de desvíos, con
  pesos reales de OSRM sobre coordenadas de OpenStreetMap.
• Camino mínimo: Dijkstra con cola de prioridad (heapq).
• Orden de visita de cada día: TSP exacto por permutaciones sobre las
  distancias mínimas de Dijkstra, saliendo y regresando a Penonomé (nodo 15).
• Costo (referencia) = distancia × COSTO_POR_KM.
• Búsqueda de hoteles / restaurantes / atractivos: datos abiertos de
  OpenStreetMap (Overpass API). No se inventan precios de hoteles.
• Precios de combustible: Secretaría Nacional de Energía (SNE), actualizados
  cada 14 días (ver COMBUSTIBLE y combustible.json).
"""

from flask import Flask, render_template, request, jsonify
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import os
import threading
import requests
import heapq
import math
import time
from itertools import permutations

from datos_sitios import ficha_completa

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# CONFIGURACIÓN
# ============================================================

OSRM_URL = os.environ.get("OSRM_URL", "https://router.project-osrm.org")

# 🔧 PARCHE 1: más mirrors de Overpass (antes eran 2, ahora 4)
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.osm.jp/api/interpreter",
]

COSTO_POR_KM = 0.15              # USD/km (referencia; justificar en la tesis)
TIMEOUT = 30
MAX_RETRIES = 3
VELOCIDAD_FALLBACK_KMH = 40

# Con el grafo oficial de Google Maps el tiempo ya es "real"; por eso el factor
# de holgura por defecto es 1.0 (los resultados coinciden con el script Python).
# Para añadir margen: variable de entorno FACTOR_HOLGURA=1.25
FACTOR_HOLGURA = float(os.environ.get("FACTOR_HOLGURA", "1.0"))

CRITERIO_OFICIAL = "distancia"
FUENTE_OFICIAL = "google"
K_VECINOS = 4
FACTOR_DESVIO = float(os.environ.get("FACTOR_DESVIO", "1.3"))
CONECTAR_HUBS = os.environ.get("CONECTAR_HUBS", "1") != "0"
MOSTRAR_NODOS_DE_PASO = os.environ.get("MOSTRAR_NODOS_DE_PASO", "0") == "1"
BASE = 15  # Penonomé

CLAVE_PESO = {"distancia": "distancia_km"}  # único criterio de optimización

# ============================================================
# PRECIOS DE COMBUSTIBLE (SNE) - ACTUALIZAR CADA 14 DÍAS
# ============================================================
COMBUSTIBLE = {
    "vigente_desde": "2026-10-02T06:00:00-05:00",
    "vigente_hasta": "2026-10-16T05:59:00-05:00",
    "fuente": "Secretaría Nacional de Energía (SNE), precios máximos de venta al público",
    "url_oficial": "https://www.energia.gob.pa",
    "url_referencia": "https://www.telemetro.com/nacionales/revise-la-lista-los-nuevos-precios-del-combustible-que-entran-vigor-este-2-octubre-n6093795",
    "moneda": "B/. (1 balboa = 1 USD)",
    "localidades": {
        "Penonomé, Aguadulce y Divisa": {"gasolina_95": 1.432, "gasolina_91": 1.326, "diesel": 1.519},
        "Panamá y Colón": {"gasolina_95": 1.424, "gasolina_91": 1.318, "diesel": 1.511},
        "Arraiján y La Chorrera": {"gasolina_95": 1.427, "gasolina_91": 1.321, "diesel": 1.514},
        "Santiago y Chitré": {"gasolina_95": 1.437, "gasolina_91": 1.331, "diesel": 1.524},
    },
    "localidad_proyecto": "Penonomé, Aguadulce y Divisa",
}
LITROS_POR_GALON = 3.785


def cargar_combustible():
    ruta = os.path.join(BASE_DIR, "combustible.json")
    if os.path.exists(ruta):
        try:
            with open(ruta, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("localidades") and data.get("localidad_proyecto") in data["localidades"]:
                return data
            print("  ⚠ combustible.json ignorado: estructura incompleta.")
        except Exception as e:
            print(f"  ⚠ combustible.json ignorado: {e}")
    return COMBUSTIBLE


# ============================================================
# DATOS: 29 ATRACTIVOS
# ============================================================
_BASE = [
    (1, "Playa Santa Clara", "PSC", "Playa", 8.37388, -80.10569, "Playa de arena blanca y aguas tranquilas"),
    (2, "Playa Farallón", "PFA", "Playa", 8.36130, -80.12977, "Playa con olas moderadas y arena dorada"),
    (3, "Playa El Salado", "PES", "Playa", 8.20159, -80.48353, "Playa tranquila cerca de Aguadulce"),
    (4, "Playa Blanca", "PBL", "Playa", 8.34595, -80.15175, "Hermosa playa de arena blanca"),
    (5, "Playa Juan Hombrón", "PJH", "Playa", 8.29827, -80.25338, "Playa con aguas cristalinas"),
    (6, "Mercado Artesanía Valle Antón", "MAV", "Cultural", 8.60408, -80.13115, "Mercado de artesanías típicas"),
    (7, "Serpentario Maravillas Tropicales", "SMT", "Naturaleza", 8.60162, -80.11503, "Exhibición de serpientes y reptiles"),
    (8, "Museo Hermanos Arias Madrid", "MHA", "Cultural/Hist.", 8.52497, -80.35677, "Museo histórico en Penonomé"),
    (9, "P.N. Omar Torrijos", "PNT", "Parque Nacional", 8.69558, -80.60450, "Parque Nacional con senderos ecológicos"),
    (10, "Sitio Arqueológico El Caño", "SAC", "Arqueológico", 8.40012, -80.50146, "Importante sitio arqueológico precolombino"),
    (11, "Museo Regional Stella Sierra", "MSS", "Cultural/Hist.", 8.24104, -80.53980, "Museo regional en Aguadulce"),
    (12, "Iglesia San Juan Bautista", "ISJ", "Histórico", 8.52188, -80.35936, "Iglesia histórica en Penonomé"),
    (13, "El Chorro Las Yayas", "CLY", "Cascada", 8.64588, -80.58997, "Hermosa cascada en La Pintada"),
    (14, "Balneario Las Mendozas", "BLM", "Balneario", 8.52654, -80.35536, "Balneario natural cerca de Penonomé"),
    (15, "Penonomé", "PEN", "Hub/Ciudad", 8.55029, -80.35474, "Capital de la provincia de Coclé"),
    (16, "Aguadulce", "AGU", "Hub/Ciudad", 8.23017, -80.55495, "Ciudad conocida por sus salinas"),
    (17, "Antón", "ANT", "Hub/Ciudad", 8.40186, -80.27115, "Ciudad cerca de las playas"),
    (18, "La Pintada", "LAP", "Hub/Ciudad", 8.59331, -80.44655, "Ciudad conocida por sus artesanías"),
    (19, "Natá", "NAT", "Hub/Ciudad", 8.33426, -80.52528, "Ciudad histórica con iglesia colonial"),
    (20, "Parroquia Ntra. Sra. Candelaria", "PNC", "Histórico", 8.59308, -80.44582, "Iglesia histórica en La Pintada"),
    (21, "Cerro Gaital", "CGA", "Montaña", 8.61666, -80.11666, "Cerro con vista panorámica"),
    (22, "Museo de Penonomé", "MPE", "Cultural", 8.51959, -80.36056, "Museo histórico en Penonomé"),
    (23, "Mercado Artesanías La Pintada", "MLA", "Cultural", 8.59702, -80.44881, "Mercado de artesanías en La Pintada"),
    (24, "Balneario Los Algarrobos", "BAL", "Naturaleza", 8.59377, -80.44295, "Balneario natural cerca de La Pintada"),
    (25, "Iglesia Santiago Apóstol", "ISA", "Histórico", 8.33215, -80.51524, "Iglesia colonial en Natá"),
    (26, "Ecoparque Don Arcelio", "ECO", "Naturaleza", 8.38084, -80.52890, "Parque ecológico cerca de Natá"),
    (27, "Salinas de Aguadulce", "SAL", "Naturaleza", 8.20203, -80.49620, "Salinas tradicionales"),
    (28, "Mariposario", "MAR", "Naturaleza", 8.60141, -80.12923, "Jardín de mariposas"),
    (29, "Canopy Adventure", "CAN", "Aventura", 8.62585, -80.13870, "Tirolesa y aventura en la selva"),
]
_OSM_COORD = {
    1: (8.37571, -80.10372), 2: (8.35894, -80.13333), 3: (8.202045, -80.483697),
    4: (8.34490, -80.15400), 5: (8.319702725314118, -80.205259322496),
    6: (8.604108, -80.131198), 7: (8.6011942, -80.1152153), 8: (8.525075, -80.356665),
    9: (8.6554, -80.7008), 10: (8.396716, -80.501499), 11: (8.241049, -80.539833),
    12: (8.521929, -80.359489), 13: (8.645952, -80.590030), 14: (8.526422, -80.355455),
    15: (8.5260, -80.3616), 16: (8.24275, -80.53888), 17: (8.3944820, -80.2663470),
    18: (8.5963, -80.4467), 19: (8.33686, -80.51725), 20: (8.593051, -80.445811),
    21: (8.624607, -80.123500), 22: (8.519549, -80.360597), 23: (8.597083, -80.448927),
    24: (8.59850400964035, -80.44361114252906), 25: (8.332057, -80.515256),
    26: (8.380838, -80.528935), 27: (8.22279, -80.49906),
    28: (8.600997663400143, -80.12844476076745), 29: (8.625407314878048, -80.13892822612566),
}

ATRACTIVOS_GOOGLE = {i: {"nombre": n, "cod": c, "tipo": t, "lat": la, "lng": lo, "descripcion": d}
                     for i, n, c, t, la, lo, d in _BASE}
ATRACTIVOS_OSM = {i: {**v, "lat": _OSM_COORD[i][0], "lng": _OSM_COORD[i][1]}
                  for i, v in ATRACTIVOS_GOOGLE.items()}

# ============================================================
# ARISTAS OFICIALES (Google Maps): (origen, destino, km, minutos)
# ============================================================
ARISTAS_GOOGLE = [
    (15, 17, 22.3, 27), (15, 10, 30.1, 33), (15, 16, 50.2, 49), (15, 18, 18.4, 23),
    (15, 8, 4.1, 7), (15, 12, 4.6, 9), (15, 14, 4.6, 9), (15, 21, 42.9, 78),
    (15, 19, 36.9, 34), (15, 13, 39.7, 62),
    (17, 1, 23.1, 25), (17, 2, 21.4, 25), (17, 4, 19.8, 22), (17, 5, 18.0, 24),
    (17, 6, 37.6, 52), (17, 7, 39.8, 57), (17, 21, 40.5, 59),
    (1, 2, 6.8, 11), (2, 4, 8.4, 12), (4, 5, 22.0, 24), (1, 5, 27.3, 32),
    (6, 7, 2.2, 5), (6, 21, 2.9, 7),
    (19, 10, 13.5, 14), (19, 17, 50.5, 42), (19, 16, 14.2, 15),
    (16, 10, 26.8, 27), (16, 11, 2.8, 6), (16, 3, 10.1, 16),
    (18, 13, 34.2, 54), (18, 20, 0.13, 1), (18, 9, 41.3, 88),
    (9, 13, 7.1, 34), (9, 10, 44.7, 85),
    (15, 22, 4.3, 8), (8, 22, 1.5, 4), (22, 12, 0.8, 3),
    (18, 23, 0.8, 1), (18, 24, 0.35, 2), (23, 24, 1.1, 2), (20, 23, 0.8, 1), (20, 24, 0.3, 1),
    (10, 25, 13.8, 15), (19, 25, 1.4, 4), (25, 26, 6.2, 7), (19, 26, 5.9, 6),
    (10, 26, 7.6, 9), (6, 28, 0.65, 2),
    (16, 27, 8.7, 15), (3, 27, 1.4, 2), (27, 11, 7.0, 10),
    (17, 28, 38.2, 53), (17, 29, 39.1, 54), (28, 7, 2.1, 5), (28, 29, 3.6, 9), (29, 21, 5.8, 12),
    (12, 14, 1.0, 3),
]

FUENTE_COORDENADAS = os.environ.get("FUENTE_COORDENADAS", FUENTE_OFICIAL).lower()
if FUENTE_COORDENADAS not in ("google", "osm"):
    FUENTE_COORDENADAS = FUENTE_OFICIAL


def obtener_atractivos_por_fuente(fuente):
    return ATRACTIVOS_OSM if fuente == "osm" else ATRACTIVOS_GOOGLE


ATRACTIVOS = obtener_atractivos_por_fuente(FUENTE_COORDENADAS)

# ============================================================
# ITINERARIO DE 7 DÍAS
# ============================================================
DIAS = [
    {"dia": 1, "destinos": [1, 2, 4, 5, 17], "zona": "🌊 Playas de Antón"},
    {"dia": 2, "destinos": [8, 22, 12, 14, 15], "zona": "🏛️ Penonomé Histórico"},
    {"dia": 3, "destinos": [18, 20, 23, 24, 13, 9], "zona": "⛰️ La Pintada - Montaña y Cultura"},
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
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def peso_arista_fallback(lat1, lng1, lat2, lng2):
    d = distancia_haversine(lat1, lng1, lat2, lng2)
    return d, (d / VELOCIDAD_FALLBACK_KMH) * 60, d * COSTO_POR_KM


# ============================================================
# OSRM (solo geometría y, en modo "osm", pesos)
# ============================================================

def obtener_matrices_osrm(atractivos):
    ids = sorted(atractivos)
    coord_str = ";".join(f"{atractivos[i]['lng']},{atractivos[i]['lat']}" for i in ids)
    url = f"{OSRM_URL}/table/v1/driving/{coord_str}"
    for intento in range(MAX_RETRIES):
        try:
            r = requests.get(url, params={"annotations": "duration,distance"}, timeout=TIMEOUT)
            data = r.json()
            if r.status_code == 200 and data.get("code") == "Ok" and data.get("durations") and data.get("distances"):
                return ids, data["distances"], data["durations"]
            time.sleep(1)
        except Exception as e:
            print(f"  Intento {intento + 1} OSRM table falló: {e}")
            time.sleep(1)
    return None


def obtener_ruta_multi_punto(puntos, con_geometria=True):
    if len(puntos) < 2:
        return {"exito": False, "error": "Puntos insuficientes"}
    coord_str = ";".join(f"{lng},{lat}" for lat, lng in puntos)
    url = f"{OSRM_URL}/route/v1/driving/{coord_str}"
    params = {"overview": "full" if con_geometria else "false", "geometries": "geojson", "steps": "false"}
    for intento in range(MAX_RETRIES):
        try:
            r = requests.get(url, params=params, timeout=60)
            data = r.json()
            if r.status_code == 200 and data.get("code") == "Ok":
                ruta = data["routes"][0]
                res = {"distancia_km": ruta["distance"] / 1000.0, "tiempo_min": ruta["duration"] / 60.0, "exito": True}
                if con_geometria:
                    res["puntos_ruta"] = [[c[1], c[0]] for c in ruta["geometry"]["coordinates"]]
                return res
            time.sleep(1)
        except Exception as e:
            print(f"  Intento {intento + 1} OSRM multi falló: {e}")
            time.sleep(1)
    return {"exito": False, "error": "OSRM no respondió (multi-punto)"}


# ============================================================
# DIJKSTRA
# ============================================================

def dijkstra(grafo, origen, criterio="distancia", destino=None):
    """Dijkstra con heapq. Devuelve (dist, prev)."""
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
        for v, ar in ady[u].items():
            nd = d + ar[clave]
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(cola, (nd, v))
    return dist, prev


def reconstruir_camino(prev, origen, destino):
    camino = [destino]
    while camino[-1] != origen:
        if camino[-1] not in prev:
            return None
        camino.append(prev[camino[-1]])
    camino.reverse()
    return camino


# ============================================================
# GRAFO
# ============================================================

def construir_grafo_google(atractivos):
    """Grafo OFICIAL: 57 aristas medidas en Google Maps."""
    ids = sorted(atractivos)
    ady = {n: {} for n in ids}
    pares = set()
    for u, v, km, mn in ARISTAS_GOOGLE:
        w = {"distancia_km": float(km), "tiempo_min": float(mn), "costo": km * COSTO_POR_KM}
        ady[u][v] = dict(w)
        ady[v][u] = dict(w)
        pares.add((min(u, v), max(u, v)))
    return {"ids": ids, "atractivos": atractivos, "ady": ady, "num_aristas": len(pares),
            "aristas_kmst": len(pares), "aristas_hubs": 0, "aristas_base": len(pares),
            "aristas_reparadas": 0, "reparadas": [], "fuente_pesos": "google",
            "modo_grafo": "Aristas medidas en Google Maps (oficial)"}


def construir_grafo_osrm(atractivos):
    """Grafo de SENSIBILIDAD: KNN + MST + hubs + reparación con pesos OSRM."""
    ids = sorted(atractivos)

    def hav(a, b):
        return distancia_haversine(atractivos[a]["lat"], atractivos[a]["lng"],
                                   atractivos[b]["lat"], atractivos[b]["lng"])

    pares = set()
    for a in ids:
        for b in sorted((x for x in ids if x != a), key=lambda x: hav(a, x))[:K_VECINOS]:
            pares.add((min(a, b), max(a, b)))
    en_arbol = {ids[0]}
    while len(en_arbol) < len(ids):
        mejor = None
        for a in en_arbol:
            for b in ids:
                if b not in en_arbol:
                    d = hav(a, b)
                    if mejor is None or d < mejor[0]:
                        mejor = (d, a, b)
        en_arbol.add(mejor[2])
        pares.add((min(mejor[1], mejor[2]), max(mejor[1], mejor[2])))
    aristas_kmst = len(pares)
    if CONECTAR_HUBS:
        hubs = [n for n in ids if atractivos[n].get("tipo") == "Hub/Ciudad"]
        for i, a in enumerate(hubs):
            for b in hubs[i + 1:]:
                pares.add((min(a, b), max(a, b)))
    aristas_base = len(pares)

    osrm = obtener_matrices_osrm(atractivos)
    indice = {n: i for i, n in enumerate(ids)}
    usados_fallback = 0

    def pesos(a, b, contar=True):
        nonlocal usados_fallback
        if osrm is not None:
            _, mat_d, mat_t = osrm
            d, t = mat_d[indice[a]][indice[b]], mat_t[indice[a]][indice[b]]
            if d is not None and t is not None:
                km = d / 1000.0
                return {"distancia_km": km, "tiempo_min": t / 60.0, "costo": km * COSTO_POR_KM}
        if contar:
            usados_fallback += 1
        km, tmin, costo = peso_arista_fallback(atractivos[a]["lat"], atractivos[a]["lng"],
                                               atractivos[b]["lat"], atractivos[b]["lng"])
        return {"distancia_km": km, "tiempo_min": tmin, "costo": costo}

    ady = {n: {} for n in ids}
    for a, b in pares:
        ady[a][b] = pesos(a, b)
        ady[b][a] = pesos(b, a)
    tmp = {"ady": ady}
    candidatos = sorted((pesos(a, b, False)["distancia_km"], a, b)
                        for a in ids for b in ids if a < b and (a, b) not in pares)
    reparadas = []
    for _, a, b in candidatos:
        dab, dba = pesos(a, b, False)["distancia_km"], pesos(b, a, False)["distancia_km"]
        cab = dijkstra(tmp, a, "distancia", b)[0][b]
        cba = dijkstra(tmp, b, "distancia", a)[0][a]
        if cab > FACTOR_DESVIO * dab or cba > FACTOR_DESVIO * dba:
            pares.add((a, b))
            ady[a][b], ady[b][a] = pesos(a, b), pesos(b, a)
            reparadas.append((a, b))
    fuente_pesos = "haversine" if osrm is None else ("mixto" if usados_fallback else "osrm")
    return {"ids": ids, "atractivos": atractivos, "ady": ady, "num_aristas": len(pares),
            "aristas_kmst": aristas_kmst, "aristas_hubs": aristas_base - aristas_kmst,
            "aristas_base": aristas_base, "aristas_reparadas": len(reparadas),
            "reparadas": reparadas, "fuente_pesos": fuente_pesos,
            "modo_grafo": "Generado (KNN+MST+hubs) con pesos OSRM (sensibilidad)"}


_GRAFOS = {}
_GRAFOS_LOCK = threading.Lock()


def obtener_grafo():
    fuente = FUENTE_COORDENADAS
    with _GRAFOS_LOCK:
        if fuente in _GRAFOS:
            return _GRAFOS[fuente]
    atr = obtener_atractivos_por_fuente(fuente)
    grafo = construir_grafo_google(atr) if fuente == "google" else construir_grafo_osrm(atr)
    if grafo["fuente_pesos"] in ("google", "osrm"):
        with _GRAFOS_LOCK:
            _GRAFOS[fuente] = grafo
    return grafo


def metricas_camino(grafo, camino):
    dist = tiempo = costo = 0.0
    segmentos = []
    for a, b in zip(camino, camino[1:]):
        ar = grafo["ady"][a][b]
        dist += ar["distancia_km"]
        tiempo += ar["tiempo_min"]
        costo += ar["costo"]
        segmentos.append({"origen": a, "destino": b, "distancia_km": round(ar["distancia_km"], 2),
                          "tiempo_min": round(ar["tiempo_min"], 2), "costo": round(ar["costo"], 2)})
    return dist, tiempo, costo, segmentos


def orden_optimo_visita(grafo, destinos, criterio="distancia"):
    """TSP exacto (permutaciones) sobre distancias mínimas de Dijkstra; base = Penonomé."""
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
    mejor_costo, mejor_orden = math.inf, None
    for perm in permutations(paradas):
        sec = [BASE] + list(perm) + [BASE]
        total = sum(D[(sec[i], sec[i + 1])] for i in range(len(sec) - 1))
        if total < mejor_costo:
            mejor_costo, mejor_orden = total, list(perm)
    return mejor_orden, mejor_costo


def construir_nodos_ruta(atractivos, camino, paradas):
    return [{"id": n, **atractivos[n], "lat_carretera": atractivos[n]["lat"],
             "lng_carretera": atractivos[n]["lng"], "es_parada": n in paradas} for n in camino]


def geometria_camino(atractivos, camino):
    puntos = [(atractivos[n]["lat"], atractivos[n]["lng"]) for n in camino]
    if len(puntos) >= 2:
        r = obtener_ruta_multi_punto(puntos, con_geometria=True)
        if r.get("exito") and len(r.get("puntos_ruta", [])) >= 2:
            return r["puntos_ruta"]
    return [[lat, lng] for lat, lng in puntos]


# ============================================================
# AUTODIAGNÓSTICO DE DATOS
# ============================================================

def diagnostico_datos():
    errores, avisos = [], []
    ids = set(ATRACTIVOS_GOOGLE)
    vistas = set()
    for u, v, km, mn in ARISTAS_GOOGLE:
        if u not in ids or v not in ids:
            errores.append(f"Arista ({u},{v}) con ID inexistente")
            continue
        if u == v:
            errores.append(f"Autolazo en {u}")
        k = frozenset((u, v))
        if k in vistas:
            errores.append(f"Arista duplicada {u}-{v}")
        vistas.add(k)
        if km <= 0 or mn <= 0:
            errores.append(f"Peso no positivo en {u}-{v}")
        a, b = ATRACTIVOS_GOOGLE[u], ATRACTIVOS_GOOGLE[v]
        h = distancia_haversine(a["lat"], a["lng"], b["lat"], b["lng"])
        if h > km + 0.05:
            avisos.append(f"{a['cod']}-{b['cod']}: carretera {km} km < línea recta {h:.2f} km (revisar medición)")
    ady = {i: set() for i in ids}
    for u, v, _, _ in ARISTAS_GOOGLE:
        ady[u].add(v)
        ady[v].add(u)
    visit, pila = set(), [BASE]
    while pila:
        x = pila.pop()
        if x not in visit:
            visit.add(x)
            pila.extend(ady[x] - visit)
    if visit != ids:
        errores.append(f"Grafo NO conexo: {sorted(ids - visit)}")
    for d in DIAS:
        if any(x not in ids for x in d["destinos"]):
            errores.append(f"Día {d['dia']} con IDs inválidos")
        if not 4 <= len(d["destinos"]) <= 6:
            errores.append(f"Día {d['dia']} no tiene 4-6 lugares")
    return {"nodos": len(ids), "aristas": len(vistas), "conexo": visit == ids,
            "errores": errores, "avisos": avisos}


# ============================================================
# BÚSQUEDA (OpenStreetMap / Overpass)
# ============================================================
_CACHE_BUSQ = {}
# 🔧 PARCHE 4: caché más larga (antes 600 = 10 min, ahora 3600 = 1 hora)
_CACHE_TTL = 3600
BBOX_COCLE = (8.15, -80.75, 8.75, -80.05)  # sur, oeste, norte, este

CATEGORIAS = {
    "hotel": '["tourism"~"^(hotel|hostel|guest_house|motel|apartment|resort|chalet)$"]',
    "restaurante": '["amenity"~"^(restaurant|cafe|fast_food|bar)$"]',
    "atraccion": '["tourism"~"^(attraction|museum|viewpoint|gallery|zoo|theme_park|artwork)$"]',
}
ETIQUETAS_TIPO = {
    "hotel": "Hotel", "hostel": "Hostal", "guest_house": "Casa de huéspedes", "motel": "Motel",
    "apartment": "Apartamento", "resort": "Resort", "chalet": "Cabaña",
    "restaurant": "Restaurante", "cafe": "Café", "fast_food": "Comida rápida", "bar": "Bar",
    "attraction": "Atracción", "museum": "Museo", "viewpoint": "Mirador", "gallery": "Galería",
    "zoo": "Zoológico", "theme_park": "Parque temático", "artwork": "Arte público",
}


def _consulta_overpass(categoria, lat=None, lng=None, radio_m=None):
    filtro = CATEGORIAS[categoria]
    if lat is not None:
        area = f"(around:{int(radio_m)},{lat},{lng})"
    else:
        s, o, n, e = BBOX_COCLE
        area = f"({s},{o},{n},{e})"
    q = f"[out:json][timeout:25];(nwr{filtro}{area};);out center tags 120;"
    ultimo = None
    for url in OVERPASS_URLS:
        try:
            r = requests.post(url, data={"data": q}, timeout=35,
                              headers={"User-Agent": "RutasCocleTesis/1.0"})
            if r.status_code == 200:
                # 🔧 PARCHE 3: verificar que sea JSON real (Overpass a veces
                # devuelve 200 con HTML de mantenimiento o de error)
                try:
                    return r.json().get("elements", [])
                except ValueError:
                    ultimo = f"{url}: respuesta no-JSON (posible mantenimiento)"
                    print(f"  ⚠ {ultimo}")
                    continue
            ultimo = f"{url}: HTTP {r.status_code}"
            print(f"  ⚠ {ultimo}")
        except Exception as e:
            ultimo = f"{url}: {e}"
            print(f"  ⚠ {ultimo}")
    raise RuntimeError(f"Overpass no respondió en ningún mirror ({ultimo})")


def _normalizar(el, categoria, lat0, lng0):
    t = el.get("tags", {})
    nombre = t.get("name") or t.get("name:es")
    if not nombre:
        return None
    lat = el.get("lat") or el.get("center", {}).get("lat")
    lng = el.get("lon") or el.get("center", {}).get("lon")
    if lat is None or lng is None:
        return None
    sub = t.get("tourism") if categoria != "restaurante" else t.get("amenity")
    direccion = ", ".join(x for x in [t.get("addr:street"), t.get("addr:city") or t.get("addr:suburb")] if x)
    web = t.get("website") or t.get("contact:website")
    return {
        "nombre": nombre, "categoria": categoria, "subtipo": ETIQUETAS_TIPO.get(sub, sub or categoria),
        "lat": lat, "lng": lng, "direccion": direccion,
        "telefono": t.get("phone") or t.get("contact:phone") or "",
        "web": web if web and web.startswith(("http://", "https://")) else "",
        "horario": t.get("opening_hours", ""), "cocina": t.get("cuisine", ""),
        "estrellas": t.get("stars", ""),
        "distancia_km": round(distancia_haversine(lat0, lng0, lat, lng), 2) if lat0 is not None else None,
        "google_maps": f"https://www.google.com/maps/search/?api=1&query={lat},{lng}",
    }


# ============================================================
# 🔧 PARCHE 2: MANEJADORES GLOBALES DE ERROR
# ============================================================
# Esto garantiza que CUALQUIER error no controlado en el servidor devuelva
# JSON (no HTML). Así el frontend nunca dirá "contenido no-JSON".
@app.errorhandler(404)
def error_404(e):
    return jsonify({"exito": False, "error": "Recurso no encontrado"}), 404

@app.errorhandler(405)
def error_405(e):
    return jsonify({"exito": False, "error": "Método no permitido"}), 405

@app.errorhandler(500)
def error_500(e):
    return jsonify({"exito": False, "error": "Error interno del servidor"}), 500

@app.errorhandler(Exception)
def error_general(e):
    print("❌ ERROR NO CONTROLADO:", repr(e))
    return jsonify({"exito": False, "error": f"Error del servidor: {e}"}), 500


# ============================================================
# RUTAS HTTP
# ============================================================

@app.route("/")
def index():
    return render_template("index.html", atractivos=ATRACTIVOS, fuente_actual=FUENTE_COORDENADAS,
                           fuente_oficial=FUENTE_OFICIAL, factor_holgura=FACTOR_HOLGURA,
                           criterio_oficial=CRITERIO_OFICIAL, costo_por_km=COSTO_POR_KM)


@app.route("/api/ruta", methods=["POST"])
def api_ruta():
    try:
        data = request.get_json(silent=True) or {}
        try:
            origen, destino = int(data["origen"]), int(data["destino"])
        except (KeyError, TypeError, ValueError):
            return jsonify({"exito": False, "error": "Debes enviar 'origen' y 'destino' (números)."}), 400
        criterio = CRITERIO_OFICIAL
        grafo = obtener_grafo()
        atractivos = grafo["atractivos"]
        if origen not in atractivos or destino not in atractivos:
            return jsonify({"exito": False, "error": "Origen o destino no existe."}), 400
        if origen == destino:
            return jsonify({"exito": False, "error": "Origen y destino no pueden ser iguales."}), 400
        _, prev = dijkstra(grafo, origen, criterio, destino)
        camino = reconstruir_camino(prev, origen, destino)
        if camino is None:
            return jsonify({"exito": False, "error": "No existe camino entre los nodos."}), 404
        dist_total, t_cond, costo_total, segmentos = metricas_camino(grafo, camino)
        t_total = t_cond * FACTOR_HOLGURA
        puntos_ruta = geometria_camino(atractivos, camino)
        if MOSTRAR_NODOS_DE_PASO:
            camino_mostrado = camino
        else:
            camino_mostrado = [origen, destino]
        nodos_ruta = construir_nodos_ruta(atractivos, camino_mostrado, {origen, destino})
        if not MOSTRAR_NODOS_DE_PASO:
            segmentos = [{"origen": origen, "destino": destino, "distancia_km": round(dist_total, 2),
                          "tiempo_min": round(t_cond, 2), "costo": round(costo_total, 2)}]
        return jsonify({
            "exito": True, "origen": origen, "destino": destino, "criterio": criterio,
            "camino": camino_mostrado, "camino_completo": camino, "pasa_por": camino[1:-1],
            "nodos_ruta": nodos_ruta, "distancia_km": round(dist_total, 2),
            "tiempo_conduccion_min": round(t_cond, 2), "tiempo_min": round(t_total, 2),
            "factor_holgura": FACTOR_HOLGURA, "costo": round(costo_total, 2),
            "fuente_metricas": grafo["fuente_pesos"], "puntos_ruta": puntos_ruta,
            "segmentos": segmentos, "nodos_visitados": len(camino_mostrado), "metodo": "dijkstra_grafo",
        })
    except Exception as e:
        print("ERROR API RUTA:", e)
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/dia/<int:dia_num>")
def api_dia(dia_num):
    try:
        dia = next((d for d in DIAS if d["dia"] == dia_num), None)
        if dia is None:
            return jsonify({"exito": False, "error": "Día inválido (1-7)."}), 400
        criterio = CRITERIO_OFICIAL
        grafo = obtener_grafo()
        atractivos = grafo["atractivos"]
        orden, _ = orden_optimo_visita(grafo, dia["destinos"], criterio)
        if orden is None:
            return jsonify({"exito": False, "error": "No se pudo calcular el orden óptimo."}), 500
        secuencia = [BASE] + orden + [BASE]
        camino, etapas = [BASE], []
        for a, b in zip(secuencia, secuencia[1:]):
            _, prev = dijkstra(grafo, a, criterio, b)
            tramo = reconstruir_camino(prev, a, b)
            if tramo is None:
                return jsonify({"exito": False, "error": "No existe camino entre paradas."}), 500
            camino.extend(tramo[1:])
            d_et, t_et, c_et, _ = metricas_camino(grafo, tramo)
            etapas.append({"origen": a, "destino": b, "distancia_km": round(d_et, 2),
                           "tiempo_min": round(t_et, 2), "costo": round(c_et, 2), "pasa_por": tramo[1:-1]})
        dist_total, t_cond, costo_total, _ = metricas_camino(grafo, camino)
        puntos_ruta = geometria_camino(atractivos, camino)
        nodos_ruta = construir_nodos_ruta(atractivos, secuencia, set(secuencia))
        return jsonify({
            "exito": True, "dia": dia_num, "zona": dia["zona"], "criterio": criterio,
            "orden_optimo": secuencia, "camino": secuencia, "camino_completo": camino,
            "nodos_ruta": nodos_ruta, "puntos_ruta": puntos_ruta, "segmentos": etapas,
            "distancia_km": round(dist_total, 2), "tiempo_conduccion_min": round(t_cond, 2),
            "tiempo_min": round(t_cond * FACTOR_HOLGURA, 2), "factor_holgura": FACTOR_HOLGURA,
            "costo": round(costo_total, 2), "fuente_metricas": grafo["fuente_pesos"],
            "nodos_visitados": len(set(secuencia)), "metodo": "dijkstra_grafo",
        })
    except Exception as e:
        print("ERROR API DIA:", e)
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/geometria", methods=["POST"])
def api_geometria():
    try:
        camino = (request.get_json(silent=True) or {}).get("camino")
        atr = ATRACTIVOS
        if (not isinstance(camino, list) or len(camino) < 2
                or any(not isinstance(n, int) or n not in atr for n in camino)):
            return jsonify({"exito": False, "error": "Camino inválido."}), 400
        return jsonify({"exito": True, "puntos_ruta": geometria_camino(atr, camino)})
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/grafo")
def api_grafo():
    try:
        grafo = obtener_grafo()
        atr = grafo["atractivos"]
        return jsonify({
            "exito": True, "fuente": FUENTE_COORDENADAS, "fuente_pesos": grafo["fuente_pesos"],
            "modo_grafo": grafo["modo_grafo"], "nodos": len(grafo["ids"]),
            "num_aristas": grafo["num_aristas"], "k_vecinos": K_VECINOS, "factor_desvio": FACTOR_DESVIO,
            "conectar_hubs": CONECTAR_HUBS, "aristas_kmst": grafo["aristas_kmst"],
            "aristas_hubs": grafo["aristas_hubs"], "aristas_reparadas": grafo["aristas_reparadas"],
            "lista_reparadas": [{"a": a, "b": b, "nombre_a": atr[a]["nombre"], "nombre_b": atr[b]["nombre"],
                                 "distancia_km": round(grafo["ady"][a][b]["distancia_km"], 2)}
                                for a, b in grafo["reparadas"]],
        })
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/salud")
def api_salud():
    """Autodiagnóstico de datos."""
    return jsonify({"exito": True, **diagnostico_datos(), "fuente_activa": FUENTE_COORDENADAS})


@app.route("/api/coordenadas")
def api_coordenadas():
    return jsonify({n: {"nombre": d["nombre"], "cod": d["cod"], "tipo": d["tipo"], "lat": d["lat"],
                        "lng": d["lng"], "lat_carretera": d["lat"], "lng_carretera": d["lng"]}
                    for n, d in ATRACTIVOS.items()})


@app.route("/api/dias")
def api_dias():
    return jsonify(DIAS)


@app.route("/api/sitios")
def api_sitios():
    """Fichas detalladas de los 29 sitios."""
    return jsonify({str(n): ficha_completa(n, d) for n, d in ATRACTIVOS.items()})


@app.route("/api/sitio/<int:nid>")
def api_sitio(nid):
    if nid not in ATRACTIVOS:
        return jsonify({"exito": False, "error": "Sitio no existe."}), 404
    dias = [d["dia"] for d in DIAS if nid in d["destinos"]]
    return jsonify({"exito": True, **ficha_completa(nid, ATRACTIVOS[nid]), "dias": dias})


@app.route("/api/combustible")
def api_combustible():
    c = cargar_combustible()
    ahora = datetime.now(ZoneInfo("America/Panama"))
    try:
        hasta = datetime.fromisoformat(c["vigente_hasta"])
        vigente = ahora <= hasta
    except Exception:
        vigente = None
    locs = {}
    for nombre, p in c["localidades"].items():
        locs[nombre] = {k: {"litro": v, "galon": round(v * LITROS_POR_GALON, 2)} for k, v in p.items()}
    p95 = c["localidades"][c["localidad_proyecto"]]["gasolina_95"]
    return jsonify({
        "exito": True, "vigente": vigente, "vigente_desde": c["vigente_desde"],
        "vigente_hasta": c["vigente_hasta"], "fuente": c["fuente"], "url_oficial": c["url_oficial"],
        "url_referencia": c.get("url_referencia", ""), "moneda": c["moneda"],
        "localidad_proyecto": c["localidad_proyecto"], "localidades": locs,
        "costo_por_km_modelo": COSTO_POR_KM,
        "rendimiento_equivalente_km_l": round(p95 / COSTO_POR_KM, 1),
        "rendimiento_equivalente_km_gal": round(p95 / COSTO_POR_KM * LITROS_POR_GALON, 1),
        "litros_por_galon": LITROS_POR_GALON,
        "nota": "Precios máximos oficiales; la estación puede cobrar menos. Se actualizan cada 14 días.",
    })


@app.route("/api/buscar")
def api_buscar():
    """
    Parámetros: tipo=hotel|restaurante|atraccion|todos, q=texto, cerca=<id nodo>, radio=<km>
    Fuente: OpenStreetMap (Overpass). No incluye precios.
    """
    try:
        tipo = request.args.get("tipo", "todos")
        q = (request.args.get("q") or "").strip().lower()[:60]
        cerca = request.args.get("cerca", type=int)
        radio = min(max(request.args.get("radio", default=5, type=float), 1), 40)
        if tipo not in ("todos", *CATEGORIAS):
            return jsonify({"exito": False, "error": "Tipo inválido."}), 400
        lat0 = lng0 = None
        if cerca:
            if cerca not in ATRACTIVOS:
                return jsonify({"exito": False, "error": "Sitio de referencia inválido."}), 400
            lat0, lng0 = ATRACTIVOS[cerca]["lat"], ATRACTIVOS[cerca]["lng"]
        cats = list(CATEGORIAS) if tipo == "todos" else [tipo]
        resultados, errores = [], []
        for cat in cats:
            clave = (cat, cerca, radio if cerca else None)
            hit = _CACHE_BUSQ.get(clave)
            if hit and time.time() - hit[0] < _CACHE_TTL:
                elems = hit[1]
            else:
                try:
                    elems = _consulta_overpass(cat, lat0, lng0, radio * 1000 if cerca else None)
                    _CACHE_BUSQ[clave] = (time.time(), elems)
                except Exception as e:
                    errores.append(f"{cat}: {e}")
                    continue
            for el in elems:
                r = _normalizar(el, cat, lat0, lng0)
                if r and (not q or q in r["nombre"].lower() or q in (r["cocina"] or "").lower()
                          or q in r["subtipo"].lower()):
                    resultados.append(r)
        if not resultados and errores and len(errores) == len(cats):
            return jsonify({"exito": False, "error": "No se pudo consultar OpenStreetMap ahora. "
                            "Intenta de nuevo en unos segundos.", "detalle": errores}), 502
        resultados.sort(key=lambda r: (r["distancia_km"] if r["distancia_km"] is not None else 0, r["nombre"]))
        return jsonify({"exito": True, "total": len(resultados), "resultados": resultados[:60],
                        "fuente": "OpenStreetMap (Overpass API)", "avisos": errores,
                        "nota": "Los precios no están disponibles en OpenStreetMap; confirme tarifas "
                                "directamente con cada establecimiento."})
    except Exception as e:
        print("ERROR API BUSCAR:", e)
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/api/fuente", methods=["GET"])
def api_fuente_get():
    return jsonify({
        "fuente": FUENTE_COORDENADAS, "fuente_oficial": FUENTE_OFICIAL,
        "fuente_nombre": "OpenStreetMap" if FUENTE_COORDENADAS == "osm" else "Google Maps",
        "es_oficial": FUENTE_COORDENADAS == FUENTE_OFICIAL, "total_atractivos": len(ATRACTIVOS),
        "factor_holgura": FACTOR_HOLGURA, "criterio_oficial": CRITERIO_OFICIAL,
        "costo_por_km": COSTO_POR_KM, "k_vecinos": K_VECINOS, "factor_desvio": FACTOR_DESVIO,
        "metodo": "dijkstra_grafo",
    })


@app.route("/api/fuente", methods=["POST"])
def api_fuente_post():
    global FUENTE_COORDENADAS, ATRACTIVOS
    try:
        nueva = str((request.get_json(silent=True) or {}).get("fuente", "")).lower().strip()
        if nueva not in ("google", "osm"):
            return jsonify({"exito": False, "error": "Fuente inválida."}), 400
        FUENTE_COORDENADAS = nueva
        ATRACTIVOS = obtener_atractivos_por_fuente(nueva)
        return jsonify({"exito": True, "fuente": nueva,
                        "fuente_nombre": "OpenStreetMap" if nueva == "osm" else "Google Maps",
                        "es_oficial": nueva == FUENTE_OFICIAL, "total_atractivos": len(ATTRACTIVOS)})
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500


if __name__ == "__main__":
    diag = diagnostico_datos()
    print("==========================================")
    print(" RUTAS TURÍSTICAS DE COCLÉ - Grafo + Dijkstra")
    print("==========================================")
    print(f"Nodos: {diag['nodos']} | Aristas oficiales: {diag['aristas']} | Conexo: {diag['conexo']}")
    print(f"Fuente activa: {FUENTE_COORDENADAS.upper()} (oficial: {FUENTE_OFICIAL.upper()})")
    print(f"Criterio oficial: {CRITERIO_OFICIAL.upper()} | Costo ref.: {COSTO_POR_KM} USD/km | Holgura: x{FACTOR_HOLGURA}")
    for e in diag["errores"]:
        print("  ❌", e)
    for a in diag["avisos"]:
        print("  ⚠", a)
    print("==========================================\n")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("FLASK_DEBUG", "0") == "1")
