from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///martillosyruedas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

MAX_MOTOTAXIS = 50
COMISION_ADMIN = 0.09
TARIFA_CORTA = 1.00 
TARIFA_LARGA = 2.00
TASA_BCV = 36.50

class Chofer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    placa_moto = db.Column(db.String(20), unique=True, nullable=False)
    activo = db.Column(db.Boolean, default=False)

class Pasajero(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20), unique=True, nullable=False)

# Nuevo Modelo para registrar ganancias y comisiones
class Viaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    monto_bs = db.Column(db.Float, nullable=False)
    comision_bs = db.Column(db.Float, nullable=False)
    estado = db.Column(db.String(20), default='completado')

@app.route('/')
def index():
    return render_template('splash.html')

@app.route('/pasajero')
def pasajero():
    return render_template('pasajero.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/chofer')
def chofer():
    return render_template('chofer.html')

@app.route('/api/tarifas', methods=['GET'])
def obtener_tarifas():
    corta_bs = TARIFA_CORTA * TASA_BCV
    larga_bs = TARIFA_LARGA * TASA_BCV
    return jsonify({'corta_bs': round(corta_bs, 2), 'larga_bs': round(larga_bs, 2)})

@app.route('/api/admin_stats', methods=['GET'])
def admin_stats():
    # En un sistema real esto suma los registros de la DB. 
    # Aquí simulamos unos viajes iniciales para que veas el panel funcionando.
    viajes_simulados = 145
    ingreso_bruto_bs = viajes_simulados * (1.5 * TASA_BCV) # Promedio entre corta y larga
    comision_total_bs = ingreso_bruto_bs * COMISION_ADMIN
    
    return jsonify({
        'total_viajes': viajes_simulados,
        'ingreso_bruto_bs': round(ingreso_bruto_bs, 2),
        'comision_bs': round(comision_total_bs, 2),
        'choferes_activos': 12,
        'max_choferes': MAX_MOTOTAXIS
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
