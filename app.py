from flask import Flask, render_template, request, jsonify
import requests
import math

app = Flask(__name__)

# ============================================================
# CONFIGURACIÓN DE GRAPHOPPER (CON TU API KEY)
# ============================================================
GRAPHOPPER_API_KEY = "0800d0c9-4f88-4108-a025-97019105035b"

# ============================================================
# DATOS DE LOS ATRACTIVOS (COORDENADAS CORREGIDAS)
# ============================================================
ATRACTIVOS = {
    1: {"nombre": "Playa Santa Clara", "cod": "PSC", "tipo": "Playa", "lat": 8.3976, "lng": -80.1148},
    2: {"nombre": "Playa Farallón", "cod": "PFA", "tipo": "Playa", "lat": 8.3782, "lng": -80.1275},
    3: {"nombre": "Playa El Salado", "cod": "PES", "tipo": "Playa", "lat": 8.1990, "lng": -80.5460},
    4: {"nombre": "Playa Blanca", "cod": "PBL", "tipo": "Playa", "lat": 8.3480, "lng": -80.0875},
    5: {"nombre": "Playa Juan Hombrón", "cod": "PJH", "tipo": "Playa", "lat": 8.2985, "lng": -80.0670},
    6: {"nombre": "Mercado Artesanía Valle Antón", "cod": "MAV", "tipo": "Cultural", "lat": 8.6185, "lng": -80.1270},
    7: {"nombre": "Serpentario Maravillas Tropicales", "cod": "SMT", "tipo": "Naturaleza", "lat": 8.6280, "lng": -80.1370},
    8: {"nombre": "Museo Hermanos Arias Madrid", "cod": "MHA", "tipo": "Cultural/Hist.", "lat": 8.5185, "lng": -80.3575},
    9: {"nombre": "P.N. Omar Torrijos", "cod": "PNT", "tipo": "Parque Nacional", "lat": 8.5480, "lng": -80.5870},
    10: {"nombre": "Sitio Arqueológico El Caño", "cod": "SAC", "tipo": "Arqueológico", "lat": 8.3985, "lng": -80.5170},
    11: {"nombre": "Museo Regional Stella Sierra", "cod": "MSS", "tipo": "Cultural/Hist.", "lat": 8.2485, "lng": -80.5470},
    12: {"nombre": "Iglesia San Juan Bautista", "cod": "ISJ", "tipo": "Histórico", "lat": 8.5180, "lng": -80.3570},
    13: {"nombre": "El Chorro Las Yayas", "cod": "CLY", "tipo": "Cascada", "lat": 8.5485, "lng": -80.6770},
    14: {"nombre": "Balneario Las Mendozas", "cod": "BLM", "tipo": "Balneario", "lat": 8.5180, "lng": -80.3270},
    15: {"nombre": "Penonomé", "cod": "PEN", "tipo": "Hub/Ciudad", "lat": 8.5185, "lng": -80.3475},
    16: {"nombre": "Aguadulce", "cod": "AGU", "tipo": "Hub/Ciudad", "lat": 8.2385, "lng": -80.5470},
    17: {"nombre": "Antón", "cod": "ANT", "tipo": "Hub/Ciudad", "lat": 8.3985, "lng": -80.2575},
    18: {"nombre": "La Pintada", "cod": "LAP", "tipo": "Hub/Ciudad", "lat": 8.5985, "lng": -80.4370},
    19: {"nombre": "Natá", "cod": "NAT", "tipo": "Hub/Ciudad", "lat": 8.3285, "lng": -80.5170},
    20: {"nombre": "Parroquia Ntra. Sra. Candelaria", "cod": "PNC", "tipo": "Histórico", "lat": 8.5980, "lng": -80.4370},
    21: {"nombre": "Cerro Gaital", "cod": "CGA", "tipo": "Montaña", "lat": 8.6185, "lng": -80.1170},
    22: {"nombre": "Museo de Penonomé", "cod": "MPE", "tipo": "Cultural", "lat": 8.5180, "lng": -80.3470},
    23: {"nombre": "Mercado Artesanías La Pintada", "cod": "MLA", "tipo": "Cultural", "lat": 8.5985, "lng": -80.4375},
    24: {"nombre": "Balneario Los Algarrobos", "cod": "BAL", "tipo": "Naturaleza", "lat": 8.5980, "lng": -80.4370},
    25: {"nombre": "Iglesia Santiago Apóstol", "cod": "ISA", "tipo": "Histórico", "lat": 8.3280, "lng": -80.5175},
    26: {"nombre": "Ecoparque Don Arcelio", "cod": "ECO", "tipo": "Naturaleza", "lat": 8.3285, "lng": -80.5170},
    27: {"nombre": "Salinas de Aguadulce", "cod": "SAL", "tipo": "Naturaleza", "lat": 8.2380, "lng": -80.5475},
    28: {"nombre": "Mariposario", "cod": "MAR", "tipo": "Naturaleza", "lat": 8.3980, "lng": -80.2570},
    29: {"nombre": "Canopy Adventure", "cod": "CAN", "tipo": "Aventura", "lat": 8.3985, "lng": -80.2570},
}

