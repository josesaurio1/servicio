import tkinter as tk
from tkinter import ttk, messagebox
from reconocimiento_facial import ReconocimientoFacial
from qr_manager import QRManager
from registro_alumno import RegistroAlumno, CARRERAS
from database import Database
from generador_documentos import GeneradorDocumentos
import threading
import os
import hashlib
from datetime import datetime, date

for carpeta in ['fotos_alumnos', 'capturas', 'codigos_qr', 'modelos', 'pdfs_qr', 'documentos']:
    os.makedirs(carpeta, exist_ok=True)

# ============================================================
# COLORES TECNM
# ============================================================
AZUL       = '#1B396A'
AZUL_CLARO = '#2a4f8f'
GRIS       = '#807E82'
BLANCO     = '#FFFFFF'
FONDO      = '#f0f2f5'
VERDE      = '#2ecc71'
ROJO       = '#e74c3c'
HEADER_BG  = '#0d1f3c'   # Azul más oscuro para que el logo se vea

def estilo_boton(btn, tipo='primario'):
    if tipo == 'primario':
        btn.configure(bg=AZUL, fg=BLANCO, activebackground=AZUL_CLARO,
                     activeforeground=BLANCO, relief='flat', cursor='hand2',
                     font=('Arial', 11, 'bold'), padx=20, pady=10)
    elif tipo == 'secundario':
        btn.configure(bg=GRIS, fg=BLANCO, activebackground='#666',
                     activeforeground=BLANCO, relief='flat', cursor='hand2',
                     font=('Arial', 11), padx=20, pady=8)

# ============================================================
# LOGIN MAESTRO
# ============================================================
class LoginMaestro:
    def __init__(self, root, callback_exito, callback_cancelar=None):
        self.db = Database()
        self.callback_exito = callback_exito
        self.callback_cancelar = callback_cancelar
        self.ventana = tk.Toplevel(root)
        self.ventana.title("Acceso Administrativo - TECNM")
        self.ventana.geometry("420x360")
        self.ventana.configure(bg=FONDO)
        self.ventana.grab_set()
        self.ventana.resizable(False, False)
        # Si cierra con X también cancela
        self.ventana.protocol("WM_DELETE_WINDOW", self.cancelar)

        tk.Frame(self.ventana, bg=AZUL, height=70).pack(fill='x')
        tk.Label(self.ventana, text="🔐 Acceso Administrativo",
                font=('Arial', 15, 'bold'), bg=AZUL, fg=BLANCO).place(x=0, y=15, width=420)

        frame = tk.Frame(self.ventana, bg=FONDO)
        frame.pack(pady=30)

        for i, (label, attr, show) in enumerate([
            ("Usuario:", "entry_usuario", ""),
            ("Contraseña:", "entry_password", "*")
        ]):
            tk.Label(frame, text=label, bg=FONDO, fg=AZUL,
                    font=('Arial', 11, 'bold')).grid(row=i, column=0, padx=15, pady=10, sticky='w')
            e = tk.Entry(frame, font=('Arial', 11), width=22, show=show, relief='solid', bd=1)
            e.grid(row=i, column=1, pady=10)
            setattr(self, attr, e)

        self.entry_password.bind('<Return>', lambda e: self.verificar())

        frame_btns = tk.Frame(self.ventana, bg=FONDO)
        frame_btns.pack()
        tk.Button(frame_btns, text="Iniciar Sesión", command=self.verificar,
                 bg=AZUL, fg=BLANCO, font=('Arial', 11, 'bold'), relief='flat',
                 cursor='hand2', padx=15, pady=8).pack(side='left', padx=8)
        tk.Button(frame_btns, text="Cancelar", command=self.cancelar,
                 bg=GRIS, fg=BLANCO, font=('Arial', 11), relief='flat',
                 cursor='hand2', padx=15, pady=8).pack(side='left', padx=8)

        self.label_error = tk.Label(self.ventana, text="", bg=FONDO, fg=ROJO, font=('Arial', 10))
        self.label_error.pack(pady=5)

    def cancelar(self):
        self.ventana.destroy()
        if self.callback_cancelar:
            self.callback_cancelar()

    def verificar(self):
        usuario = self.entry_usuario.get()
        password = self.entry_password.get()
        if not usuario or not password:
            self.label_error.config(text="⚠️ Ingresa usuario y contraseña")
            return
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        maestro = self.db.obtener_datos(
            "SELECT * FROM maestros WHERE usuario=%s AND password=%s AND activo=1",
            (usuario, password_hash)
        )
        if maestro:
            self.ventana.destroy()
            self.callback_exito(maestro[0])
        else:
            self.label_error.config(text="❌ Usuario o contraseña incorrectos")

