import sqlite3

conexion = sqlite3.connect('mototaxi.db')
cursor = conexion.cursor()

# Añadir columna de saldo a la tabla usuarios si no existe
try:
    cursor.execute("ALTER TABLE usuarios ADD COLUMN saldo_usd REAL DEFAULT 0.0")
except sqlite3.OperationalError:
    pass # La columna ya existe

# Tabla de solicitudes de recarga por Pago Móvil
cursor.execute('''
CREATE TABLE IF NOT EXISTS recargas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chofer_id INTEGER,
    monto_usd REAL,
    banco_origen TEXT,
    referencia TEXT UNIQUE,
    estado TEXT DEFAULT 'pendiente',
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(chofer_id) REFERENCES usuarios(id)
)
''')

conexion.commit()
conexion.close()
print("Base de datos actualizada con Billetera Virtual.")
