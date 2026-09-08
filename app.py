from flask import Flask, render_template, request, jsonify
import requests
import heapq
import math
import time

app = Flask(__name__)

# ============================================================
# CONFIGURACIÓN
# ============================================================

OSRM_BASE_URL = "https://router.project-osrm.org"

# Costo estimado utilizado en el proyecto:
# USD 0.15 por kilómetro
COSTO_POR_KM = 0.15

# Tiempo máximo de espera para OSRM
TIMEOUT_OSRM = 40

# ============================================================
# ATRACTIVOS TURÍSTICOS
# ============================================================
#
# IMPORTANTE:
# Las coordenadas representan el punto geográfico utilizado
# por la plataforma.
#
# OSRM posteriormente busca el segmento vial más cercano
# mediante el servicio Nearest.
#
# ============================================================

ATRACTIVOS = {

    1: {
        "nombre": "Playa Santa Clara",
        "cod": "PSC",
        "tipo": "Playa",
        "lat": 8.37518,
        "lng": -80.10355
    },

    2: {
        "nombre": "Playa Farallón",
        "cod": "PFA",
        "tipo": "Playa",
        "lat": 8.3610,
        "lng": -80.1302
    },

    3: {
        "nombre": "Playa El Salado",
        "cod": "PES",
        "tipo": "Playa",
        "lat": 8.1930,
        "lng": -80.4832
    },

    4: {
        "nombre": "Playa Blanca",
        "cod": "PBL",
        "tipo": "Playa",
        "lat": 8.34535,
        "lng": -80.15234
    },

    5: {
        "nombre": "Playa Juan Hombrón",
        "cod": "PJH",
        "tipo": "Playa",
        "lat": 8.2983,
        "lng": -80.2534
    },

    6: {
        "nombre": "Mercado Artesanía Valle Antón",
        "cod": "MAV",
        "tipo": "Cultural",
        "lat": 8.6008,
        "lng": -80.1295
    },

    7: {
        "nombre": "Serpentario Maravillas Tropicales",
        "cod": "SMT",
        "tipo": "Naturaleza",
        "lat": 8.5995,
        "lng": -80.1275
    },

    8: {
        "nombre": "Museo Hermanos Arias Madrid",
        "cod": "MHA",
        "tipo": "Cultural/Hist.",
        "lat": 8.52508,
        "lng": -80.35666
    },

    9: {
        "nombre": "P.N. Omar Torrijos",
        "cod": "PNT",
        "tipo": "Parque Nacional",
        "lat": 8.6505,
        "lng": -80.7125
    },

    10: {
        "nombre": "Sitio Arqueológico El Caño",
        "cod": "SAC",
        "tipo": "Arqueológico",
        "lat": 8.3960,
        "lng": -80.5013
    },

    11: {
        "nombre": "Museo Regional Stella Sierra",
        "cod": "MSS",
        "tipo": "Cultural/Hist.",
        "lat": 8.2400,
        "lng": -80.5460
    },

    12: {
        "nombre": "Iglesia San Juan Bautista",
        "cod": "ISJ",
        "tipo": "Histórico",
        "lat": 8.5220,
        "lng": -80.3594
    },

    13: {
        "nombre": "El Chorro Las Yayas",
        "cod": "CLY",
        "tipo": "Cascada",
        "lat": 8.6100,
        "lng": -80.4550
    },

    14: {
        "nombre": "Balneario Las Mendozas",
        "cod": "BLM",
        "tipo": "Balneario",
        "lat": 8.5450,
        "lng": -80.3700
    },

    15: {
        "nombre": "Penonomé",
        "cod": "PEN",
        "tipo": "Hub/Ciudad",
        "lat": 8.51889,
        "lng": -80.35727
    },

    16: {
        "nombre": "Aguadulce",
        "cod": "AGU",
        "tipo": "Hub/Ciudad",
        "lat": 8.2400,
        "lng": -80.5400
    },

    17: {
        "nombre": "Antón",
        "cod": "ANT",
        "tipo": "Hub/Ciudad",
        "lat": 8.3985,
        "lng": -80.2609
    },

    18: {
        "nombre": "La Pintada",
        "cod": "LAP",
        "tipo": "Hub/Ciudad",
        "lat": 8.6012,
        "lng": -80.4489
    },

    19: {
        "nombre": "Natá",
        "cod": "NAT",
        "tipo": "Hub/Ciudad",
        "lat": 8.3300,
        "lng": -80.5200
    },

    20: {
        "nombre": "Parroquia Ntra. Sra. Candelaria",
        "cod": "PNC",
        "tipo": "Histórico",
        "lat": 8.5600,
        "lng": -80.4700
    },

    21: {
        "nombre": "Cerro Gaital",
        "cod": "CGA",
        "tipo": "Montaña",
        "lat": 8.6250,
        "lng": -80.1280
    },

    22: {
        "nombre": "Museo de Penonomé",
        "cod": "MPE",
        "tipo": "Cultural",
        "lat": 8.51956,
        "lng": -80.36061
    },

    23: {
        "nombre": "Mercado Artesanías La Pintada",
        "cod": "MLA",
        "tipo": "Cultural",
        "lat": 8.6012,
        "lng": -80.4489
    },

    24: {
        "nombre": "Balneario Los Algarrobos",
        "cod": "BAL",
        "tipo": "Naturaleza",
        "lat": 8.6050,
        "lng": -80.4500
    },

    25: {
        "nombre": "Iglesia Santiago Apóstol",
        "cod": "ISA",
        "tipo": "Histórico",
        "lat": 8.3305,
        "lng": -80.5195
    },

    26: {
        "nombre": "Ecoparque Don Arcelio",
        "cod": "ECO",
        "tipo": "Naturaleza",
        "lat": 8.3700,
        "lng": -80.5200
    },

    27: {
        "nombre": "Salinas de Aguadulce",
        "cod": "SAL",
        "tipo": "Naturaleza",
        "lat": 8.2000,
        "lng": -80.5600
    },

    28: {
        "nombre": "Mariposario",
        "cod": "MAR",
        "tipo": "Naturaleza",
        "lat": 8.4000,
        "lng": -80.2600
    },

    29: {
        "nombre": "Canopy Adventure",
        "cod": "CAN",
        "tipo": "Aventura",
        "lat": 8.6000,
        "lng": -80.1280
    }
}


