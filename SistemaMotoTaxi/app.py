from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = 'clave_secreta_super_segura_para_el_negocio'

def obtener_conexion():
    conexion = sqlite3.connect('mototaxi.db')
    conexion.row_factory = sqlite3.Row
    return conexion

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        telefono = request.form['telefono']
        password = request.form['password']
        
        conexion = obtener_conexion()
        usuario = conexion.execute('SELECT * FROM usuarios WHERE telefono = ? AND password = ?', (telefono, password)).fetchone()
        conexion.close()
        
        if usuario:
            session['usuario_id'] = usuario['id']
            session['rol'] = usuario['rol']
            
            if usuario['rol'] == 'admin':
                return redirect(url_for('panel_admin'))
            elif usuario['rol'] == 'chofer':
                return redirect(url_for('panel_chofer'))
            else:
                return redirect(url_for('panel_pasajero'))
        else:
            return "Datos incorrectos. Inténtalo de nuevo."
            
    return render_template('login.html')

@app.route('/admin', methods=['GET', 'POST'])
def panel_admin():
    if 'rol' not in session or session['rol'] != 'admin':
        return redirect(url_for('login'))
        
    conexion = obtener_conexion()
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        password = request.form['password']
        placa = request.form['placa_moto']
        
        try:
            conexion.execute('''
                INSERT INTO usuarios (nombre, telefono, password, rol, estatus_chofer, placa_moto)
                VALUES (?, ?, ?, 'chofer', 'offline', ?)
            ''', (nombre, telefono, password, placa))
            conexion.commit()
        except sqlite3.IntegrityError:
            pass
        conexion.close()
        return redirect(url_for('panel_admin'))

    stats = conexion.execute('''
        SELECT 
            COUNT(id) as total_carreras,
            COALESCE(SUM(tarifa_usd), 0) as volumen_total,
            COALESCE(SUM(comision_admin), 0) as tus_ganancias
        FROM viajes WHERE estado = 'finalizado'
    ''').fetchone()

    choferes = conexion.execute("SELECT * FROM usuarios WHERE rol = 'chofer'").fetchall()
    conexion.close()
    
    return render_template('admin.html', stats=stats, choferes=choferes)

@app.route('/chofer')
def panel_chofer():
    if 'rol' not in session or session['rol'] != 'chofer':
        return redirect(url_for('login'))
    
    conexion = obtener_conexion()
    chofer = conexion.execute('SELECT * FROM usuarios WHERE id = ?', (session['usuario_id'],)).fetchone()
    conexion.close()
    
    return render_template('chofer.html', chofer=chofer)

@app.route('/pasajero')
def panel_pasajero():
    if 'rol' not in session or session['rol'] != 'pasajero':
        return redirect(url_for('login'))
    return render_template('pasajero.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
