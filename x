import sqlite3

usuario = validar_usuario_existe("6300444")

if usuario:
    print("Usuario encontrado:", usuario)
else:
    print("Usuario no encontrado")