# ============================================================
# VARIABLES GLOBALES DEL GRAFO
# ============================================================

GRAFO = {}

MATRIZ_DISTANCIAS = {}
MATRIZ_TIEMPOS = {}

PUNTOS_AJUSTADOS = {}

GRAFO_CARGADO = False


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def validar_id_atractivo(id_atractivo):
    """
    Comprueba que el ID exista.
    """

    try:
        id_atractivo = int(id_atractivo)
    except Exception:
        return False

    return id_atractivo in ATRACTIVOS


def distancia_haversine(lat1, lon1, lat2, lon2):
    """
    Distancia geográfica aproximada entre dos coordenadas.
    Se utiliza únicamente como referencia.
    """

    radio = 6371.0

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    diferencia_lat = math.radians(lat2 - lat1)
    diferencia_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(diferencia_lat / 2) ** 2
        +
        math.cos(lat1)
        * math.cos(lat2)
        * math.sin(diferencia_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return radio * c


# ============================================================
# OSRM - NEAREST
# ============================================================

def obtener_punto_carretera(lat, lng):
    """
    Ajusta una coordenada al segmento vial más cercano
    utilizando el servicio Nearest de OSRM.

    OSRM devuelve las coordenadas como:
    [longitud, latitud]
    """

    url = (
        f"{OSRM_BASE_URL}/nearest/v1/driving/"
        f"{lng},{lat}"
    )

    params = {
        "number": 1
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=TIMEOUT_OSRM
        )

        if response.status_code != 200:
            return {
                "exito": False,
                "error": f"OSRM HTTP {response.status_code}"
            }

        data = response.json()

        if data.get("code") != "Ok":
            return {
                "exito": False,
                "error": data.get(
                    "message",
                    "OSRM no encontró una carretera."
                )
            }

        waypoints = data.get("waypoints", [])

        if not waypoints:
            return {
                "exito": False,
                "error": "No se encontró un segmento vial cercano."
            }

        waypoint = waypoints[0]

        location = waypoint.get("location")

        if not location or len(location) != 2:
            return {
                "exito": False,
                "error": "OSRM devolvió una ubicación inválida."
            }

        snapped_lng = location[0]
        snapped_lat = location[1]

        distancia = waypoint.get("distance", 0)

        return {
            "exito": True,
            "lat": snapped_lat,
            "lng": snapped_lng,
            "distancia_m": round(distancia, 2),
            "nombre_carretera": waypoint.get("name", "")
        }

    except requests.exceptions.Timeout:

        return {
            "exito": False,
            "error": "Tiempo de espera agotado al consultar OSRM."
        }

    except requests.exceptions.RequestException as e:

        return {
            "exito": False,
            "error": f"Error de conexión con OSRM: {str(e)}"
        }

    except Exception as e:

        return {
            "exito": False,
            "error": f"Error inesperado: {str(e)}"
        }


# ============================================================
# AJUSTAR TODOS LOS ATRACTIVOS A LA RED VIAL
# ============================================================

def ajustar_puntos_a_carreteras():
    """
    Busca el segmento vial más cercano para cada atractivo.

    Se ejecuta una sola vez y guarda los resultados en memoria.
    """

    global PUNTOS_AJUSTADOS

    print("\n==============================================")
    print("AJUSTANDO ATRACTIVOS A LA RED VIAL DE OSRM")
    print("==============================================\n")

    PUNTOS_AJUSTADOS = {}

    for id_atractivo, lugar in ATRACTIVOS.items():

        resultado = obtener_punto_carretera(
            lugar["lat"],
            lugar["lng"]
        )

        if resultado["exito"]:

            PUNTOS_AJUSTADOS[id_atractivo] = {
                "lat": resultado["lat"],
                "lng": resultado["lng"],
                "distancia_m": resultado["distancia_m"],
                "nombre_carretera": resultado.get(
                    "nombre_carretera",
                    ""
                )
            }

            print(
                f"OK {id_atractivo:02d} "
                f"{lugar['nombre']} "
                f"-> {resultado['distancia_m']} m"
            )

        else:

            # Si Nearest falla, conservamos la coordenada original.
            PUNTOS_AJUSTADOS[id_atractivo] = {
                "lat": lugar["lat"],
                "lng": lugar["lng"],
                "distancia_m": None,
                "nombre_carretera": "",
                "advertencia": resultado["error"]
            }

            print(
                f"ADVERTENCIA {id_atractivo:02d} "
                f"{lugar['nombre']} "
                f"-> {resultado['error']}"
            )

        # Pequeña pausa para evitar consultas excesivamente rápidas.
        time.sleep(0.05)


# ============================================================
# OSRM - TABLE
# ============================================================

def construir_matriz_osrm():
    """
    Obtiene una matriz de distancia y tiempo entre los 29 atractivos.

    OSRM Table es adecuado para problemas de optimización porque
    devuelve matrices de duración y distancia entre múltiples
    ubicaciones.
    """

    global MATRIZ_DISTANCIAS
    global MATRIZ_TIEMPOS

    ids = sorted(ATRACTIVOS.keys())

    coordenadas = []

    for id_atractivo in ids:

        punto = PUNTOS_AJUSTADOS.get(id_atractivo)

        if punto:

            coordenadas.append(
                f"{punto['lng']},{punto['lat']}"
            )

        else:

            lugar = ATRACTIVOS[id_atractivo]

            coordenadas.append(
                f"{lugar['lng']},{lugar['lat']}"
            )

    coordenadas_string = ";".join(coordenadas)

    url = (
        f"{OSRM_BASE_URL}/table/v1/driving/"
        f"{coordenadas_string}"
    )

    params = {
        "annotations": "distance,duration"
    }

    print("\n==============================================")
    print("CONSTRUYENDO MATRIZ OSRM")
    print("==============================================\n")

    try:

        response = requests.get(
            url,
            params=params,
            timeout=TIMEOUT_OSRM
        )

        if response.status_code != 200:

            raise RuntimeError(
                f"OSRM HTTP {response.status_code}"
            )

        data = response.json()

        if data.get("code") != "Ok":

            raise RuntimeError(
                data.get(
                    "message",
                    "OSRM no pudo construir la matriz."
                )
            )

        distancias = data.get("distances")
        duraciones = data.get("durations")

        if not distancias or not duraciones:

            raise RuntimeError(
                "OSRM no devolvió distancias o duraciones."
            )

        MATRIZ_DISTANCIAS = {}
        MATRIZ_TIEMPOS = {}

        for i, id_origen in enumerate(ids):

            MATRIZ_DISTANCIAS[id_origen] = {}
            MATRIZ_TIEMPOS[id_origen] = {}

            for j, id_destino in enumerate(ids):

                distancia = distancias[i][j]
                duracion = duraciones[i][j]

                MATRIZ_DISTANCIAS[id_origen][id_destino] = (
                    distancia
                )

                MATRIZ_TIEMPOS[id_origen][id_destino] = (
                    duracion
                )

        print(
            f"OK. Matriz construida: "
            f"{len(ids)} x {len(ids)}"
        )

        return True

    except Exception as e:

        print(
            "ERROR construyendo matriz OSRM:",
            e
        )

        MATRIZ_DISTANCIAS = {}
        MATRIZ_TIEMPOS = {}

        return False


# ============================================================
# CONSTRUIR GRAFO
# ============================================================

def construir_grafo():
    """
    Construye un grafo dirigido.

    Cada atractivo es un nodo.

    Cada conexión contiene:

    - distancia
    - tiempo
    - costo
    """

    global GRAFO

    GRAFO = {}

    ids = sorted(ATRACTIVOS.keys())

    for id_origen in ids:

        GRAFO[id_origen] = {}

        for id_destino in ids:

            if id_origen == id_destino:
                continue

            distancia_m = (
                MATRIZ_DISTANCIAS
                .get(id_origen, {})
                .get(id_destino)
            )

            tiempo_s = (
                MATRIZ_TIEMPOS
                .get(id_origen, {})
                .get(id_destino)
            )

            # Algunas combinaciones pueden no tener ruta.
            if distancia_m is None or tiempo_s is None:
                continue

            distancia_km = distancia_m / 1000.0
            tiempo_min = tiempo_s / 60.0
            costo = distancia_km * COSTO_POR_KM

            GRAFO[id_origen][id_destino] = {

                "distancia_km": distancia_km,

                "tiempo_min": tiempo_min,

                "costo": costo
            }

    print(
        f"Grafo construido con "
        f"{len(GRAFO)} nodos."
    )


# ============================================================
# PREPARAR SISTEMA
# ============================================================

def preparar_grafo():

    global GRAFO_CARGADO

    if GRAFO_CARGADO:
        return True

    print("\n")
    print("==============================================")
    print("INICIANDO SISTEMA DE RUTAS TURÍSTICAS")
    print("==============================================")

    ajustar_puntos_a_carreteras()

    matriz_ok = construir_matriz_osrm()

    if not matriz_ok:

        print(
            "No fue posible construir la matriz OSRM."
        )

        return False

    construir_grafo()

    GRAFO_CARGADO = True

    print("==============================================")
    print("GRAFO LISTO")
    print("==============================================\n")

    return True


# ============================================================
# DIJKSTRA
# ============================================================

def dijkstra(origen, destino, criterio="distancia"):
    """
    Algoritmo de Dijkstra.

    criterio:
        distancia
        tiempo
        costo
    """

    if origen not in GRAFO:
        return None

    if destino not in GRAFO:
        return None

    if criterio not in (
        "distancia",
        "tiempo",
        "costo"
    ):
        criterio = "distancia"

    distancias = {
        nodo: float("inf")
        for nodo in GRAFO
    }

    anteriores = {
        nodo: None
        for nodo in GRAFO
    }

    distancias[origen] = 0

    cola = [
        (0, origen)
    ]

    visitados = set()

    while cola:

        distancia_actual, nodo_actual = heapq.heappop(
            cola
        )

        if nodo_actual in visitados:
            continue

        visitados.add(nodo_actual)

        if nodo_actual == destino:
            break

        vecinos = GRAFO.get(
            nodo_actual,
            {}
        )

        for vecino, datos in vecinos.items():

            peso = datos[criterio]

            nueva_distancia = (
                distancia_actual + peso
            )

            if nueva_distancia < distancias[vecino]:

                distancias[vecino] = nueva_distancia

                anteriores[vecino] = nodo_actual

                heapq.heappush(
                    cola,
                    (
                        nueva_distancia,
                        vecino
                    )
                )

    if distancias[destino] == float("inf"):
        return None

    # Reconstruir camino
    camino = []

    actual = destino

    while actual is not None:

        camino.append(actual)

        actual = anteriores[actual]

    camino.reverse()

    # Calcular totales reales
    distancia_total = 0
    tiempo_total = 0
    costo_total = 0

    tramos = []

    for i in range(len(camino) - 1):

        a = camino[i]
        b = camino[i + 1]

        datos = GRAFO[a][b]

        distancia_total += datos["distancia_km"]
        tiempo_total += datos["tiempo_min"]
        costo_total += datos["costo"]

        tramos.append({
            "origen": a,
            "destino": b,
            "distancia_km": datos["distancia_km"],
            "tiempo_min": datos["tiempo_min"],
            "costo": datos["costo"]
        })

    return {

        "camino": camino,

        "criterio": criterio,

        "peso_total": distancias[destino],

        "distancia_km": distancia_total,

        "tiempo_min": tiempo_total,

        "costo": costo_total,

        "tramos": tramos
    }


# ============================================================
# OBTENER GEOMETRÍA DE UNA RUTA
# ============================================================

def obtener_geometria_ruta(camino):
    """
    Obtiene la geometría vial correspondiente al camino
    seleccionado por Dijkstra.
    """

    if not camino or len(camino) < 2:

        return {
            "exito": False,
            "error": "El camino no contiene suficientes nodos."
        }

    coordenadas = []

    for id_atractivo in camino:

        punto = PUNTOS_AJUSTADOS.get(
            id_atractivo
        )

        if not punto:

            lugar = ATRACTIVOS[id_atractivo]

            coordenadas.append(
                f"{lugar['lng']},{lugar['lat']}"
            )

        else:

            coordenadas.append(
                f"{punto['lng']},{punto['lat']}"
            )

    coordenadas_string = ";".join(
        coordenadas
    )

    url = (
        f"{OSRM_BASE_URL}/route/v1/driving/"
        f"{coordenadas_string}"
    )

    params = {

        "overview": "full",

        "geometries": "geojson",

        "steps": "true",

        "alternatives": "false"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=TIMEOUT_OSRM
        )

        if response.status_code != 200:

            return {
                "exito": False,
                "error": (
                    f"OSRM HTTP "
                    f"{response.status_code}"
                )
            }

        data = response.json()

        if data.get("code") != "Ok":

            return {
                "exito": False,
                "error": data.get(
                    "message",
                    "OSRM no encontró la geometría."
                )
            }

        route = data["routes"][0]

        geometria = route["geometry"]["coordinates"]

        puntos_ruta = [
            [coord[1], coord[0]]
            for coord in geometria
        ]

        instrucciones = []

        for leg in route.get("legs", []):

            for step in leg.get("steps", []):

                maneuver = step.get(
                    "maneuver",
                    {}
                )

                tipo = maneuver.get(
                    "type",
                    ""
                )

                modifier = maneuver.get(
                    "modifier",
                    ""
                )

                nombre = step.get(
                    "name",
                    ""
                )

                if tipo == "depart":

                    texto = "Iniciar recorrido"

                elif tipo == "arrive":

                    texto = "Llegar al destino"

                elif tipo == "turn":

                    if modifier:
                        texto = (
                            f"Girar {modifier}"
                        )
                    else:
                        texto = "Realizar giro"

                elif tipo == "roundabout":

                    texto = "Entrar en la rotonda"

                elif tipo == "merge":

                    texto = "Incorporarse a la vía"

                else:

                    texto = tipo.capitalize()

                if nombre:

                    texto += f" por {nombre}"

                instrucciones.append(
                    texto
                )

        return {

            "exito": True,

            "puntos_ruta": puntos_ruta,

            "instrucciones": instrucciones
        }

    except Exception as e:

        return {
            "exito": False,
            "error": str(e)
        }


# ============================================================
# RUTA PRINCIPAL
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html",
        atractivos=ATRACTIVOS
    )


