import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash

app = Flask(__name__)
app.secret_key = 'martillos_ruedas_secret_key'

def get_db_connection():
    conn = sqlite3.connect('mototaxi.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pasajeros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT UNIQUE NOT NULL,
            pin TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS choferes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT UNIQUE NOT NULL,
            pin TEXT NOT NULL,
            placa TEXT,
            saldo REAL DEFAULT 0.00,
            estado TEXT DEFAULT 'Activo'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recargas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chofer_id INTEGER,
            chofer_nombre TEXT,
            monto REAL NOT NULL,
            referencia TEXT NOT NULL,
            metodo_pago TEXT DEFAULT 'Pago Movil',
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            estado TEXT DEFAULT 'Pendiente',
            FOREIGN KEY (chofer_id) REFERENCES choferes (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuraciones (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS carreras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pasajero_nombre TEXT,
            pasajero_telefono TEXT,
            latitud_origen TEXT,
            longitud_origen TEXT,
            estado TEXT DEFAULT 'Pendiente',
            precio REAL DEFAULT 2.00,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute("INSERT OR IGNORE INTO configuraciones (clave, valor) VALUES ('precio_base', '2.00')")
    
    # Registro del Chofer Hans Bolívar
    cursor.execute("SELECT * FROM choferes WHERE nombre LIKE '%Hans%' OR nombre LIKE '%Bolivar%'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO choferes (nombre, telefono, pin, placa, saldo, estado) VALUES (?, ?, ?, ?, ?, ?)",
            ('Hans Bolívar', '04120001122', '1234', 'AB123CD', 15.00, 'Activo')
        )
        
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login_operativo', methods=['GET', 'POST'])
@app.route('/procesar_pin', methods=['GET', 'POST'])
def login_operativo():
    if request.method == 'POST':
        pin = request.form.get('pin_operativo') or request.form.get('pin', '').strip()
        
        if pin == '1234' or pin == 'admin':
            session['user_rol'] = 'admin'
            return redirect(url_for('admin_panel'))
        
        conn = get_db_connection()
        chofer = conn.execute("SELECT * FROM choferes WHERE pin = ?", (pin,)).fetchone()
        conn.close()
        
        if chofer:
            session['user_id'] = chofer['id']
            session['user_nombre'] = chofer['nombre']
            session['user_rol'] = 'chofer'
            return redirect(url_for('panel_chofer'))
        else:
            flash("PIN incorrecto. Usa 1234 para ingresar al Panel Administrador.", "danger")
            return redirect(url_for('index'))
    return redirect(url_for('index'))

@app.route('/login_pasajero', methods=['POST'])
def login_pasajero():
    telefono = request.form.get('telefono', '').strip()
    pin = request.form.get('pin', '').strip()

    if len(pin) != 6 or not pin.isdigit():
        flash("El PIN debe contener exactamente 6 dígitos numéricos.", "danger")
        return redirect(url_for('index'))

    conn = get_db_connection()
    pasajero = conn.execute(
        "SELECT * FROM pasajeros WHERE telefono = ? AND pin = ?", 
        (telefono, pin)
    ).fetchone()

    if pasajero:
        session['user_id'] = pasajero['id']
        session['user_nombre'] = pasajero['nombre']
        session['user_rol'] = 'pasajero'
        conn.close()
        return redirect(url_for('index_pasajero'))
    else:
        nombre_defecto = f"Pasajero {telefono[-4:]}"
        conn.execute(
            "INSERT INTO pasajeros (nombre, telefono, pin) VALUES (?, ?, ?)",
            (nombre_defecto, telefono, pin)
        )
        conn.commit()
        nuevo = conn.execute("SELECT * FROM pasajeros WHERE telefono = ?", (telefono,)).fetchone()
        session['user_id'] = nuevo['id']
        session['user_nombre'] = nuevo['nombre']
        session['user_rol'] = 'pasajero'
        conn.close()
        return redirect(url_for('index_pasajero'))

@app.route('/index_pasajero')
def index_pasajero():
    conn = get_db_connection()
    tarifa = conn.execute("SELECT valor FROM configuraciones WHERE clave = 'precio_base'").fetchone()
    conn.close()
    precio_base = tarifa['valor'] if tarifa else "2.00"
    return render_template('index_pasajero.html', precio_base=precio_base)

@app.route('/chofer')
def panel_chofer():
    return f"<h3>Panel de Chofer Activo - Bienvenido {session.get('user_nombre', 'Chofer')}</h3><br><a href='/'>Volver al Login</a>"

@app.route('/admin')
def admin_panel():
    conn = get_db_connection()
    tarifa = conn.execute("SELECT valor FROM configuraciones WHERE clave = 'precio_base'").fetchone()
    carreras = conn.execute("SELECT * FROM carreras ORDER BY id DESC").fetchall()
    recargas_pendientes = conn.execute("SELECT * FROM recargas WHERE estado = 'Pendiente' ORDER BY id DESC").fetchall()
    choferes = conn.execute("SELECT * FROM choferes ORDER BY id ASC").fetchall()
    pasajeros = conn.execute("SELECT * FROM pasajeros ORDER BY id ASC").fetchall()
    conn.close()
    
    tarifa_actual = tarifa['valor'] if tarifa else "2.00"
    return render_template(
        'admin.html', 
        tarifa_actual=tarifa_actual, 
        carreras=carreras, 
        recargas_pendientes=recargas_pendientes,
        choferes=choferes,
        pasajeros=pasajeros
    )

@app.route('/admin/aprobar_recarga/<int:id_recarga>', methods=['POST'])
def aprobar_recarga(id_recarga):
    conn = get_db_connection()
    recarga = conn.execute("SELECT * FROM recargas WHERE id = ?", (id_recarga,)).fetchone()
    if recarga and recarga['estado'] == 'Pendiente':
        conn.execute("UPDATE choferes SET saldo = saldo + ? WHERE id = ?", (recarga['monto'], recarga['chofer_id']))
        conn.execute("UPDATE recargas SET estado = 'Aprobado' WHERE id = ?", (id_recarga,))
        conn.commit()
        flash(f"Recarga #{id_recarga} aprobada con éxito.", "success")
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/rechazar_recarga/<int:id_recarga>', methods=['POST'])
def rechazar_recarga(id_recarga):
    conn = get_db_connection()
    conn.execute("UPDATE recargas SET estado = 'Rechazado' WHERE id = ?", (id_recarga,))
    conn.commit()
    conn.close()
    flash(f"Recarga #{id_recarga} rechazada.", "warning")
    return redirect(url_for('admin_panel'))

@app.route('/admin/recarga_manual', methods=['POST'])
def recarga_manual():
    chofer_id = request.form.get('chofer_id')
    monto = float(request.form.get('monto', 0))
    referencia = request.form.get('referencia', 'EFECTIVO-DIRECTO')
    
    if chofer_id and monto > 0:
        conn = get_db_connection()
        chofer = conn.execute("SELECT nombre FROM choferes WHERE id = ?", (chofer_id,)).fetchone()
        nombre = chofer['nombre'] if chofer else "Chofer"
        conn.execute("UPDATE choferes SET saldo = saldo + ? WHERE id = ?", (monto, chofer_id))
        conn.execute(
            "INSERT INTO recargas (chofer_id, chofer_nombre, monto, referencia, metodo_pago, estado) VALUES (?, ?, ?, ?, 'Efectivo/Manual', 'Aprobado')",
            (chofer_id, nombre, monto, referencia)
        )
        conn.commit()
        conn.close()
        flash(f"Abonados ${monto} a {nombre}.", "success")
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/registrar_chofer', methods=['POST'])
def registrar_chofer():
    nombre = request.form.get('nombre')
    telefono = request.form.get('telefono', '0000000000')
    pin = request.form.get('pin')
    placa = request.form.get('placa', '')
    
    if nombre and pin:
        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO choferes (nombre, telefono, pin, placa) VALUES (?, ?, ?, ?)",
                (nombre, telefono, pin, placa)
            )
            conn.commit()
            flash(f"Chofer {nombre} registrado.", "success")
        except:
            flash("El chofer ya existe o el teléfono está duplicado.", "danger")
        conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/cambiar_precio', methods=['POST'])
def admin_cambiar_precio():
    nuevo_precio = request.form.get('nuevo_precio')
    if nuevo_precio:
        conn = get_db_connection()
        conn.execute(
            "INSERT OR REPLACE INTO configuraciones (clave, valor) VALUES ('precio_base', ?)",
            (str(nuevo_precio),)
        )
        conn.commit()
        conn.close()
        flash("Tarifa base actualizada.", "info")
    return redirect(url_for('admin_panel'))

@app.route('/admin/carrera/editar/<int:id_carrera>', methods=['POST'])
def editar_carrera(id_carrera):
    precio = request.form.get('precio')
    estado = request.form.get('estado')
    conn = get_db_connection()
    conn.execute("UPDATE carreras SET precio = ?, estado = ? WHERE id = ?", (precio, estado, id_carrera))
    conn.commit()
    conn.close()
    flash(f"Carrera #{id_carrera} actualizada.", "info")
    return redirect(url_for('admin_panel'))

@app.route('/admin/carrera/eliminar/<int:id_carrera>', methods=['POST'])
def eliminar_carrera(id_carrera):
    conn = get_db_connection()
    conn.execute("DELETE FROM carreras WHERE id = ?", (id_carrera,))
    conn.commit()
    conn.close()
    flash(f"Carrera #{id_carrera} eliminada.", "warning")
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
