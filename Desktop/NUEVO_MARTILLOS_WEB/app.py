from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import math
import os
import urllib.request
import json
from urllib.parse import quote

app = Flask(__name__)
app.secret_key = 'martillosi_secret_key_2026'

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'martillosiruedas.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    cupo = db.Column(db.String(20), nullable=True)
    placa = db.Column(db.String(20), nullable=True)
    balance = db.Column(db.Float, default=15.0)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    origin_lat = db.Column(db.Float, nullable=False)
    origin_lng = db.Column(db.Float, nullable=False)
    dest_lat = db.Column(db.Float, nullable=False)
    dest_lng = db.Column(db.Float, nullable=False)
    driver_lat = db.Column(db.Float, nullable=True)
    driver_lng = db.Column(db.Float, nullable=True)
    distance_km = db.Column(db.Float, nullable=False)
    fare = db.Column(db.Float, nullable=False)
    commission = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='PENDIENTE')

with app.app_context():
    db.create_all()
    if not User.query.filter_by(phone='04120000000').first():
        admin = User(phone='04120000000', role='admin', name='Administrador General')
        admin.set_password('admin123')
        db.session.add(admin)

    if not User.query.filter_by(phone='04241112233').first():
        driver = User(phone='04241112233', role='driver', name='Carlos Mototaxi', cupo='01', placa='AB1C23', balance=20.0)
        driver.set_password('chofer123')
        db.session.add(driver)

    if not User.query.filter_by(phone='04140000000').first():
        client = User(phone='04140000000', role='client', name='María Pérez')
        client.set_password('pasajero123')
        db.session.add(client)

    db.session.commit()

def calculate_haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if user.role == 'admin':
        return redirect(url_for('admin_panel'))
    elif user.role == 'driver':
        return render_template('driver.html', user=user)
    return render_template('index.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form
        phone = data.get('phone')
        password = data.get('password')
        user = User.query.filter_by(phone=phone).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            print(f"DEBUG: Login exitoso para {user.name} ({user.role}), ID: {user.id}")
            return redirect(url_for('home'))
        return render_template('login.html', error='Número o contraseña incorrectos')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/search', methods=['GET'])
def api_search():
    query = request.args.get('q', '')
    if not query: return jsonify([])
    search_query = query + ", San Juan de los Morros, Guárico, Venezuela"
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={quote(search_query)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'MartillosiRuedasApp/2.0'})
    try:
        with urllib.request.urlopen(req) as resp:
            return jsonify(json.loads(resp.read().decode()))
    except:
        return jsonify([])

@app.route('/api/request_ride', methods=['POST'])
def request_ride():
    if 'user_id' not in session:
        print("DEBUG ERROR: /api/request_ride llamado sin sesión activa.")
        return jsonify({'error': 'No autorizado. Inicia sesión de nuevo.'}), 401
    
    data = request.get_json(silent=True) or request.form
    print(f"DEBUG: Solicitud de viaje recibida con datos: {data}")
    
    try:
        dist = calculate_haversine(float(data['orig_lat']), float(data['orig_lng']), float(data['dest_lat']), float(data['dest_lng']))
        fare = 1.00 if dist <= 3.0 else 2.00
        commission = fare * 0.09

        ride = Ride(
            client_id=session['user_id'],
            origin_lat=float(data['orig_lat']), origin_lng=float(data['orig_lng']),
            dest_lat=float(data['dest_lat']), dest_lng=float(data['dest_lng']),
            distance_km=round(dist, 2), fare=fare, commission=commission, status='PENDIENTE'
        )
        db.session.add(ride)
        db.session.commit()
        print(f"DEBUG: ¡Viaje #{ride.id} creado con éxito y guardado en PENDIENTE!")
        return jsonify({'success': True, 'ride_id': ride.id, 'fare': fare, 'distance': round(dist, 2)})
    except Exception as e:
        print(f"DEBUG EXCEPTION en request_ride: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/active_rides', methods=['GET'])
def get_active_rides():
    rides = Ride.query.filter_by(status='PENDIENTE').all()
    return jsonify([{
        'id': r.id, 'client_name': User.query.get(r.client_id).name,
        'orig_lat': r.origin_lat, 'orig_lng': r.origin_lng,
        'dest_lat': r.dest_lat, 'dest_lng': r.dest_lng,
        'distance': r.distance_km, 'fare': r.fare, 'commission': r.commission
    } for r in rides])

@app.route('/api/accept_ride', methods=['POST'])
def accept_ride():
    if 'user_id' not in session: return jsonify({'error': 'No autorizado'}), 401
    driver = User.query.get(session['user_id'])
    data = request.get_json(silent=True) or request.form
    ride = Ride.query.get(data.get('ride_id'))
    if not ride or ride.status != 'PENDIENTE':
        return jsonify({'success': False, 'message': 'La carrera ya no está disponible'})
    if driver.balance < ride.commission:
        return jsonify({'success': False, 'message': 'Saldo insuficiente para comisión'})
    driver.balance -= ride.commission
    ride.driver_id = driver.id
    ride.status = 'ACEPTADO'
    db.session.commit()
    print(f"DEBUG: Chofer {driver.name} aceptó el viaje #{ride.id}")
    return jsonify({'success': True, 'ride_id': ride.id, 'new_balance': round(driver.balance, 2)})

@app.route('/api/update_driver_location', methods=['POST'])
def update_driver_location():
    if 'user_id' not in session: return jsonify({'error': 'No autorizado'}), 401
    data = request.get_json(silent=True) or request.form
    ride = Ride.query.filter_by(driver_id=session['user_id']).filter(Ride.status.in_(['ACEPTADO', 'EN_SITIO', 'EN_CURSO'])).first()
    if ride:
        ride.driver_lat, ride.driver_lng = float(data['lat']), float(data['lng'])
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/api/update_ride_status', methods=['POST'])
def update_ride_status():
    if 'user_id' not in session: return jsonify({'error': 'No autorizado'}), 401
    data = request.get_json(silent=True) or request.form
    ride = Ride.query.get(data.get('ride_id'))
    if ride:
        ride.status = data.get('status')
        db.session.commit()
        return jsonify({'success': True, 'status': ride.status})
    return jsonify({'success': False})

@app.route('/api/ride_status/<int:ride_id>', methods=['GET'])
def get_ride_status(ride_id):
    ride = Ride.query.get(ride_id)
    if not ride: return jsonify({'error': 'No encontrada'}), 404
    driver = User.query.get(ride.driver_id) if ride.driver_id else None
    return jsonify({
        'status': ride.status, 'driver_name': driver.name if driver else None,
        'driver_phone': driver.phone if driver else None, 'placa': driver.placa if driver else None,
        'cupo': driver.cupo if driver else None, 'driver_lat': ride.driver_lat, 'driver_lng': ride.driver_lng
    })

@app.route('/admin')
def admin_panel():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if user.role != 'admin': return redirect(url_for('home'))
    drivers = User.query.filter_by(role='driver').all()
    total_comm = db.session.query(db.func.sum(Ride.commission)).filter(Ride.status != 'PENDIENTE').scalar() or 0.0
    return render_template('admin.html', drivers=drivers, total_commission=round(total_comm, 2))

@app.route('/api/recharge', methods=['POST'])
def recharge():
    if 'user_id' not in session: return jsonify({'error': 'No autorizado'}), 401
    data = request.get_json(silent=True) or request.form
    driver = User.query.get(data.get('driver_id'))
    if driver:
        driver.balance += float(data.get('amount', 5.0))
        db.session.commit()
        return jsonify({'success': True, 'new_balance': round(driver.balance, 2)})
    return jsonify({'success': False})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
