import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

conexion = sqlite3.connect('mototaxi.db')
cursor = conexion.cursor()

# 1. Recrear la tabla usuarios con esquema limpio y estandarizado
cursor.execute("DROP TABLE IF EXISTS usuarios_bak")
cursor.execute("CREATE TABLE IF NOT EXISTS usuarios_temp AS SELECT * FROM usuarios")

cursor.execute("DROP TABLE IF EXISTS usuarios")
cursor.execute('''
    CREATE TABLE usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        cedula TEXT NOT NULL,
        telefono TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        rol TEXT NOT NULL,
        saldo_usd REAL DEFAULT 0.0,
        estado_cuenta TEXT DEFAULT 'activo',
        placa_moto TEXT DEFAULT '',
        estatus_chofer TEXT DEFAULT 'offline'
    )
''')

# 2. Insertar usuarios con hashes garantizados
cuentas = [
    ('Administrador Principal', 'V-00000000', '0000', 'admin123', 'admin', 0.0, 'activo', '', 'offline'),
    ('Pasajero de Prueba', 'V-11111111', '1111', 'pasajero123', 'pasajero', 50.0, 'activo', '', 'offline'),
    ('Carlos Moto', 'V-22222222', '2222', 'chofer123', 'chofer', 20.0, 'activo', 'AA1B23', 'offline')
]

for nombre, cedula, telefono, clave, rol, saldo, estado, placa, estatus in cuentas:
    p_hash = generate_password_hash(clave)
    cursor.execute('''
        INSERT INTO usuarios (nombre, cedula, telefono, password, rol, saldo_usd, estado_cuenta, placa_moto, estatus_chofer)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (nombre, cedula, telefono, p_hash, rol, saldo, estado, placa, estatus))

conexion.commit()

# 3. Prueba de verificación directa
print("--- COMPROBACIÓN DE CREDENCIALES EN BASE DE DATOS ---")
conexion.row_factory = sqlite3.Row
cursor_test = conexion.cursor()

for t, c in [('0000', 'admin123'), ('1111', 'pasajero123'), ('2222', 'chofer123')]:
    row = cursor_test.execute("SELECT * FROM usuarios WHERE telefono = ?", (t,)).fetchone()
    if row and check_password_hash(row['password'], c):
        print(f" SUCCESS -> Teléfono '{t}' ({row['rol']}): Login CORRECTO")
    else:
        print(f" ERROR -> Teléfono '{t}': Falló verificación")

conexion.close()