# ============================================================
# API RUTA + DIJKSTRA
# ============================================================

@app.route(
    "/api/ruta",
    methods=["POST"]
)
def api_ruta():

    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "exito": False,
                "error": "No se recibieron datos."
            }), 400

        origen = int(
            data.get("origen")
        )

        destino = int(
            data.get("destino")
        )

        criterio = data.get(
            "criterio",
            "distancia"
        )

        if not validar_id_atractivo(origen):

            return jsonify({
                "exito": False,
                "error": "El origen no existe."
            }), 400

        if not validar_id_atractivo(destino):

            return jsonify({
                "exito": False,
                "error": "El destino no existe."
            }), 400

        if origen == destino:

            return jsonify({
                "exito": False,
                "error": (
                    "El origen y el destino "
                    "deben ser diferentes."
                )
            }), 400

        if criterio not in (
            "distancia",
            "tiempo",
            "costo"
        ):

            criterio = "distancia"

        # Preparar grafo
        if not preparar_grafo():

            return jsonify({
                "exito": False,
                "error": (
                    "No fue posible preparar "
                    "el grafo de rutas."
                )
            }), 500

        # Ejecutar Dijkstra
        resultado = dijkstra(
            origen,
            destino,
            criterio
        )

        if not resultado:

            return jsonify({
                "exito": False,
                "error": (
                    "No existe una ruta disponible "
                    "entre los nodos seleccionados."
                )
            }), 404

        # Obtener geometría
        geometria = obtener_geometria_ruta(
            resultado["camino"]
        )

        if not geometria["exito"]:

            return jsonify({
                "exito": False,
                "error": geometria["error"]
            }), 500

        camino = resultado["camino"]

        nodos_ruta = []

        for posicion, id_nodo in enumerate(
            camino,
            start=1
        ):

            nodo = dict(
                ATRACTIVOS[id_nodo]
            )

            nodo["orden"] = posicion

            punto = PUNTOS_AJUSTADOS.get(
                id_nodo
            )

            if punto:

                nodo["lat_carretera"] = (
                    punto["lat"]
                )

                nodo["lng_carretera"] = (
                    punto["lng"]
                )

                nodo["distancia_carretera_m"] = (
                    punto.get("distancia_m")
                )

            nodos_ruta.append(nodo)

        return jsonify({

            "exito": True,

            "algoritmo": "Dijkstra",

            "criterio": criterio,

            "criterio_nombre": {
                "distancia": "Distancia mínima",
                "tiempo": "Tiempo mínimo",
                "costo": "Costo mínimo"
            }[criterio],

            "origen": origen,

            "destino": destino,

            "nodo_origen": ATRACTIVOS[origen],

            "nodo_destino": ATRACTIVOS[destino],

            "camino": camino,

            "nodos_ruta": nodos_ruta,

            "distancia_km": round(
                resultado["distancia_km"],
                2
            ),

            "tiempo_min": round(
                resultado["tiempo_min"]
            ),

            "costo": round(
                resultado["costo"],
                2
            ),

            "peso_total": round(
                resultado["peso_total"],
                4
            ),

            "tramos": resultado["tramos"],

            "puntos_ruta": (
                geometria["puntos_ruta"]
            ),

            "instrucciones": (
                geometria["instrucciones"]
            )
        })

    except Exception as e:

        print(
            "ERROR /api/ruta:",
            e
        )

        return jsonify({
            "exito": False,
            "error": str(e)
        }), 500


