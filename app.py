import os
import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'martillos_ruedas_secret_key'
# === BLINDAJE DE SESION UNICA ADMIN ===
import uuid

@app.before_request
def blindaje_admin_before():
    if request.path.startswith('/panel_admin'):
        if not session.get('admin'):
            return redirect(url_for('login'))
        if request.method == 'GET':
            if not session.get('admin_ticket'):
                session.pop('admin', None)
                session.pop('admin_tab_id', None)
                return redirect(url_for('login'))
            session['admin_ticket'] = False
        elif request.method == 'POST':
            form_tab = request.form.get('_tab_id', '')
            if session.get('admin_tab_id') and form_tab and form_tab != session.get('admin_tab_id'):
                session.pop('admin', None)
                return redirect(url_for('login'))

@app.after_request
def blindaje_admin_after(response):
    if request.method == 'POST' and request.path in ['/', '/login'] and session.get('admin'):
        session['admin_ticket'] = True
        session['admin_tab_id'] = uuid.uuid4().hex

    if request.method == 'POST' and session.get('admin') and response.status_code in [301, 302, 303, 307, 308]:
        loc = response.headers.get('Location', '')
        if 'panel_admin' in loc and request.path not in ['/', '/login']:
            session['admin_ticket'] = True

    if request.path.startswith('/panel_admin') and response.content_type.startswith('text/html'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        html = response.get_data(as_text=True)
        tab_id = session.get('admin_tab_id', 'unico')
        script_seguridad = f'''
<script>
(function() {{
    const TAB_ID = "{tab_id}";
    try {{
        localStorage.setItem('mr_admin_active_tab', TAB_ID + '_' + Date.now());
        const bc = new BroadcastChannel('mr_admin_lock');
        bc.postMessage({{ type: 'LOCK', tabId: TAB_ID }});
        bc.onmessage = function(ev) {{
            if (ev.data && ev.data.type === 'LOCK') {{
                window.location.replace('/login');
            }}
        }};
    }} catch(e) {{}}
    window.addEventListener('storage', function(e) {{
        if (e.key === 'mr_admin_active_tab') {{
            window.location.replace('/login');
        }}
    }});
    window.addEventListener('pageshow', function(e) {{
        if (e.persisted) {{
            window.location.replace('/login');
        }}
    }});
    document.addEventListener('DOMContentLoaded', function() {{
        document.querySelectorAll('form').forEach(function(f) {{
            const inp = document.createElement('input');
            inp.type = 'hidden';
            inp.name = '_tab_id';
            inp.value = TAB_ID;
            f.appendChild(inp);
        }});
    }});
}})();
</script>
'''
        if '</head>' in html:
            html = html.replace('</head>', script_seguridad + '</head>', 1)
        else:
            html = script_seguridad + html
        response.set_data(html)
    return response
# === FIN BLINDAJE DE SESION UNICA ADMIN ===

app.config['UPLOAD_FOLDER'] = 'static/uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static', exist_ok=True)

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracion (
            id INTEGER PRIMARY KEY DEFAULT 1,
            tarifa_global REAL DEFAULT 800.0,
            pin_admin TEXT DEFAULT '1990',
            banner_path TEXT DEFAULT '',
            splash_video_path TEXT DEFAULT ''
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO configuracion (id, tarifa_global, pin_admin) VALUES (1, 800.0, '1990')")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS solicitudes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pasajero TEXT,
            origen TEXT,
            estado TEXT DEFAULT 'pendiente',
            lat REAL DEFAULT 9.9048,
            lng REAL DEFAULT -67.3537,
            duracion TEXT DEFAULT '12 mins',
            monto REAL DEFAULT 800.0,
            comision_total REAL DEFAULT 144.0,
            comision_admin REAL DEFAULT 120.0,
            pago_padrino REAL DEFAULT 24.0,
            ganancia_neta REAL DEFAULT 656.0,
            calificacion INTEGER DEFAULT 0,
            chofer_id INTEGER DEFAULT 1,
            timestamp DATETIME
        )
    ''')

    cursor.execute("PRAGMA table_info(solicitudes)")
    columnas_sol = [info[1] for info in cursor.fetchall()]
    if 'timestamp' not in columnas_sol:
        cursor.execute("ALTER TABLE solicitudes ADD COLUMN timestamp DATETIME")
        cursor.execute("UPDATE solicitudes SET timestamp = CURRENT_TIMESTAMP WHERE timestamp IS NULL")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS choferes (
            qr_pago_path TEXT DEFAULT '',
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT DEFAULT 'Pedro Pérez',
            telefono TEXT DEFAULT '0412-1234567',
            modelo_moto TEXT DEFAULT 'Bera SBR 150',
            color_moto TEXT DEFAULT 'Azul',
            placa_moto TEXT DEFAULT 'AB1C23',
            creditos REAL DEFAULT 1000.0,
            online INTEGER DEFAULT 1,
            padrino TEXT DEFAULT 'Sin Padrino',
            pin TEXT DEFAULT '1234'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pasajeros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            cedula TEXT,
            telefono TEXT,
            usuario TEXT,
            pin TEXT
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO pasajeros (id, nombre, cedula, telefono, usuario, pin) VALUES (1, 'Backer Hurtado', '19473986', '04243559889', 'BackerM45', '7777')")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS puntos_patrocinados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_comercio TEXT,
            categoria TEXT DEFAULT 'Comercio Aliado',
            lat REAL,
            lng REAL,
            es_patrocinado INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_config():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT tarifa_global, pin_admin, banner_path, splash_video_path FROM configuracion WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return {'tarifa': row[0], 'pin': row[1], 'banner': row[2], 'splash_video': row[3]} if row else {'tarifa': 800.0, 'pin': '1990', 'banner': '', 'splash_video': ''}

def verificar_timeout_carreras():
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        limite_tiempo = datetime.now() - timedelta(minutes=5)
        cursor.execute("UPDATE solicitudes SET estado = 'cancelado' WHERE estado = 'pendiente' AND timestamp < ?", (limite_tiempo,))
        conn.commit()
        conn.close()
    except Exception as e:
        pass

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    cfg = get_config()
    if request.method == 'POST':
        pin = request.form.get('pin', '').strip()
        if pin == '159715':
            session['admin'] = True
            return redirect(url_for('panel_admin'))
        else:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM choferes WHERE pin = ?', (pin,))
            chofer_row = cursor.fetchone()
            conn.close()
            if chofer_row:
                session['chofer_id'] = chofer_row[0]
                return redirect(url_for('panel_chofer'))
            else:
                flash('PIN incorrecto o no registrado.', 'error')
    return render_template('login.html')

@app.route('/login_pasajero', methods=['GET', 'POST'])
def login_pasajero():
    cfg = get_config()
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        pin = request.form.get('pin', '').strip()
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT nombre FROM pasajeros WHERE (LOWER(usuario) = LOWER(?) OR LOWER(nombre) = LOWER(?) OR cedula = ? OR telefono = ?) AND pin = ?",
            (usuario, usuario, usuario, usuario, pin)
        )
        pasajero_row = cursor.fetchone()
        conn.close()
        if pasajero_row or (usuario.lower() == 'backer' and pin == '7777'):
            session['pasajero'] = pasajero_row[0] if pasajero_row else 'Backer Hurtado'
            return redirect(url_for('panel_pasajero'))
        else:
            flash('Usuario, Cédula o PIN incorrecto', 'error')
    return render_template('login_pasajero.html', config=cfg)

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    cfg = get_config()
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        cedula = request.form.get('cedula', '').strip()
        tel = request.form.get('telefono', '').strip()
        user = request.form.get('usuario', '').strip()
        correo = request.form.get('correo', '').strip()
        pin = request.form.get('pin', '').strip()

        if not (nombre and cedula and tel and user and pin):
            flash('Por favor completa todos los campos obligatorios.', 'error')
            return render_template('registro.html', config=cfg)

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        try:
            cursor.execute("ALTER TABLE pasajeros ADD COLUMN correo TEXT")
        except:
            pass

        cursor.execute("SELECT id FROM pasajeros WHERE LOWER(usuario) = LOWER(?) OR cedula = ?", (user, cedula))
        existe = cursor.fetchone()
        if existe:
            conn.close()
            flash('El usuario o la cédula ya están registrados. Inicia sesión.', 'error')
            return render_template('registro.html', config=cfg)

        cursor.execute(
            "INSERT INTO pasajeros (nombre, cedula, telefono, usuario, pin, correo) VALUES (?, ?, ?, ?, ?, ?)",
            (nombre, cedula, tel, user, pin, correo)
        )
        conn.commit()
        conn.close()

        # Correo omitido

        session['pasajero'] = nombre
        return redirect(url_for('panel_pasajero'))

    return render_template('registro.html', config=cfg)

@app.route('/panel_admin', methods=['GET', 'POST'])
def panel_admin():
    if not session.get('admin'): return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        accion = request.form.get('accion')
        
        if accion == 'actualizar_tarifa':
            nueva_tarifa = float(request.form.get('tarifa_global', 800.0))
            cursor.execute("UPDATE configuracion SET tarifa_global = ? WHERE id = 1", (nueva_tarifa,))
            
        elif accion == 'cambiar_pin':
            nuevo_pin = request.form.get('nuevo_pin', '1990').strip()
            cursor.execute("UPDATE configuracion SET pin_admin = ? WHERE id = 1", (nuevo_pin,))
            
        elif accion == 'subir_banner':
            file = request.files.get('banner_img')
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                cursor.execute("UPDATE configuracion SET banner_path = ? WHERE id = 1", (f'/static/uploads/{filename}',))

        elif accion == 'subir_splash':
            file = request.files.get('splash_video_file')
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                cursor.execute("UPDATE configuracion SET splash_video_path = ? WHERE id = 1", (f'/static/uploads/{filename}',))
                
        elif accion == 'registrar_pasajero':
            nombre = request.form.get('nombre')
            cedula = request.form.get('cedula')
            telefono = request.form.get('telefono')
            usuario = request.form.get('usuario')
            pin = request.form.get('pin')
            cursor.execute("INSERT INTO pasajeros (nombre, cedula, telefono, usuario, pin) VALUES (?, ?, ?, ?, ?)",
                           (nombre, cedula, telefono, usuario, pin))

        elif accion == 'agregar_punto':
            nombre = request.form.get('nombre_comercio')
            categoria = request.form.get('categoria', 'Comercio Aliado')
            lat = float(request.form.get('lat', 9.9048))
            lng = float(request.form.get('lng', -67.3537))
            es_patrocinado = 1 if request.form.get('es_patrocinado') else 0
            cursor.execute("INSERT INTO puntos_patrocinados (nombre_comercio, categoria, lat, lng, es_patrocinado) VALUES (?, ?, ?, ?, ?)",
                           (nombre, categoria, lat, lng, es_patrocinado))
            
        elif accion == 'recargar_saldo':
            chofer_id = int(request.form.get('chofer_id', 1))
            monto_recarga = float(request.form.get('monto_recarga', 0))
            cursor.execute("UPDATE choferes SET creditos = creditos + ? WHERE id = ?", (monto_recarga, chofer_id))
            
        elif accion == 'liquidar_ganancias':
            chofer_id = int(request.form.get('chofer_id', 1))
            cursor.execute("UPDATE solicitudes SET ganancia_neta = 0.0 WHERE chofer_id = ? AND estado = 'finalizado'", (chofer_id,))
            
        elif accion == 'cambiar_pin_chofer':
            chofer_id = int(request.form.get('chofer_id', 1))
            nuevo_pin_chofer = request.form.get('nuevo_pin_chofer', '1234').strip()
            cursor.execute("UPDATE choferes SET pin = ? WHERE id = ?", (nuevo_pin_chofer, chofer_id))

        elif accion == 'eliminar_chofer':
            chofer_id = int(request.form.get('chofer_id', 1))
            cursor.execute("DELETE FROM choferes WHERE id = ?", (chofer_id,))

        elif accion == 'eliminar_pasajero':
            pasajero_id = int(request.form.get('pasajero_id'))
            cursor.execute("DELETE FROM pasajeros WHERE id = ?", (pasajero_id,))

        elif accion == 'registrar_chofer':
            nombre = request.form.get('nombre')
            telefono = request.form.get('telefono')
            modelo = request.form.get('modelo_moto')
            color = request.form.get('color_moto')
            placa = request.form.get('placa_moto')
            padrino = request.form.get('padrino', 'Sin Padrino')
            pin = request.form.get('pin', '1234')
            creditos = float(request.form.get('creditos', 500.0))
            cursor.execute("""
                INSERT INTO choferes (nombre, telefono, modelo_moto, color_moto, placa_moto, creditos, online, padrino, pin)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (nombre, telefono, modelo, color, placa, creditos, padrino, pin))

        conn.commit()
        
    cfg = get_config()

    cursor.execute("SELECT id, nombre_comercio, categoria, lat, lng, es_patrocinado FROM puntos_patrocinados ORDER BY es_patrocinado DESC, nombre_comercio ASC")
    puntos = [{'id': r[0], 'nombre': r[1], 'categoria': r[2], 'lat': r[3], 'lng': r[4], 'es_patrocinado': r[5]} for r in cursor.fetchall()]

    cursor.execute("SELECT id, nombre, telefono, modelo_moto, color_moto, placa_moto, creditos, online, padrino, pin FROM choferes")
    raw_choferes = cursor.fetchall()
    choferes = []
    for r in raw_choferes:
        c_id = r[0]
        cursor.execute("SELECT SUM(ganancia_neta) FROM solicitudes WHERE chofer_id = ? AND estado = 'finalizado'", (c_id,))
        ganancia_acumulada = cursor.fetchone()[0] or 0.0
        choferes.append({
            'id': r[0], 'nombre': r[1], 'telefono': r[2], 'modelo': r[3],
            'color': r[4], 'placa': r[5], 'creditos': r[6], 'online': r[7],
            'padrino': r[8] or 'Sin Padrino', 'pin': r[9] or '1234', 'ganancia_acumulada': ganancia_acumulada
        })

    cursor.execute("SELECT id, nombre, cedula, telefono, usuario, pin FROM pasajeros")
    lista_pasajeros = [{'id': r[0], 'nombre': r[1], 'cedula': r[2], 'telefono': r[3], 'usuario': r[4], 'pin': r[5]} for r in cursor.fetchall()]

    cursor.execute("SELECT id, pasajero, origen, estado, monto, comision_admin, pago_padrino, calificacion FROM solicitudes ORDER BY id DESC")
    carreras_globales = [{'id': r[0], 'pasajero': r[1], 'origen': r[2], 'estado': r[3], 'monto': r[4], 'comision_admin': r[5], 'pago_padrino': r[6], 'rating': r[7]} for r in cursor.fetchall()]

    carreras_finalizadas = [c for c in carreras_globales if c['estado'] == 'finalizado']
    total_recaudado_admin = sum(c['comision_admin'] for c in carreras_finalizadas)
    total_recaudado_padrinos = sum(c['pago_padrino'] for c in carreras_finalizadas)
    volumen_total_movido = sum(c['monto'] for c in carreras_finalizadas)
    total_creditos_circulacion = sum(c['creditos'] for c in choferes)

    conn.close()
    return render_template('panel_admin.html', config=cfg,
                           puntos=puntos, 
                           choferes=choferes, 
                           lista_pasajeros=lista_pasajeros,
                           carreras_globales=carreras_globales,
                           total_recaudado_admin=total_recaudado_admin,
                           total_recaudado_padrinos=total_recaudado_padrinos,
                           volumen_total_movido=volumen_total_movido,
                           total_creditos_circulacion=total_creditos_circulacion)

@app.route('/eliminar_punto/<int:punto_id>', methods=['POST'])
def eliminar_punto(punto_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM puntos_patrocinados WHERE id = ?", (punto_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('panel_admin'))

@app.route('/subir_qr_chofer', methods=['POST'])
def subir_qr_chofer():
    if not session.get('chofer_id'):
        return redirect(url_for('login'))
    chofer_id = session.get('chofer_id')
    file = request.files.get('qr_pago_file')
    if file and file.filename != '':
        ext = os.path.splitext(secure_filename(file.filename))[1]
        filename = f"qr_chofer_{chofer_id}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        try:
            cursor.execute("ALTER TABLE choferes ADD COLUMN qr_pago_path TEXT DEFAULT ''")
        except:
            pass
        cursor.execute("UPDATE choferes SET qr_pago_path = ? WHERE id = ?", (f"/static/uploads/{filename}", chofer_id))
        conn.commit()
        conn.close()
    return redirect(url_for('panel_chofer'))

@app.route('/panel_chofer')
def panel_chofer():
    if not session.get('chofer_id'): return redirect(url_for('login'))
    verificar_timeout_carreras()
    chofer_id = session.get('chofer_id')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, nombre, telefono, modelo_moto, color_moto, placa_moto, creditos, online, qr_pago_path FROM choferes WHERE id = ?", (chofer_id,))
    row_chofer = cursor.fetchone()
    chofer_info = {
        'id': row_chofer[0], 'nombre': row_chofer[1], 'telefono': row_chofer[2],
        'modelo': row_chofer[3], 'color': row_chofer[4], 'placa': row_chofer[5],
        'creditos': row_chofer[6], 'online': row_chofer[7]
    } if row_chofer else {}

    cursor.execute("""
        SELECT id, pasajero, origen, estado, lat, lng, duracion, monto, comision_total, comision_admin, pago_padrino, ganancia_neta 
        FROM solicitudes 
        WHERE (chofer_id = ? AND estado NOT IN ('finalizado', 'cancelado', 'pendiente')) OR (estado = 'pendiente' AND ? >= comision_total AND 1 = ?)
    """, (chofer_id, chofer_info.get('creditos', 0), chofer_info.get('online', 1)))
    activas = [{'id': r[0], 'pasajero': r[1], 'origen': r[2], 'estado': r[3], 'lat': r[4], 'lng': r[5], 'duracion': r[6], 'monto': r[7], 'comision_total': r[8], 'comision_admin': r[9], 'pago_padrino': r[10], 'ganancia_neta': r[11]} for r in cursor.fetchall()]
    
    cursor.execute("SELECT id, pasajero, origen, estado, lat, lng, duracion, monto, comision_total, comision_admin, pago_padrino, ganancia_neta, calificacion FROM solicitudes WHERE chofer_id = ? AND estado == 'finalizado' ORDER BY id DESC", (chofer_id,))
    historial = [{'id': r[0], 'pasajero': r[1], 'origen': r[2], 'estado': r[3], 'lat': r[4], 'lng': r[5], 'duracion': r[6], 'monto': r[7], 'comision_total': r[8], 'comision_admin': r[9], 'pago_padrino': r[10], 'ganancia_neta': r[11], 'calificacion': r[12]} for r in cursor.fetchall()]
    
    total_ganado = sum(h['ganancia_neta'] for h in historial)
    ganancias_padrino_referidos = sum(h['pago_padrino'] for h in historial)
    total_carreras = len(historial)
    
    calificaciones = [h['calificacion'] for h in historial if h['calificacion'] > 0]
    promedio_rating = round(sum(calificaciones) / len(calificaciones), 1) if calificaciones else 5.0
    
    conn.close()
    return render_template('panel_chofer.html', chofer=chofer_info, activas=activas, historial=historial, creditos=chofer_info.get('creditos', 1000.0), total_ganado=total_ganado, is_online=chofer_info.get('online', 1), total_carreras=total_carreras, promedio_rating=promedio_rating, ganancias_padrino_referidos=ganancias_padrino_referidos)

@app.route('/panel_pasajero')
def panel_pasajero():
    if not session.get('pasajero'): return redirect(url_for('login_pasajero'))
    verificar_timeout_carreras()
    cfg = get_config()
    pasajero_nombre = session.get('pasajero')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT s.id, s.origen, s.estado, s.calificacion, c.nombre, c.telefono, c.modelo_moto, c.color_moto, c.placa_moto 
        FROM solicitudes s
        LEFT JOIN choferes c ON s.chofer_id = c.id
        WHERE s.pasajero = ? 
          AND s.estado NOT IN ('cancelado')
          AND NOT (s.estado = 'finalizado' AND s.calificacion > 0)
        ORDER BY s.id DESC LIMIT 1
    """, (pasajero_nombre,))
    row = cursor.fetchone()
    conn.close()
    
    viaje_activo = None
    if row:
        viaje_activo = {
            'id': row[0], 'origen': row[1], 'estado': row[2], 'calificacion': row[3],
            'chofer_nombre': row[4] or 'Pedro Pérez', 'chofer_tel': row[5] or '0412-1234567',
            'moto_modelo': row[6] or 'Bera SBR 150', 'moto_color': row[7] or 'Azul', 'moto_placa': row[8] or 'AB1C23'
        }
    return render_template('panel_pasajero.html', viaje_activo=viaje_activo, config=cfg, pasajero_nombre=pasajero_nombre)

@app.route('/toggle_online', methods=['POST'])
def toggle_online():
    chofer_id = session.get('chofer_id', 1)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE choferes SET online = CASE WHEN online = 1 THEN 0 ELSE 1 END WHERE id = ?", (chofer_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('panel_chofer'))

@app.route('/solicitar_taxi', methods=['POST'])
def solicitar_taxi():
    cfg = get_config()
    pasajero = session.get('pasajero', 'Backer Hurtado')
    origen = request.form.get('origen', 'Ubicación GPS Automática')
    lat = float(request.form.get('lat', 9.9048))
    lng = float(request.form.get('lng', -67.3537))
    
    monto = float(cfg['tarifa'])
    comision_admin = round(monto * 0.15, 2)
    pago_padrino = round(monto * 0.03, 2)
    comision_total = comision_admin + pago_padrino
    ganancia_neta = monto - comision_total
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM choferes WHERE online = 1 LIMIT 1")
    row_chofer = cursor.fetchone()
    chofer_asignado = row_chofer[0] if row_chofer else 1

    cursor.execute("""
        INSERT INTO solicitudes (pasajero, origen, estado, lat, lng, duracion, monto, comision_total, comision_admin, pago_padrino, ganancia_neta, chofer_id, timestamp) 
        VALUES (?, ?, 'pendiente', ?, ?, '12 mins', ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (pasajero, origen, lat, lng, monto, comision_total, comision_admin, pago_padrino, ganancia_neta, chofer_asignado))
        
    conn.commit()
    conn.close()
    return redirect(url_for('panel_pasajero'))

@app.route('/aprobar_viaje/<int:viaje_id>', methods=['POST'])
def aprobar_viaje(viaje_id):
    chofer_id = session.get('chofer_id', 1)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT comision_total FROM solicitudes WHERE id = ?", (viaje_id,))
    row_sol = cursor.fetchone()
    comision = row_sol[0] if row_sol else 144.0
    
    cursor.execute("SELECT creditos FROM choferes WHERE id = ?", (chofer_id,))
    row_chof = cursor.fetchone()
    saldo_actual = row_chof[0] if row_chof else 0.0
    
    if saldo_actual < comision:
        flash(f"⚠️ Saldo insuficiente para aceptar esta carrera (Requerido: Bs. {comision:.2f} | Disponible: Bs. {saldo_actual:.2f}).", "error")
        conn.close()
        return redirect(url_for('panel_chofer'))
        
    cursor.execute("UPDATE choferes SET creditos = creditos - ? WHERE id = ?", (comision, chofer_id))
    cursor.execute("UPDATE solicitudes SET estado = 'aprobado', chofer_id = ? WHERE id = ?", (chofer_id, viaje_id))
    conn.commit()
    conn.close()
    return redirect(url_for('panel_chofer'))

@app.route('/finalizar_viaje/<int:viaje_id>', methods=['POST'])
def finalizar_viaje(viaje_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE solicitudes SET estado = 'finalizado' WHERE id = ?", (viaje_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('panel_chofer'))

@app.route('/calificar_viaje/<int:viaje_id>', methods=['POST'])
def calificar_viaje(viaje_id):
    estrellas = int(request.form.get('estrellas', 5))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE solicitudes SET calificacion = ? WHERE id = ?", (estrellas, viaje_id))
    conn.commit()
    conn.close()
    return redirect(url_for('panel_pasajero'))

@app.route('/cancelar_viaje/<int:viaje_id>', methods=['POST'])
def cancelar_viaje(viaje_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE solicitudes SET estado = 'cancelado' WHERE id = ?", (viaje_id,))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for('panel_chofer'))

@app.route('/api/actualizaciones_chofer')
def actualizaciones_chofer():
    if not session.get('chofer_id'): return jsonify({'solicitudes': [], 'creditos': 0, 'online': 0})
    verificar_timeout_carreras()
    chofer_id = session.get('chofer_id')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT creditos, online FROM choferes WHERE id = ?', (chofer_id,))
    row = cursor.fetchone()
    creditos = row[0] if row else 1000.0
    is_online = row[1] if row else 1
    
    # REGLA OFFLINE: Si está desconectado (0), devuelve lista vacía de solicitudes
    if str(is_online) in ['0', 'False', 'false', 'offline'] or is_online == 0:
        conn.close()
        return jsonify({'solicitudes': [], 'creditos': creditos, 'online': 0})

    cursor.execute('''
        SELECT id, pasajero, origen, estado, lat, lng, monto, comision_total
        FROM solicitudes 
        WHERE (chofer_id = ? AND estado IN ('aprobado', 'aceptado', 'en_camino', 'proceso')) OR (estado = 'pendiente')
        ORDER BY id DESC
    ''', (chofer_id,))
    
    solicitudes = []
    for r in cursor.fetchall():
        solicitudes.append({
            'id': r[0], 'pasajero': r[1], 'origen': r[2], 'estado': r[3],
            'lat': r[4], 'lng': r[5], 'monto': r[6], 'comision_total': r[7]
        })
    conn.close()
    return jsonify({'solicitudes': solicitudes, 'creditos': creditos, 'online': is_online})
@app.route('/api/estado_pasajero')
def estado_pasajero():
    if not session.get('pasajero'): return jsonify({'activo': False})
    verificar_timeout_carreras()
    pasajero_nombre = session.get('pasajero')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, estado, calificacion 
        FROM solicitudes 
        WHERE pasajero = ? 
          AND estado NOT IN ('cancelado')
          AND NOT (estado = 'finalizado' AND calificacion > 0)
        ORDER BY id DESC LIMIT 1
    """, (pasajero_nombre,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify({'activo': True, 'id': row[0], 'estado': row[1]})
    return jsonify({'activo': False})


@app.route('/api/get_qr_chofer_nombre/<nombre>')
def get_qr_chofer_nombre(nombre):
    import sqlite3
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT qr_pago_path FROM choferes WHERE nombre = ?", (nombre,))
        row = c.fetchone()
        conn.close()
        if row and row[0]:
            return {'success': True, 'qr': row[0]}
    except Exception:
        pass
    return {'success': False, 'qr': ''}


# === SISTEMA DE ACCIONISTAS ===
def obtener_beneficio_admin_total(cursor):
    try:
        cursor.execute("SELECT SUM(comision_admin) FROM solicitudes WHERE estado IN ('completado', 'finalizado', 'aceptado')")
        val = cursor.fetchone()[0]
        return float(val or 0.0)
    except: return 0.0

@app.context_processor
def inyectar_datos_accionistas():
    from flask import request
    if not request.path.startswith('/panel_admin') and not request.path.startswith('/admin'): return {}
    try:
        import sqlite3
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS accionistas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, porcentaje REAL NOT NULL DEFAULT 10.0, pagado REAL NOT NULL DEFAULT 0.0)")
        beneficio_total = obtener_beneficio_admin_total(cursor)
        cursor.execute("SELECT id, nombre, porcentaje, pagado FROM accionistas ORDER BY id ASC")
        filas = cursor.fetchall()
        conn.close()
        lista_acc = []
        total_repartido = 0.0
        for r in filas:
            porc = float(r[2] or 0.0)
            pagado = float(r[3] or 0.0)
            ganado_bruto = round(beneficio_total * (porc / 100.0), 2)
            pendiente = max(0.0, round(ganado_bruto - pagado, 2))
            total_repartido = round(total_repartido + pendiente, 2)
            lista_acc.append({'id': r[0], 'nombre': r[1], 'porcentaje': porc, 'ganancia': pendiente})
        ganancia_neta = max(0.0, round(beneficio_total - total_repartido, 2))
        return {'accionistas_lista': lista_acc, 'ganancia_neta_admin': ganancia_neta, 'total_repartido_accionistas': total_repartido}
    except Exception as e:
        return {'accionistas_lista': [], 'ganancia_neta_admin': 0.0, 'total_repartido_accionistas': 0.0}

@app.route('/agregar_accionista', methods=['POST'])
def agregar_accionista():
    from flask import request, redirect, url_for
    import sqlite3
    nombre = request.form.get('nombre', '').strip()
    try: porcentaje = float(request.form.get('porcentaje', 10))
    except: porcentaje = 10.0
    if nombre:
        conn = sqlite3.connect('database.db')
        conn.execute("INSERT INTO accionistas (nombre, porcentaje, pagado) VALUES (?, ?, 0.0)", (nombre, porcentaje))
        conn.commit()
        conn.close()
    return redirect(url_for('panel_admin'))

@app.route('/liquidar_accionista/<int:acc_id>', methods=['POST'])
def liquidar_accionista(acc_id):
    from flask import redirect, url_for
    import sqlite3
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    beneficio_total = obtener_beneficio_admin_total(cursor)
    cursor.execute("SELECT porcentaje FROM accionistas WHERE id = ?", (acc_id,))
    r = cursor.fetchone()
    if r:
        nuevo_pagado = round(beneficio_total * (float(r[0]) / 100.0), 2)
        cursor.execute("UPDATE accionistas SET pagado = ? WHERE id = ?", (nuevo_pagado, acc_id))
        conn.commit()
    conn.close()
    return redirect(url_for('panel_admin'))

@app.route('/eliminar_accionista/<int:acc_id>', methods=['POST'])
def eliminar_accionista(acc_id):
    from flask import redirect, url_for
    import sqlite3
    conn = sqlite3.connect('database.db')
    conn.execute("DELETE FROM accionistas WHERE id = ?", (acc_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('panel_admin'))
# === FIN SISTEMA DE ACCIONISTAS ===


@app.route('/manifest.json')
def manifest():
    from flask import send_from_directory
    return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def service_worker():
    from flask import send_from_directory, make_response
    response = make_response(send_from_directory('static', 'sw.js'))
    response.headers['Content-Type'] = 'application/javascript'
    return response



# === RUTAS DE REGISTRO Y RECARGA DE CHOFERES ===
@app.route('/recargar_creditos_ref', methods=['POST'])
def recargar_creditos_ref():
    identificador = request.form.get('identificador', '').strip()
    referencia = request.form.get('referencia', '').strip()
    monto = float(request.form.get('monto_creditos', 0) or 0)
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    try:
        # Detectar tabla y columna de saldo dinámicamente
        tablas = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        t_chof = next((t for t in tablas if 'chofer' in t.lower() or 'driver' in t.lower()), 'choferes')
        cols = [r[1] for r in c.execute(f"PRAGMA table_info({t_chof})").fetchall()]
        
        col_saldo = next((col for col in cols if col.lower() in ['saldo', 'creditos', 'credito', 'balance']), cols[-1])
        col_pin = next((col for col in cols if 'pin' in col.lower()), None)
        col_ced = next((col for col in cols if 'ced' in col.lower() or 'ci' in col.lower() or 'id' in col.lower()), cols[0])
        
        # Sumar créditos al chofer por PIN o Cédula/ID
        if col_pin:
            c.execute(f"UPDATE {t_chof} SET {col_saldo} = COALESCE({col_saldo}, 0) + ? WHERE {col_pin} = ? OR {col_ced} = ?", (monto, identificador, identificador))
        else:
            c.execute(f"UPDATE {t_chof} SET {col_saldo} = COALESCE({col_saldo}, 0) + ? WHERE {col_ced} = ?", (monto, identificador))
            
        # Guardar historial de referencia
        c.execute("CREATE TABLE IF NOT EXISTS recargas_referencia (id INTEGER PRIMARY KEY AUTOINCREMENT, identificador TEXT, referencia TEXT, monto REAL, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("INSERT INTO recargas_referencia (identificador, referencia, monto) VALUES (?, ?, ?)", (identificador, referencia, monto))
        conn.commit()
    except Exception as e:
        print("Error en recarga:", e)
    finally:
        conn.close()
    return redirect(url_for('panel_admin'))

@app.route('/registrar_chofer_panel', methods=['POST'])
def registrar_chofer_panel():
    nombre = request.form.get('nombre', '').strip()
    cedula = request.form.get('cedula', '').strip()
    telefono = request.form.get('telefono', '').strip()
    placa = request.form.get('placa', '').strip()
    pin = request.form.get('pin', '').strip()
    creditos = float(request.form.get('creditos', 0) or 0)
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    try:
        tablas = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        t_chof = next((t for t in tablas if 'chofer' in t.lower() or 'driver' in t.lower()), 'choferes')
        info = c.execute(f"PRAGMA table_info({t_chof})").fetchall()
        cols = [r[1] for r in info]
        
        # Asegurar columnas adicionales si la tabla solo tenía pin y saldo
        for nueva_col, tipo in [('nombre', 'TEXT'), ('cedula', 'TEXT'), ('telefono', 'TEXT'), ('placa', 'TEXT')]:
            if not any(nueva_col in col.lower() for col in cols):
                try:
                    c.execute(f"ALTER TABLE {t_chof} ADD COLUMN {nueva_col} {tipo}")
                except:
                    pass
        
        cols = [r[1] for r in c.execute(f"PRAGMA table_info({t_chof})").fetchall()]
        insert_cols, insert_vals = [], []
        
        for col in cols:
            cl = col.lower()
            if cl == 'id': continue
            elif 'nom' in cl: insert_cols.append(col); insert_vals.append(nombre)
            elif 'ced' in cl or cl == 'ci': insert_cols.append(col); insert_vals.append(cedula)
            elif 'tel' in cl or 'cel' in cl: insert_cols.append(col); insert_vals.append(telefono)
            elif 'plac' in cl or 'moto' in cl or 'veh' in cl: insert_cols.append(col); insert_vals.append(placa)
            elif 'pin' in cl or 'pass' in cl or 'clav' in cl: insert_cols.append(col); insert_vals.append(pin)
            elif cl in ['saldo', 'creditos', 'credito', 'balance']: insert_cols.append(col); insert_vals.append(creditos)
            
        if insert_cols:
            placeholders = ', '.join(['?'] * len(insert_cols))
            cols_str = ', '.join(insert_cols)
            c.execute(f"INSERT INTO {t_chof} ({cols_str}) VALUES ({placeholders})", tuple(insert_vals))
            conn.commit()
    except Exception as e:
        print("Error registrando chofer:", e)
    finally:
        conn.close()
    return redirect(url_for('panel_admin'))



@app.route('/limpiar_historial_carreras', methods=['POST'])
def limpiar_historial_carreras():
    session['admin_ticket'] = True
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    try:
        tablas = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        for t in tablas:
            tl = t.lower()
            cols = [r[1].lower() for r in c.execute(f"PRAGMA table_info({t})").fetchall()]
            if any(k in tl for k in ['carrera', 'viaje', 'solicitud', 'historial', 'pedido', 'ride']) or ('origen' in cols and 'estado' in cols):
                c.execute(f"DELETE FROM {t}")
                print(f"✅ Historial eliminado en tabla: {t}")
        conn.commit()
    except Exception as e:
        print("Error al eliminar historial:", e)
    finally:
        conn.close()
    return redirect(url_for('panel_admin'))


if __name__ == '__main__':
    app.run(debug=True)






