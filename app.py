from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import math
import csv
import io

app = Flask(__name__)
app.secret_key = 'clave_secreta_super_segura_para_el_negocio'

def formatear_whatsapp(telefono):
    if not telefono:
        return ''
    num = ''.join(filter(str.isdigit, str(telefono)))
    if num.startswith('0'):
        num = '58' + num[1:]
    elif not num.startswith('58') and len(num) == 10:
        num = '58' + num
    return num

app.jinja_env.filters['wa_format'] = formatear_whatsapp

def obtener_conexion():
    conexion = sqlite3.connect('mototaxi.db')
    conexion.row_factory = sqlite3.Row
    return conexion

def inicializar_db():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            cedula TEXT UNIQUE NOT NULL,
            telefono TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL,
            estatus_chofer TEXT,
            placa_moto TEXT,
            modelo_moto TEXT,
            anio_moto TEXT,
            saldo_usd REAL DEFAULT 0.0,
            estado_cuenta TEXT DEFAULT 'activo'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS viajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pasajero_id INTEGER NOT NULL,
            chofer_id INTEGER,
            tarifa_usd REAL NOT NULL,
            comision_admin REAL NOT NULL,
            estado TEXT NOT NULL,
            FOREIGN KEY (pasajero_id) REFERENCES usuarios (id),
            FOREIGN KEY (chofer_id) REFERENCES usuarios (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recargas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chofer_id INTEGER NOT NULL,
            referencia TEXT NOT NULL,
            monto_usd REAL NOT NULL,
            estado TEXT DEFAULT 'pendiente',
            FOREIGN KEY (chofer_id) REFERENCES usuarios (id)
        )
    ''')

    cursor.execute("PRAGMA table_info(usuarios)")
    columnas = [col[1] for col in cursor.fetchall()]
    if 'estado_cuenta' not in columnas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN estado_cuenta TEXT DEFAULT 'activo'")

    conexion.commit()
    conexion.close()

inicializar_db()

def calcular_distancia_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        telefono = request.form.get('telefono', '').strip()
        password = request.form.get('password', '').strip()
        
        conexion = obtener_conexion()
        try:
            usuario = conexion.execute('SELECT * FROM usuarios WHERE telefono = ?', (telefono,)).fetchone()
            if usuario:
                es_valida = False
                pass_guardada = usuario['password']
                
                if pass_guardada.startswith('scrypt:') or pass_guardada.startswith('pbkdf2:'):
                    es_valida = check_password_hash(pass_guardada, password)
                else:
                    es_valida = (pass_guardada == password)
                    if es_valida:
                        nuevo_hash = generate_password_hash(password)
                        conexion.execute('UPDATE usuarios SET password = ? WHERE id = ?', (nuevo_hash, usuario['id']))
                        conexion.commit()

                if es_valida:
                    u_dict = dict(usuario)
                    if u_dict.get('rol') == 'chofer' and u_dict.get('estado_cuenta') == 'suspendido':
                        return "Su cuenta de chofer ha sido SUSPENDIDA por la administración."

                    session['usuario_id'] = usuario['id']
                    session['rol'] = usuario['rol']
                    
                    if usuario['rol'] == 'admin':
                        return redirect(url_for('panel_admin'))
                    elif usuario['rol'] == 'chofer':
                        return redirect(url_for('panel_chofer'))
                    else:
                        return redirect(url_for('panel_pasajero'))
            
            return "Datos incorrectos."
        finally:
            conexion.close()

    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        rol = request.form.get('rol', 'pasajero')
        nombre = request.form.get('nombre', '').strip()
        cedula = request.form.get('cedula', '').strip()
        telefono = request.form.get('telefono', '').strip()
        password = request.form.get('password', '').strip()
        placa = request.form.get('placa_moto', '').strip()
        modelo = request.form.get('modelo_moto', '').strip()
        anio = request.form.get('anio_moto', '').strip()
        
        password_hash = generate_password_hash(password)
        
        conexion = obtener_conexion()
        try:
            saldo_inicial = 0.0
            estatus_chofer = 'offline' if rol == 'chofer' else None
            cursor = conexion.cursor()
            cursor.execute('''INSERT INTO usuarios (nombre, cedula, telefono, password, rol, estatus_chofer, placa_moto, modelo_moto, anio_moto, saldo_usd, estado_cuenta)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'activo')''', 
                           (nombre, cedula, telefono, password_hash, rol, estatus_chofer, placa, modelo, anio, saldo_inicial))
            conexion.commit()
            session['usuario_id'] = cursor.lastrowid
            session['rol'] = rol
            return redirect(url_for('panel_chofer') if rol == 'chofer' else url_for('panel_pasajero'))
        except sqlite3.IntegrityError:
            return "El teléfono o cédula ya existen."
        finally:
            conexion.close()

    return render_template('registro.html')

@app.route('/admin', methods=['GET', 'POST'])
def panel_admin():
    if session.get('rol') != 'admin': return redirect(url_for('login'))
    conexion = obtener_conexion()
    try:
        stats = conexion.execute("SELECT COUNT(id) as total_carreras, COALESCE(SUM(tarifa_usd), 0) as volumen_total, COALESCE(SUM(comision_admin), 0) as tus_ganancias FROM viajes WHERE estado = 'finalizado'").fetchone()
        
        choferes = conexion.execute('''
            SELECT u.*, 
                   (SELECT COUNT(v.id) FROM viajes v WHERE v.chofer_id = u.id AND v.estado = 'finalizado') as carreras_completadas,
                   (SELECT COALESCE(SUM(v.tarifa_usd), 0) FROM viajes v WHERE v.chofer_id = u.id AND v.estado = 'finalizado') as total_generado
            FROM usuarios u 
            WHERE u.rol = 'chofer'
            ORDER BY u.id DESC
        ''').fetchall()
        
        recargas_pendientes = conexion.execute("SELECT r.*, u.nombre as chofer_nombre, u.telefono as chofer_tel FROM recargas r JOIN usuarios u ON r.chofer_id = u.id WHERE r.estado = 'pendiente'").fetchall()
        return render_template('admin.html', stats=stats, choferes=choferes, recargas=recargas_pendientes)
    finally:
        conexion.close()

@app.route('/admin/exportar-reporte')
def exportar_reporte():
    if session.get('rol') != 'admin': return redirect(url_for('login'))
    conexion = obtener_conexion()
    try:
        viajes = conexion.execute('''
            SELECT v.id, v.tarifa_usd, v.comision_admin, v.estado,
                   p.nombre as pasajero, c.nombre as chofer, c.placa_moto as placa
            FROM viajes v
            LEFT JOIN usuarios p ON v.pasajero_id = p.id
            LEFT JOIN usuarios c ON v.chofer_id = c.id
            ORDER BY v.id DESC
        ''').fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID Viaje', 'Pasajero', 'Chofer', 'Placa Moto', 'Monto Cobrado (USD)', 'Comision Admin 9% (USD)', 'Estado'])

        for v in viajes:
            writer.writerow([
                v['id'],
                v['pasajero'] or 'N/A',
                v['chofer'] or 'N/A',
                v['placa'] or 'N/A',
                f"{v['tarifa_usd']:.2f}",
                f"{v['comision_admin']:.2f}",
                v['estado'].upper()
            ])

        response = Response(output.getvalue(), mimetype="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=reporte_martillosi_ruedas.csv"
        return response
    finally:
        conexion.close()

@app.route('/admin/aprobar-recarga/<int:id_recarga>', methods=['POST'])
def aprobar_recarga(id_recarga):
    if session.get('rol') != 'admin': return redirect(url_for('login'))
    conexion = obtener_conexion()
    try:
        recarga = conexion.execute("SELECT * FROM recargas WHERE id = ? AND estado = 'pendiente'", (id_recarga,)).fetchone()
        if recarga:
            conexion.execute("UPDATE usuarios SET saldo_usd = saldo_usd + ? WHERE id = ?", (recarga['monto_usd'], recarga['chofer_id']))
            conexion.execute("UPDATE recargas SET estado = 'aprobado' WHERE id = ?", (id_recarga,))
            conexion.commit()
    finally:
        conexion.close()
    return redirect(url_for('panel_admin'))

@app.route('/admin/chofer/ajustar-saldo/<int:id_chofer>', methods=['POST'])
def admin_ajustar_saldo(id_chofer):
    if session.get('rol') != 'admin': return redirect(url_for('login'))
    
    try:
        monto = float(request.form.get('monto', 0.0))
    except ValueError:
        monto = 0.0

    operacion = request.form.get('operacion', 'sumar')
    
    if monto > 0:
        conexion = obtener_conexion()
        try:
            if operacion == 'sumar':
                conexion.execute("UPDATE usuarios SET saldo_usd = saldo_usd + ? WHERE id = ?", (monto, id_chofer))
            elif operacion == 'restar':
                conexion.execute("UPDATE usuarios SET saldo_usd = MAX(0, saldo_usd - ?) WHERE id = ?", (monto, id_chofer))
            conexion.commit()
        finally:
            conexion.close()

    return redirect(url_for('panel_admin'))

@app.route('/admin/chofer/toggle-estado/<int:id_chofer>', methods=['POST'])
def admin_toggle_estado(id_chofer):
    if session.get('rol') != 'admin': return redirect(url_for('login'))
    conexion = obtener_conexion()
    try:
        chofer = conexion.execute("SELECT estado_cuenta FROM usuarios WHERE id = ?", (id_chofer,)).fetchone()
        if chofer:
            estado_actual = dict(chofer).get('estado_cuenta', 'activo')
            nuevo_estado = 'suspendido' if estado_actual == 'activo' else 'activo'
            
            if nuevo_estado == 'suspendido':
                conexion.execute("UPDATE usuarios SET estado_cuenta = ?, estatus_chofer = 'offline' WHERE id = ?", (nuevo_estado, id_chofer))
            else:
                conexion.execute("UPDATE usuarios SET estado_cuenta = ? WHERE id = ?", (nuevo_estado, id_chofer))
            conexion.commit()
    finally:
        conexion.close()
    return redirect(url_for('panel_admin'))

@app.route('/chofer', methods=['GET', 'POST'])
def panel_chofer():
    if session.get('rol') != 'chofer': return redirect(url_for('login'))
    conexion = obtener_conexion()
    try:
        chofer = conexion.execute('SELECT * FROM usuarios WHERE id = ?', (session['usuario_id'],)).fetchone()
        
        if dict(chofer).get('estado_cuenta') == 'suspendido':
            session.clear()
            return "Tu cuenta ha sido suspendida por la administración."

        viaje_activo = conexion.execute('''
            SELECT v.*, p.nombre as pasajero_nombre, p.telefono as pasajero_tel 
            FROM viajes v 
            JOIN usuarios p ON v.pasajero_id = p.id 
            WHERE v.chofer_id = ? AND v.estado = 'aceptado'
        ''', (session['usuario_id'],)).fetchone()
        
        historial = conexion.execute('''
            SELECT v.*, p.nombre as pasajero_nombre 
            FROM viajes v 
            JOIN usuarios p ON v.pasajero_id = p.id 
            WHERE v.chofer_id = ? AND v.estado = 'finalizado'
            ORDER BY v.id DESC LIMIT 10
        ''', (session['usuario_id'],)).fetchall()

        return render_template('chofer.html', chofer=chofer, viaje_activo=viaje_activo, historial=historial)
    finally:
        conexion.close()

@app.route('/chofer/toggle', methods=['POST'])
def toggle_chofer():
    if session.get('rol') != 'chofer': return redirect(url_for('login'))
    conexion = obtener_conexion()
    try:
        chofer = conexion.execute('SELECT * FROM usuarios WHERE id = ?', (session['usuario_id'],)).fetchone()
        if dict(chofer).get('estado_cuenta') == 'suspendido':
            return "Tu cuenta está suspendida."
        if chofer['saldo_usd'] < 0.09:
            return "Saldo insuficiente."
        nuevo_estatus = 'online' if chofer['estatus_chofer'] == 'offline' else 'offline'
        conexion.execute('UPDATE usuarios SET estatus_chofer = ? WHERE id = ?', (nuevo_estatus, session['usuario_id']))
        conexion.commit()
        return redirect(url_for('panel_chofer'))
    finally:
        conexion.close()

@app.route('/api/calcular-tarifa', methods=['POST'])
def api_calcular_tarifa():
    data = request.json or {}
    lat_o = data.get('lat_origen', 0.0)
    lon_o = data.get('lon_origen', 0.0)
    lat_d = data.get('lat_destino', 0.0)
    lon_d = data.get('lon_destino', 0.0)
    
    distancia_km = calcular_distancia_km(lat_o, lon_o, lat_d, lon_d)
    tarifa = 1.00 if distancia_km <= 2.0 else 1.00 + ((distancia_km - 2.0) * 0.40)
    return jsonify({'distancia_km': round(distancia_km, 2), 'tarifa_usd': round(tarifa, 2), 'comision_admin': round(tarifa * 0.09, 2)})

@app.route('/api/carreras-pendientes')
def api_carreras_pendientes():
    if session.get('rol') != 'chofer': return jsonify([])
    conexion = obtener_conexion()
    try:
        carreras = conexion.execute("SELECT * FROM viajes WHERE estado = 'pendiente'").fetchall()
        return jsonify([dict(c) for c in carreras])
    finally:
        conexion.close()

@app.route('/api/aceptar-carrera/<int:id_viaje>', methods=['POST'])
def api_aceptar_carrera(id_viaje):
    if session.get('rol') != 'chofer': return jsonify({'exito': False, 'motivo': 'No autorizado'})
    conexion = obtener_conexion()
    try:
        chofer = conexion.execute('SELECT * FROM usuarios WHERE id = ?', (session['usuario_id'],)).fetchone()
        
        if dict(chofer).get('estado_cuenta') == 'suspendido':
            return jsonify({'exito': False, 'motivo': 'Cuenta suspendida'})

        viaje = conexion.execute("SELECT * FROM viajes WHERE id = ? AND estado = 'pendiente'", (id_viaje,)).fetchone()
        
        if not viaje: 
            return jsonify({'exito': False, 'motivo': 'Carrera tomada por otro'})
        if chofer['saldo_usd'] < viaje['comision_admin']: 
            return jsonify({'exito': False, 'motivo': 'Sin saldo'})
            
        conexion.execute("UPDATE usuarios SET saldo_usd = saldo_usd - ? WHERE id = ?", (viaje['comision_admin'], session['usuario_id']))
        conexion.execute("UPDATE viajes SET chofer_id = ?, estado = 'aceptado' WHERE id = ?", (session['usuario_id'], id_viaje))
        conexion.commit()
        return jsonify({'exito': True})
    finally:
        conexion.close()

@app.route('/chofer/finalizar-carrera/<int:id_viaje>', methods=['POST'])
def chofer_finalizar_carrera(id_viaje):
    if session.get('rol') != 'chofer': return redirect(url_for('login'))
    conexion = obtener_conexion()
    try:
        conexion.execute("UPDATE viajes SET estado = 'finalizado' WHERE id = ? AND chofer_id = ?", (id_viaje, session['usuario_id']))
        conexion.commit()
    finally:
        conexion.close()
    return redirect(url_for('panel_chofer'))

@app.route('/pasajero', methods=['GET', 'POST'])
def panel_pasajero():
    if session.get('rol') != 'pasajero': return redirect(url_for('login'))
    conexion = obtener_conexion()
    try:
        if request.method == 'POST':
            try:
                tarifa = float(request.form.get('tarifa', 1.0))
            except ValueError:
                tarifa = 1.0
            conexion.execute("INSERT INTO viajes (pasajero_id, tarifa_usd, comision_admin, estado) VALUES (?, ?, ?, 'pendiente')", (session['usuario_id'], tarifa, tarifa * 0.09))
            conexion.commit()
            return redirect(url_for('panel_pasajero'))
            
        viaje_activo = conexion.execute("SELECT v.*, u.nombre as chofer_nombre, u.placa_moto as chofer_placa, u.telefono as chofer_tel FROM viajes v LEFT JOIN usuarios u ON v.chofer_id = u.id WHERE v.pasajero_id = ? AND v.estado IN ('pendiente', 'aceptado')", (session['usuario_id'],)).fetchone()
        historial = conexion.execute("SELECT v.*, u.nombre as chofer_nombre, u.placa_moto as chofer_placa FROM viajes v LEFT JOIN usuarios u ON v.chofer_id = u.id WHERE v.pasajero_id = ? AND v.estado = 'finalizado' ORDER BY v.id DESC LIMIT 10", (session['usuario_id'],)).fetchall()

        return render_template('pasajero.html', viaje=viaje_activo, historial=historial)
    finally:
        conexion.close()

@app.route('/pasajero/cancelar/<int:id_viaje>', methods=['POST'])
def pasajero_cancelar(id_viaje):
    if session.get('rol') != 'pasajero': return redirect(url_for('login'))
    conexion = obtener_conexion()
    try:
        conexion.execute("UPDATE viajes SET estado = 'cancelado' WHERE id = ? AND pasajero_id = ? AND estado = 'pendiente'", (id_viaje, session['usuario_id']))
        conexion.commit()
    finally:
        conexion.close()
    return redirect(url_for('panel_pasajero'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
