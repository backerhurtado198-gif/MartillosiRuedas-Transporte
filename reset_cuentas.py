import sqlite3
from werkzeug.security import generate_password_hash

conexion = sqlite3.connect('mototaxi.db')
cursor = conexion.cursor()

# Cuentas a garantizar
cuentas = [
    ('Administrador Principal', 'V-00000000', '0000', 'admin123', 'admin', 0.0, 'activo', 'N/A', 'offline'),
    ('Pasajero de Prueba', 'V-11111111', '1111', 'pasajero123', 'pasajero', 50.0, 'activo', 'N/A', 'offline'),
    ('Carlos Moto', 'V-22222222', '2222', 'chofer123', 'chofer', 20.0, 'activo', 'AA1B23', 'offline')
]

cursor.execute("PRAGMA table_info(usuarios)")
columnas = [col[1] for col in cursor.fetchall()]

for nombre, cedula, telefono, clave, rol, saldo, estado, placa, estatus in cuentas:
    pass_hash = generate_password_hash(clave)
    
    existe = cursor.execute("SELECT id FROM usuarios WHERE telefono = ?", (telefono,)).fetchone()
    
    if existe:
        cursor.execute("UPDATE usuarios SET password = ?, estado_cuenta = ? WHERE telefono = ?", (pass_hash, 'activo', telefono))
        print(f"✅ Contraseña restablecida para {rol.upper()} (Teléfono: {telefono})")
    else:
        cols_insert = ['nombre', 'cedula', 'telefono', 'password', 'rol', 'saldo_usd', 'estado_cuenta']
        vals_insert = [nombre, cedula, telefono, pass_hash, rol, saldo, 'activo']
        
        if 'placa_moto' in columnas and rol == 'chofer':
            cols_insert.append('placa_moto')
            vals_insert.append(placa)
        if 'estatus_chofer' in columnas and rol == 'chofer':
            cols_insert.append('estatus_chofer')
            vals_insert.append(estatus)
            
        placeholders = ', '.join(['?'] * len(vals_insert))
        cols_str = ', '.join(cols_insert)
        
        cursor.execute(f"INSERT INTO usuarios ({cols_str}) VALUES ({placeholders})", vals_insert)
        print(f"✅ Cuenta {rol.upper()} creada correctamente (Teléfono: {telefono})")

conexion.commit()

print("\n--- ESTADO DE USUARIOS EN LA BASE DE DATOS ---")
cursor.execute("SELECT id, nombre, telefono, rol, estado_cuenta FROM usuarios")
for u in cursor.fetchall():
    print(f"ID: {u[0]} | Nombre: {u[1]} | Teléfono: {u[2]} | Rol: {u[3]} | Estado: {u[4]}")

conexion.close()
