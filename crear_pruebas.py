import sqlite3
from werkzeug.security import generate_password_hash

conexion = sqlite3.connect('mototaxi.db')
cursor = conexion.cursor()

cursor.execute("PRAGMA table_info(usuarios)")
columnas = [col[1] for col in cursor.fetchall()]

# 1. Pasajero de prueba
pass_pasajero = generate_password_hash('pasajero123')
p = cursor.execute("SELECT * FROM usuarios WHERE telefono = '1111'").fetchone()
if p:
    cursor.execute("UPDATE usuarios SET password = ?, estado_cuenta = 'activo' WHERE telefono = '1111'", (pass_pasajero,))
else:
    cursor.execute('''
        INSERT INTO usuarios (nombre, cedula, telefono, password, rol, saldo_usd, estado_cuenta)
        VALUES ('Pasajero de Prueba', 'V-11111111', '1111', ?, 'pasajero', 50.0, 'activo')
    ''', (pass_pasajero,))

# 2. Chofer de prueba
pass_chofer = generate_password_hash('chofer123')
c = cursor.execute("SELECT * FROM usuarios WHERE telefono = '2222'").fetchone()
if c:
    cursor.execute("UPDATE usuarios SET password = ?, estado_cuenta = 'activo' WHERE telefono = '2222'", (pass_chofer,))
else:
    sql = "INSERT INTO usuarios (nombre, cedula, telefono, password, rol, saldo_usd, estado_cuenta"
    vals = "VALUES ('Carlos Moto', 'V-22222222', '2222', ?, 'chofer', 20.0, 'activo'"
    if 'placa_moto' in columnas:
        sql += ", placa_moto"
        vals += ", 'AA1B23'"
    if 'estatus_chofer' in columnas:
        sql += ", estatus_chofer"
        vals += ", 'offline'"
    sql += ") " + vals + ")"
    cursor.execute(sql, (pass_chofer,))

conexion.commit()
conexion.close()
print("✅ Cuentas de prueba para Pasajero y Chofer creadas con éxito.")