# ============================================================
# LOGIN ALUMNO
# ============================================================
class LoginAlumno:
    def __init__(self, root, callback_exito, callback_cancelar=None):
        self.db = Database()
        self.callback_exito = callback_exito
        self.callback_cancelar = callback_cancelar
        self.ventana = tk.Toplevel(root)
        self.ventana.title("Acceso Estudiante - TECNM")
        self.ventana.geometry("420x400")
        self.ventana.configure(bg=FONDO)
        self.ventana.grab_set()
        self.ventana.resizable(False, False)
        self.ventana.protocol("WM_DELETE_WINDOW", self.cancelar)

        tk.Frame(self.ventana, bg=AZUL, height=70).pack(fill='x')
        tk.Label(self.ventana, text="🎓 Acceso Estudiante",
                font=('Arial', 15, 'bold'), bg=AZUL, fg=BLANCO).place(x=0, y=15, width=420)

        tk.Label(self.ventana, text="Usuario: Número de Control",
                bg=FONDO, fg=GRIS, font=('Arial', 9)).pack(pady=(40, 0))
        tk.Label(self.ventana, text="Contraseña: Iniciales apellidos + No. Control",
                bg=FONDO, fg=GRIS, font=('Arial', 9)).pack()
        tk.Label(self.ventana, text="Ejemplo: si te llamas Calderon Bahena → CB22670034",
                bg=FONDO, fg=GRIS, font=('Arial', 9, 'italic')).pack(pady=(0, 10))

        frame = tk.Frame(self.ventana, bg=FONDO)
        frame.pack()
        for i, (label, attr, show) in enumerate([
            ("No. Control:", "entry_control", ""),
            ("Contraseña:", "entry_password", "*")
        ]):
            tk.Label(frame, text=label, bg=FONDO, fg=AZUL,
                    font=('Arial', 11, 'bold')).grid(row=i, column=0, padx=15, pady=10, sticky='w')
            e = tk.Entry(frame, font=('Arial', 11), width=22, show=show, relief='solid', bd=1)
            e.grid(row=i, column=1, pady=10)
            setattr(self, attr, e)

        self.entry_password.bind('<Return>', lambda e: self.verificar())

        frame_btns = tk.Frame(self.ventana, bg=FONDO)
        frame_btns.pack(pady=5)
        tk.Button(frame_btns, text="Entrar", command=self.verificar,
                 bg=AZUL, fg=BLANCO, font=('Arial', 11, 'bold'), relief='flat',
                 cursor='hand2', padx=15, pady=8).pack(side='left', padx=8)
        tk.Button(frame_btns, text="Cancelar", command=self.cancelar,
                 bg=GRIS, fg=BLANCO, font=('Arial', 11), relief='flat',
                 cursor='hand2', padx=15, pady=8).pack(side='left', padx=8)

        self.label_error = tk.Label(self.ventana, text="", bg=FONDO, fg=ROJO, font=('Arial', 10))
        self.label_error.pack()

    def cancelar(self):
        self.ventana.destroy()
        if self.callback_cancelar:
            self.callback_cancelar()

    def verificar(self):
        numero_control = self.entry_control.get().strip()
        password = self.entry_password.get().strip()
        if not numero_control or not password:
            self.label_error.config(text="⚠️ Ingresa tus datos")
            return
        alumno = self.db.obtener_datos(
            "SELECT * FROM alumnos WHERE numero_control=%s AND activo=1", (numero_control,)
        )
        if not alumno:
            self.label_error.config(text="❌ Número de control no encontrado")
            return
        alumno = alumno[0]
        apellidos = alumno['apellidos'].strip().split()
        iniciales = ''.join([a[0].upper() for a in apellidos if a])
        password_esperada = f"{iniciales}{numero_control}"
        if password == password_esperada:
            self.ventana.destroy()
            self.callback_exito(alumno)
        else:
            self.label_error.config(text="❌ Contraseña incorrecta")

