from flask import Flask, render_template, request, jsonify
import requests
import heapq
import math

app = Flask(__name__)

# ============================================================
# CONFIGURACIÓN
# ============================================================

OSRM_URL = "https://router.project-osrm.org"

# ============================================================
# ATRACTIVOS TURÍSTICOS
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
# DISTANCIA GEOGRÁFICA AUXILIAR
# ============================================================

def distancia_haversine(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia aproximada entre dos coordenadas
    utilizando la fórmula de Haversine.
    """

    radio_tierra = 6371.0

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

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return radio_tierra * c


# ============================================================
# OBTENER PUNTO MÁS CERCANO A UNA CARRETERA
# ============================================================

def obtener_punto_carretera(lat, lng):

    url = (
        f"{OSRM_URL}/nearest/v1/driving/"
        f"{lng},{lat}"
    )

    params = {
        "number": 1
    }

    try:

        respuesta = requests.get(
            url,
            params=params,
            timeout=30
        )

        data = respuesta.json()

        if respuesta.status_code == 200 and data.get("code") == "Ok":

            waypoint = data["waypoints"][0]

            coordenadas = waypoint["location"]

            return {
                "lng": coordenadas[0],
                "lat": coordenadas[1],
                "indice": waypoint.get("waypoint_index"),
                "exito": True
            }

        return {
            "exito": False,
            "error": data.get(
                "message",
                "No se encontró una carretera cercana."
            )
        }

    except Exception as e:

        return {
            "exito": False,
            "error": str(e)
        }


# ============================================================
# AJUSTAR TODOS LOS NODOS A LA RED VIAL
# ============================================================

def ajustar_puntos_a_carreteras():

    puntos_ajustados = {}

    for nodo_id, atractivo in ATRACTIVOS.items():

        resultado = obtener_punto_carretera(
            atractivo["lat"],
            atractivo["lng"]
        )

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

def obtener_ruta_osrm(
    origen_lat,
    origen_lng,
    destino_lat,
    destino_lng
):

    url = (
        f"{OSRM_URL}/route/v1/driving/"
        f"{origen_lng},{origen_lat};"
        f"{destino_lng},{destino_lat}"
    )

    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "true"
    }

    try:

        respuesta = requests.get(
            url,
            params=params,
            timeout=30
        )

        data = respuesta.json()

        if respuesta.status_code != 200:
            return {
                "exito": False,
                "error": data.get(
                    "message",
                    "Error en OSRM."
                )
            }

        if data.get("code") != "Ok":
            return {
                "exito": False,
                "error": data.get(
                    "message",
                    "No se pudo calcular la ruta."
                )
            }

        ruta = data["routes"][0]

        distancia_km = ruta["distance"] / 1000
        tiempo_min = ruta["duration"] / 60

        # ====================================================
        # COSTO
        # ====================================================
        # Costo estimado de operación:
        # $0.15 por kilómetro.
        # ====================================================

        costo = distancia_km * 0.15

        geometria = ruta["geometry"]["coordinates"]

        puntos_ruta = [
            [coordenada[1], coordenada[0]]
            for coordenada in geometria
        ]

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

    except Exception as e:

        return {
            "exito": False,
            "error": str(e)
        }


# ============================================================
# CONSTRUIR MATRIZ DE DISTANCIAS Y TIEMPOS
# ============================================================

def construir_matriz_osrm(puntos):

    ids = list(puntos.keys())

    coordenadas = ";".join(
        f"{puntos[nodo]['lng']},{puntos[nodo]['lat']}"
        for nodo in ids
    )

    url = (
        f"{OSRM_URL}/table/v1/driving/"
        f"{coordenadas}"
    )

    params = {
        "annotations": "duration,distance"
    }

    try:

        respuesta = requests.get(
            url,
            params=params,
            timeout=60
        )

        data = respuesta.json()

        if respuesta.status_code != 200:
            raise Exception(
                data.get(
                    "message",
                    "Error al construir matriz OSRM."
                )
            )

        if data.get("code") != "Ok":
            raise Exception(
                data.get(
                    "message",
                    "OSRM no pudo construir la matriz."
                )
            )

        matriz_distancia = data["distances"]
        matriz_tiempo = data["durations"]

        return ids, matriz_distancia, matriz_tiempo

    except Exception as e:

        print("Error construyendo matriz:", e)

        return None, None, None


# ============================================================
# CONSTRUIR GRAFO
# ============================================================

def construir_grafo(puntos):

    ids, matriz_distancia, matriz_tiempo = construir_matriz_osrm(
        puntos
    )

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

            costo = distancia_km * 0.15

            grafo[nodo_origen][nodo_destino] = {

                "distancia_km": round(
                    distancia_km,
                    2
                ),

                "tiempo_min": round(
                    tiempo_min,
                    2
                ),

                "costo": round(
                    costo,
                    2
                )
            }

    return grafo


# ============================================================
# PREPARAR GRAFO
# ============================================================

GRAFO = {}
PUNTOS_AJUSTADOS = {}

def preparar_grafo():

    global GRAFO
    global PUNTOS_AJUSTADOS

    print("Preparando red vial...")

    PUNTOS_AJUSTADOS = ajustar_puntos_a_carreteras()

    print("Construyendo matriz de rutas...")

    GRAFO = construir_grafo(
        PUNTOS_AJUSTADOS
    )

    print(
        f"Grafo construido con {len(GRAFO)} nodos."
    )


# ============================================================
# DIJKSTRA
# ============================================================

def dijkstra(grafo, origen, destino, criterio):

    # ========================================================
    # CORRECCIÓN PRINCIPAL
    # ========================================================
    #
    # El frontend envía:
    #
    # distancia
    # tiempo
    # costo
    #
    # Pero las aristas contienen:
    #
    # distancia_km
    # tiempo_min
    # costo
    #
    # Por eso hacemos esta correspondencia.
    # ========================================================

    pesos = {

        "distancia": "distancia_km",

        "tiempo": "tiempo_min",

        "costo": "costo"
    }

    if criterio not in pesos:

        criterio = "tiempo"

    campo_peso = pesos[criterio]

    # ========================================================
    # Inicialización
    # ========================================================

    distancias = {
        nodo: float("inf")
        for nodo in grafo
    }

    anteriores = {
        nodo: None
        for nodo in grafo
    }

    distancias[origen] = 0

    cola_prioridad = [
        (0, origen)
    ]

    # ========================================================
    # ALGORITMO DE DIJKSTRA
    # ========================================================

    while cola_prioridad:

        distancia_actual, nodo_actual = heapq.heappop(
            cola_prioridad
        )

        if distancia_actual > distancias[nodo_actual]:
            continue

        if nodo_actual == destino:
            break

        vecinos = grafo.get(
            nodo_actual,
            {}
        )

        for vecino, datos in vecinos.items():

            # ================================================
            # CORRECCIÓN:
            # antes estaba:
            #
            # peso = datos[criterio]
            #
            # ahora usamos:
            #
            # peso = datos[campo_peso]
            # ================================================

            peso = datos[campo_peso]

            nueva_distancia = (
                distancia_actual + peso
            )

            if nueva_distancia < distancias[vecino]:

                distancias[vecino] = nueva_distancia

                anteriores[vecino] = nodo_actual

                heapq.heappush(
                    cola_prioridad,
                    (
                        nueva_distancia,
                        vecino
                    )
                )

    # ========================================================
    # VERIFICAR SI EXISTE CAMINO
    # ========================================================

    if distancias.get(destino, float("inf")) == float("inf"):

        return None

    # ========================================================
    # RECONSTRUIR CAMINO
    # ========================================================

    camino = []

    nodo = destino

    while nodo is not None:

        camino.append(nodo)

        nodo = anteriores[nodo]

    camino.reverse()

    return {

        "camino": camino,

        "peso_total": round(
            distancias[destino],
            2
        ),

        "criterio": criterio
    }


# ============================================================
# OBTENER GEOMETRÍA COMPLETA DEL CAMINO
# ============================================================

def obtener_geometria_camino(camino):

    if not camino or len(camino) < 2:

        return []

    coordenadas = ";".join(

        f"{PUNTOS_AJUSTADOS[nodo]['lng']},"
        f"{PUNTOS_AJUSTADOS[nodo]['lat']}"

        for nodo in camino
    )

    url = (
        f"{OSRM_URL}/route/v1/driving/"
        f"{coordenadas}"
    )

    params = {

        "overview": "full",

        "geometries": "geojson",

        "steps": "true"
    }

    try:

        respuesta = requests.get(
            url,
            params=params,
            timeout=60
        )

        data = respuesta.json()

        if respuesta.status_code != 200:
            return []

        if data.get("code") != "Ok":
            return []

        ruta = data["routes"][0]

        geometria = ruta["geometry"]["coordinates"]

        return [
            [coord[1], coord[0]]
            for coord in geometria
        ]

    except Exception as e:

        print(
            "Error obteniendo geometría:",
            e
        )

        return []


# ============================================================
# RUTA DIRECTA OSRM
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html",
        atractivos=ATRACTIVOS
    )


# ============================================================
# API PRINCIPAL DE DIJKSTRA
# ============================================================

@app.route(
    "/api/ruta",
    methods=["POST"]
)
def api_ruta():

    try:

        data = request.get_json()

        origen = int(
            data["origen"]
        )

        destino = int(
            data["destino"]
        )

        criterio = data.get(
            "criterio",
            "tiempo"
        )

        # ====================================================
        # VALIDAR NODOS
        # ====================================================

        if origen not in ATRACTIVOS:

            return jsonify({

                "exito": False,

                "error":
                "El nodo de origen no existe."

            }), 400

        if destino not in ATRACTIVOS:

            return jsonify({

                "exito": False,

                "error":
                "El nodo de destino no existe."

            }), 400

        if origen == destino:

            return jsonify({

                "exito": False,

                "error":
                "El origen y destino no pueden ser iguales."

            }), 400

        # ====================================================
        # ASEGURAR QUE EL GRAFO ESTÉ PREPARADO
        # ====================================================

        if not GRAFO:

            preparar_grafo()

        # ====================================================
        # EJECUTAR DIJKSTRA
        # ====================================================

        resultado_dijkstra = dijkstra(

            GRAFO,

            origen,

            destino,

            criterio
        )

        if resultado_dijkstra is None:

            return jsonify({

                "exito": False,

                "error":
                "No se encontró un camino entre los nodos seleccionados."

            }), 404

        camino = resultado_dijkstra[
            "camino"
        ]

        # ====================================================
        # GEOMETRÍA DE LA RUTA
        # ====================================================

        puntos_ruta = obtener_geometria_camino(
            camino
        )

        # ====================================================
        # CALCULAR DATOS TOTALES
        # ====================================================

        distancia_total = 0

        tiempo_total = 0

        costo_total = 0

        segmentos = []

        for i in range(
            len(camino) - 1
        ):

            nodo_a = camino[i]

            nodo_b = camino[i + 1]

            datos_segmento = GRAFO[
                nodo_a
            ][
                nodo_b
            ]

            distancia_total += (
                datos_segmento[
                    "distancia_km"
                ]
            )

            tiempo_total += (
                datos_segmento[
                    "tiempo_min"
                ]
            )

            costo_total += (
                datos_segmento[
                    "costo"
                ]
            )

            segmentos.append({

                "origen": nodo_a,

                "destino": nodo_b,

                "distancia_km":
                datos_segmento[
                    "distancia_km"
                ],

                "tiempo_min":
                datos_segmento[
                    "tiempo_min"
                ],

                "costo":
                datos_segmento[
                    "costo"
                ]
            })

        # ====================================================
        # NODOS DEL CAMINO
        # ====================================================

        nodos_ruta = []

        for nodo in camino:

            nodos_ruta.append({

                "id": nodo,

                **ATRACTIVOS[nodo],

                "lat_ruta":
                PUNTOS_AJUSTADOS[nodo][
                    "lat"
                ],

                "lng_ruta":
                PUNTOS_AJUSTADOS[nodo][
                    "lng"
                ]
            })

        # ====================================================
        # RESPUESTA
        # ====================================================

        return jsonify({

            "exito": True,

            "origen": origen,

            "destino": destino,

            "criterio": criterio,

            "camino": camino,

            "nodos_ruta": nodos_ruta,

            "distancia_km":
            round(
                distancia_total,
                2
            ),

            "tiempo_min":
            round(
                tiempo_total
            ),

            "costo":
            round(
                costo_total,
                2
            ),

            "puntos_ruta":
            puntos_ruta,

            "segmentos":
            segmentos,

            "nodos_visitados":
            len(camino)

        })

    except Exception as e:

        print(
            "ERROR API RUTA:",
            e
        )

        return jsonify({

            "exito": False,

            "error": str(e)

        }), 500


# ============================================================
# API PARA COORDENADAS
# ============================================================

@app.route(
    "/api/coordenadas"
)
def api_coordenadas():

    if not PUNTOS_AJUSTADOS:

        preparar_grafo()

    resultado = {}

    for nodo, datos in PUNTOS_AJUSTADOS.items():

        resultado[nodo] = {

            "nombre":
            datos["nombre"],

            "cod":
            datos["cod"],

            "tipo":
            datos["tipo"],

            "lat":
            datos["lat"],

            "lng":
            datos["lng"],

            "lat_original":
            datos.get(
                "lat_original",
                datos["lat"]
            ),

            "lng_original":
            datos.get(
                "lng_original",
                datos["lng"]
            )
        }

    return jsonify(resultado)


# ============================================================
# API DEL GRAFO
# ============================================================

@app.route(
    "/api/grafo"
)
def api_grafo():

    if not GRAFO:

        preparar_grafo()

    return jsonify(GRAFO)


# ============================================================
# ITINERARIOS DE 7 DÍAS
# ============================================================

@app.route(
    "/api/dias"
)
def api_dias():

    dias = [

        {
            "dia": 1,
            "destinos": [
                1, 2, 4, 5, 17
            ],
            "zona":
            "🌊 Playas de Antón"
        },

        {
            "dia": 2,
            "destinos": [
                8, 22, 12, 14, 15
            ],
            "zona":
            "🏛️ Penonomé Histórico"
        },

        {
            "dia": 3,
            "destinos": [
                18, 20, 23,
                24, 13, 9
            ],
            "zona":
            "⛰️ La Pintada - Montaña"
        },

        {
            "dia": 4,
            "destinos": [
                10, 25, 26, 19
            ],
            "zona":
            "🏺 Ruta Arqueológica de Natá"
        },

        {
            "dia": 5,
            "destinos": [
                6, 7, 28,
                21, 29
            ],
            "zona":
            "🌿 Naturaleza de Antón"
        },

        {
            "dia": 6,
            "destinos": [
                16, 3, 27, 11
            ],
            "zona":
            "🌅 Tesoros de Aguadulce"
        },

        {
            "dia": 7,
            "destinos": [
                15, 18, 20,
                23, 24
            ],
            "zona":
            "🎯 Circuito Integrador"
        }

    ]

    return jsonify(dias)


# ============================================================
# INICIO DE LA APLICACIÓN
# ============================================================

if __name__ == "__main__":

    print(
        "=========================================="
    )

    print(
        " RUTAS TURÍSTICAS DE COCLÉ"
    )

    print(
        " Optimización mediante Dijkstra"
    )

    print(
        "=========================================="
    )

    print(
        f"Atractivos registrados: "
        f"{len(ATRACTIVOS)}"
    )

    # --------------------------------------------------------
    # No construimos el grafo inmediatamente.
    #
    # Esto evita que Flask tarde demasiado al arrancar,
    # ya que OSRM debe consultar las carreteras.
    # --------------------------------------------------------

    print(
        "Servidor iniciado."
    )

    app.run(
        debug=True
    )
