from flask import Flask, render_template, request, jsonify
import heapq

app = Flask(__name__)

# ===== DATOS DE LOS ATRACTIVOS (29 lugares) =====
ATRACTIVOS = {
    1: {"nombre": "Playa Santa Clara", "cod": "PSC", "tipo": "Playa", "lat": 8.42, "lng": -80.12},
    2: {"nombre": "Playa Farallón", "cod": "PFA", "tipo": "Playa", "lat": 8.38, "lng": -80.13},
    3: {"nombre": "Playa El Salado", "cod": "PES", "tipo": "Playa", "lat": 8.20, "lng": -80.55},
    4: {"nombre": "Playa Blanca", "cod": "PBL", "tipo": "Playa", "lat": 8.35, "lng": -80.09},
    5: {"nombre": "Playa Juan Hombrón", "cod": "PJH", "tipo": "Playa", "lat": 8.30, "lng": -80.07},
    6: {"nombre": "Mercado Artesanía Valle Antón", "cod": "MAV", "tipo": "Cultural", "lat": 8.62, "lng": -80.13},
    7: {"nombre": "Serpentario Maravillas Tropicales", "cod": "SMT", "tipo": "Naturaleza", "lat": 8.63, "lng": -80.14},
    8: {"nombre": "Museo Hermanos Arias Madrid", "cod": "MHA", "tipo": "Cultural/Hist.", "lat": 8.52, "lng": -80.36},
    9: {"nombre": "P.N. Omar Torrijos", "cod": "PNT", "tipo": "Parque Nacional", "lat": 8.55, "lng": -80.59},
    10: {"nombre": "Sitio Arqueológico El Caño", "cod": "SAC", "tipo": "Arqueológico", "lat": 8.40, "lng": -80.52},
    11: {"nombre": "Museo Regional Stella Sierra", "cod": "MSS", "tipo": "Cultural/Hist.", "lat": 8.25, "lng": -80.55},
    12: {"nombre": "Iglesia San Juan Bautista", "cod": "ISJ", "tipo": "Histórico", "lat": 8.52, "lng": -80.36},
    13: {"nombre": "El Chorro Las Yayas", "cod": "CLY", "tipo": "Cascada", "lat": 8.55, "lng": -80.68},
    14: {"nombre": "Balneario Las Mendozas", "cod": "BLM", "tipo": "Balneario", "lat": 8.52, "lng": -80.33},
    15: {"nombre": "Penonomé", "cod": "PEN", "tipo": "Hub/Ciudad", "lat": 8.52, "lng": -80.35},
    16: {"nombre": "Aguadulce", "cod": "AGU", "tipo": "Hub/Ciudad", "lat": 8.24, "lng": -80.55},
    17: {"nombre": "Antón", "cod": "ANT", "tipo": "Hub/Ciudad", "lat": 8.40, "lng": -80.26},
    18: {"nombre": "La Pintada", "cod": "LAP", "tipo": "Hub/Ciudad", "lat": 8.60, "lng": -80.44},
    19: {"nombre": "Natá", "cod": "NAT", "tipo": "Hub/Ciudad", "lat": 8.33, "lng": -80.52},
    20: {"nombre": "Parroquia Ntra. Sra. Candelaria", "cod": "PNC", "tipo": "Histórico", "lat": 8.60, "lng": -80.44},
    21: {"nombre": "Cerro Gaital", "cod": "CGA", "tipo": "Montaña", "lat": 8.62, "lng": -80.12},
    22: {"nombre": "Museo de Penonomé", "cod": "MPE", "tipo": "Cultural", "lat": 8.52, "lng": -80.35},
    23: {"nombre": "Mercado Artesanías La Pintada", "cod": "MLA", "tipo": "Cultural", "lat": 8.60, "lng": -80.44},
    24: {"nombre": "Balneario Los Algarrobos", "cod": "BAL", "tipo": "Naturaleza", "lat": 8.60, "lng": -80.44},
    25: {"nombre": "Iglesia Santiago Apóstol", "cod": "ISA", "tipo": "Histórico", "lat": 8.33, "lng": -80.52},
    26: {"nombre": "Ecoparque Don Arcelio", "cod": "ECO", "tipo": "Naturaleza", "lat": 8.33, "lng": -80.52},
    27: {"nombre": "Salinas de Aguadulce", "cod": "SAL", "tipo": "Naturaleza", "lat": 8.24, "lng": -80.55},
    28: {"nombre": "Mariposario", "cod": "MAR", "tipo": "Naturaleza", "lat": 8.40, "lng": -80.26},
    29: {"nombre": "Canopy Adventure", "cod": "CAN", "tipo": "Aventura", "lat": 8.40, "lng": -80.26},
}

