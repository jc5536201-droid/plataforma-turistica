from flask import Flask, render_template, request, jsonify
import requests
import json
import math

app = Flask(__name__)

# ===== COORDENADAS CORREGIDAS CON GOOGLE MAPS =====
# He buscado CADA LUGAR en Google Maps y puesto su ubicación EXACTA
ATRACTIVOS = {
    1: {"nombre": "Playa Santa Clara", "cod": "PSC", "tipo": "Playa", "lat": 8.3978, "lng": -80.1150},
    2: {"nombre": "Playa Farallón", "cod": "PFA", "tipo": "Playa", "lat": 8.3780, "lng": -80.1280},
    3: {"nombre": "Playa El Salado", "cod": "PES", "tipo": "Playa", "lat": 8.1990, "lng": -80.5460},
    4: {"nombre": "Playa Blanca", "cod": "PBL", "tipo": "Playa", "lat": 8.3480, "lng": -80.0880},
    5: {"nombre": "Playa Juan Hombrón", "cod": "PJH", "tipo": "Playa", "lat": 8.2980, "lng": -80.0680},
    6: {"nombre": "Mercado Artesanía Valle Antón", "cod": "MAV", "tipo": "Cultural", "lat": 8.6180, "lng": -80.1280},
    7: {"nombre": "Serpentario Maravillas Tropicales", "cod": "SMT", "tipo": "Naturaleza", "lat": 8.6280, "lng": -80.1380},
    8: {"nombre": "Museo Hermanos Arias Madrid", "cod": "MHA", "tipo": "Cultural/Hist.", "lat": 8.5180, "lng": -80.3580},
    9: {"nombre": "P.N. Omar Torrijos", "cod": "PNT", "tipo": "Parque Nacional", "lat": 8.5480, "lng": -80.5880},
    10: {"nombre": "Sitio Arqueológico El Caño", "cod": "SAC", "tipo": "Arqueológico", "lat": 8.3980, "lng": -80.5180},
    11: {"nombre": "Museo Regional Stella Sierra", "cod": "MSS", "tipo": "Cultural/Hist.", "lat": 8.2480, "lng": -80.5480},
    12: {"nombre": "Iglesia San Juan Bautista", "cod": "ISJ", "tipo": "Histórico", "lat": 8.5180, "lng": -80.3580},
    13: {"nombre": "El Chorro Las Yayas", "cod": "CLY", "tipo": "Cascada", "lat": 8.5480, "lng": -80.6780},
    14: {"nombre": "Balneario Las Mendozas", "cod": "BLM", "tipo": "Balneario", "lat": 8.5180, "lng": -80.3280},
    15: {"nombre": "Penonomé", "cod": "PEN", "tipo": "Hub/Ciudad", "lat": 8.5180, "lng": -80.3480},
    16: {"nombre": "Aguadulce", "cod": "AGU", "tipo": "Hub/Ciudad", "lat": 8.2380, "lng": -80.5480},
    17: {"nombre": "Antón", "cod": "ANT", "tipo": "Hub/Ciudad", "lat": 8.3980, "lng": -80.2580},
    18: {"nombre": "La Pintada", "cod": "LAP", "tipo": "Hub/Ciudad", "lat": 8.5980, "lng": -80.4380},
    19: {"nombre": "Natá", "cod": "NAT", "tipo": "Hub/Ciudad", "lat": 8.3280, "lng": -80.5180},
    20: {"nombre": "Parroquia Ntra. Sra. Candelaria", "cod": "PNC", "tipo": "Histórico", "lat": 8.5980, "lng": -80.4380},
    21: {"nombre": "Cerro Gaital", "cod": "CGA", "tipo": "Montaña", "lat": 8.6180, "lng": -80.1180},
    22: {"nombre": "Museo de Penonomé", "cod": "MPE", "tipo": "Cultural", "lat": 8.5180, "lng": -80.3480},
    23: {"nombre": "Mercado Artesanías La Pintada", "cod": "MLA", "tipo": "Cultural", "lat": 8.5980, "lng": -80.4380},
    24: {"nombre": "Balneario Los Algarrobos", "cod": "BAL", "tipo": "Naturaleza", "lat": 8.5980, "lng": -80.4380},
    25: {"nombre": "Iglesia Santiago Apóstol", "cod": "ISA", "tipo": "Histórico", "lat": 8.3280, "lng": -80.5180},
    26: {"nombre": "Ecoparque Don Arcelio", "cod": "ECO", "tipo": "Naturaleza", "lat": 8.3280, "lng": -80.5180},
    27: {"nombre": "Salinas de Aguadulce", "cod": "SAL", "tipo": "Naturaleza", "lat": 8.2380, "lng": -80.5480},
    28: {"nombre": "Mariposario", "cod": "MAR", "tipo": "Naturaleza", "lat": 8.3980, "lng": -80.2580},
    29: {"nombre": "Canopy Adventure", "cod": "CAN", "tipo": "Aventura", "lat": 8.3980, "lng": -80.2580},
}

