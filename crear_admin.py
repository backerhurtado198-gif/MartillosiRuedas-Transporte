import sqlite3
from werkzeug.security import generate_password_hash

conexion = sqlite3.connect('mototaxi.db')
cursor = conexion.cursor()

pass_hash = generate_password_hash('admin123')

admin = cursor.execute("SELECT * FROM usuarios WHERE rol = 'admin'").fetchone()

if admin:
    cursor.execute("UPDATE usuarios SET password = ?, telefono = '0000', estado_cuenta = 'activo' WHERE rol = 'admin'", (pass_hash,))
    print("✅ Credenciales de Administrador actualizadas.")
else:
    cursor.execute('''
        INSERT INTO usuarios (nombre, cedula, telefono, password, rol, saldo_usd, estado_cuenta)
        VALUES ('Administrador Principal', 'V-00000000', '0000', ?, 'admin', 0.0, 'activo')
    ''', (pass_hash,))
    print("✅ Usuario Administrador creado con éxito.")

conexion.commit()
conexion.close()