# ============================================================
# API PARA VERIFICAR COORDENADAS
# ============================================================

@app.route(
    "/api/coordenadas",
    methods=["GET"]
)
def api_coordenadas():

    if not preparar_grafo():

        return jsonify({
            "exito": False,
            "error": "No se pudieron preparar las coordenadas."
        }), 500

    resultado = []

    for id_atractivo, lugar in ATRACTIVOS.items():

        punto = PUNTOS_AJUSTADOS.get(
            id_atractivo,
            {}
        )

        elemento = dict(lugar)

        elemento["id"] = id_atractivo

        elemento["lat_carretera"] = (
            punto.get("lat")
        )

        elemento["lng_carretera"] = (
            punto.get("lng")
        )

        elemento["distancia_carretera_m"] = (
            punto.get("distancia_m")
        )

        elemento["carretera"] = (
            punto.get(
                "nombre_carretera",
                ""
            )
        )

        elemento["advertencia"] = (
            punto.get(
                "advertencia"
            )
        )

        resultado.append(elemento)

    return jsonify({
        "exito": True,
        "atractivos": resultado
    })


# ============================================================
# API PARA MOSTRAR EL GRAFO
# ============================================================

@app.route(
    "/api/grafo",
    methods=["GET"]
)
def api_grafo():

    if not preparar_grafo():

        return jsonify({
            "exito": False,
            "error": "No se pudo construir el grafo."
        }), 500

    nodos = []

    for id_nodo, lugar in ATRACTIVOS.items():

        nodos.append({
            "id": id_nodo,
            "nombre": lugar["nombre"],
            "codigo": lugar["cod"],
            "lat": lugar["lat"],
            "lng": lugar["lng"]
        })

    aristas = []

    for origen, vecinos in GRAFO.items():

        for destino, datos in vecinos.items():

            aristas.append({

                "origen": origen,

                "destino": destino,

                "distancia_km": round(
                    datos["distancia_km"],
                    3
                ),

                "tiempo_min": round(
                    datos["tiempo_min"],
                    2
                ),

                "costo": round(
                    datos["costo"],
                    2
                )
            })

    return jsonify({

        "exito": True,

        "nodos": nodos,

        "aristas": aristas,

        "total_nodos": len(nodos),

        "total_aristas": len(aristas)
    })


