import sqlite3
from werkzeug.security import generate_password_hash

def inicializar_db_auto():
    conexion = sqlite3.connect('mototaxi.db')
    cursor = conexion.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
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
    
    cuentas = [
        ('Administrador Principal', 'V-00000000', '0000', 'admin123', 'admin', 0.0, 'activo', '', 'offline'),
        ('Pasajero de Prueba', 'V-11111111', '1111', 'pasajero123', 'pasajero', 50.0, 'activo', '', 'offline'),
        ('Carlos Moto', 'V-22222222', '2222', 'chofer123', 'chofer', 20.0, 'activo', 'AA1B23', 'offline')
    ]
    
    for nombre, cedula, telefono, clave, rol, saldo, estado, placa, estatus in cuentas:
        existe = cursor.execute("SELECT id FROM usuarios WHERE telefono = ?", (telefono,)).fetchone()
        if not existe:
            p_hash = generate_password_hash(clave)
            cursor.execute('''
                INSERT INTO usuarios (nombre, cedula, telefono, password, rol, saldo_usd, estado_cuenta, placa_moto, estatus_chofer)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nombre, cedula, telefono, p_hash, rol, saldo, estado, placa, estatus))
            
    conexion.commit()
    conexion.close()

if __name__ == '__main__':
    inicializar_db_auto()
