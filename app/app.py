import sqlite3
from flask import Flask, render_template, request, jsonify
import math

app = Flask(__name__)
DB_NAME = "mototaxi.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT, role TEXT, phone TEXT, balance_bs REAL DEFAULT 0.0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS rides (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    passenger_id INTEGER, driver_id INTEGER,
                    origin TEXT, destination TEXT, distance_km REAL,
                    price_bs REAL, admin_commission_bs REAL, status TEXT)''')
    conn.commit()
    conn.close()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@app.route('/')
def passenger_panel():
    return render_template('passenger.html')

@app.route('/driver')
def driver_panel():
    return render_template('driver.html')

@app.route('/admin')
def admin_panel():
    return render_template('admin.html')

@app.route('/api/calculate_fare', methods=['POST'])
def calculate_fare():
    data = request.json
    lat1, lon1 = data['lat1'], data['lon1']
    lat2, lon2 = data['lat2'], data['lon2']
    
    km = round(haversine(lat1, lon1, lat2, lon2), 2)
    
    tarifa_base_bs = 60.0
    costo_por_km_bs = 25.0
    
    total_bs = round(tarifa_base_bs + (km * costo_por_km_bs), 2)
    comision_admin_bs = round(total_bs * 0.09, 2)
    monto_chofer_bs = round(total_bs - comision_admin_bs, 2)
    
    return jsonify({
        "distance_km": km,
        "total_bs": total_bs,
        "admin_commission_bs": comision_admin_bs,
        "driver_earnings_bs": monto_chofer_bs
    })

if __name__ == '__main__':
    init_db()
    print("Servidor listo en http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)