# ============================================================
# ITINERARIOS DE 7 DÍAS
# ============================================================

@app.route(
    "/api/dias",
    methods=["GET"]
)
def api_dias():

    dias = [

        {
            "dia": 1,
            "destinos": [
                1, 2, 4, 5, 17
            ],
            "zona": "🌊 Playas de Antón"
        },

        {
            "dia": 2,
            "destinos": [
                8, 22, 12, 14, 15
            ],
            "zona": "🏛️ Penonomé Histórico"
        },

        {
            "dia": 3,
            "destinos": [
                18, 20, 23, 24, 13, 9
            ],
            "zona": "⛰️ La Pintada - Montaña"
        },

        {
            "dia": 4,
            "destinos": [
                10, 25, 26, 19
            ],
            "zona": "🏺 Ruta Arqueológica de Natá"
        },

        {
            "dia": 5,
            "destinos": [
                6, 7, 28, 21, 29
            ],
            "zona": "🌿 Naturaleza de Antón"
        },

        {
            "dia": 6,
            "destinos": [
                16, 3, 27, 11
            ],
            "zona": "🌅 Tesoros de Aguadulce"
        },

        {
            "dia": 7,
            "destinos": [
                15, 18, 20, 23, 24
            ],
            "zona": "🎯 Circuito Integrador"
        }
    ]

    return jsonify(dias)


# ============================================================
# INICIAR SERVIDOR
# ============================================================

if __name__ == "__main__":

    print("")
    print("==============================================")
    print(" PLATAFORMA DE RUTAS TURÍSTICAS DE COCLÉ")
    print(" Algoritmo de Dijkstra")
    print("==============================================")
    print("")

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