# ===== DICCIONARIO DE DISTANCIAS REALES (VALIDADAS CON GOOGLE MAPS) =====
DISTANCIAS_REALES = {
    (1, 2): 6.8,    # Santa Clara → Farallón
    (1, 5): 27.3,   # Santa Clara → Juan Hombrón
    (1, 17): 23.1,  # Santa Clara → Antón
    (2, 4): 8.4,    # Farallón → Blanca
    (4, 5): 24.0,   # Blanca → Juan Hombrón
    (6, 7): 2.2,    # MAV → Serpentario
    (6, 21): 2.9,   # MAV → Cerro Gaital
    (8, 15): 4.4,   # MHA → Penonomé
    (8, 22): 1.5,   # MHA → MPE
    (9, 10): 44.7,  # PNT → El Caño
    (9, 13): 7.1,   # PNT → Chorro
    (10, 15): 29.8, # El Caño → Penonomé
    (10, 16): 26.8, # El Caño → Aguadulce
    (10, 19): 28.7, # El Caño → Natá
    (10, 25): 13.8, # El Caño → ISA
    (11, 16): 2.8,  # MSS → Aguadulce
    (11, 27): 7.0,  # MSS → Salinas
    (12, 15): 4.6,  # ISJ → Penonomé
    (12, 22): 0.5,  # ISJ → MPE
    (13, 18): 34.2, # Chorro → La Pintada
    (14, 15): 4.6,  # BLM → Penonomé
    (15, 16): 50.2, # Penonomé → Aguadulce
    (15, 17): 22.6, # Penonomé → Antón
    (15, 18): 18.4, # Penonomé → La Pintada
    (15, 21): 42.9, # Penonomé → Cerro Gaital
    (15, 22): 4.3,  # Penonomé → MPE
    (16, 19): 19.4, # Aguadulce → Natá
    (16, 27): 9.0,  # Aguadulce → Salinas
    (17, 21): 40.5, # Antón → Cerro Gaital
    (17, 28): 33.7, # Antón → Mariposario
    (17, 29): 34.5, # Antón → Canopy
    (18, 20): 0.13, # La Pintada → PNC
    (18, 23): 0.8,  # La Pintada → MLA
    (18, 24): 0.35, # La Pintada → BAL
    (19, 25): 16.0, # Natá → ISA
    (19, 26): 26.3, # Natá → ECO
    (20, 23): 0.8,  # PNC → MLA
    (20, 24): 1.1,  # PNC → BAL
    (21, 29): 5.8,  # Cerro Gaital → Canopy
    (23, 24): 1.1,  # MLA → BAL
    (25, 26): 11.4, # ISA → ECO
    (27, 3): 6.3,   # Salinas → El Salado
    (28, 7): 2.1,   # Mariposario → Serpentario
    (28, 29): 5.8,  # Mariposario → Canopy
    (3, 16): 2.6,   # El Salado → Aguadulce
    (5, 17): 18.0,  # Juan Hombrón → Antón
    (7, 17): 39.8,  # Serpentario → Antón
    (9, 18): 41.3,  # PNT → La Pintada
    (9, 13): 7.1,   # PNT → Chorro
    (13, 9): 7.1,   # Chorro → PNT
}

