from flask import Flask, render_template, request, jsonify
import requests
import json
import math

app = Flask(__name__)

# ===== DATOS DE LOS ATRACTIVOS (COORDENADAS APROXIMADAS) =====
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

# ===== FUNCIÓN PARA AJUSTAR COORDENADAS A LA CARRETERA MÁS CERCANA =====
def ajustar_coordenada_osrm(lat, lng):
    """
    Usa OSRM para encontrar la carretera más cercana a una coordenada
    Retorna las coordenadas ajustadas (sobre la carretera)
    """
    url = f"http://router.project-osrm.org/route/v1/driving/{lng},{lat};{lng+0.001},{lat+0.001}"
    params = {
        "overview": "false",
        "radiuses": "2000"  # Buscar en 2km
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if response.status_code == 200 and data.get('code') == 'Ok':
            # OSRM encontró una ruta, extraer el punto de inicio ajustado
            waypoints = data.get('waypoints', [])
            if waypoints and len(waypoints) > 0:
                location = waypoints[0].get('location', [])
                if location and len(location) >= 2:
                    # OSRM devuelve [lng, lat]
                    return {
                        'lat': location[1],
                        'lng': location[0],
                        'ajustado': True
                    }
    except Exception as e:
        print(f"❌ Error ajustando coordenada: {e}")
    
    # Si falla, devolver las coordenadas originales
    return {
        'lat': lat,
        'lng': lng,
        'ajustado': False
    }

# ===== FUNCIÓN PARA CALCULAR RUTA CON OSRM =====
def calcular_ruta_osrm(origen_lat, origen_lng, destino_lat, destino_lng):
    """
    Calcula la ruta usando OSRM con ajuste automático de coordenadas
    """
    
    # ===== PRIMERO: AJUSTAR COORDENADAS =====
    origen_ajustado = ajustar_coordenada_osrm(origen_lat, origen_lng)
    destino_ajustado = ajustar_coordenada_osrm(destino_lat, destino_lng)
    
    if origen_ajustado['ajustado']:
        print(f"📍 Origen ajustado: {origen_ajustado['lat']}, {origen_ajustado['lng']}")
    else:
        print(f"⚠️ No se pudo ajustar origen, usando coordenada original")
    
    if destino_ajustado['ajustado']:
        print(f"📍 Destino ajustado: {destino_ajustado['lat']}, {destino_ajustado['lng']}")
    else:
        print(f"⚠️ No se pudo ajustar destino, usando coordenada original")
    
    # ===== SEGUNDO: CALCULAR RUTA CON COORDENADAS AJUSTADAS =====
    url = f"http://router.project-osrm.org/route/v1/driving/{origen_ajustado['lng']},{origen_ajustado['lat']};{destino_ajustado['lng']},{destino_ajustado['lat']}"
    
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "true",
        "alternatives": "false",
        "radiuses": "500"  # Radio más pequeño porque ya ajustamos
    }
    
    print(f"🔍 Calculando ruta OSRM...")
    print(f"📍 Origen: {origen_ajustado['lat']}, {origen_ajustado['lng']}")
    print(f"📍 Destino: {destino_ajustado['lat']}, {destino_ajustado['lng']}")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        print(f"📡 Código de respuesta: {response.status_code}")
        
        if response.status_code == 200 and data.get('code') == 'Ok':
            # Extraer datos de la ruta
            route = data['routes'][0]
            
            # Distancia en metros -> kilómetros
            distancia_km = route['distance'] / 1000
            # Duración en segundos -> minutos
            tiempo_min = route['duration'] / 60
            # Costo estimado
            costo = round(distancia_km * 0.15, 2)
            
            # Extraer puntos de la geometría
            geometria = route['geometry']['coordinates']
            puntos_ruta = [[coord[1], coord[0]] for coord in geometria]
            
            # Extraer instrucciones
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
            
    except requests.exceptions.Timeout:
        print("❌ Timeout - OSRM tardó demasiado")
        return {'exito': False, 'error': 'Timeout de conexión'}
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
    """Endpoint de prueba para verificar el ajuste de coordenadas"""
    resultado = calcular_ruta_osrm(8.5180, -80.3480, 8.3980, -80.2580)
    return jsonify(resultado)

@app.route('/api/ajustar/<float:lat>/<float:lng>')
def ajustar_coordenada(lat, lng):
    """Endpoint para probar el ajuste de una coordenada"""
    resultado = ajustar_coordenada_osrm(lat, lng)
    return jsonify(resultado)

if __name__ == '__main__':
    print("🚀 Iniciando servidor...")
    print("📍 Usando OSRM con ajuste automático de coordenadas")
    app.run(debug=True)