# ============================================================
# FUNCIÓN PARA CALCULAR RUTA CON GRAPHOPPER
# ============================================================
def calcular_ruta_graphhopper(origen_lat, origen_lng, destino_lat, destino_lng):
    """
    Calcula la ruta usando GraphHopper API
    """
    
    url = "https://graphhopper.com/api/1/route"
    
    params = {
        "point": [
            f"{origen_lat},{origen_lng}",
            f"{destino_lat},{destino_lng}"
        ],
        "vehicle": "car",
        "locale": "es",
        "key": GRAPHOPPER_API_KEY,
        "type": "json",
        "points_encoded": "false",
        "elevation": "false",
        "debug": "false",
        "ch.disable": "true"
    }
    
    print(f"🔍 Calculando ruta GraphHopper...")
    print(f"📍 Origen: {origen_lat}, {origen_lng}")
    print(f"📍 Destino: {destino_lat}, {destino_lng}")
    
    try:
        respuesta = requests.get(url, params=params, timeout=30)
        data = respuesta.json()
        
        print(f"📡 Código GraphHopper: {respuesta.status_code}")
        
        if respuesta.status_code == 200:
            path = data['paths'][0]
            
            distancia_km = path['distance'] / 1000
            tiempo_min = path['time'] / 60000
            costo = round(distancia_km * 0.15, 2)
            
            puntos_ruta = path['points']['coordinates']
            puntos_ruta = [[p[1], p[0]] for p in puntos_ruta]
            
            instrucciones = []
            for step in path.get('instructions', []):
                instrucciones.append(step.get('text', ''))
            
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
            print(f"❌ Error GraphHopper: {error_msg}")
            return {'exito': False, 'error': error_msg}
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {'exito': False, 'error': str(e)}

# ============================================================
# RUTAS DE LA PÁGINA WEB
# ============================================================
@app.route('/')
def index():
    return render_template('index.html', atractivos=ATRACTIVOS)

@app.route('/api/ruta', methods=['POST'])
def api_ruta():
    try:
        data = request.json
        origen = int(data['origen'])
        destino = int(data['destino'])
        
        if origen not in ATRACTIVOS or destino not in ATRACTIVOS:
            return jsonify({'exito': False, 'error': 'Nodo no existe'}), 400
        
        if origen == destino:
            return jsonify({'exito': False, 'error': 'Origen y destino iguales'}), 400
        
        origen_data = ATRACTIVOS[origen]
        destino_data = ATRACTIVOS[destino]
        
        resultado = calcular_ruta_graphhopper(
            origen_data['lat'], origen_data['lng'],
            destino_data['lat'], destino_data['lng']
        )
        
        if resultado['exito']:
            return jsonify({
                'exito': True,
                'origen': origen,
                'destino': destino,
                'nodo_origen': origen_data,
                'nodo_destino': destino_data,
                'distancia_km': resultado['distancia_km'],
                'tiempo_min': resultado['tiempo_min'],
                'costo': resultado['costo'],
                'puntos_ruta': resultado['puntos_ruta'],
                'instrucciones': resultado['instrucciones']
            })
        else:
            return jsonify({'exito': False, 'error': resultado.get('error', 'Error al calcular')}), 500
            
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)}), 500

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
    """Prueba que GraphHopper funciona"""
    resultado = calcular_ruta_graphhopper(8.5185, -80.3475, 8.3985, -80.2575)
    return jsonify(resultado)

if __name__ == '__main__':
    print("🚀 Iniciando servidor con GraphHopper...")
    print(f"📍 Atractivos: {len(ATRACTIVOS)}")
    print("✅ API Key configurada correctamente")
    app.run(debug=True, host='0.0.0.0', port=5000)
