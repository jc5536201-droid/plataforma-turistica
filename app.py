from flask import Flask, render_template, request, jsonify
import requests
import json

app = Flask(__name__)

# ===== COORDENADAS VERIFICADAS (investigadas y corregidas) =====
# Fuentes: Wikipedia (ES/EN), OpenStreetMap/Mapcarta, Geodatos.net, sitios oficiales
# de municipios (municipios.gob.pa), Mindat.org y páginas turísticas verificadas.
#
# NOTA IMPORTANTE: los sitios marcados con (*) en el comentario no tienen una
# fuente georreferenciada de alta precisión (son atractivos pequeños/poco
# documentados en línea): se ubicaron lo más cerca posible del poblado o zona
# donde realmente se encuentran, según fuentes textuales. Te recomiendo
# verificarlos en Google Maps antes de usarlos en la tesis si necesitas
# precisión de nivel "punto exacto del sendero/entrada".
ATRACTIVOS = {
    1: {"nombre": "Playa Santa Clara", "cod": "PSC", "tipo": "Playa", "lat": 8.3825, "lng": -80.1086},
    2: {"nombre": "Playa Farallón", "cod": "PFA", "tipo": "Playa", "lat": 8.3610, "lng": -80.1302},
    3: {"nombre": "Playa El Salado", "cod": "PES", "tipo": "Playa", "lat": 8.1930, "lng": -80.4832},
    4: {"nombre": "Playa Blanca", "cod": "PBL", "tipo": "Playa", "lat": 8.3500, "lng": -80.1450},
    5: {"nombre": "Playa Juan Hombrón", "cod": "PJH", "tipo": "Playa", "lat": 8.2983, "lng": -80.2534},
    6: {"nombre": "Mercado Artesanía Valle Antón", "cod": "MAV", "tipo": "Cultural", "lat": 8.6008, "lng": -80.1295},
    7: {"nombre": "Serpentario Maravillas Tropicales", "cod": "SMT", "tipo": "Naturaleza", "lat": 8.5995, "lng": -80.1275},  # (*)
    8: {"nombre": "Museo Hermanos Arias Madrid", "cod": "MHA", "tipo": "Cultural/Hist.", "lat": 8.5350, "lng": -80.3600},  # (*) vía a Las Mendozas
    9: {"nombre": "P.N. Omar Torrijos", "cod": "PNT", "tipo": "Parque Nacional", "lat": 8.6878, "lng": -80.6433},
    10: {"nombre": "Sitio Arqueológico El Caño", "cod": "SAC", "tipo": "Arqueológico", "lat": 8.3960, "lng": -80.5013},
    11: {"nombre": "Museo Regional Stella Sierra", "cod": "MSS", "tipo": "Cultural/Hist.", "lat": 8.2400, "lng": -80.5460},  # (*) casco de Aguadulce
    12: {"nombre": "Iglesia San Juan Bautista", "cod": "ISJ", "tipo": "Histórico", "lat": 8.5220, "lng": -80.3594},
    13: {"nombre": "El Chorro Las Yayas", "cod": "CLY", "tipo": "Cascada", "lat": 8.6100, "lng": -80.4550},  # (*) distrito La Pintada
    14: {"nombre": "Balneario Las Mendozas", "cod": "BLM", "tipo": "Balneario", "lat": 8.5450, "lng": -80.3700},  # (*) río Zaratí, cerca de Penonomé
    15: {"nombre": "Penonomé", "cod": "PEN", "tipo": "Hub/Ciudad", "lat": 8.5187, "lng": -80.3553},
    16: {"nombre": "Aguadulce", "cod": "AGU", "tipo": "Hub/Ciudad", "lat": 8.2400, "lng": -80.5400},
    17: {"nombre": "Antón", "cod": "ANT", "tipo": "Hub/Ciudad", "lat": 8.3985, "lng": -80.2609},
    18: {"nombre": "La Pintada", "cod": "LAP", "tipo": "Hub/Ciudad", "lat": 8.6012, "lng": -80.4489},
    19: {"nombre": "Natá", "cod": "NAT", "tipo": "Hub/Ciudad", "lat": 8.3300, "lng": -80.5200},
    20: {"nombre": "Parroquia Ntra. Sra. Candelaria", "cod": "PNC", "tipo": "Histórico", "lat": 8.5600, "lng": -80.4700},  # (*) La Candelaria, km167 Interamericana
    21: {"nombre": "Cerro Gaital", "cod": "CGA", "tipo": "Montaña", "lat": 8.6250, "lng": -80.1280},  # (*) mirador norte de El Valle
    22: {"nombre": "Museo de Penonomé", "cod": "MPE", "tipo": "Cultural", "lat": 8.5190, "lng": -80.3570},  # Casco Antiguo, Barrio San Antonio
    23: {"nombre": "Mercado Artesanías La Pintada", "cod": "MLA", "tipo": "Cultural", "lat": 8.6012, "lng": -80.4489},
    24: {"nombre": "Balneario Los Algarrobos", "cod": "BAL", "tipo": "Naturaleza", "lat": 8.6050, "lng": -80.4500},  # (*) río Coclé del Sur, La Pintada
    25: {"nombre": "Iglesia Santiago Apóstol", "cod": "ISA", "tipo": "Histórico", "lat": 8.3305, "lng": -80.5195},
    26: {"nombre": "Ecoparque Don Arcelio", "cod": "ECO", "tipo": "Naturaleza", "lat": 8.3700, "lng": -80.5200},  # (*) cerca de Natá
    27: {"nombre": "Salinas de Aguadulce", "cod": "SAL", "tipo": "Naturaleza", "lat": 8.2000, "lng": -80.5600},  # (*) salineras costeras al sur de Aguadulce
    28: {"nombre": "Mariposario", "cod": "MAR", "tipo": "Naturaleza", "lat": 8.4000, "lng": -80.2600},  # (*) Antón
    29: {"nombre": "Canopy Adventure", "cod": "CAN", "tipo": "Aventura", "lat": 8.6000, "lng": -80.1280},  # corregido: está en El Valle de Antón, no en Antón ciudad
}

# ===== FUNCIÓN PARA CALCULAR RUTA CON OSRM =====
def calcular_ruta_osrm(origen_lat, origen_lng, destino_lat, destino_lng):
    """
    Calcula la ruta usando OSRM
    """
    
    url = f"http://router.project-osrm.org/route/v1/driving/{origen_lng},{origen_lat};{destino_lng},{destino_lat}"
    
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "true",
        "alternatives": "false",
        "radiuses": "1000;1000"
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
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
            
            return {
                'distancia_km': round(distancia_km, 1),
                'tiempo_min': round(tiempo_min),
                'costo': costo,
                'puntos_ruta': puntos_ruta,
                'instrucciones': instrucciones,
                'exito': True
            }
        else:
            return {'exito': False, 'error': data.get('message', 'Error desconocido')}
            
    except Exception as e:
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
    
    origen_data = ATRACTIVOS[origen]
    destino_data = ATRACTIVOS[destino]
    
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

if __name__ == '__main__':
    app.run(debug=True)
