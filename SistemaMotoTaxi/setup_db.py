import sqlite3

def crear_base_datos():
    conexion = sqlite3.connect('mototaxi.db')
    cursor = conexion.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        telefono TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        rol TEXT NOT NULL,
        estatus_chofer TEXT DEFAULT 'offline',
        placa_moto TEXT,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS viajes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pasajero_id INTEGER NOT NULL,
        chofer_id INTEGER,
        origen_lat REAL NOT NULL,
        origen_lng REAL NOT NULL,
        destino_lat REAL NOT NULL,
        destino_lng REAL NOT NULL,
        distancia_km REAL NOT NULL,
        tarifa_usd REAL NOT NULL,
        tarifa_bs REAL NOT NULL,
        comision_admin REAL NOT NULL,
        estado TEXT DEFAULT 'pendiente',
        fecha_viaje TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pasajero_id) REFERENCES usuarios (id),
        FOREIGN KEY (chofer_id) REFERENCES usuarios (id)
    )
    """)

    try:
        cursor.execute("""
        INSERT INTO usuarios (nombre, telefono, password, rol)
        VALUES ('Admin Principal', '0000000000', 'admin123', 'admin')
        """)
    except sqlite3.IntegrityError:
        pass

    conexion.commit()
    conexion.close()
    print("¡Base de datos 'mototaxi.db' creada exitosamente y lista para producción!")

if __name__ == '__main__':
    crear_base_datos()
