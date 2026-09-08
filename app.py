from flask import Flask, request, jsonify
import os
import requests
import heapq
import math

app = Flask(__name__)

OSRM_URL = os.environ.get(
    "OSRM_URL",
    "https://router.project-osrm.org"
)

COSTO_POR_KM = 0.15
OSRM_TIMEOUT = 60

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
    29: {"nombre": "Canopy Adventure", "cod": "CAN", "tipo": "Aventura", "lat": 8.62598002, "lng": -80.1388213},
}

GRAFO = {}
PUNTOS_AJUSTADOS = {}
CACHE_RUTAS = {}


def obtener_punto_carretera(lat, lng):
    url = f"{OSRM_URL}/nearest/v1/driving/{lng},{lat}"
    try:
        r = requests.get(url, params={"number": 1}, timeout=30)
        data = r.json()

        if r.status_code == 200 and data.get("code") == "Ok" and data.get("waypoints"):
            location = data["waypoints"][0]["location"]
            return {
                "lat": location[1],
                "lng": location[0],
                "exito": True
            }

        return {"exito": False, "error": data.get("message", "No se encontró carretera.")}

    except Exception as e:
        return {"exito": False, "error": str(e)}


def ajustar_puntos_a_carreteras():
    puntos = {}

    for nodo, atractivo in ATRACTIVOS.items():
        resultado = obtener_punto_carretera(
            atractivo["lat"],
            atractivo["lng"]
        )

        if resultado["exito"]:
            lat_carretera = resultado["lat"]
            lng_carretera = resultado["lng"]
        else:
            lat_carretera = atractivo["lat"]
            lng_carretera = atractivo["lng"]

        puntos[nodo] = {
            **atractivo,
            "lat_original": atractivo["lat"],
            "lng_original": atractivo["lng"],
            "lat": lat_carretera,
            "lng": lng_carretera,
        }

    return puntos


def construir_matriz_osrm(puntos):
    ids = list(puntos.keys())

    coordenadas = ";".join(
        f"{puntos[n]['lng']},{puntos[n]['lat']}"
        for n in ids
    )

    url = f"{OSRM_URL}/table/v1/driving/{coordenadas}"

    try:
        r = requests.get(
            url,
            params={"annotations": "duration,distance"},
            timeout=OSRM_TIMEOUT
        )
        data = r.json()

        if r.status_code != 200 or data.get("code") != "Ok":
            print("Error OSRM TABLE:", data.get("message"))
            return None, None, None

        return ids, data.get("distances"), data.get("durations")

    except Exception as e:
        print("Error matriz OSRM:", e)
        return None, None, None


def construir_grafo(puntos):
    ids, matriz_distancia, matriz_tiempo = construir_matriz_osrm(puntos)

    if ids is None:
        return {}

    grafo = {nodo: {} for nodo in ids}

    for i, origen in enumerate(ids):
        for j, destino in enumerate(ids):

            if i == j:
                continue

            distancia_m = matriz_distancia[i][j]
            tiempo_s = matriz_tiempo[i][j]

            # OSRM no encontró conexión en este sentido.
            # NO se crea una arista.
            if distancia_m is None or tiempo_s is None:
                continue

            if distancia_m <= 0 or tiempo_s <= 0:
                continue

            distancia_km = distancia_m / 1000
            tiempo_min = tiempo_s / 60
            costo = distancia_km * COSTO_POR_KM

            # GRAFO DIRIGIDO:
            # origen -> destino
            # No se agrega automáticamente destino -> origen.
            grafo[origen][destino] = {
                "distancia_km": round(distancia_km, 3),
                "tiempo_min": round(tiempo_min, 3),
                "costo": round(costo, 3),
                "origen": origen,
                "destino": destino,
                "dirigida": True
            }

    return grafo


def preparar_grafo():
    global GRAFO, PUNTOS_AJUSTADOS

    print("Preparando puntos de carretera...")
    PUNTOS_AJUSTADOS = ajustar_puntos_a_carreteras()

    print("Construyendo grafo dirigido con OSRM...")
    GRAFO = construir_grafo(PUNTOS_AJUSTADOS)

    aristas = sum(len(v) for v in GRAFO.values())

    print(f"Nodos: {len(GRAFO)}")
    print(f"Aristas dirigidas: {aristas}")
    print("Grafo listo.")


def dijkstra(grafo, origen, destino, criterio):
    campos = {
        "distancia": "distancia_km",
        "tiempo": "tiempo_min",
        "costo": "costo"
    }

    if criterio not in campos:
        criterio = "distancia"

    campo = campos[criterio]

    distancias = {
        nodo: float("inf")
        for nodo in grafo
    }

    anteriores = {
        nodo: None
        for nodo in grafo
    }

    distancias[origen] = 0

    cola = [(0, origen)]

    while cola:
        distancia_actual, nodo_actual = heapq.heappop(cola)

        if distancia_actual > distancias[nodo_actual]:
            continue

        if nodo_actual == destino:
            break

        # SOLO se recorren las aristas que existen:
        # nodo_actual -> vecino
        for vecino, datos in grafo.get(nodo_actual, {}).items():

            peso = datos[campo]
            nueva_distancia = distancia_actual + peso

            if nueva_distancia < distancias[vecino]:
                distancias[vecino] = nueva_distancia
                anteriores[vecino] = nodo_actual

                heapq.heappush(
                    cola,
                    (nueva_distancia, vecino)
                )

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
        "peso_total": round(distancias[destino], 3),
        "criterio": criterio
    }


