import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import sqlite3
import os
import platform
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
import queue
# win32api import is optional (Windows printing)
try:
    import win32api
except Exception:
    win32api = None

# ----------------- CONFIG -----------------
DB_FILE = "pesajes.db"
PROV_DB = "proveedores.db"
MP_DB = "mp.db"
PESADO_DB = "pesado.db"
USUARIOS_DB = "usuarios_activos.db"
LOGO_PATH = "LOGO IQ.PNG"
PRINTER_NAME = "CUSTOM P3L"

# ----------------- GLOBALS -----------------
peso_queue = queue.Queue()
peso_actual = None
peso_anterior = None
lecturas_estables = 0
UMBRAL_ESTABLE = 0.05
LECTURAS_PARA_ESTABLE = 5

tarjeta_ventana = None

# ----------------- DB INIT -----------------
def init_db():
    """Crea la tabla si no existe. No borra nada existente (preserva autoincrement)."""
    conn = sqlite3.connect(DB_FILE)
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
            pesado_en TEXT,
            usuario_validador TEXT,
            usuario_pesador TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# ----------------- HELPERS DB -----------------
def fetch_proveedores_activos():
    try:
        conn = sqlite3.connect(PROV_DB)
        c = conn.cursor()
        c.execute("SELECT codigo_proveedor FROM proveedores")
        rows = [r[0] for r in c.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []

def fetch_materias_primas():
    try:
        conn = sqlite3.connect(MP_DB)
        c = conn.cursor()
        c.execute("SELECT nombre_mp FROM mp")
        rows = [r[0] for r in c.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []

def fetch_pesado_en():
    try:
        conn = sqlite3.connect(PESADO_DB)
        c = conn.cursor()
        c.execute("SELECT pesado_en FROM pesado")
        rows = [r[0] for r in c.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []

def verificar_usuario_activo(numero_tarjeta):
    try:
        conn = sqlite3.connect(USUARIOS_DB)
        c = conn.cursor()
        c.execute("SELECT * FROM usuarios WHERE tarjeta = ? AND status = 'activo'", (numero_tarjeta,))
        u = c.fetchone()
        conn.close()
        return u
    except Exception:
        return None

# ----------------- NUEVO: obtener usuarios activos (por nombre) -----------------
def obtener_usuarios_activos():
    try:
        conn = sqlite3.connect(USUARIOS_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT nombre FROM usuarios WHERE status = 'activo'")
        usuarios = [row[0] for row in cursor.fetchall()]
        conn.close()
        return usuarios
    except Exception:
        return []

# ----------------- PESO (simulado para pruebas) -----------------
def leer_peso_simulado():
    """Simulación: empuja 100.0 kg constantemente para pruebas."""
    global peso_actual
    while True:
        peso = 100.0
        peso_queue.put(peso)
        time.sleep(0.1)

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

            indicador_frame.config(bg="green" if lecturas_estables >= LECTURAS_PARA_ESTABLE else "red")

            if isinstance(peso, float):
                peso_anterior = peso
    except queue.Empty:
        pass
    app.after(100, procesar_peso_desde_cola)

# ----------------- UI: proveedor info -----------------
def mostrar_info_proveedor(event=None):
    nombre = nombre_combobox.get()
    if nombre == "..." or not nombre:
        proveedor_info_label.config(text="⚠️ Selecciona un proveedor válido.", fg="red")
        validar_tarjeta_btn.config(state="disabled")
        return
    try:
        conn = sqlite3.connect(PROV_DB)
        c = conn.cursor()
        c.execute("SELECT * FROM proveedores WHERE codigo_proveedor = ?", (nombre,))
        prov = c.fetchone()
        conn.close()
    except Exception:
        prov = None

    if prov:
        texto = f"📦 Razón Social: {prov[1]}\n🏢 Empresa Compradora: {prov[2]}\n✅ Estatus: {prov[3]}"
        proveedor_info_label.config(text=texto, fg="black")
        validar_tarjeta_btn.config(state="normal")
    else:
        proveedor_info_label.config(text="Proveedor no encontrado.", fg="red")
        validar_tarjeta_btn.config(state="disabled")

# ----------------- VENTANA TARA -----------------
def abrir_ventana_tara():
    if nombre_combobox.get() in (None, "...") or materia_combobox.get() in (None, "...") or pesado_en_combobox.get() in (None, "..."):
        messagebox.showerror("Error", "Selecciona proveedor, materia prima y donde se está pesando antes.")
        return

    ventana = tk.Toplevel(app)
    ventana.title("Ingresar Tara")
    ventana.geometry("380x200")
    ventana.configure(bg="#f7f7f7")

    tk.Label(ventana, text="Ingrese Tara (kg):", font=("Arial", 14), bg="#f7f7f7").pack(pady=12)
    entrada = tk.Entry(ventana, font=("Arial", 18))
    entrada.pack(pady=6)
    entrada.focus_set()

    def on_confirm():
        nonlocal ventana
        try:
            tara_val = float(entrada.get())
        except Exception:
            messagebox.showerror("Error", "Ingresa un valor numérico válido para la tara.")
            return
        subtotal = peso_actual
        neto = subtotal - tara_val
        if neto < 0:
            messagebox.showerror("Error", "Peso neto negativo. Revisa tara.")
            return

        nombre_lote = nombre_combobox.get().strip()
        materia = materia_combobox.get().strip()
        tipo_mov = tipo_mov_var.get().strip()
        pesado_en = pesado_en_combobox.get().strip()

        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("""
                INSERT INTO lotes (nombre_lote, materia_prima, peso_bruto, tara, peso_neto, tipo_movimiento, pesado_en, usuario_validador, usuario_pesador)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (nombre_lote, materia, subtotal, tara_val, neto, tipo_mov, pesado_en, "TEMP", "TEMP"))
            conn.commit()
            lote_id = c.lastrowid
            conn.close()
        except Exception as e:
            messagebox.showerror("Error DB", f"No se pudo guardar el lote: {e}")
            ventana.destroy()
            return

        ventana.destroy()
        abrir_validacion_tarjeta(lote_id)

    tk.Button(ventana, text="Confirmar", font=("Arial", 14), bg="#007a00", fg="white", command=on_confirm).pack(pady=14)

# ----------------- VENTANA TARJETA -----------------
def abrir_validacion_tarjeta(lote_id):
    global tarjeta_ventana
    if tarjeta_ventana is not None and tk.Toplevel.winfo_exists(tarjeta_ventana):
        messagebox.showwarning("Advertencia", "Ya hay una ventana de tarjeta abierta.")
        return

    tarjeta_ventana = tk.Toplevel(app)
    tarjeta_ventana.title("Validar Tarjeta")
    tarjeta_ventana.geometry("420x220")
    tarjeta_ventana.configure(bg="#f0f0f0")

    tk.Label(tarjeta_ventana, text="Inserta número de tarjeta:", font=("Arial", 14), bg="#f0f0f0").pack(pady=12)
    entrada = tk.Entry(tarjeta_ventana, font=("Arial", 18), width=26)
    entrada.pack(pady=8)
    entrada.focus_set()

    processed = {"done": False}

    def procesar_tarjeta(event=None):
        if processed["done"]:
            return
        processed["done"] = True

        numero = entrada.get().strip()
        if not numero:
            messagebox.showerror("Error", "No se detectó número de tarjeta.")
            tarjeta_ventana.destroy()
            return

        usuario = verificar_usuario_activo(numero)
        if not usuario:
            messagebox.showerror("Error", "Usuario no válido o inactivo.")
            tarjeta_ventana.destroy()
            return

        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE lotes SET usuario_validador = ?, usuario_pesador = ? WHERE id = ?", (usuario[1], usuario[1], lote_id))
            conn.commit()
            conn.close()
        except Exception as e:
            messagebox.showerror("Error DB", f"No se pudo actualizar lote: {e}")
            tarjeta_ventana.destroy()
            return

        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id, nombre_lote, materia_prima, peso_bruto, tara, peso_neto, tipo_movimiento, pesado_en, usuario_validador, usuario_pesador, timestamp FROM lotes WHERE id = ?", (lote_id,))
            fila = c.fetchone()
            conn.close()
        except Exception as e:
            messagebox.showerror("Error DB", f"No se pudo leer lote: {e}")
            tarjeta_ventana.destroy()
            return

        if not fila:
            messagebox.showerror("Error", "Registro del lote no encontrado.")
            tarjeta_ventana.destroy()
            return

        tarjeta_ventana.destroy()
        generar_e_imprimir_pdf_desde_fila(fila)
        limpiar_formulario()

    entrada.bind("<Return>", procesar_tarjeta)

# ----------------- IMPRIMIR (ticket) -----------------
def generar_e_imprimir_pdf_desde_fila(fila):
    try:
        (lote_id, nombre_lote, materia_prima, bruto, tara, neto, tipo_mov, pesado_en, usuario_validador, usuario_pesador, timestamp) = fila

        os.makedirs("tickets", exist_ok=True)
        ahora = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = str(nombre_lote).replace(" ", "_").replace("/", "_")
        filename = f"ticket_{lote_id}_{safe_name}_{ahora}.pdf"
        pdf_path = os.path.join(os.getcwd(), "tickets", filename)

        ticket_w = 100 * mm
        ticket_h = 230 * mm
        c = canvas.Canvas(pdf_path, pagesize=(ticket_w, ticket_h))

        try:
            logo_w = 40 * mm
            logo_h = 15 * mm
            logo_x = (ticket_w - logo_w) / 2
            logo_y = ticket_h - logo_h - 10
            c.drawImage(LOGO_PATH, logo_x, logo_y, width=logo_w, height=logo_h, preserveAspectRatio=True)
        except Exception:
            logo_y = ticket_h - 10

        y = logo_y - 20
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(ticket_w / 2, y, "TICKET DE PESO")
        y -= 30

        c.setFont("Helvetica", 14)
        c.drawString(18, y, f"ID Lote: {lote_id}"); y -= 20
        c.drawString(18, y, "Tipo Movimiento:"); y -= 20
        c.setFont("Helvetica", 16)
        c.drawString(14, y, str(tipo_mov)); y -= 25
        c.setFont("Helvetica", 14)
        c.drawString(18, y, "Fecha y Hora:"); y -= 20
        c.setFont("Helvetica", 16)
        fecha_str = str(timestamp) if timestamp else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.drawString(14, y, fecha_str); y -= 25
        c.setFont("Helvetica", 14)
        c.drawString(18, y, "Proveedor:"); y -= 20
        c.setFont("Helvetica", 16)
        c.drawString(14, y, str(nombre_lote)); y -= 25
        c.setFont("Helvetica", 14)
        c.drawString(18, y, "Materia Prima:"); y -= 20
        c.setFont("Helvetica", 16)
        c.drawString(14, y, str(materia_prima)); y -= 25
        c.setFont("Helvetica", 14)
        c.drawString(18, y, "Pesado en:"); y -= 20
        c.setFont("Helvetica", 16)
        c.drawString(14, y, str(pesado_en)); y -= 30
        c.setFont("Helvetica", 14)
        c.drawString(18, y, "Subtotal (Bruto):"); y -= 20
        c.setFont("Helvetica-Bold", 16)
        c.drawString(20, y, f"{(bruto or 0):.2f} kg"); y -= 25
        c.setFont("Helvetica", 14)
        c.drawString(18, y, "Tara:"); y -= 20
        c.setFont("Helvetica-Bold", 16)
        c.drawString(20, y, f"{(tara or 0):.2f} kg"); y -= 25
        c.setFont("Helvetica", 14)
        c.drawString(18, y, "Peso Neto:"); y -= 20
        c.setFont("Helvetica-Bold", 20)
        c.drawString(20, y, f"{(neto or 0):.2f} kg"); y -= 40
        c.setFont("Helvetica", 14)
        c.drawString(18, y, f"Pesador: {usuario_pesador or ''}"); y -= 18

        c.showPage()
        c.save()

        messagebox.showinfo("Información", f"Ticket guardado correctamente: {pdf_path}")

        if platform.system() == "Windows" and win32api is not None:
            try:
                win32api.ShellExecute(0, "print", pdf_path, f'"{PRINTER_NAME}"', ".", 0)
            except Exception as e:
                messagebox.showwarning("Impresión", f"No se pudo enviar a la impresora: {e}")

    except Exception as e:
        messagebox.showerror("Error impresión", f"Ocurrió un error al generar el ticket: {e}")

# ----------------- LIMPIAR FORMULARIO -----------------
def limpiar_formulario():
    nombre_combobox.set("...")
    proveedor_info_label.config(text="")
    materia_combobox.set("...")
    pesado_en_combobox.set("...")
    tipo_mov_var.set("ENTRADA")

# ----------------- REPORTE DIARIO (sin impresión) -----------------
def imprimir_reporte_diario(usuario):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        inicio_dia = f"{fecha_hoy} 00:00:00"
        fin_dia = f"{fecha_hoy} 23:59:59"

        cursor.execute("""
            SELECT id, nombre_lote, materia_prima, pesado_en, tara, peso_neto
            FROM lotes
            WHERE usuario_pesador = ? AND timestamp BETWEEN ? AND ?
            ORDER BY id ASC
        """, (usuario, inicio_dia, fin_dia))

        registros = cursor.fetchall()
        conn.close()

        if not registros:
            messagebox.showinfo("Información", f"No hay registros de hoy para {usuario}.")
            return

        total_pesajes = len(registros)
        peso_total = sum(r[5] for r in registros if r[5] is not None)

        os.makedirs("reportes", exist_ok=True)
        ahora = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path = os.path.join("reportes", f"reporte_{usuario}_{ahora}.pdf")

        from reportlab.lib.pagesizes import LETTER
        c = canvas.Canvas(pdf_path, pagesize=LETTER)
        width, height = LETTER

        # Márgenes
        margen_izq = 40
        margen_der = width - 40
        y_inicio = height - 80

        # Logo
        try:
            logo_w = 80
            logo_h = 40
            c.drawImage(LOGO_PATH, (width - logo_w)/2, y_inicio, width=logo_w, height=logo_h, preserveAspectRatio=True)
        except Exception:
            pass

        y = y_inicio - 60
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(width/2, y, f"Reporte Diario de Pesajes - {usuario}")
        y -= 30
        c.setFont("Helvetica", 12)
        c.drawCentredString(width/2, y, f"Fecha: {fecha_hoy}")
        y -= 40

        # Ancho de columnas relativo a los márgenes
        columnas = {
            "ID": 0.05,
            "Proveedor": 0.25,
            "Materia Prima": 0.25,
            "Pesado en": 0.2,
            "Tara": 0.125,
            "Peso Neto": 0.125
        }

        # Posición de cada columna
        x_positions = {}
        x = margen_izq
        for col, propor in columnas.items():
            x_positions[col] = x
            x += (margen_der - margen_izq) * propor

        # Cabecera
        c.setFont("Helvetica-Bold", 12)
        for col in columnas.keys():
            if col in ["Tara", "Peso Neto"]:
                c.drawRightString(x_positions[col] + (margen_der - margen_izq)*columnas[col] - 2, y, col)
            else:
                c.drawString(x_positions[col], y, col)
        y -= 20
        c.line(margen_izq, y, margen_der, y)
        y -= 15

        # Filas
        c.setFont("Helvetica", 11)
        for (id_lote, proveedor, materia_prima, pesado_en, tara, peso_neto) in registros:
            if y < 80:
                c.showPage()
                c.setFont("Helvetica", 11)
                y = height - 80

            c.drawString(x_positions["ID"], y, str(id_lote))
            c.drawString(x_positions["Proveedor"], y, proveedor if proveedor else "—")
            c.drawString(x_positions["Materia Prima"], y, materia_prima if materia_prima else "—")
            c.drawString(x_positions["Pesado en"], y, pesado_en if pesado_en else "—")
            c.drawRightString(x_positions["Tara"] + (margen_der - margen_izq)*columnas["Tara"] - 2, y, f"{tara:.2f}" if tara else "0.00")
            c.drawRightString(x_positions["Peso Neto"] + (margen_der - margen_izq)*columnas["Peso Neto"] - 2, y, f"{peso_neto:.2f}" if peso_neto else "0.00")
            y -= 20

        # Línea final
        y -= 10
        c.line(margen_izq, y, margen_der, y)
        y -= 30

        # Resumen
        c.setFont("Helvetica-Bold", 13)
        c.drawString(margen_izq, y, f"🧾 Total de pesajes: {total_pesajes}")
        y -= 20
        c.drawString(margen_izq, y, f"⚖️ Peso neto acumulado: {peso_total:.2f} kg")

        c.save()

        messagebox.showinfo("Información", f"Reporte generado correctamente: {pdf_path}")

    except Exception as e:
        messagebox.showerror("Error", f"Error generando el reporte: {e}")

# ----------------- VENTANA REPORTE -----------------
def abrir_ventana_reporte():
    ventana_reporte = tk.Toplevel(app)
    ventana_reporte.title("Imprimir Reporte Diario")
    ventana_reporte.geometry("500x300")
    ventana_reporte.configure(bg="#f7f7f7")

    tk.Label(ventana_reporte, text="Selecciona el usuario:", font=("Arial", 16), bg="#f7f7f7").pack(pady=15)
    usuarios = obtener_usuarios_activos()
    if not usuarios:
        usuarios = ["(No hay usuarios activos)"]

    usuario_combobox = ttk.Combobox(ventana_reporte, font=("Arial", 14), values=usuarios, state="readonly", width=30)
    usuario_combobox.pack(pady=10)
    if usuarios:
        usuario_combobox.set(usuarios[0])

    def confirmar_reporte():
        usuario = usuario_combobox.get()
        if usuario in ("", "(No hay usuarios activos)"):
            messagebox.showerror("Error", "Selecciona un usuario válido.")
            return
        imprimir_reporte_diario(usuario)
        ventana_reporte.destroy()

    tk.Button(ventana_reporte, text="Generar Reporte", bg="#004080", fg="white",
              font=("Arial", 14, "bold"), command=confirmar_reporte).pack(pady=25)

# ----------------- INTERFAZ -----------------
init_db()

app = tk.Tk()
app.title("Sistema de Pesaje de Lotes")
app.geometry("1000x900")
app.configure(bg="#ffffff")

indicador_frame = tk.Frame(app, width=1000, height=30, bg="red", bd=2, relief="sunken")
indicador_frame.pack(pady=5)

tk.Label(app, text="PESO ACTUAL", font=("Arial", 25, "bold"), bg="#ffffff", fg="#333").pack(pady=(10, 0))
peso_label = tk.Label(app, text="---- kg", font=("Arial", 80, "bold"), fg="#000000", bg="#ffffff")
peso_label.pack(pady=10)

nombre_frame = tk.Frame(app, bg="#f0f0f0")
nombre_frame.pack(pady=20)

tipo_mov_var = tk.StringVar(value="ENTRADA")
tk.Label(nombre_frame, text="Tipo Movimiento:", font=("Arial", 16), bg="#f0f0f0").pack(anchor="w", padx=5, pady=5)
tk.Radiobutton(nombre_frame, text="Entrada", variable=tipo_mov_var, value="ENTRADA", bg="#f0f0f0").pack(anchor="w", padx=5)
tk.Radiobutton(nombre_frame, text="Salida", variable=tipo_mov_var, value="SALIDA", bg="#f0f0f0").pack(anchor="w", padx=5)

tk.Label(nombre_frame, text="Selecciona Código de Proveedor:", font=("Arial", 16), bg="#f0f0f0").pack(anchor="w", padx=5, pady=5)
proveedores = fetch_proveedores_activos()
proveedores.insert(0, "...")
nombre_combobox = ttk.Combobox(nombre_frame, font=("Arial", 16), width=20, values=proveedores, state="readonly")
nombre_combobox.pack(padx=5, pady=5)
nombre_combobox.set("...")
nombre_combobox.bind("<<ComboboxSelected>>", mostrar_info_proveedor)

proveedor_info_label = tk.Label(nombre_frame, text="", font=("Arial", 14), bg="#f0f0f0", justify="left")
proveedor_info_label.pack(anchor="w", padx=5, pady=5)

tk.Label(nombre_frame, text="Selecciona Tipo de Materia Prima:", font=("Arial", 16), bg="#f0f0f0").pack(anchor="w", padx=5, pady=5)
materias = fetch_materias_primas()
materias.insert(0, "...")
materia_combobox = ttk.Combobox(nombre_frame, font=("Arial", 16), width=20, values=materias, state="readonly")
materia_combobox.pack(padx=5, pady=5)
materia_combobox.set("...")

tk.Label(nombre_frame, text="Selecciona donde se esta pesando:", font=("Arial", 16), bg="#f0f0f0").pack(anchor="w", padx=5, pady=5)
pesado_list = fetch_pesado_en()
pesado_list.insert(0, "...")
pesado_en_combobox = ttk.Combobox(nombre_frame, font=("Arial", 16), width=20, values=pesado_list, state="readonly")
pesado_en_combobox.pack(padx=5, pady=5)
pesado_en_combobox.set("...")

validar_tarjeta_btn = tk.Button(app, text="Imprimir con Tarjeta", bg="#800000", fg="white", command=abrir_ventana_tara, font=("Arial", 16, "bold"))
validar_tarjeta_btn.pack(pady=20)

reporte_btn = tk.Button(app, text="📄 Generar Reporte Diario", bg="#004080", fg="white", font=("Arial", 16, "bold"), command=abrir_ventana_reporte)
reporte_btn.pack(pady=10)

mensaje_label = tk.Label(app, text="", font=("Arial", 14), fg="green", bg="#ffffff")
mensaje_label.pack(pady=10)

t = threading.Thread(target=leer_peso_simulado, daemon=True)
t.start()
procesar_peso_desde_cola()

app.mainloop()
