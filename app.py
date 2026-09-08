from flask import Flask, render_template, request, jsonify
import requests
import json
import time
import urllib3

# Desactivar advertencias de SSL (solo para Render)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# ===== TU API KEY DE OPENROUTESERVICE =====
ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjgwYWNhZjY3NjIwYjQ2MTRiZjI0Nzg0MDMxOGQ4N2QyIiwiaCI6Im11cm11cjY0In0="

# ===== DATOS DE LOS ATRACTIVOS =====
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

# ===== FUNCIÓN PARA CALCULAR RUTA CON OPENROUTESERVICE =====
def calcular_ruta_ors(origen_lat, origen_lng, destino_lat, destino_lng):
    """
    Calcula la ruta usando OpenRouteService API
    """
    
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    
    # OpenRouteService usa formato [longitud, latitud]
    coordenadas = [[origen_lng, origen_lat], [destino_lng, destino_lat]]
    
    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8"
    }
    
    data = {
        "coordinates": coordenadas,
        "units": "km",
        "language": "es",
        "geometry": "true",
        "instructions": "true",
        "elevation": "false"
    }
    
    print(f"🔍 Calculando ruta ORS...")
    print(f"📍 Origen: {origen_lat}, {origen_lng}")
    print(f"📍 Destino: {destino_lat}, {destino_lng}")
    
    try:
        # Aumentar timeout y usar verify=False para evitar problemas SSL
        response = requests.post(
            url, 
            json=data, 
            headers=headers, 
            timeout=60,
            verify=True
        )
        
        print(f"📡 Código de respuesta: {response.status_code}")
        
        if response.status_code == 200:
            resultado = response.json()
            
            # Extraer datos
            feature = resultado['features'][0]
            properties = feature['properties']
            segment = properties['segments'][0]
            
            distancia_km = segment['distance'] / 1000
            tiempo_min = segment['duration'] / 60
            costo = round(distancia_km * 0.15, 2)
            
            # Extraer puntos de la ruta
            geometria = feature['geometry']['coordinates']
            puntos_ruta = [[coord[1], coord[0]] for coord in geometria]
            
            # Extraer instrucciones
            instrucciones = []
            if 'steps' in segment:
                for step in segment['steps']:
                    instrucciones.append(step.get('instruction', ''))
            
            print(f"✅ Ruta calculada: {distancia_km} km, {tiempo_min} min")
            
            return {
                'distancia_km': round(distancia_km, 1),
                'tiempo_min': round(tiempo_min),
                'costo': costo,
                'puntos_ruta': puntos_ruta,
                'instrucciones': instrucciones,
                'exito': True
            }
        else:
            error_text = response.text[:500] if response.text else "Sin respuesta"
            print(f"❌ Error {response.status_code}: {error_text}")
            
            # Intentar con verify=False si falla SSL
            if "SSL" in error_text or "certificate" in error_text:
                print("🔄 Reintentando con verify=False...")
                response = requests.post(
                    url, 
                    json=data, 
                    headers=headers, 
                    timeout=60,
                    verify=False
                )
                if response.status_code == 200:
                    resultado = response.json()
                    feature = resultado['features'][0]
                    segment = feature['properties']['segments'][0]
                    distancia_km = segment['distance'] / 1000
                    tiempo_min = segment['duration'] / 60
                    costo = round(distancia_km * 0.15, 2)
                    geometria = feature['geometry']['coordinates']
                    puntos_ruta = [[coord[1], coord[0]] for coord in geometria]
                    return {
                        'distancia_km': round(distancia_km, 1),
                        'tiempo_min': round(tiempo_min),
                        'costo': costo,
                        'puntos_ruta': puntos_ruta,
                        'instrucciones': [],
                        'exito': True
                    }
            
            return {'exito': False, 'error': f"Error {response.status_code}: {response.text[:200]}"}
            
    except requests.exceptions.Timeout:
        print("❌ Timeout - La API tardó demasiado en responder")
        return {'exito': False, 'error': 'Timeout - La API tardó demasiado'}
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Error de conexión: {str(e)}")
        return {'exito': False, 'error': f'Error de conexión: {str(e)}'}
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")
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
    
    resultado = calcular_ruta_ors(
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

@app.route('/api/test')
def test_api():
    """Endpoint de prueba para verificar que la API Key funciona"""
    test_result = calcular_ruta_ors(8.52, -80.35, 8.42, -80.12)
    return jsonify(test_result)

if __name__ == '__main__':
    print("🚀 Iniciando servidor...")
    print("📍 API Key configurada")
    app.run(debug=True)