# ============================================================
# PERFIL DEL ALUMNO
# ============================================================
class PerfilAlumno:
    def __init__(self, root, alumno):
        self.db = Database()
        self.gen = GeneradorDocumentos()
        self.alumno = alumno
        self.ventana = tk.Toplevel(root)
        self.ventana.title(f"Perfil - {alumno['nombre']} {alumno['apellidos']}")
        self.ventana.geometry("650x580")
        self.ventana.configure(bg=FONDO)
        # Al cerrar perfil no hace nada especial
        self.mostrar_perfil()

    def calcular_horas(self):
        registros = self.db.obtener_datos("""
            SELECT tipo, fecha_hora FROM registros
            WHERE alumno_id=%s ORDER BY fecha_hora ASC
        """, (self.alumno['id'],))
        horas = 0.0
        entrada = None
        for r in registros:
            if r['tipo'] == 'entrada':
                entrada = r['fecha_hora']
            elif r['tipo'] == 'salida' and entrada:
                diff = (r['fecha_hora'] - entrada).total_seconds() / 3600
                horas += diff
                entrada = None
        return round(horas, 2)

    def mostrar_perfil(self):
        horas = self.calcular_horas()
        self.db.ejecutar_query(
            "UPDATE alumnos SET horas_totales=%s WHERE id=%s",
            (horas, self.alumno['id'])
        )

        header = tk.Frame(self.ventana, bg=AZUL, height=80)
        header.pack(fill='x')
        tk.Label(header, text=f"👤 {self.alumno['nombre']} {self.alumno['apellidos']}",
                font=('Arial', 14, 'bold'), bg=AZUL, fg=BLANCO).pack(pady=10)
        tk.Label(header, text=f"No. Control: {self.alumno['numero_control']}",
                font=('Arial', 10), bg=AZUL, fg='#acd').pack()

        frame_info = tk.Frame(self.ventana, bg=BLANCO, relief='solid', bd=1)
        frame_info.pack(fill='x', padx=20, pady=15)

        hora_e = self.alumno.get('hora_entrada', '08:00:00')
        hora_s = self.alumno.get('hora_salida', '14:00:00')
        # Formatear si viene como timedelta
        if hasattr(hora_e, 'seconds'):
            h, m = divmod(hora_e.seconds // 60, 60)
            hora_e = f"{h:02d}:{m:02d}"
        if hasattr(hora_s, 'seconds'):
            h, m = divmod(hora_s.seconds // 60, 60)
            hora_s = f"{h:02d}:{m:02d}"

        datos = [
            ("🏫 Carrera:", self.alumno.get('carrera', '-')),
            ("🏢 Departamento:", self.alumno.get('departamento', '-')),
            ("📋 Programa:", self.alumno.get('programa', '-')),
            ("🕐 Horario:", f"{hora_e} — {hora_s}"),
            ("📅 Fecha de inicio:", str(self.alumno.get('fecha_inicio', '-'))),
        ]
        for i, (label, valor) in enumerate(datos):
            bg = FONDO if i % 2 == 0 else BLANCO
            fila = tk.Frame(frame_info, bg=bg)
            fila.pack(fill='x')
            tk.Label(fila, text=label, font=('Arial', 10, 'bold'),
                    bg=bg, fg=AZUL, width=18, anchor='w').pack(side='left', padx=10, pady=6)
            tk.Label(fila, text=valor, font=('Arial', 10),
                    bg=bg, fg='#333').pack(side='left', pady=6)

        frame_horas = tk.Frame(self.ventana, bg=BLANCO, relief='solid', bd=1)
        frame_horas.pack(fill='x', padx=20, pady=5)
        tk.Label(frame_horas, text="⏱️ Horas de Servicio Social",
                font=('Arial', 12, 'bold'), bg=BLANCO, fg=AZUL).pack(pady=8)

        META = 480
        porcentaje = min(horas / META, 1.0)
        canvas = tk.Canvas(frame_horas, width=580, height=30, bg=FONDO, highlightthickness=0)
        canvas.pack(padx=15, pady=5)
        canvas.create_rectangle(0, 5, 580, 25, fill='#ddd', outline='')
        color_barra = VERDE if horas >= 480 else (AZUL if horas >= 160 else '#f39c12')
        canvas.create_rectangle(0, 5, int(580 * porcentaje), 25, fill=color_barra, outline='')

        tk.Label(frame_horas, text=f"{horas:.1f} / {META} horas  ({porcentaje*100:.1f}%)",
                font=('Arial', 11, 'bold'), bg=BLANCO,
                fg=VERDE if horas >= 480 else AZUL).pack(pady=5)

        hitos = tk.Frame(frame_horas, bg=BLANCO)
        hitos.pack(pady=5)
        for hrs, label in [(160, "1er Reporte"), (320, "2do Reporte"), (480, "Liberación")]:
            ok = horas >= hrs
            tk.Label(hitos, text=f"{'✅' if ok else '⏳'} {hrs}h {label}",
                    font=('Arial', 9), bg=BLANCO, fg=VERDE if ok else GRIS).pack(side='left', padx=15)

        frame_docs = tk.Frame(self.ventana, bg=FONDO)
        frame_docs.pack(fill='x', padx=20, pady=10)
        tk.Label(frame_docs, text="📄 Documentos disponibles:",
                font=('Arial', 11, 'bold'), bg=FONDO, fg=AZUL).pack(anchor='w')

        frame_btns = tk.Frame(frame_docs, bg=FONDO)
        frame_btns.pack(fill='x', pady=5)

        docs = [
            ("Reporte 1 (160h)", horas >= 160, lambda: self.generar_doc('reporte', 1)),
            ("Reporte 2 (320h)", horas >= 320, lambda: self.generar_doc('reporte', 2)),
            ("Reporte 3 (480h)", horas >= 480, lambda: self.generar_doc('reporte', 3)),
            ("Eval. Actividades", horas >= 160, lambda: self.generar_doc('eval_actividades', 0)),
            ("Eval. Cualitativa", horas >= 160, lambda: self.generar_doc('eval_cualitativa', 0)),
            ("Autoevaluación", horas >= 160, lambda: self.generar_doc('autoeval', 0)),
            ("🎓 Liberación", horas >= 480, lambda: self.generar_doc('liberacion', 0)),
        ]
        for i, (texto, disponible, cmd) in enumerate(docs):
            btn = tk.Button(frame_btns, text=texto,
                           command=cmd if disponible else lambda: messagebox.showinfo(
                               "No disponible", "Aún no has completado las horas necesarias"),
                           bg=AZUL if disponible else GRIS,
                           fg=BLANCO, font=('Arial', 9), relief='flat',
                           cursor='hand2' if disponible else 'arrow', padx=8, pady=6)
            btn.grid(row=i // 4, column=i % 4, padx=4, pady=4, sticky='ew')

    def generar_doc(self, tipo, numero):
        try:
            path = self.gen.generar(tipo, self.alumno, numero)
            if path:
                resp = messagebox.askyesno("✅ Documento listo", "Documento generado.\n¿Deseas abrirlo?")
                if resp:
                    os.startfile(os.path.abspath(path))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar: {e}")

# ============================================================
# APP PRINCIPAL
# ============================================================
class AppControlServicio:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Control de Servicio Social - TECNM")
        self.root.geometry("700x500")
        self.root.configure(bg=FONDO)
        self.root.resizable(False, False)

        self.rf = ReconocimientoFacial()
        self.qr_mgr = QRManager()
        self.registro = RegistroAlumno()
        self.db = Database()
        self.maestro_actual = None

        # Flag para cancelar reconocimiento en curso
        self._cancelar_reconocimiento = False

        self.mostrar_pantalla_inicio()

    # ============================================================
    # PANTALLA INICIO
    # ============================================================
    def mostrar_pantalla_inicio(self):
        self.limpiar()

        # Header — fondo más oscuro para que el logo azul se vea
        header = tk.Frame(self.root, bg=HEADER_BG, height=110)
        header.pack(fill='x')
        header.pack_propagate(False)

        try:
            from PIL import Image, ImageTk
            import numpy as np
            img = Image.open("logo_tecnm_frame.png").convert("RGBA")
            data = np.array(img)
            # Quitar fondo negro del logo
            mask = (data[:,:,0] < 40) & (data[:,:,1] < 40) & (data[:,:,2] < 40)
            data[mask] = [0, 0, 0, 0]
            img = Image.fromarray(data)
            img = img.resize((200, 78), Image.LANCZOS)
            # Pegar sobre fondo oscuro
            fondo_img = Image.new('RGBA', (200, 78), (13, 31, 60, 255))
            fondo_img.paste(img, (0, 0), img)
            self.logo_img = ImageTk.PhotoImage(fondo_img.convert('RGB'))
            tk.Label(header, image=self.logo_img, bg=HEADER_BG).pack(side='left', padx=20, pady=15)
        except Exception as e:
            tk.Label(header, text="TECNM", font=('Arial', 16, 'bold'),
                    bg=HEADER_BG, fg=BLANCO).pack(side='left', padx=20, pady=15)

        tk.Label(header, text="Control de Servicio Social",
                font=('Arial', 17, 'bold'), bg=HEADER_BG, fg=BLANCO).pack(side='left', pady=38)

        tk.Label(self.root, text="¿Cómo deseas ingresar?",
                font=('Arial', 14), bg=FONDO, fg=AZUL).pack(pady=25)

        frame_cards = tk.Frame(self.root, bg=FONDO)
        frame_cards.pack(expand=True)

        cards = [
            ("🎓", "Estudiante", "Registrar entrada/salida\nver tu perfil y horas", self.modo_estudiante, AZUL),
            ("👨‍🏫", "Docente /\nAdministrativo", "Gestionar alumnos\ny ver reportes", self.modo_admin, '#533483'),
        ]
        for emoji, titulo, desc, cmd, color in cards:
            card = tk.Frame(frame_cards, bg=BLANCO, relief='solid', bd=1, width=250, height=220)
            card.pack(side='left', padx=25, pady=10)
            card.pack_propagate(False)
            tk.Label(card, text=emoji, font=('Arial', 40), bg=BLANCO).pack(pady=(20, 5))
            tk.Label(card, text=titulo, font=('Arial', 13, 'bold'), bg=BLANCO, fg=color).pack()
            tk.Label(card, text=desc, font=('Arial', 9), bg=BLANCO, fg=GRIS, justify='center').pack(pady=5)
            tk.Button(card, text="Seleccionar", command=cmd, bg=color, fg=BLANCO,
                     font=('Arial', 10, 'bold'), relief='flat', cursor='hand2',
                     padx=15, pady=6).pack(pady=10)

        self.status_var = tk.StringVar(value="Sistema listo ✅")
        tk.Label(self.root, textvariable=self.status_var,
                bg=FONDO, fg=GRIS, font=('Arial', 9)).pack(side='bottom', pady=8)

    # ============================================================
    # MODO ESTUDIANTE
    # ============================================================
    def modo_estudiante(self):
        self.limpiar()

        header = tk.Frame(self.root, bg=AZUL, height=70)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="🎓 Acceso Estudiante",
                font=('Arial', 15, 'bold'), bg=AZUL, fg=BLANCO).pack(side='left', padx=20, pady=20)
        tk.Button(header, text="← Menú principal", command=self.mostrar_pantalla_inicio,
                 bg=AZUL_CLARO, fg=BLANCO, relief='flat', cursor='hand2',
                 font=('Arial', 10), padx=10, pady=5).pack(side='right', padx=15, pady=20)

        tk.Label(self.root, text="Selecciona tu método de registro",
                font=('Arial', 12), bg=FONDO, fg=AZUL).pack(pady=20)

        frame_btns = tk.Frame(self.root, bg=FONDO)
        frame_btns.pack(pady=10)

        card1 = tk.Frame(frame_btns, bg=BLANCO, relief='solid', bd=1, width=220, height=190)
        card1.pack(side='left', padx=20)
        card1.pack_propagate(False)
        tk.Label(card1, text="😊", font=('Arial', 35), bg=BLANCO).pack(pady=(20, 5))
        tk.Label(card1, text="Reconocimiento\nFacial", font=('Arial', 12, 'bold'),
                bg=BLANCO, fg=AZUL).pack()
        tk.Label(card1, text="Mira a la cámara\ny parpadea 3 veces",
                font=('Arial', 8), bg=BLANCO, fg=GRIS).pack()
        tk.Button(card1, text="Usar cámara", command=self.iniciar_facial,
                 bg=AZUL, fg=BLANCO, font=('Arial', 10), relief='flat',
                 cursor='hand2', padx=10, pady=6).pack(pady=10)

        card2 = tk.Frame(frame_btns, bg=BLANCO, relief='solid', bd=1, width=220, height=190)
        card2.pack(side='left', padx=20)
        card2.pack_propagate(False)
        tk.Label(card2, text="📱", font=('Arial', 35), bg=BLANCO).pack(pady=(20, 5))
        tk.Label(card2, text="Código QR", font=('Arial', 12, 'bold'),
                bg=BLANCO, fg=AZUL).pack()
        tk.Label(card2, text="Presenta tu credencial\nQR a la cámara",
                font=('Arial', 8), bg=BLANCO, fg=GRIS).pack()
        tk.Button(card2, text="Escanear QR", command=self.iniciar_qr,
                 bg=AZUL, fg=BLANCO, font=('Arial', 10), relief='flat',
                 cursor='hand2', padx=10, pady=6).pack(pady=10)

        tk.Label(self.root, text="─────── o ───────", bg=FONDO, fg=GRIS).pack(pady=10)
        btn_perfil = tk.Button(self.root, text="👤 Ver mi perfil y horas",
                              command=self.login_perfil_alumno,
                              bg=GRIS, fg=BLANCO, font=('Arial', 11), relief='flat',
                              cursor='hand2', padx=20, pady=8)
        btn_perfil.pack()

        self.status_var = tk.StringVar(value="Sistema listo ✅")
        tk.Label(self.root, textvariable=self.status_var,
                bg=FONDO, fg=GRIS, font=('Arial', 9)).pack(side='bottom', pady=8)

    # ============================================================
    # MODO ADMIN
    # ============================================================
    def modo_admin(self):
        if self.maestro_actual:
            self.pantalla_admin()
        else:
            LoginMaestro(self.root, self.on_login_admin,
                        callback_cancelar=self.mostrar_pantalla_inicio)

    def on_login_admin(self, maestro):
        self.maestro_actual = maestro
        self.pantalla_admin()

    def pantalla_admin(self):
        self.limpiar()

        header = tk.Frame(self.root, bg='#533483', height=70)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text=f"👨‍🏫 Panel Administrativo — {self.maestro_actual['nombre']}",
                font=('Arial', 13, 'bold'), bg='#533483', fg=BLANCO).pack(side='left', padx=20, pady=20)

        frame_header_btns = tk.Frame(header, bg='#533483')
        frame_header_btns.pack(side='right', padx=15, pady=15)
        tk.Button(frame_header_btns, text="🔓 Cerrar sesión",
                 command=self.cerrar_sesion_admin,
                 bg='#6a4a9e', fg=BLANCO, relief='flat', cursor='hand2',
                 font=('Arial', 9), padx=8, pady=4).pack(side='left', padx=4)
        tk.Button(frame_header_btns, text="← Menú principal",
                 command=self.mostrar_pantalla_inicio,
                 bg='#6a4a9e', fg=BLANCO, relief='flat', cursor='hand2',
                 font=('Arial', 9), padx=8, pady=4).pack(side='left', padx=4)

        frame_btns = tk.Frame(self.root, bg=FONDO)
        frame_btns.pack(expand=True)

        opciones = [
            ("➕", "Registrar\nAlumno", self._abrir_registro),
            ("📊", "Ver\nRegistros", self._abrir_registros),
            ("👥", "Ver\nAlumnos", self._abrir_alumnos),
        ]
        for emoji, titulo, cmd in opciones:
            card = tk.Frame(frame_btns, bg=BLANCO, relief='solid', bd=1, width=170, height=160)
            card.pack(side='left', padx=15, pady=20)
            card.pack_propagate(False)
            tk.Label(card, text=emoji, font=('Arial', 30), bg=BLANCO).pack(pady=(20, 5))
            tk.Label(card, text=titulo, font=('Arial', 11, 'bold'), bg=BLANCO,
                    fg='#533483', justify='center').pack()
            tk.Button(card, text="Abrir", command=cmd, bg='#533483', fg=BLANCO,
                     font=('Arial', 10), relief='flat', cursor='hand2',
                     padx=12, pady=5).pack(pady=8)

        self.status_var = tk.StringVar(value=f"Sesión activa: {self.maestro_actual['nombre']}")
        tk.Label(self.root, textvariable=self.status_var,
                bg=FONDO, fg=GRIS, font=('Arial', 9)).pack(side='bottom', pady=8)

    def cerrar_sesion_admin(self):
        self.maestro_actual = None
        self.mostrar_pantalla_inicio()

    # ============================================================
    # HELPERS
    # ============================================================
    def limpiar(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def login_perfil_alumno(self):
        LoginAlumno(self.root, self.abrir_perfil)

    def abrir_perfil(self, alumno):
        PerfilAlumno(self.root, alumno)

    # ============================================================
    # RECONOCIMIENTO FACIAL — con botón cancelar
    # ============================================================
    def iniciar_facial(self):
        self.status_var.set("🎥 Abriendo cámara...")
        self._cancelar_reconocimiento = False

        # Ventana de estado con botón cancelar
        self.ventana_camara = tk.Toplevel(self.root)
        self.ventana_camara.title("Reconocimiento Facial")
        self.ventana_camara.geometry("320x160")
        self.ventana_camara.configure(bg=FONDO)
        self.ventana_camara.resizable(False, False)
        self.ventana_camara.grab_set()
        self.ventana_camara.protocol("WM_DELETE_WINDOW", self._cancelar_facial)

        tk.Frame(self.ventana_camara, bg=AZUL, height=45).pack(fill='x')
        tk.Label(self.ventana_camara, text="😊 Reconocimiento Facial",
                font=('Arial', 12, 'bold'), bg=AZUL, fg=BLANCO).place(x=0, y=10, width=320)

        tk.Label(self.ventana_camara, text="Mira a la cámara y parpadea 3 veces.\nPresiona Q en la cámara para cancelar.",
                font=('Arial', 10), bg=FONDO, fg=AZUL, justify='center').pack(pady=15)

        tk.Button(self.ventana_camara, text="❌ Cancelar",
                 command=self._cancelar_facial,
                 bg=ROJO, fg=BLANCO, font=('Arial', 11, 'bold'),
                 relief='flat', cursor='hand2', padx=20, pady=8).pack()

        def ejecutar():
            resultado = self.rf.iniciar_reconocimiento()
            # Cerrar ventana de estado
            if hasattr(self, 'ventana_camara') and self.ventana_camara.winfo_exists():
                self.ventana_camara.destroy()

            if self._cancelar_reconocimiento:
                self.root.after(0, lambda: self.status_var.set("✅ Sistema listo"))
                return

            if resultado:
                tipo = resultado['tipo'].upper()
                nombre = resultado['nombre']
                msg = f"✅ {tipo} registrada: {nombre}"
                self.root.after(0, lambda: self._mostrar_exito_registro(msg))
            else:
                self.root.after(0, self._ofrecer_qr)

        threading.Thread(target=ejecutar, daemon=True).start()

    def _cancelar_facial(self):
        self._cancelar_reconocimiento = True
        if hasattr(self, 'ventana_camara') and self.ventana_camara.winfo_exists():
            self.ventana_camara.destroy()
        self.status_var.set("✅ Sistema listo")
        # Forzar cierre de cámara OpenCV
        import cv2
        cv2.destroyAllWindows()

    # ============================================================
    # QR — con botón cancelar
    # ============================================================
    def iniciar_qr(self):
        self.status_var.set("📱 Escanea tu código QR...")
        self._cancelar_reconocimiento = False

        self.ventana_qr = tk.Toplevel(self.root)
        self.ventana_qr.title("Escaneo QR")
        self.ventana_qr.geometry("320x160")
        self.ventana_qr.configure(bg=FONDO)
        self.ventana_qr.resizable(False, False)
        self.ventana_qr.grab_set()
        self.ventana_qr.protocol("WM_DELETE_WINDOW", self._cancelar_qr)

        tk.Frame(self.ventana_qr, bg=AZUL, height=45).pack(fill='x')
        tk.Label(self.ventana_qr, text="📱 Escaneo de Código QR",
                font=('Arial', 12, 'bold'), bg=AZUL, fg=BLANCO).place(x=0, y=10, width=320)

        tk.Label(self.ventana_qr, text="Presenta tu credencial QR a la cámara.\nPresiona Q en la cámara para cancelar.",
                font=('Arial', 10), bg=FONDO, fg=AZUL, justify='center').pack(pady=15)

        tk.Button(self.ventana_qr, text="❌ Cancelar",
                 command=self._cancelar_qr,
                 bg=ROJO, fg=BLANCO, font=('Arial', 11, 'bold'),
                 relief='flat', cursor='hand2', padx=20, pady=8).pack()

        def ejecutar():
            alumno, codigo = self.qr_mgr.leer_qr_camara()
            if hasattr(self, 'ventana_qr') and self.ventana_qr.winfo_exists():
                self.ventana_qr.destroy()

            if self._cancelar_reconocimiento:
                self.root.after(0, lambda: self.status_var.set("✅ Sistema listo"))
                return

            if alumno:
                tipo = self.rf.determinar_tipo_registro(alumno['id'])
                self.db.ejecutar_query(
                    "INSERT INTO registros (alumno_id, tipo, metodo) VALUES (%s, %s, 'qr')",
                    (alumno['id'], tipo)
                )
                nombre = f"{alumno['nombre']} {alumno['apellidos']}"
                msg = f"✅ QR: {tipo.upper()} — {nombre}"
                self.root.after(0, lambda: self._mostrar_exito_registro(msg))
            else:
                self.root.after(0, lambda: self.status_var.set("⚠️ QR no reconocido"))

        threading.Thread(target=ejecutar, daemon=True).start()

    def _cancelar_qr(self):
        self._cancelar_reconocimiento = True
        if hasattr(self, 'ventana_qr') and self.ventana_qr.winfo_exists():
            self.ventana_qr.destroy()
        self.status_var.set("✅ Sistema listo")
        import cv2
        cv2.destroyAllWindows()

    def _ofrecer_qr(self):
        resp = messagebox.askyesno(
            "No reconocido",
            "No se pudo identificar tu rostro.\n\n¿Deseas usar tu código QR en su lugar?"
        )
        if resp:
            self.iniciar_qr()
        else:
            self.status_var.set("✅ Sistema listo")

    def _mostrar_exito_registro(self, mensaje):
        self.status_var.set(mensaje)
        messagebox.showinfo("✅ Registro exitoso", mensaje)
        self.status_var.set("✅ Sistema listo")

    # ============================================================
    # PANEL ADMIN — VENTANAS ÚNICAS (no se apilan)
    # ============================================================
    def _abrir_ventana_unica(self, attr, titulo, ancho, alto, constructor):
        """Abre una ventana y cierra la anterior del mismo tipo si existe."""
        ventana_existente = getattr(self, attr, None)
        if ventana_existente and ventana_existente.winfo_exists():
            ventana_existente.lift()
            ventana_existente.focus_force()
            return
        ventana = tk.Toplevel(self.root)
        ventana.title(titulo)
        ventana.geometry(f"{ancho}x{alto}")
        ventana.configure(bg=FONDO)
        setattr(self, attr, ventana)
        constructor(ventana)

    def _abrir_registro(self):
        self._abrir_ventana_unica('_win_registro', 'Registrar Nuevo Alumno', 480, 580,
                                  self._construir_registro)

    def _abrir_registros(self):
        self._abrir_ventana_unica('_win_registros', 'Registros de Asistencia', 800, 450,
                                  self._construir_registros)

    def _abrir_alumnos(self):
        self._abrir_ventana_unica('_win_alumnos', 'Alumnos Registrados', 800, 430,
                                  self._construir_alumnos)

    def _construir_registro(self, ventana):
        tk.Frame(ventana, bg='#533483', height=50).pack(fill='x')
        tk.Label(ventana, text="➕ Nuevo Alumno", font=('Arial', 13, 'bold'),
                bg='#533483', fg=BLANCO).place(x=0, y=12, width=480)

        frame = tk.Frame(ventana, bg=FONDO)
        frame.pack(pady=15)

        campos = ['Número de Control', 'Nombre', 'Apellidos', 'Departamento', 'Programa']
        entradas = {}
        for i, campo in enumerate(campos):
            tk.Label(frame, text=campo + ":", bg=FONDO, fg=AZUL,
                    font=('Arial', 10, 'bold')).grid(row=i, column=0, padx=15, pady=6, sticky='w')
            e = tk.Entry(frame, font=('Arial', 10), width=28, relief='solid', bd=1)
            e.grid(row=i, column=1, pady=6)
            entradas[campo] = e

        tk.Label(frame, text="Carrera:", bg=FONDO, fg=AZUL,
                font=('Arial', 10, 'bold')).grid(row=len(campos), column=0, padx=15, pady=6, sticky='w')
        carrera_var = tk.StringVar(value=CARRERAS[0])
        ttk.Combobox(frame, textvariable=carrera_var, values=CARRERAS,
                    state='readonly', font=('Arial', 10), width=26).grid(
                    row=len(campos), column=1, pady=6)

        tk.Label(frame, text="Hora entrada:", bg=FONDO, fg=AZUL,
                font=('Arial', 10, 'bold')).grid(row=len(campos)+1, column=0, padx=15, pady=6, sticky='w')
        hora_entrada = tk.Entry(frame, font=('Arial', 10), width=12, relief='solid', bd=1)
        hora_entrada.insert(0, "08:00")
        hora_entrada.grid(row=len(campos)+1, column=1, pady=6, sticky='w')

        tk.Label(frame, text="Hora salida:", bg=FONDO, fg=AZUL,
                font=('Arial', 10, 'bold')).grid(row=len(campos)+2, column=0, padx=15, pady=6, sticky='w')
        hora_salida = tk.Entry(frame, font=('Arial', 10), width=12, relief='solid', bd=1)
        hora_salida.insert(0, "14:00")
        hora_salida.grid(row=len(campos)+2, column=1, pady=6, sticky='w')

        def confirmar():
            numero_control = entradas['Número de Control'].get().strip()
            nombre = entradas['Nombre'].get().strip()
            apellidos = entradas['Apellidos'].get().strip()
            departamento = entradas['Departamento'].get().strip()
            programa = entradas['Programa'].get().strip()
            carrera = carrera_var.get()
            h_entrada = hora_entrada.get().strip()
            h_salida = hora_salida.get().strip()

            if not all([numero_control, nombre, apellidos, departamento, programa]):
                messagebox.showwarning("Campos vacíos", "Completa todos los campos")
                return

            ventana.destroy()
            self.status_var.set(f"📸 Registrando a {nombre}...")

            def ejecutar():
                exito, resultado = self.registro.registrar_alumno(
                    numero_control, nombre, apellidos, carrera
                )
                if exito:
                    alumno = self.db.obtener_datos(
                        "SELECT id FROM alumnos WHERE numero_control=%s", (numero_control,)
                    )
                    if alumno:
                        self.db.ejecutar_query("""
                            UPDATE alumnos SET departamento=%s, programa=%s,
                            hora_entrada=%s, hora_salida=%s, fecha_inicio=%s WHERE id=%s
                        """, (departamento, programa, h_entrada, h_salida,
                              date.today(), alumno[0]['id']))
                    self.rf.cargar_encodings()
                    pdf_path = resultado
                    def mostrar_exito():
                        resp = messagebox.askyesno("✅ Registro exitoso",
                            f"Alumno {nombre} registrado.\n¿Deseas abrir el PDF con su QR?")
                        if resp:
                            os.startfile(os.path.abspath(pdf_path))
                    self.root.after(0, mostrar_exito)
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", resultado))
                self.root.after(0, lambda: self.status_var.set("✅ Sistema listo"))

            threading.Thread(target=ejecutar, daemon=True).start()

        tk.Button(ventana, text="📸 Capturar y Registrar", command=confirmar,
                 bg=AZUL, fg=BLANCO, font=('Arial', 11, 'bold'), relief='flat',
                 cursor='hand2', padx=20, pady=10).pack(pady=10)

    def _construir_registros(self, ventana):
        tk.Frame(ventana, bg='#533483', height=45).pack(fill='x')
        tk.Label(ventana, text="📊 Registros de Entradas y Salidas",
                font=('Arial', 12, 'bold'), bg='#533483', fg=BLANCO).place(x=0, y=10, width=800)

        frame_tabla = tk.Frame(ventana)
        frame_tabla.pack(fill='both', expand=True, padx=10, pady=(50, 10))

        columns = ('Nombre', 'No. Control', 'Carrera', 'Tipo', 'Método', 'Fecha/Hora')
        tree = ttk.Treeview(frame_tabla, columns=columns, show='headings', height=15)
        anchos = [160, 110, 190, 80, 80, 145]
        for col, ancho in zip(columns, anchos):
            tree.heading(col, text=col)
            tree.column(col, width=ancho)

        # Color por tipo
        tree.tag_configure('entrada', foreground='#1a7a1a')
        tree.tag_configure('salida', foreground='#7a1a1a')

        scrollbar = ttk.Scrollbar(frame_tabla, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        registros = self.db.obtener_datos("""
            SELECT a.nombre, a.apellidos, a.numero_control, a.carrera,
                   r.tipo, r.metodo, r.fecha_hora
            FROM registros r JOIN alumnos a ON r.alumno_id = a.id
            ORDER BY r.fecha_hora DESC LIMIT 200
        """)
        for reg in registros:
            tag = 'entrada' if reg['tipo'] == 'entrada' else 'salida'
            tree.insert('', 'end', tags=(tag,), values=(
                f"{reg['nombre']} {reg['apellidos']}", reg['numero_control'],
                reg['carrera'], reg['tipo'].upper(), reg['metodo'].upper(), str(reg['fecha_hora'])
            ))

    def _construir_alumnos(self, ventana):
        tk.Frame(ventana, bg='#533483', height=45).pack(fill='x')
        tk.Label(ventana, text="👥 Alumnos Registrados",
                font=('Arial', 12, 'bold'), bg='#533483', fg=BLANCO).place(x=0, y=10, width=800)

        frame_tabla = tk.Frame(ventana)
        frame_tabla.pack(fill='both', expand=True, padx=10, pady=(50, 10))

        columns = ('No. Control', 'Nombre', 'Apellidos', 'Carrera', 'Departamento', 'Horas', 'Inicio')
        tree = ttk.Treeview(frame_tabla, columns=columns, show='headings', height=14)
        anchos = [110, 120, 120, 160, 130, 60, 90]
        for col, ancho in zip(columns, anchos):
            tree.heading(col, text=col)
            tree.column(col, width=ancho)
        scrollbar = ttk.Scrollbar(frame_tabla, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        alumnos = self.db.obtener_datos(
            "SELECT * FROM alumnos WHERE activo=1 ORDER BY fecha_registro DESC"
        )
        for a in alumnos:
            tree.insert('', 'end', values=(
                a['numero_control'], a['nombre'], a['apellidos'],
                a['carrera'], a.get('departamento', '-'),
                f"{a.get('horas_totales', 0):.1f}h", str(a.get('fecha_inicio', '-'))
            ))

    def ejecutar(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = AppControlServicio()
    app.ejecutar()