import sqlite3



def insertar_proveedores(mp):
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect('mp.db')
        cursor = conn.cursor()

        # Insertar múltiples proveedores
        cursor.executemany("""
            SELECT * FROM proveedores 
        """)
