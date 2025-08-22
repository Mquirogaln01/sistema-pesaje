import sqlite3



def insertar_proveedores(proveedores):
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect('proveedores.db')
        cursor = conn.cursor()

        # Insertar múltiples proveedores
        cursor.executemany("""
            INSERT INTO proveedores (codigo_proveedor, razon_social, empresa_compradora, estatus)
            VALUES (?, ?, ?, ?)
        """, proveedores)

        # Confirmar cambios
        conn.commit()
        print(f"{len(proveedores)} proveedores insertados correctamente.")
    except sqlite3.Error as e:
        print(f"Error al insertar los proveedores: {e}")
    finally:
        conn.close()

# Datos de proveedores a insertar
proveedores = [
    ("PIQ-01", "AMN Logistica, S.A de C.V", "IQA", "ACTIVO"),
    ("PIQ-02", "Corporativa Vulcahierro, S.A.P.I de C.V", "IQA/IQB", "ACTIVO"),
    ("PIQ-03", "Luis Alfonso Mora Conchas", "IQB", "INACTIVO"),
    ("PIQ-04", "Ma Tlalli, S.A de C.V", "IQB", "INACTIVO"),
    ("PIQ-05", "REMETA, S.A de C.V", "IQA", "INACTIVO"),
    ("PIQ-06", "SMS FOREMEX, S. de R.L de C.V", "IQA/IQB", "INACTIVO"),
    ("PIQ-07", "Aso Alloy de México, S.A de C.V", "IQA", "INACTIVO"),
    ("PIQ-08", "Tromap Comercial S.A de C.V", "IQA", "INACTIVO"),
    ("PIQ-09", "Faist Alucast S. de R.L de C.V", "IQA", "ACTIVO"),
    ("PIQ-10", "Jimenez Palomo Paula", "IQB", "INACTIVO"),
    ("PIQ-11", "Comercializadora MC", "IQA", "INACTIVO"),
    ("PIQ-12", "Rongtai Industrial Development Leon S de RL de CV", "IQA", "ACTIVO"),
    ("PIQ-13", "Toyota Tsusho México SA DE CV", "IQA", "ACTIVO"),
    ("PIQ-14", "Tomas Rafael Toribio Hernandez", "IQB", "INACTIVO"),
    ("PIQ-15", "Recuperación Industrial del Bajío SA de CV", "IQA", "ACTIVO"),
    ("PIQ-16", "Metales Calvo SA de CV", "IQA", "INACTIVO"),
    ("PIQ-17", "Pablo López Hernández", "IQA", "ACTIVO"),
    ("PIQ-18", "Global Cast Alloy S.A de C.V.", "IQA/IQB", "ACTIVO"),
    ("PIQ-19", "Roi Briquetting S.A. de C.V.", "IQA/IQB", "ACTIVO"),
    ("PIQ-20", "Olimpo S.A. de C.V.", "IQB", "INACTIVO"),
    ("PIQ-21", "Gama Job S.A. de C.V.", "IQA", "INACTIVO"),
    ("PIQ-22", "Kaizen Mexicana S.A. de C.V.", "IQA", "INACTIVO"),
    ("PIQ-23", "Cimetal S.A. de C.V.", "IQA", "INACTIVO"),
    ("PIQ-24", "Raqsa S.A. de C.V.", "IQA", "INACTIVO"),
    ("PIQ-25", "Non Ferrous S.A. de C.V.", "IQB", "ACTIVO"),
    ("PIQ-26", "Héctor de la Fuente Burgos", "IQA", "INACTIVO"),
    ("PIQ-27", "Omnisource S.A. de C.V.", "IQA", "INACTIVO"),
    ("PIQ-28", "Recuperadora de metales DDR S.A. de C.V.", "IQA", "INACTIVO"),
    ("PIQ-29", "Marco Metales S.A. de C.V.", "IQA", "INACTIVO"),
    ("PIQ-30", "Possehl México S.A. de C.V.", "IQA", "INACTIVO"),
    ("PIQ-31", "Nedec México S.A. de C.V.", "IQA", "ACTIVO"),
    ("PIQ-32", "Maria Fernanda Hernandez Hernandez", "IQB", "INACTIVO"),
    ("PIQ-33", "IPI Refractarios S.A. de C.V.", "IQA", "ACTIVO"),
    ("PIQ-34", "Mario Alberto Castillo Quiroz", "IQB", "INACTIVO"),
    ("PIQ-35", "JRG Comercial S.A. de C.V.", "IQA/IQB", "INACTIVO"),
    ("PIQ-36", "Maria Guadalupe Manriquez Torres", "IQB", "INACTIVO"),
    ("PIQ-37", "Ma. Isabel Bustamante Dominguez", "IQA", "INACTIVO"),
    ("PIQ-38", "Daniel Chowell", "IQB", "ACTIVO"),
    ("PIQ-39", "Marco Antonio Ramirez", "IQB", "INACTIVO"),
    ("PIQ-40", "Recuperadora 'Del Valle'", "IQB", "ACTIVO"),
    ("PIQ-41", "Industriales Inrecba", "IQB", "ACTIVO"),
    ("PIQ-42", "Arturo Guevara", "IQB", "ACTIVO"),
    ("PIQ-43", "Recicladora Las Hadas", "IQB", "ACTIVO"),
    ("PIQ-44", "Reclicladora Camila", "IQB", "INACTIVO"),
    ("PIQ-45", "Martín Díaz", "IQB", "ACTIVO"),
    ("PIQ-46", "Ferro Alloys", "IQA", "ACTIVO"),
    ("PIQ-47", "ICZA Soluciones Industriales", "IQB", "INACTIVO"),
    ("PIQ-48", "Recycling and Metals SKIPER S.A. De C.V.", "IQB", "INACTIVO"),
    ("PIQ-49", "Black Metal 56 S.A. DE C.V", "IQB", "INACTIVO"),
    ("PIQ-50", "Miguel Landín", "IQB", "INACTIVO"),
    ("PIQ-51", "Interamericana de Materiales", "IQA", "INACTIVO"),
    ("PIQ-52", "Brembo", "IQA", "INACTIVO"),
    ("PIQ-53", "Fagor", "IQA", "INACTIVO"),
    ("PIQ-54", "No hay proveedor", "N/A", "N/A"),
    ("PIQ-55", "WF-Trading", "IQA", "ACTIVO"),
    ("PIQ-56", "Prosodio", "IQA", "ACTIVO"),
    ("PIQ-57", "José Luis Bernal", "IQB", "ACTIVO"),
    ("PIQ-58", "Noe Nicasio", "IQB", "INACTIVO"),
    ("PIQ-59", "No hay proveedor", "N/A", "N/A"),
    ("PIQ-60", "Comerzializadora Alloys Guzanz", "IQB", "INACTIVO"),
    ("PIQ-61", "Dimosa", "IQB/IQA", "INACTIVO"),
    ("PIQ-62", "Grupo Magtre", "IQB", "ACTIVO"),
    ("PIQ-63", "No hay proveedor", "N/A", "N/A"),
    ("PIQ-64", "Ecosoluciones", "IQB", "ACTIVO"),
    ("PIQ-65", "Nafta", "IQA", "INACTIVO"),
    ("PIQ-66", "Wilkinson Gary Iron & Metal Inc.", "IQA", "ACTIVO"),
    ("PIQ-67", "Levitated Metals LLC", "IQA", "ACTIVO"),
    ("PIQ-68", "Felipe Maquila", "IQB", "ACTIVO"),
    ("PIQ-69", "Castmet", "IQA", "ACTIVO"),
    ("PIQ-70", "Cranes Industry", "IQA", "ACTIVO"),
    ("PIQ-71", "Recuperadora las vias", "IQB", "ACTIVO"),
    ("PIQ-72", "Sherlym", "IQA", "ACTIVO"),
    ("PIQ-73", "Kalischatarra", "IQA", "ACTIVO"),
    ("PIQ-74", "Hoesch", "IQA", "ACTIVO"),
    ("PIQ-75", "Ichiban", "IQA", "ACTIVO"),
    ("PIQ-76", "Recycle Mexico Ambiental", "IQA", "ACTIVO"),
    ("PIQ-77", "Precozul", "IQA", "ACTIVO"),
    ("PIQ-78", "Siete metales", "IQB", "ACTIVO")
]

# Llamar a la función para insertar proveedores
insertar_proveedores(proveedores)