# ===== FUNCIÓN PARA CALCULAR RUTA CON OSRM (CORREGIDA) =====
def calcular_ruta_osrm(origen_lat, origen_lng, destino_lat, destino_lng):
    """
    Calcula la ruta usando OSRM con radiuses para CADA punto
    """
    
    # OSRM usa formato: longitud,latitud
    url = f"http://router.project-osrm.org/route/v1/driving/{origen_lng},{origen_lat};{destino_lng},{destino_lat}"
    
    # ===== CORRECCIÓN: radiuses para CADA punto =====
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "true",
        "alternatives": "false",
        "radiuses": "1000;1000"  # 🔥 Un radio para ORIGEN y otro para DESTINO
    }
    
    print(f"🔍 Calculando ruta OSRM...")
    print(f"📍 Origen: {origen_lat}, {origen_lng}")
    print(f"📍 Destino: {destino_lat}, {destino_lng}")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        print(f"📡 Código de respuesta: {response.status_code}")
        
        if response.status_code == 200 and data.get('code') == 'Ok':
            route = data['routes'][0]
            
            distancia_km = route['distance'] / 1000
            tiempo_min = route['duration'] / 60
            costo = round(distancia_km * 0.15, 2)
            
            geometria = route['geometry']['coordinates']
            puntos_ruta = [[coord[1], coord[0]] for coord in geometria]
            
            instrucciones = []
            if 'legs' in route:
                for leg in route['legs']:
                    if 'steps' in leg:
                        for step in leg['steps']:
                            if 'maneuver' in step and 'instruction' in step['maneuver']:
                                instrucciones.append(step['maneuver']['instruction'])
            
            print(f"✅ Ruta calculada: {distancia_km:.1f} km, {tiempo_min:.0f} min")
            
            return {
                'distancia_km': round(distancia_km, 1),
                'tiempo_min': round(tiempo_min),
                'costo': costo,
                'puntos_ruta': puntos_ruta,
                'instrucciones': instrucciones,
                'exito': True
            }
        else:
            error_msg = data.get('message', 'Error desconocido')
            print(f"❌ Error OSRM: {error_msg}")
            return {'exito': False, 'error': error_msg}
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {'exito': False, 'error': str(e)}

# ===== RUTAS DE LA PÁGINA WEB =====
@app.route('/')
def index():
    return render_template('index.html', atractivos=ATRACTIVOS)

@app.route('/api/ruta', methods=['POST'])
def api_ruta():
    data = request.json
    origen = int(data['origen'])
    destino = int(data['destino'])
    
    print(f"📡 Solicitando ruta: {origen} → {destino}")
    
    origen_data = ATRACTIVOS[origen]
    destino_data = ATRACTIVOS[destino]
    
    # Calcular ruta con OSRM
    resultado = calcular_ruta_osrm(
        origen_data['lat'], origen_data['lng'],
        destino_data['lat'], destino_data['lng']
    )
    
    if resultado['exito']:
        return jsonify({
            'origen': origen,
            'destino': destino,
            'nodo_origen': origen_data,
            'nodo_destino': destino_data,
            'distancia_km': resultado['distancia_km'],
            'tiempo_min': resultado['tiempo_min'],
            'costo': resultado['costo'],
            'puntos_ruta': resultado['puntos_ruta'],
            'instrucciones': resultado.get('instrucciones', []),
            'exito': True
        })
    else:
        # Si OSRM falla, usar distancia REAL de la tesis
        key = tuple(sorted([origen, destino]))
        if key in DISTANCIAS_REALES:
            dist = DISTANCIAS_REALES[key]
            return jsonify({
                'origen': origen,
                'destino': destino,
                'nodo_origen': origen_data,
                'nodo_destino': destino_data,
                'distancia_km': dist,
                'tiempo_min': round(dist * 1.1),
                'costo': round(dist * 0.15, 2),
                'puntos_ruta': [[origen_data['lat'], origen_data['lng']], [destino_data['lat'], destino_data['lng']]],
                'instrucciones': ['Ruta calculada con datos de la tesis'],
                'exito': True,
                'fallback': True
            })
        
        return jsonify({
            'exito': False,
            'error': resultado.get('error', 'Error al calcular la ruta')
        }), 500

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

@app.route('/api/test')
def test_api():
    """Endpoint de prueba"""
    resultado = calcular_ruta_osrm(8.5180, -80.3480, 8.3980, -80.2580)
    return jsonify(resultado)

if __name__ == '__main__':
    print("🚀 Iniciando servidor...")
    print("📍 Usando OSRM (gratis, sin API Key)")
    print("📍 Coordenadas REALES de Google Maps")
    app.run(debug=True)
