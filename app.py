import sqlite3
import csv
import io
import re
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response, session

app = Flask(__name__)
app.secret_key = 'martillosi_ruedas_key_super_segura_2026'
app.permanent_session_lifetime = timedelta(days=30)

def init_db():
    try:
        with sqlite3.connect('mototaxis.db') as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS carreras
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         tipo TEXT,
                         precio REAL,
                         estado TEXT,
                         chofer TEXT DEFAULT 'Sin Asignar',
                         driver_id INTEGER DEFAULT 0,
                         pasajero TEXT DEFAULT 'Anónimo')''')
            
            try:
                c.execute("ALTER TABLE carreras ADD COLUMN driver_id INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass

            try:
                c.execute("ALTER TABLE carreras ADD COLUMN padrino_pagado INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass

            c.execute('''CREATE TABLE IF NOT EXISTS drivers
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         name TEXT,
                         pin TEXT UNIQUE,
                         unidad TEXT,
                         padrino_id INTEGER DEFAULT 0)''')
            
            try:
                c.execute("ALTER TABLE drivers ADD COLUMN padrino_id INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            
            c.execute('''CREATE TABLE IF NOT EXISTS passengers
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         nombre TEXT,
                         contacto TEXT UNIQUE)''')
            
            c.execute('CREATE INDEX IF NOT EXISTS idx_passenger_contacto ON passengers(contacto)')
            
            c.execute("SELECT COUNT(*) FROM drivers")
            if c.fetchone()[0] == 0:
                c.execute("INSERT INTO drivers (name, pin, unidad, padrino_id) VALUES (?, ?, ?, ?)", 
                          ("Carlos Pérez", "2201", "Unidad #1", 0))
            
            c.execute("SELECT COUNT(*) FROM passengers")
            if c.fetchone()[0] == 0:
                c.execute("INSERT INTO passengers (nombre, contacto) VALUES (?, ?)", 
                          ("Ana Gómez", "04121234567"))

            conn.commit()
    except Exception as e:
        print(f"Error crítico al inicializar la BD: {e}")

init_db()

def validar_contacto(contacto):
    contacto = contacto.strip()
    if '@' in contacto:
        return contacto.endswith('@gmail.com')
    clean_phone = re.sub(r'[\s\-\(\)]', '', contacto)
    pattern = r'^(?:\+58|58|0)?(412|414|424|416|426)\d{7}$'
    return bool(re.match(pattern, clean_phone))

@app.route('/')
def login_page():
    return render_template('login.html', error=None)

@app.route('/procesar_pin', methods=['POST'])
def procesar_pin():
    pin = request.form.get('pin', '').strip()
    if pin == '0000':
        session.permanent = True
        session['rol'] = 'admin'
        return redirect(url_for('admin'))
    
    try:
        with sqlite3.connect('mototaxis.db') as conn:
            c = conn.cursor()
            c.execute("SELECT id, name, unidad FROM drivers WHERE pin = ?", (pin,))
            driver = c.fetchone()
            
        if driver:
            session.permanent = True
            session['rol'] = 'chofer'
            session['driver_id'] = driver[0]
            session['chofer_nombre'] = driver[1]
            session['unidad'] = driver[2]
            return redirect(url_for('chofer'))
    except Exception as e:
        print(f"Error en login chofer: {e}")
        
    return render_template('login.html', error="PIN inválido o no registrado.")

@app.route('/procesar_pasajero', methods=['POST'])
def procesar_pasajero():
    contacto = request.form.get('contacto', '').strip()
    if not validar_contacto(contacto):
        return render_template('login.html', error="Formato inválido. Use correo @gmail.com o móvil de Venezuela (Ej: 04121234567).")
    
    try:
        with sqlite3.connect('mototaxis.db') as conn:
            c = conn.cursor()
            c.execute("SELECT nombre FROM passengers WHERE contacto = ?", (contacto,))
            pass_row = c.fetchone()
            
        if pass_row:
            session.permanent = True
            session['rol'] = 'pasajero'
            session['nombre'] = pass_row[0]
            session['contacto'] = contacto
            return redirect(url_for('pasajero'))
        else:
            return render_template('login.html', error="Acceso denegado: Este contacto no está registrado.")
    except Exception as e:
        return render_template('login.html', error="Error al procesar la verificación.")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/pasajero')
def pasajero():
    if session.get('rol') != 'pasajero':
        return redirect(url_for('login_page'))
    return render_template('index.html', nombre=session.get('nombre'), contacto=session.get('contacto'))

@app.route('/chofer')
def chofer():
    if session.get('rol') != 'chofer':
        return redirect(url_for('login_page'))
    return render_template('driver.html', unidad=session.get('unidad'), nombre=session.get('chofer_nombre'))

@app.route('/admin')
def admin():
    if session.get('rol') != 'admin':
        return redirect(url_for('login_page'))
    return render_template('admin.html')

@app.route('/api/admin/agregar-chofer', methods=['POST'])
def agregar_chofer():
    if session.get('rol') != 'admin':
        return jsonify({"status": "error", "mensaje": "No autorizado"}), 403
    try:
        datos = request.json
        nombre = datos.get('nombre')
        pin = datos.get('pin')
        unidad = datos.get('unidad')
        padrino_raw = datos.get('padrino', 0)
        try:
            padrino_id = int(padrino_raw) if padrino_raw else 0
        except ValueError:
            padrino_id = 0

        with sqlite3.connect('mototaxis.db') as conn:
            c = conn.cursor()
            c.execute("INSERT INTO drivers (name, pin, unidad, padrino_id) VALUES (?, ?, ?, ?)", 
                      (nombre, pin, unidad, padrino_id))
            conn.commit()
        return jsonify({"status": "success", "mensaje": "Chofer agregado con éxito"})
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "mensaje": "El PIN ya está en uso."}), 400
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route('/api/admin/drivers', methods=['GET'])
def listar_choferes():
    if session.get('rol') != 'admin':
        return jsonify([]), 403
    try:
        with sqlite3.connect('mototaxis.db') as conn:
            c = conn.cursor()
            query = '''
                SELECT d.id, d.name, d.pin, d.unidad, d.padrino_id, 
                       COALESCE(p.name, 'Ninguno (Independiente)') as nombre_padrino
                FROM drivers d
                LEFT JOIN drivers p ON d.padrino_id = p.id
            '''
            c.execute(query)
            rows = c.fetchall()
            
            drivers = []
            for r in rows:
                driver_id = r[0]
                # Calcular ganancia pendiente de referidos para este chofer
                c.execute('''
                    SELECT SUM(c.precio * 0.03) 
                    FROM carreras c 
                    JOIN drivers ahijado ON c.driver_id = ahijado.id 
                    WHERE ahijado.padrino_id = ? AND c.estado = 'aceptada' AND c.padrino_pagado = 0
                ''', (driver_id,))
                res_sum = c.fetchone()[0]
                ganancia_pend = res_sum if res_sum else 0.0

                drivers.append({
                    "id": driver_id, "name": r[1], "pin": r[2], "unidad": r[3], 
                    "padrino_id": r[4], "padrino_nombre": r[5],
                    "ganancia_pendiente": ganancia_pend
                })
        return jsonify(drivers)
    except Exception as e:
        return jsonify([])

@app.route('/api/admin/pagar-referidos/<int:driver_id>', methods=['POST'])
def pagar_referidos(driver_id):
    if session.get('rol') != 'admin':
        return jsonify({"status": "error", "mensaje": "No autorizado"}), 403
    try:
        with sqlite3.connect('mototaxis.db') as conn:
            c = conn.cursor()
            # Marcar como pagadas todas las carreras de los ahijados de este chofer
            c.execute('''
                UPDATE carreras 
                SET padrino_pagado = 1 
                WHERE estado = 'aceptada' AND padrino_pagado = 0 AND driver_id IN (
                    SELECT id FROM drivers WHERE padrino_id = ?
                )
            ''', (driver_id,))
            conn.commit()
        return jsonify({"status": "success", "mensaje": "Referidos pagados y contador reiniciado a 0"})
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route('/api/chofer/referidos', methods=['GET'])
def chofer_referidos():
    if session.get('rol') != 'chofer':
        return jsonify({"error": "No autorizado"}), 403
    try:
        driver_id = session.get('driver_id')
        with sqlite3.connect('mototaxis.db') as conn:
            c = conn.cursor()
            # Obtener ahijados y su contribución pendiente
            c.execute("SELECT id, name, unidad FROM drivers WHERE padrino_id = ?", (driver_id,))
            ahijados_rows = c.fetchall()
            
            ahijados_lista = []
            total_ganancia_pendiente = 0.0
            
            for ahijado in ahijados_rows:
                ahijado_id = ahijado[0]
                # Sumar carreras aceptadas no pagadas de este ahijado
                c.execute('''
                    SELECT SUM(precio * 0.03), COUNT(*) 
                    FROM carreras 
                    WHERE driver_id = ? AND estado = 'aceptada' AND padrino_pagado = 0
                ''', (ahijado_id,))
                res = c.fetchone()
                monto = res[0] if res and res[0] else 0.0
                carreras_count = res[1] if res and res[1] else 0
                
                total_ganancia_pendiente += monto
                ahijados_lista.append({
                    "nombre": ahijado[1],
                    "unidad": ahijado[2],
                    "carreras_referidas": carreras_count,
                    "ganancia": monto
                })

        return jsonify({
            "total_pendiente": total_ganancia_pendiente,
            "ahijados": ahijados_lista
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/agregar-pasajero', methods=['POST'])
def agregar_pasajero():
    if session.get('rol') != 'admin':
        return jsonify({"status": "error", "mensaje": "No autorizado"}), 403
    try:
        datos = request.json
        nombre = datos.get('nombre')
        contacto = datos.get('contacto', '').strip()
        if not validar_contacto(contacto):
            return jsonify({"status": "error", "mensaje": "Formato de contacto inválido."}), 400
            
        with sqlite3.connect('mototaxis.db') as conn:
            c = conn.cursor()
            c.execute("INSERT INTO passengers (nombre, contacto) VALUES (?, ?)", (nombre, contacto))
            conn.commit()
        return jsonify({"status": "success", "mensaje": "Pasajero registrado exitosamente"})
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "mensaje": "Este contacto ya se encuentra registrado."}), 400
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route('/api/admin/passengers', methods=['GET'])
def listar_pasajeros():
    if session.get('rol') != 'admin':
        return jsonify([]), 403
    try:
        with sqlite3.connect('mototaxis.db') as conn:
            c = conn.cursor()
            c.execute("SELECT id, nombre, contacto FROM passengers ORDER BY id DESC LIMIT 100")
            passengers = [{"id": r[0], "nombre": r[1], "contacto": r[2]} for r in c.fetchall()]
        return jsonify(passengers)
    except Exception as e:
        return jsonify([])

@app.route('/api/solicitar', methods=['POST'])
def solicitar_carrera():
    if not session.get('rol'):
        session.permanent = True
        session['rol'] = 'pasajero'
    if not session.get('nombre'):
        session['nombre'] = 'Pasajero Web'
    if not session.get('contacto'):
        session['contacto'] = '04120000000'

    try:
        datos = request.json
        pasajero_info = f"{session.get('nombre')} ({session.get('contacto')})"
        with sqlite3.connect('mototaxis.db') as conn:
            c = conn.cursor()
            c.execute("INSERT INTO carreras (tipo, precio, estado, chofer, driver_id, pasajero, padrino_pagado, origen) VALUES (?, ?, 'pendiente', 'Pendiente', 0, ?, 0, ?)",
                      (datos.get('tipo', 'Carrera Corta'), float(datos.get('precio', 1.0)), pasajero_info, datos.get('origen', 'San Juan de los Morros')))
            conn.commit()
        return jsonify({"status": "success", "mensaje": "Carrera solicitada"})
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route('/api/pendientes', methods=['GET'])
def ver_pendientes():
    if session.get('rol') != 'chofer':
        return jsonify([]), 403
    try:
        with sqlite3.connect('mototaxis.db') as conn:
            c = conn.cursor()
            c.execute("SELECT id, tipo, precio, pasajero, origen FROM carreras WHERE estado = 'pendiente'")
            carreras = [{"id": row[0], "tipo": row[1], "precio": row[2], "pasajero": row[3], "origen": row[4]} for row in c.fetchall()]
        return jsonify(carreras)
    except Exception as e:
        return jsonify([])

@app.route('/api/aceptar/<int:id_carrera>', methods=['POST'])
def aceptar_carrera(id_carrera):
    if session.get('rol') != 'chofer':
        return jsonify({"status": "error", "mensaje": "No autorizado"}), 403
    try:
        chofer_info = f"{session.get('chofer_nombre')} ({session.get('unidad')})"
        driver_id = session.get('driver_id', 0)
        with sqlite3.connect('mototaxis.db') as conn:
            c = conn.cursor()
            c.execute("UPDATE carreras SET estado = 'aceptada', chofer = ?, driver_id = ? WHERE id = ?", 
                      (chofer_info, driver_id, id_carrera))
            conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    if session.get('rol') != 'admin':
        return jsonify({"error": "No autorizado"}), 403
    try:
        with sqlite3.connect('mototaxis.db') as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM carreras")
            total_carreras = c.fetchone()[0]
            
            c.execute('''
                SELECT c.id, c.tipo, c.precio, c.estado, c.chofer, c.pasajero,
                       d.padrino_id, p.name as padrino_nombre
                FROM carreras c
                LEFT JOIN drivers d ON c.driver_id = d.id
                LEFT JOIN drivers p ON d.padrino_id = p.id
                ORDER BY c.id DESC
            ''')
            rows = c.fetchall()
            
            ingresos_brutos = 0.0
            comision_plataforma_total = 0.0
            pago_padrinos_total = 0.0
            
            carreras_lista = []
            for r in rows:
                precio = r[2] or 0.0
                estado = r[3]
                comision_carrera = 0.0
                padrino_comision = 0.0
                
                if estado == 'aceptada':
                    ingresos_brutos += precio
                    comision_carrera = precio * 0.15
                    comision_plataforma_total += comision_carrera
                    if r[6] and r[6] > 0:
                        padrino_comision = precio * 0.03
                        pago_padrinos_total += padrino_comision

                carreras_lista.append({
                    "id": r[0], "tipo": r[1], "precio": precio, "estado": estado,
                    "chofer": r[4], "pasajero": r[5], "comision": comision_carrera,
                    "padrino_nombre": r[7] if r[7] else "Ninguno",
                    "padrino_comision": padrino_comision
                })

            c.execute("SELECT COUNT(*) FROM passengers")
            total_pasajeros = c.fetchone()[0]
            
        ganancia_neta = comision_plataforma_total - pago_padrinos_total
        
        return jsonify({
            "total_carreras": total_carreras,
            "ingresos_brutos": ingresos_brutos,
            "comision_plataforma_total": comision_plataforma_total,
            "pago_padrinos_total": pago_padrinos_total,
            "ganancia_neta": ganancia_neta,
            "total_pasajeros": total_pasajeros,
            "carreras": carreras_lista
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/export', methods=['GET'])
def exportar_csv():
    if session.get('rol') != 'admin':
        return redirect(url_for('login_page'))
    try:
        with sqlite3.connect('mototaxis.db') as conn:
            c = conn.cursor()
            c.execute("SELECT id, tipo, precio, estado, chofer, pasajero FROM carreras ORDER BY id DESC")
            rows = c.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID de Carrera', 'Tipo de Carrera', 'Precio (USD)', 'Estado', 'Chofer Asignado', 'Pasajero'])
        for row in rows:
            writer.writerow(row)
        
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=reporte_carreras_martillosiruedas.csv"
        response.headers["Content-type"] = "text/csv"
        return response
    except Exception as e:
        return "Error al generar el reporte", 500

@app.route('/api/admin/eliminar-chofer/<int:id>', methods=['POST'])
def eliminar_chofer(id):
    if session.get('rol') != 'admin':
        return jsonify({"status": "error", "mensaje": "No autorizado"}), 403
    try:
        with sqlite3.connect('mototaxis.db') as conn:
            c = conn.cursor()
            c.execute("DELETE FROM drivers WHERE id = ?", (id,))
            conn.commit()
        return jsonify({"status": "success", "mensaje": "Chofer eliminado"})
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route('/api/admin/eliminar-pasajero/<int:id>', methods=['POST'])
def eliminar_pasajero(id):
    if session.get('rol') != 'admin':
        return jsonify({"status": "error", "mensaje": "No autorizado"}), 403
    try:
        with sqlite3.connect('mototaxis.db') as conn:
            c = conn.cursor()
            c.execute("DELETE FROM passengers WHERE id = ?", (id,))
            conn.commit()
        return jsonify({"status": "success", "mensaje": "Pasajero eliminado"})
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route('/api/admin/eliminar-carrera/<int:id>', methods=['POST'])
def eliminar_carrera(id):
    if session.get('rol') != 'admin':
        return jsonify({"status": "error", "mensaje": "No autorizado"}), 403
    try:
        with sqlite3.connect('mototaxis.db') as conn:
            c = conn.cursor()
            c.execute("DELETE FROM carreras WHERE id = ?", (id,))
            conn.commit()
        return jsonify({"status": "success", "mensaje": "Carrera eliminada"})
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route('/mapa')
def ver_mapa():
    return render_template('mapa_prueba.html')



if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
