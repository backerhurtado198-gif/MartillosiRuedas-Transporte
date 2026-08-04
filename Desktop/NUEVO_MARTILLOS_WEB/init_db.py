import sqlite3

def inicializar_bd():
    conn = sqlite3.connect('martillos.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        telefono TEXT UNIQUE NOT NULL,
        clave TEXT NOT NULL,
        rol TEXT NOT NULL,
        num_cupo INTEGER,
        placa_moto TEXT,
        saldo_billetera REAL DEFAULT 0.0,
        estado TEXT DEFAULT 'activo',
        fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS carreras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pasajero_id INTEGER,
        mototaxista_id INTEGER,
        origen_texto TEXT,
        origen_lat REAL,
        origen_lng REAL,
        destino_texto TEXT,
        destino_lat REAL,
        destino_lng REAL,
        distancia_km REAL,
        precio_total REAL,
        comision_app REAL,
        metodo_pago TEXT DEFAULT 'efectivo',
        estado TEXT DEFAULT 'solicitada',
        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pasajero_id) REFERENCES usuarios (id),
        FOREIGN KEY (mototaxista_id) REFERENCES usuarios (id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS historial_monedero (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mototaxista_id INTEGER,
        monto REAL NOT NULL,
        tipo TEXT NOT NULL,
        concepto TEXT,
        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (mototaxista_id) REFERENCES usuarios (id)
    )
    ''')

    # Usuario Admin y Mototaxi #01 de prueba
    cursor.execute("INSERT OR IGNORE INTO usuarios (id, nombre, telefono, clave, rol) VALUES (1, 'Administrador Martillos', '04120000000', 'admin123', 'admin')")
    cursor.execute("INSERT OR IGNORE INTO usuarios (id, nombre, telefono, clave, rol, num_cupo, placa_moto, saldo_billetera) VALUES (2, 'Jose Mototaxi #01', '04241234567', 'moto123', 'mototaxista', 1, 'AB1C23D', 5.00)")

    conn.commit()
    conn.close()
    print("-> Base de datos martillos.db verificada e inicializada.")

if __name__ == '__main__':
    inicializar_bd()
