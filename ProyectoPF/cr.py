import sqlite3

# Conectar a la base de datos
conn = sqlite3.connect('FIME_v2.db')
cursor = conn.cursor()

# Crear tabla asistencia con columna profesor y materia
cursor.execute('''
    CREATE TABLE IF NOT EXISTS asistencia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profesor TEXT,
        materia TEXT,
        carrera TEXT,
        fecha TEXT,
        asistio TEXT
    )
''')

# Confirmar cambios y cerrar la conexión
conn.commit()
conn.close()
print("Tabla asistencia creada o verificada exitosamente.")
