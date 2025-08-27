import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import serial
import threading
import time
import sqlite3
import os
import platform
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
import win32api

# ---------- CONFIGURACIÓN ----------
SERIAL_PORT = "COM10"
BAUD_RATE = 9600
LOGO_PATH = "LOGO IQ.PNG"
NOMBRE_IMPRESORA_TERMICA = "CUSTOM P3L"  # Cambiar si tienes otro nombre de impresora

# ---------- BASE DE DATOS ----------
def init_db():
    conn = sqlite3.connect("pesajes.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_lote TEXT NOT NULL,
            peso REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    # Verificar si la columna materia_prima ya existe
    cursor.execute("PRAGMA table_info(lotes)")
    columnas = [col[1] for col in cursor.fetchall()]
    if "materia_prima" not in columnas:
        cursor.execute("ALTER TABLE lotes ADD COLUMN materia_prima TEXT")
        conn.commit()

    conn.close()

def guardar_lote(nombre_lote, materia_prima, peso):
    conn = sqlite3.connect("pesajes.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO lotes (nombre_lote, materia_prima, peso) VALUES (?, ?, ?)", (nombre_lote, materia_prima, peso))
    conn.commit()
    conn.close()

def obtener_proveedores_activos():
    conn = sqlite3.connect("proveedores.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM proveedores WHERE estatus='ACTIVO'")
    proveedores = cursor.fetchall()
    conn.close()
    return [proveedor[1] for proveedor in proveedores]

def obtener_materias_primas():
    conn = sqlite3.connect("mp.db")
    cursor = conn.cursor()
    cursor.execute("SELECT nombre_mp FROM mp")
    materias_primas = [row[0] for row in cursor.fetchall()]
    conn.close()
    return materias_primas

def mostrar_info_proveedor(event=None):
    nombre = nombre_combobox.get()

    if nombre == "...":
        proveedor_info_label.config(text="⚠️ Selecciona un proveedor válido.", fg="red")
        imprimir_btn.config(state="disabled")
        return

    conn = sqlite3.connect("proveedores.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM proveedores WHERE codigo_proveedor = ?", (nombre,))
    proveedor = cursor.fetchone()
    conn.close()

    if proveedor:
        texto = (
            f"📦 Razon Social: {proveedor[2]}\n"
            f"🏢 Empresa Compradora: {proveedor[3]}\n"
            f"✅ Estatus: {proveedor[4]}"
        )
        proveedor_info_label.config(text=texto, fg="black")
        imprimir_btn.config(state="normal")
    else:
        proveedor_info_label.config(text="Proveedor no encontrado.", fg="red")
        imprimir_btn.config(state="disabled")

# ---------- LECTURA DEL PESO ----------
def leer_peso():
    global peso_actual
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
            while True:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    try:
                        peso_actual = float(line)
                        actualizar_peso(peso_actual)
                    except ValueError:
                        continue
                time.sleep(0.2)
    except serial.SerialException:
        actualizar_peso("ERROR BASCULA")

def actualizar_peso(peso):
    peso_str = f"{peso:.2f} kg" if isinstance(peso, float) else str(peso)
    peso_label.config(text=peso_str)

def mostrar_mensaje(texto, color="green"):
    mensaje_label.config(text=texto, fg=color)
    mensaje_label.after(5000, lambda: mensaje_label.config(text=""))

def imprimir_ticket_con_logo():
    if not isinstance(peso_actual, float):
        mostrar_mensaje("No hay un peso válido. Revisa conexión.", "red")
        return

    nombre_lote = nombre_combobox.get().strip()
    if not nombre_lote or nombre_lote == "...":
        mostrar_mensaje("Selecciona un proveedor válido.", "red")
        return

    materia_prima = materia_combobox.get().strip()
    if not materia_prima or materia_prima == "...":
        mostrar_mensaje("Selecciona un tipo de materia prima.", "red")
        return

    guardar_lote(nombre_lote, materia_prima, peso_actual)

    ahora = datetime.now()
    fecha_hora_str = ahora.strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs("tickets", exist_ok=True)
    filename = f"ticket_{nombre_lote}_{ahora.strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = os.path.join("tickets", filename)

    ticket_width = 100 * mm
    ticket_height = 280 * mm

    try:
        c = canvas.Canvas(pdf_path, pagesize=(ticket_width, ticket_height))

        logo_width = 40 * mm
        logo_height = 15 * mm
        logo_x = (ticket_width - logo_width) / 2
        logo_y = ticket_height - logo_height - 10

        try:
            c.drawImage(LOGO_PATH, logo_x, logo_y, width=logo_width, height=logo_height, preserveAspectRatio=True)
        except Exception as e:
            print("Error al cargar el logo:", e)

        y = logo_y - 20

        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(ticket_width / 2, y, "TICKET DE PESO INTERNO")
        y -= 30

        c.setFont("Helvetica", 14)
        c.drawString(18, y, "Fecha y Hora:")
        y -= 20
        c.setFont("Helvetica", 16)
        c.drawString(14, y, fecha_hora_str)
        y -= 25

        c.setFont("Helvetica", 14)
        c.drawString(18, y, "Código de Proveedor:")
        y -= 20
        c.setFont("Helvetica", 16)
        c.drawString(14, y, nombre_lote)
        y -= 25

        c.setFont("Helvetica", 14)
        c.drawString(18, y, "Materia Prima:")
        y -= 20
        c.setFont("Helvetica", 16)
        c.drawString(14, y, materia_prima)
        y -= 25

        c.setFont("Helvetica", 14)
        c.drawString(18, y, "Peso:")
        y -= 20
        c.setFont("Helvetica-Bold", 18)
        c.drawString(20, y, f"{peso_actual:.2f} kg")

        c.showPage()
        c.save()

        mostrar_mensaje(f"PDF generado: {pdf_path}")

        if platform.system() == "Windows":
            try:
                win32api.ShellExecute(0, "printto", pdf_path, f'"{NOMBRE_IMPRESORA_TERMICA}"', ".", 0)
                mostrar_mensaje("Ticket enviado a impresión.")
            except Exception as e:
                mostrar_mensaje("Error al imprimir directamente.", "red")
    except Exception as e:
        mostrar_mensaje("Error al generar el ticket.", "red")


# ---------- INTERFAZ ----------
app = tk.Tk()
app.title("Sistema de Pesaje de Lotes")
app.geometry("1000x900")
app.configure(bg="#ffffff")

# Logo
try:
    logo_img = Image.open(LOGO_PATH)
    logo_img = logo_img.resize((200, 100))
    logo_tk = ImageTk.PhotoImage(logo_img)
    logo_label = tk.Label(app, image=logo_tk, bg="#ffffff")
    logo_label.pack(pady=10)
except Exception as e:
    print("No se pudo cargar el logo:", e)

# Peso actual
peso_label_title = tk.Label(app, text="PESO ACTUAL", font=("Arial", 25, "bold"), bg="#ffffff", fg="#333")
peso_label_title.pack(pady=(10, 0))

peso_label = tk.Label(app, text="---- kg", font=("Arial", 80, "bold"), fg="#000000", bg="#ffffff")
peso_label.pack(pady=10)

# Campo proveedor
nombre_frame = tk.Frame(app, bg="#f0f0f0")
nombre_frame.pack(pady=20)

nombre_label = tk.Label(nombre_frame, text="Selecciona Código de Proveedor:", font=("Arial", 16), bg="#f0f0f0")
nombre_label.pack(anchor="w")

proveedores_activos = obtener_proveedores_activos()
proveedores_activos.insert(0, "...")
nombre_combobox = ttk.Combobox(nombre_frame, font=("Arial", 20), width=50, values=proveedores_activos, state="readonly")
nombre_combobox.pack(pady=5)
nombre_combobox.set(proveedores_activos[0])
nombre_combobox.bind("<<ComboboxSelected>>", mostrar_info_proveedor)

proveedor_info_label = tk.Label(nombre_frame, text="", font=("Arial", 26), bg="#f0f0f0", justify="left")
proveedor_info_label.pack(pady=5, anchor="w")

# Materia Prima
materia_prima_label = tk.Label(nombre_frame, text="Selecciona Tipo de Materia Prima:", font=("Arial", 16), bg="#f0f0f0")
materia_prima_label.pack(anchor="w")

materias_primas = obtener_materias_primas()
materias_primas.insert(0, "...")
materia_combobox = ttk.Combobox(nombre_frame, font=("Arial", 20), width=50, values=materias_primas, state="readonly")
materia_combobox.pack(pady=5)
materia_combobox.set(materias_primas[0])

# Botones
estilo_botones = {
    "font": ("Arial", 16, "bold"),
    "padx": 10,
    "pady": 5,
    "width": 15,
    "bd": 0
}

boton_frame = tk.Frame(app, bg="#f0f0f0")
boton_frame.pack(pady=20)

mensaje_label = tk.Label(app, text="", font=("Arial", 14), fg="green", bg="#ffffff")
mensaje_label.pack(pady=10)

imprimir_btn = tk.Button(
    boton_frame, text="Imprimir y Guardar", bg="#800000", fg="white",
    command=imprimir_ticket_con_logo, state="disabled", **estilo_botones
)
imprimir_btn.pack(side="left", padx=10)

# ---------- INICIO ----------
init_db()
peso_actual = None
lectura_thread = threading.Thread(target=leer_peso, daemon=True)
lectura_thread.start()

app.mainloop()