def obtener_geometria_camino(camino):
    if not camino or len(camino) < 2:
        return []

    coordenadas = ";".join(
        f"{PUNTOS_AJUSTADOS[n]['lng']},{PUNTOS_AJUSTADOS[n]['lat']}"
        for n in camino
    )

    url = f"{OSRM_URL}/route/v1/driving/{coordenadas}"

    try:
        r = requests.get(
            url,
            params={
                "overview": "full",
                "geometries": "geojson",
                "steps": "true"
            },
            timeout=OSRM_TIMEOUT
        )

        data = r.json()

        if r.status_code != 200 or data.get("code") != "Ok":
            return []

        coordenadas_ruta = data["routes"][0]["geometry"]["coordinates"]

        return [
            [coord[1], coord[0]]
            for coord in coordenadas_ruta
        ]

    except Exception as e:
        print("Error geometría:", e)
        return []


@app.route("/api/ruta", methods=["POST"])
def api_ruta():
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "exito": False,
                "error": "No se recibieron datos."
            }), 400

        origen = int(data["origen"])
        destino = int(data["destino"])
        criterio = data.get("criterio", "distancia")

        if origen not in ATRACTIVOS or destino not in ATRACTIVOS:
            return jsonify({
                "exito": False,
                "error": "Origen o destino no válido."
            }), 400

        if origen == destino:
            return jsonify({
                "exito": False,
                "error": "Origen y destino no pueden ser iguales."
            }), 400

        if not GRAFO:
            preparar_grafo()

        resultado = dijkstra(
            GRAFO,
            origen,
            destino,
            criterio
        )

        if resultado is None:
            return jsonify({
                "exito": False,
                "error": "No existe un camino válido entre los puntos."
            }), 404

        camino = resultado["camino"]

        puntos_ruta = obtener_geometria_camino(camino)

        distancia_total = 0
        tiempo_total = 0
        costo_total = 0

        segmentos = []

        for i in range(len(camino) - 1):
            a = camino[i]
            b = camino[i + 1]

            # Verificación de seguridad:
            # la arista debe existir exactamente como a -> b.
            if b not in GRAFO.get(a, {}):
                return jsonify({
                    "exito": False,
                    "error": f"No existe la conexión dirigida {a} -> {b}."
                }), 500

            datos_segmento = GRAFO[a][b]

            distancia_total += datos_segmento["distancia_km"]
            tiempo_total += datos_segmento["tiempo_min"]
            costo_total += datos_segmento["costo"]

            segmentos.append(datos_segmento)

        nodos_ruta = []

        for nodo in camino:
            punto = PUNTOS_AJUSTADOS[nodo]

            nodos_ruta.append({
                "id": nodo,
                "nombre": punto["nombre"],
                "cod": punto["cod"],
                "tipo": punto["tipo"],

                "lat": punto["lat_original"],
                "lng": punto["lng_original"],

                "lat_original": punto["lat_original"],
                "lng_original": punto["lng_original"],

                "lat_carretera": punto["lat"],
                "lng_carretera": punto["lng"],

                "lat_ruta": punto["lat"],
                "lng_ruta": punto["lng"]
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

            "nodos_visitados": len(camino),

            "grafo_dirigido": True,
            "motor_ruteo": "OSRM / OpenStreetMap",
            "algoritmo": "Dijkstra"
        })

    except Exception as e:
        print("ERROR API RUTA:", e)

        return jsonify({
            "exito": False,
            "error": str(e)
        }), 500


@app.route("/api/coordenadas")
def api_coordenadas():
    if not PUNTOS_AJUSTADOS:
        preparar_grafo()

    resultado = {}

    for nodo, datos in PUNTOS_AJUSTADOS.items():
        resultado[nodo] = {
            "nombre": datos["nombre"],
            "cod": datos["cod"],
            "tipo": datos["tipo"],

            "lat": datos["lat_original"],
            "lng": datos["lng_original"],

            "lat_original": datos["lat_original"],
            "lng_original": datos["lng_original"],

            "lat_carretera": datos["lat"],
            "lng_carretera": datos["lng"]
        }

    return jsonify(resultado)


@app.route("/api/grafo")
def api_grafo():
    if not GRAFO:
        preparar_grafo()

    return jsonify(GRAFO)


@app.route("/api/verificacion")
def api_verificacion():
    if not PUNTOS_AJUSTADOS:
        preparar_grafo()

    resultado = {}

    for nodo, atractivo in ATRACTIVOS.items():
        punto = PUNTOS_AJUSTADOS[nodo]

        resultado[nodo] = {
            "nombre": atractivo["nombre"],
            "lat_original": atractivo["lat"],
            "lng_original": atractivo["lng"],
            "lat_carretera": punto["lat"],
            "lng_carretera": punto["lng"]
        }

    return jsonify(resultado)


@app.route("/api/dias")
def api_dias():
    return jsonify([
        {
            "dia": 1,
            "destinos": [1, 2, 4, 5, 17],
            "zona": "🌊 Playas de Antón"
        },
        {
            "dia": 2,
            "destinos": [8, 22, 12, 14, 15],
            "zona": "🏛️ Penonomé Histórico"
        },
        {
            "dia": 3,
            "destinos": [18, 20, 23, 24, 13, 9],
            "zona": "⛰️ La Pintada - Montaña"
        },
        {
            "dia": 4,
            "destinos": [10, 25, 26, 19],
            "zona": "🏺 Ruta Arqueológica de Natá"
        },
        {
            "dia": 5,
            "destinos": [6, 7, 28, 21, 29],
            "zona": "🌿 Naturaleza de Antón"
        },
        {
            "dia": 6,
            "destinos": [16, 3, 27, 11],
            "zona": "🌅 Tesoros de Aguadulce"
        },
        {
            "dia": 7,
            "destinos": [15, 18, 20, 23, 24],
            "zona": "🎯 Circuito Integrador"
        }
    ])


if __name__ == "__main__":
    preparar_grafo()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1"
    )