# ===== LAS CARRETERAS (conexiones entre lugares) =====
ARISTAS = [
    (15, 17, 22.6, 25), (15, 10, 29.8, 31), (15, 16, 50.2, 46),
    (15, 18, 18.4, 23), (15, 8, 4.4, 8), (15, 12, 4.6, 9),
    (15, 14, 4.6, 9), (15, 21, 42.9, 78), (17, 1, 23.1, 25),
    (17, 2, 21.4, 25), (17, 4, 19.8, 22), (17, 5, 18.0, 24),
    (17, 6, 37.6, 59), (17, 7, 39.8, 63), (17, 21, 40.5, 65),
    (1, 2, 6.8, 11), (2, 4, 8.4, 12), (4, 5, 24.0, 29),
    (1, 5, 27.3, 32), (6, 7, 2.2, 5), (6, 21, 2.9, 7),
    (19, 10, 28.7, 37), (19, 17, 66.0, 66), (19, 16, 19.4, 31),
    (16, 10, 26.8, 27), (16, 11, 2.8, 6), (16, 3, 2.6, 7),
    (18, 13, 34.2, 54), (18, 20, 0.13, 1), (18, 9, 41.3, 88),
    (9, 13, 7.1, 34), (9, 10, 44.7, 85), (15, 22, 4.3, 8),
    (8, 22, 1.5, 4), (22, 12, 0.5, 2), (18, 23, 0.8, 1),
    (18, 24, 0.35, 2), (23, 24, 1.1, 2), (20, 23, 0.8, 1),
    (20, 24, 1.1, 2), (10, 25, 13.8, 15), (19, 25, 16.0, 28),
    (25, 26, 11.4, 13), (19, 26, 26.3, 35), (16, 27, 9.0, 14),
    (3, 27, 6.3, 8), (27, 11, 7.0, 10), (17, 28, 33.7, 56),
    (17, 29, 34.5, 57), (28, 7, 2.1, 5), (28, 29, 5.8, 12),
    (29, 21, 5.8, 12),
]

# ===== CONSTRUIR EL GRAFO =====
grafo = {n: [] for n in ATRACTIVOS}
for u, v, d, t in ARISTAS:
    costo = round(d * 0.15, 2)
    grafo[u].append((v, d, t, costo))
    grafo[v].append((u, d, t, costo))

# ===== ALGORITMO DE DIJKSTRA =====
def dijkstra(origen, destino, criterio):
    idx = {"distancia": 1, "tiempo": 2, "costo": 3}[criterio]
    INF = float('inf')
    dist = {n: INF for n in grafo}
    prev = {n: None for n in grafo}
    dist[origen] = 0
    heap = [(0, origen)]
    
    while heap:
        d_u, u = heapq.heappop(heap)
        if d_u > dist[u]:
            continue
        if u == destino:
            break
        for v, d, t, c in grafo[u]:
            pesos = [d, t, c]
            peso = pesos[idx]
            alt = dist[u] + peso
            if alt < dist[v]:
                dist[v] = alt
                prev[v] = u
                heapq.heappush(heap, (alt, v))
    
    camino = []
    actual = destino
    while actual is not None:
        camino.append(actual)
        actual = prev[actual]
    camino.reverse()
    
    if camino and camino[0] == origen:
        return camino, dist[destino]
    return [], None

# ===== RUTAS DE LA PÁGINA WEB =====
@app.route('/')
def index():
    return render_template('index.html', atractivos=ATRACTIVOS)

@app.route('/api/ruta', methods=['POST'])
def api_ruta():
    data = request.json
    origen = int(data['origen'])
    destino = int(data['destino'])
    criterio = data.get('criterio', 'distancia')
    camino, total = dijkstra(origen, destino, criterio)
    
    if camino:
        return jsonify({
            'camino': camino,
            'total': total,
            'nodos': [ATRACTIVOS[n] for n in camino],
            'coordenadas': [[ATRACTIVOS[n]['lat'], ATRACTIVOS[n]['lng']] for n in camino]
        })
    return jsonify({'error': 'No se encontró ruta'}), 404

@app.route('/api/dias')
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

if __name__ == '__main__':
    app.run(debug=True)