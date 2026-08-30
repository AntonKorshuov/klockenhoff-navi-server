import os
import json
import requests
import math
import time
from flask import Flask, request, jsonify, send_from_directory
from geopy.geocoders import Nominatim

app = Flask(__name__, static_folder='static')
DATA_FILE = 'clients_db.json'
ROUTE_FILE = 'saved_route.json'

geolocator = Nominatim(user_agent='klockenhoff_navi_app')

OFFICE_LOCATION = {
    'id': 0,
    'name': 'Klockenhoff GmbH',
    'address': '44379 Dortmund, Bünnerhelfstraße 32',
    'tour': 'Офис',
    'plz': '44379',
    'city': 'Dortmund',
    'street': 'Bünnerhelfstraße 32',
    'lat': 51.5073323,
    'lng': 7.4047794
}

def load_clients():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    if os.path.exists('clients.json'):
        with open('clients.json', 'r', encoding='utf-8') as f:
            clients = json.load(f)
            db = [OFFICE_LOCATION] + clients
            save_clients(db)
            return db
    return [OFFICE_LOCATION]

def save_clients(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/developer_ak_logo.png')
def download_logo_png():
    return send_from_directory('static', 'developer_ak_logo.png', as_attachment=True)

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/developer_ak_logo.svg')
def download_logo_svg():
    return send_from_directory('static', 'developer_ak_logo.svg', as_attachment=True)

@app.route('/Klockenhoff_NAVI.apk')
@app.route('/NAVI.apk')
def download_apk():
    return send_from_directory('static', 'NAVI.apk', as_attachment=True)

@app.route('/Klockenhoff_Clients.xlsx')
def download_excel():
    return send_from_directory('static', 'Klockenhoff_Clients.xlsx', as_attachment=True)

@app.route('/api/clients', methods=['GET'])
def get_clients():
    db = load_clients()
    return jsonify(db)

@app.route('/api/clients', methods=['POST'])
def add_client():
    data = request.json
    db = load_clients()
    
    client_id = data.get('id')
    is_update = client_id is not None and any(c['id'] == client_id for c in db)

    if is_update:
        new_id = int(client_id)
        # Remove existing client object for replacement
        db = [c for c in db if c['id'] != new_id]
    else:
        new_id = max([c['id'] for c in db] or [0]) + 1

    name = data.get('name', f'Client {new_id}')
    address = data.get('address', '')
    tour = data.get('tour', '')
    plz = data.get('plz', '')
    city = data.get('city', '')
    street = data.get('street', '')
    
    lat = data.get('lat')
    lng = data.get('lng')
    
    if lat is None or lng is None:
        queries = []
        if street and plz and city:
            queries.append(f'{street}, {plz} {city}, Germany')
        if street and city:
            queries.append(f'{street}, {city}, Germany')
        if address:
            queries.append(f'{address}, Germany')
            queries.append(address)
        if plz and city:
            queries.append(f'{plz} {city}, Germany')

        for q in queries:
            try:
                loc = geolocator.geocode(q, timeout=10)
                if loc:
                    lat, lng = loc.latitude, loc.longitude
                    break
            except Exception as ge:
                print(f"Geocoding exception for query '{q}': {ge}")

        if lat is None or lng is None:
            lat, lng = OFFICE_LOCATION['lat'], OFFICE_LOCATION['lng']
            
    client = {
        'id': new_id,
        'name': name,
        'address': address or f'{plz} {city} {street}'.strip(),
        'tour': tour,
        'plz': plz,
        'city': city,
        'street': street,
        'lat': float(lat),
        'lng': float(lng)
    }
    
    db.append(client)
    save_clients(db)
    return jsonify({'status': 'success', 'client': client})

@app.route('/api/clients/import', methods=['POST'])
def import_clients_batch():
    data = request.json
    new_clients = data.get('clients', [])
    if not isinstance(new_clients, list):
        return jsonify({'status': 'error', 'message': 'Invalid data format'}), 400

    db = load_clients()
    max_id = max([c['id'] for c in db] or [0])

    added_clients = []
    for item in new_clients:
        max_id += 1
        name = item.get('name') or item.get('Имя клиента') or item.get('Kundenname') or f'Client {max_id}'
        address = item.get('address') or item.get('Полный адрес') or item.get('Adresse') or ''
        street = item.get('street') or item.get('Улица и дом') or item.get('Straße') or ''
        plz = str(item.get('plz') or item.get('Индекс (PLZ)') or item.get('PLZ') or '')
        city = item.get('city') or item.get('Город (Ort)') or item.get('Ort') or ''
        tour = item.get('tour') or item.get('Тур (Tag)') or item.get('Tour') or ''

        lat = item.get('lat') or item.get('Широта (Lat)')
        lng = item.get('lng') or item.get('Долгота (Lng)')

        if lat is not None and lng is not None:
            try:
                lat, lng = float(lat), float(lng)
            except ValueError:
                lat, lng = None, None

        if lat is None or lng is None:
            queries = []
            if street and plz and city:
                queries.append(f'{street}, {plz} {city}, Germany')
            if street and city:
                queries.append(f'{street}, {city}, Germany')
            if address:
                queries.append(f'{address}, Germany')
                queries.append(address)
            if plz and city:
                queries.append(f'{plz} {city}, Germany')

            for q in queries:
                try:
                    loc = geolocator.geocode(q, timeout=5)
                    if loc:
                        lat, lng = loc.latitude, loc.longitude
                        break
                except Exception:
                    pass

            if lat is None or lng is None:
                lat, lng = OFFICE_LOCATION['lat'], OFFICE_LOCATION['lng']

        c_obj = {
            'id': max_id,
            'name': name,
            'address': address or f'{plz} {city} {street}'.strip(),
            'tour': tour,
            'plz': plz,
            'city': city,
            'street': street,
            'lat': float(lat),
            'lng': float(lng)
        }
        db.append(c_obj)
        added_clients.append(c_obj)

    save_clients(db)
    return jsonify({'status': 'success', 'count': len(added_clients)})

@app.route('/api/clients/<int:client_id>', methods=['DELETE'])
def delete_client(client_id):
    db = load_clients()
    db = [c for c in db if c.get('id') != client_id]
    save_clients(db)
    return jsonify({'status': 'success'})

@app.route('/api/route/optimize', methods=['POST'])
def optimize_route():
    data = request.json
    client_ids = data.get('client_ids', [])
    start_id = data.get('start_id', 0)
    end_id = data.get('end_id', 0)
    
    db = {c['id']: c for c in load_clients()}
    
    selected_clients = []
    if start_id in db:
        selected_clients.append(db[start_id])
        
    for cid in client_ids:
        if cid in db and cid != start_id and cid != end_id:
            selected_clients.append(db[cid])
            
    if end_id in db and end_id != start_id:
        selected_clients.append(db[end_id])
    elif end_id == start_id and len(selected_clients) > 0:
        selected_clients.append(db[start_id])

    for c in selected_clients:
        if c.get('lat') is None or c.get('lng') is None:
            c['lat'] = OFFICE_LOCATION['lat']
            c['lng'] = OFFICE_LOCATION['lng']

    if len(selected_clients) < 2:
        return jsonify({'status': 'error', 'message': 'Bitte wählen Sie mindestens einen Kunden aus'})

    coords_str = ';'.join([f"{c['lng']},{c['lat']}" for c in selected_clients])
    osrm_url = f"https://router.project-osrm.org/trip/v1/driving/{coords_str}?source=first&destination=last&overview=full&geometries=geojson"
    
    try:
        res = requests.get(osrm_url, timeout=10)
        res_data = res.json()
        
        if res_data.get('code') == 'Ok' and 'trips' in res_data:
            trip = res_data['trips'][0]
            waypoints = res_data.get('waypoints', [])
            
            # Sort clients by the order visited in the trip (waypoint_index is order in trip)
            # waypoints array corresponds to selected_clients input indices.
            # waypoints[i]['waypoint_index'] tells us at which step in the trip selected_clients[i] is visited!
            ordered_clients = [None] * len(selected_clients)
            for input_idx, wp in enumerate(waypoints):
                trip_visit_step = wp['waypoint_index']
                ordered_clients[trip_visit_step] = selected_clients[input_idx]
                
            distance_km = round(trip['distance'] / 1000.0, 1)
            duration_min = round(trip['duration'] / 60.0)
            geometry = trip['geometry']
            
            route_id = data.get('route_id') or str(int(time.time()))
            route_title = data.get('route_title') or "Маршрут"
            
            result = {
                'status': 'success',
                'id': route_id,
                'title': route_title,
                'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
                'ordered_clients': ordered_clients,
                'distance_km': distance_km,
                'duration_min': duration_min,
                'geometry': geometry
            }
            
            save_route_to_db(result)
            return jsonify(result)
    except Exception as e:
        print(f'OSRM Trip API error: {e}')

    # Step 1: PLZ / City Geographical Clustering & 2-Opt Loop Uncrossing Algorithm
    real_clients = selected_clients[1:-1] if (len(selected_clients) > 2 and selected_clients[0]['id'] == selected_clients[-1]['id']) else selected_clients[1:]
    office_start = selected_clients[0]
    office_end = selected_clients[-1]

    def haversine_dist(c1, c2):
        return math.hypot(c1['lat'] - c2['lat'], c1['lng'] - c2['lng'])

    def total_route_dist(route):
        d = 0.0
        for i in range(len(route) - 1):
            d += haversine_dist(route[i], route[i+1])
        return d

    # Group clients by geographical area (PLZ prefix / City)
    clusters = {}
    for c in real_clients:
        cluster_key = (c.get('plz') or '')[:3] or (c.get('city') or 'default')
        if cluster_key not in clusters:
            clusters[cluster_key] = []
        clusters[cluster_key].append(c)

    # Order clusters by nearest distance from current location
    curr_point = office_start
    ordered_cluster_keys = []
    unvisited_keys = list(clusters.keys())

    while unvisited_keys:
        best_key = min(unvisited_keys, key=lambda k: min(haversine_dist(curr_point, client) for client in clusters[k]))
        ordered_cluster_keys.append(best_key)
        unvisited_keys.remove(best_key)
        # Move curr_point to the closest client in that cluster
        curr_point = min(clusters[best_key], key=lambda client: haversine_dist(curr_point, client))

    # Nearest neighbor within each cluster
    initial_route = [office_start]
    for k in ordered_cluster_keys:
        cluster_clients = clusters[k]
        curr = initial_route[-1]
        while cluster_clients:
            nearest = min(cluster_clients, key=lambda c: haversine_dist(curr, c))
            initial_route.append(nearest)
            cluster_clients.remove(nearest)
            curr = nearest

    if office_start['id'] == office_end['id']:
        initial_route.append(office_end)

    # Apply 2-Opt Algorithm to uncross any loops
    best_route = initial_route
    improved = True
    max_iterations = 100
    it = 0

    while improved and it < max_iterations:
        improved = False
        it += 1
        for i in range(1, len(best_route) - 2):
            for j in range(i + 1, len(best_route) - 1):
                if j - i == 1:
                    continue
                # Calculate current vs swapped edge distances
                d_curr = haversine_dist(best_route[i-1], best_route[i]) + haversine_dist(best_route[j], best_route[j+1])
                d_swap = haversine_dist(best_route[i-1], best_route[j]) + haversine_dist(best_route[i], best_route[j+1])
                if d_swap < d_curr - 1e-6:
                    # Reverse segment from i to j
                    best_route[i:j+1] = reversed(best_route[i:j+1])
                    improved = True

    ordered = best_route
    total_dist = total_route_dist(ordered) * 111.0

    geometry = {
        'type': 'LineString',
        'coordinates': [[c['lng'], c['lat']] for c in ordered]
    }
    
    route_id = data.get('route_id') or str(int(time.time()))
    route_title = data.get('route_title') or "Маршрут"
    
    result = {
        'status': 'success',
        'id': route_id,
        'title': route_title,
        'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
        'ordered_clients': ordered,
        'distance_km': round(total_dist, 1),
        'duration_min': round(total_dist * 1.5),
        'geometry': geometry
    }
    
    save_route_to_db(result)
    return jsonify(result)

@app.route('/api/route/recalculate', methods=['POST'])
def recalculate_route():
    data = request.json
    ordered_clients = data.get('ordered_clients', [])
    route_id = data.get('id')
    route_title = data.get('title')

    if len(ordered_clients) < 2:
        return jsonify({'status': 'error', 'message': 'Nicht genug Punkte'})

    coords_str = ';'.join([f"{c['lng']},{c['lat']}" for c in ordered_clients])
    osrm_url = f"https://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"

    try:
        res = requests.get(osrm_url, timeout=10)
        res_data = res.json()

        if res_data.get('code') == 'Ok' and 'routes' in res_data:
            route_info = res_data['routes'][0]
            distance_km = round(route_info['distance'] / 1000.0, 1)
            duration_min = round(route_info['duration'] / 60.0)
            geometry = route_info['geometry']

            result = {
                'status': 'success',
                'id': route_id,
                'title': route_title,
                'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
                'ordered_clients': ordered_clients,
                'distance_km': distance_km,
                'duration_min': duration_min,
                'geometry': geometry
            }
            save_route_to_db(result)
            return jsonify(result)
    except Exception as e:
        print(f'OSRM Route API error: {e}')

    # Fallback if OSRM call fails
    result = {
        'status': 'success',
        'id': route_id,
        'title': route_title,
        'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
        'ordered_clients': ordered_clients,
        'distance_km': data.get('distance_km', 0),
        'duration_min': data.get('duration_min', 0),
        'geometry': {'type': 'LineString', 'coordinates': [[c['lng'], c['lat']] for c in ordered_clients]}
    }
    save_route_to_db(result)
    return jsonify(result)

def load_routes_db():
    if os.path.exists('routes_db.json'):
        with open('routes_db.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_route_to_db(route_obj):
    routes = load_routes_db()
    # Replace existing or append
    routes = [r for r in routes if r.get('id') != route_obj['id']]
    routes.insert(0, route_obj)
    with open('routes_db.json', 'w', encoding='utf-8') as f:
        json.dump(routes, f, ensure_ascii=False, indent=2)

@app.route('/api/route/sync_saved', methods=['POST'])
def sync_saved_route():
    try:
        data = request.json
        save_route_to_db(data)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/routes', methods=['GET'])
def get_routes():
    routes = load_routes_db()
    return jsonify(routes)

@app.route('/api/routes/<route_id>', methods=['PUT'])
def update_route(route_id):
    route_obj = request.json
    save_route_to_db(route_obj)
    return jsonify({'status': 'success'})

@app.route('/api/routes/<route_id>', methods=['DELETE'])
def delete_route(route_id):
    routes = load_routes_db()
    routes = [r for r in routes if str(r.get('id')) != str(route_id)]
    with open('routes_db.json', 'w', encoding='utf-8') as f:
        json.dump(routes, f, ensure_ascii=False, indent=2)
    return jsonify({'status': 'success'})

@app.route('/api/route/saved', methods=['GET'])
def get_saved_route():
    routes = load_routes_db()
    if routes:
        return jsonify(routes[0])
    return jsonify({'status': 'none'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
