import tkinter as tk
from tkinter import ttk, messagebox
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
import queue

# ---------- cola global ----------
peso_queue = queue.Queue()

# ---------- configuración de estabilidad ----------
peso_anterior = None
UMBRAL_ESTABLE = 0.05  # tolerancia de cambio para considerar estable
lecturas_estables = 0
LECTURAS_PARA_ESTABLE = 5  # cuántas lecturas consecutivas dentro del umbral

# ---------- CONFIGURACIÓN ----------
SERIAL_PORT = "COM10"
BAUD_RATE = 9600
LOGO_PATH = "LOGO IQ.PNG"
NOMBRE_IMPRESORA_TERMICA = "CUSTOM P3L"

# ---------- variable global para ventana de tarjeta ----------
tarjeta_ventana = None

# ---------- BASE DE DATOS ----------
def init_db():
    conn = sqlite3.connect("pesajes.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_lote TEXT NOT NULL,
            materia_prima TEXT,
            peso_bruto REAL,
            tara REAL,
            peso_neto REAL,
            tipo_movimiento TEXT,
            usuario_validador TEXT,
            usuario_pesador TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def guardar_lote_con_tara(usuario, subtotal, tara, neto):
    nombre_lote = nombre_combobox.get().strip()
    materia_prima = materia_combobox.get().strip()
    tipo_mov = tipo_mov_var.get().strip()
    pesado_en = pesado_en_combobox.get().strip()

    conn = sqlite3.connect("pesajes.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO lotes (nombre_lote, materia_prima, peso_bruto, tara, peso_neto, tipo_movimiento, usuario_validador, usuario_pesador)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (nombre_lote, materia_prima, subtotal, tara, neto, tipo_mov, usuario[1], usuario[1]))
    conn.commit()
    conn.close()

def obtener_proveedores_activos():
    conn = sqlite3.connect("proveedores.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM proveedores WHERE estatus = 'ACTIVO'")
    proveedores = cursor.fetchall()
    conn.close()
    return [proveedor[0] for proveedor in proveedores]

def obtener_materias_primas():
    conn = sqlite3.connect("mp.db")
    cursor = conn.cursor()
    cursor.execute("SELECT nombre_mp FROM mp")
    materias_primas = [row[0] for row in cursor.fetchall()]
    conn.close()
    return materias_primas

def obtener_pesado_en():
    conn = sqlite3.connect("pesado.db")
    cursor = conn.cursor()
    cursor.execute("SELECT pesado_en FROM pesado")
    pesado_en = [row[0] for row in cursor.fetchall()]
    conn.close()
    return pesado_en

def verificar_usuario_activo(numero_tarjeta):
    conn = sqlite3.connect("usuarios_activos.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE tarjeta = ? AND status = 'activo'", (numero_tarjeta,))
    usuario = cursor.fetchone()
    conn.close()
    return usuario

# ---------- LECTURA DEL PESO ----------
def leer_peso():
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1) as ser:
            while True:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        try:
                            peso = float(line)
                            peso_queue.put(peso)
                        except ValueError:
                            pass
                time.sleep(0.05)
    except serial.SerialException:
        peso_queue.put("ERROR BASCULA")

def procesar_peso_desde_cola():
    global peso_actual, peso_anterior, lecturas_estables

    try:
        while True:
            peso = peso_queue.get_nowait()
            peso_actual = peso
            peso_str = f"{peso:.2f} kg" if isinstance(peso, float) else str(peso)
            if peso_label.cget("text") != peso_str:
                peso_label.config(text=peso_str)

            if isinstance(peso, float) and peso_anterior is not None:
                diferencia = abs(peso - peso_anterior)
                if diferencia <= UMBRAL_ESTABLE:
                    lecturas_estables += 1
                else:
                    lecturas_estables = 0
            else:
                lecturas_estables = 0

            if lecturas_estables >= LECTURAS_PARA_ESTABLE:
                indicador_frame.config(bg="green")
            else:
                indicador_frame.config(bg="red")

            if isinstance(peso, float):
                peso_anterior = peso

    except queue.Empty:
        pass

    app.after(100, procesar_peso_desde_cola)

def mostrar_mensaje_emergente(tipo, mensaje):
    if tipo == "informacion":
        messagebox.showinfo("Información", mensaje)
    elif tipo == "advertencia":
        messagebox.showwarning("Advertencia", mensaje)
    elif tipo == "error":
        messagebox.showerror("Error", mensaje)
    else:
        messagebox.showinfo("Mensaje", mensaje)

# ---------- IMPRESIÓN DE TICKET ----------
def imprimir_ticket_con_logo(usuario, subtotal, tara, neto):
    nombre_lote = nombre_combobox.get().strip()
    materia_prima = materia_combobox.get().strip()
    tipo_mov = tipo_mov_var.get().strip()
    pesado_en = pesado_en_combobox.get().strip()

    ahora = datetime.now()
    fecha_hora_str = ahora.strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs("tickets", exist_ok=True)
    filename = f"ticket_{nombre_lote}_{ahora.strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = os.path.join("tickets", filename)

    ticket_width = 100 * mm
    ticket_height = 230 * mm

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
        c.drawCentredString(ticket_width / 2, y, "TICKET DE PESO")
        y -= 30

        c.setFont("Helvetica", 14)
        c.drawString(18, y, "Tipo Movimiento:")
        y -= 20
        c.setFont("Helvetica", 16)
        c.drawString(14, y, tipo_mov)
        y -= 25

        c.setFont("Helvetica", 14)
        c.drawString(18, y, "Fecha y Hora:")
        y -= 20
        c.setFont("Helvetica", 16)
        c.drawString(14, y, fecha_hora_str)
        y -= 25

        c.setFont("Helvetica", 14)
        c.drawString(18, y, "Proveedor:")
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
        c.drawString(18, y, "Pesado en:")
        y -= 20
        c.setFont("Helvetica", 16)
        c.drawString(14, y, pesado_en)
        y -= 30

        # Mostrar Subtotal, Tara y Neto
        c.setFont("Helvetica", 14)
        c.drawString(18, y, "Subtotal (Bruto):")
        y -= 20
        c.setFont("Helvetica-Bold", 16)
        c.drawString(20, y, f"{subtotal:.2f} kg")
        y -= 25

        c.setFont("Helvetica", 14)
        c.drawString(18, y, "Tara:")
        y -= 20
        c.setFont("Helvetica-Bold", 16)
        c.drawString(20, y, f"{tara:.2f} kg")
        y -= 25

        c.setFont("Helvetica", 14)
        c.drawString(18, y, "Peso Neto:")
        y -= 20
        c.setFont("Helvetica-Bold", 20)
        c.drawString(20, y, f"{neto:.2f} kg")

        y -= 40
        c.setFont("Helvetica", 14)
        c.drawString(18, y, f"Pesador: {usuario[1]}")
        c.showPage()
        c.save()

        mostrar_mensaje_emergente("informacion", f"PDF generado: {pdf_path}")

        if platform.system() == "Windows":
            try:
                win32api.ShellExecute(0, "print", pdf_path, f'"{NOMBRE_IMPRESORA_TERMICA}"', ".", 0)
                mostrar_mensaje_emergente("informacion", "⚠️ Ticket enviado a impresión.")
            except Exception as e:
                mostrar_mensaje_emergente("error", "⚠️ Error al imprimir directamente.")
    except Exception as e:
        mostrar_mensaje_emergente("error", "⚠️ Error al generar el ticket.")

# ---------- VENTANAS ----------
def abrir_ventana_tara(usuario):
    ventana_tara = tk.Toplevel(app)
    ventana_tara.title("Ingresar Tara")
    ventana_tara.geometry("400x250")
    ventana_tara.configure(bg="#f9f9f9")

    tk.Label(ventana_tara, text="Ingrese Tara (kg):", font=("Arial", 16), bg="#f9f9f9").pack(pady=15)
    tara_entry = tk.Entry(ventana_tara, font=("Arial", 18), width=15)
    tara_entry.pack(pady=10)
    tara_entry.focus_set()

    def calcular_y_guardar():
        try:
            tara = float(tara_entry.get())
            subtotal = peso_actual
            peso_neto = subtotal - tara

            if peso_neto < 0:
                mostrar_mensaje_emergente("error", "El peso neto no puede ser negativo.")
                return

            guardar_lote_con_tara(usuario, subtotal, tara, peso_neto)
            imprimir_ticket_con_logo(usuario, subtotal, tara, peso_neto)
            mostrar_mensaje_emergente("informacion", f"✅ Peso neto calculado: {peso_neto:.2f} kg")
            ventana_tara.destroy()

        except ValueError:
            mostrar_mensaje_emergente("error", "⚠️ Ingresa un valor numérico válido para la tara.")

    tk.Button(ventana_tara, text="Confirmar", font=("Arial", 16), bg="#006400", fg="white",
              command=calcular_y_guardar).pack(pady=20)

def abrir_validacion_tarjeta():
    global tarjeta_ventana

    if tarjeta_ventana is not None and tk.Toplevel.winfo_exists(tarjeta_ventana):
        mostrar_mensaje_emergente("advertencia", "La ventana ya está abierta.")
        return

    tarjeta_ventana = tk.Toplevel(app)
    tarjeta_ventana.title("Validar Tarjeta")
    tarjeta_ventana.geometry("400x200")
    tarjeta_ventana.configure(bg="#f0f0f0")

    def on_close():
        global tarjeta_ventana
        tarjeta_ventana.destroy()
        tarjeta_ventana = None

    tarjeta_ventana.protocol("WM_DELETE_WINDOW", on_close)

    tarjeta_label = tk.Label(
        tarjeta_ventana,
        text=" ⚠️ Ingrese número de tarjeta: ⚠️ ",
        font=("Arial", 16),
        bg="#f0f0f0"
    )
    tarjeta_label.pack(pady=10)

    tarjeta_entry = tk.Entry(
        tarjeta_ventana,
        font=("Arial", 20),
        width=25
    )
    tarjeta_entry.pack(pady=10)
    tarjeta_entry.focus_set()

    def on_enter(event):
        numero_tarjeta = tarjeta_entry.get()
        usuario = verificar_usuario_activo(numero_tarjeta)
        if usuario:
            mostrar_mensaje_emergente("informacion", f"Usuario: {usuario[1]} validado.")
            on_close()
            abrir_ventana_tara(usuario)
        else:
            mostrar_mensaje_emergente("error", "⚠️ Usuario no válido o inactivo.")

    tarjeta_entry.bind("<Return>", on_enter)

# ---------- INICIO ----------
init_db()
peso_actual = None
lectura_thread = threading.Thread(target=leer_peso, daemon=True)
lectura_thread.start()

app = tk.Tk()
app.title("Sistema de Pesaje de Lotes")
app.geometry("1000x900")
app.configure(bg="#ffffff")

indicador_frame = tk.Frame(app, width=1000, height=30, bg="red", bd=2, relief="sunken")
indicador_frame.pack(pady=5)

peso_label_title = tk.Label(app, text="PESO ACTUAL", font=("Arial", 25, "bold"), bg="#ffffff", fg="#333")
peso_label_title.pack(pady=(10, 0))

peso_label = tk.Label(app, text="---- kg", font=("Arial", 80, "bold"), fg="#000000", bg="#ffffff")
peso_label.pack(pady=10)

nombre_frame = tk.Frame(app, bg="#f0f0f0")
nombre_frame.pack(pady=20)

tipo_mov_var = tk.StringVar(value="ENTRADA")
tk.Label(nombre_frame, text="Tipo Movimiento:", font=("Arial", 16), bg="#f0f0f0").pack(anchor="w", padx=5, pady=5)
tk.Radiobutton(nombre_frame, text="Entrada", variable=tipo_mov_var, value="ENTRADA", bg="#f0f0f0").pack(anchor="w", padx=5)
tk.Radiobutton(nombre_frame, text="Salida", variable=tipo_mov_var, value="SALIDA", bg="#f0f0f0").pack(anchor="w", padx=5)

nombre_label = tk.Label(nombre_frame, text="Selecciona Código de Proveedor:", font=("Arial", 16), bg="#f0f0f0")
nombre_label.pack(anchor="w", padx=5, pady=5)

proveedores_activos = obtener_proveedores_activos()
proveedores_activos.insert(0, "...")
nombre_combobox = ttk.Combobox(nombre_frame, font=("Arial", 16), width=20, values=proveedores_activos, state="readonly")
nombre_combobox.pack(padx=5, pady=5)
nombre_combobox.set(proveedores_activos[0])

materia_prima_label = tk.Label(nombre_frame, text="Selecciona Tipo de Materia Prima:", font=("Arial", 16), bg="#f0f0f0")
materia_prima_label.pack(anchor="w", padx=5, pady=5)

materias_primas = obtener_materias_primas()
materias_primas.insert(0, "...")
materia_combobox = ttk.Combobox(nombre_frame, font=("Arial", 16), width=20, values=materias_primas, state="readonly")
materia_combobox.pack(padx=5, pady=5)
materia_combobox.set(materias_primas[0])

pesado_en_label = tk.Label(nombre_frame, text="Selecciona donde se esta pesando:", font=("Arial", 16), bg="#f0f0f0")
pesado_en_label.pack(anchor="w", padx=5, pady=5)

pesado_en = obtener_pesado_en()
pesado_en.insert(0, "...")
pesado_en_combobox = ttk.Combobox(nombre_frame, font=("Arial", 16), width=20, values=pesado_en, state="readonly")
pesado_en_combobox.pack(padx=5, pady=5)
pesado_en_combobox.set(pesado_en[0])

validar_tarjeta_btn = tk.Button(app, text="Imprimir con Tarjeta", bg="#800000", fg="white",
                                command=abrir_validacion_tarjeta, font=("Arial", 16, "bold"))
validar_tarjeta_btn.pack(pady=20)

mensaje_label = tk.Label(app, text="", font=("Arial", 14), fg="green", bg="#ffffff")
mensaje_label.pack(pady=10)

procesar_peso_desde_cola()
app.mainloop()
