import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from reconocimiento_facial import ReconocimientoFacial
from qr_manager import QRManager
from registro_alumno import RegistroAlumno
from database import Database
import threading
import os

# Crear carpetas necesarias
for carpeta in ['fotos_alumnos', 'capturas', 'codigos_qr', 'modelos']:
    os.makedirs(carpeta, exist_ok=True)

class AppControlServicio:
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Control de Asistencia - TECNM")
        self.root.geometry("800x600")
        self.root.configure(bg='#1a1a2e')
        
        self.rf = ReconocimientoFacial()
        self.qr = QRManager()
        self.registro = RegistroAlumno()
        self.db = Database()
        
        self.crear_interfaz()
    
    def crear_interfaz(self):
        # Header
        header = tk.Frame(self.root, bg='#16213e', height=80)
        header.pack(fill='x', pady=(0,20))
        
        tk.Label(header, text="🎓 TECNM - Control de Servicio Social", 
                font=('Arial', 18, 'bold'), bg='#16213e', fg='white').pack(pady=20)
        
        # Botones principales
        frame_botones = tk.Frame(self.root, bg='#1a1a2e')
        frame_botones.pack(expand=True)
        
        botones = [
            ("😊 Reconocimiento Facial", self.iniciar_facial, '#0f3460', 'white'),
            ("📱 Escanear QR", self.iniciar_qr, '#0f3460', 'white'),
            ("➕ Registrar Alumno", self.registrar_alumno, '#533483', 'white'),
            ("📊 Ver Registros", self.ver_registros, '#1a1a2e', '#4ecca3'),
            ("⚠️ Ver Alertas", self.ver_alertas, '#1a1a2e', '#ff6b6b'),
        ]
        
        for texto, comando, bg, fg in botones:
            btn = tk.Button(
                frame_botones, text=texto, command=comando,
                font=('Arial', 13), bg=bg, fg=fg,
                width=30, height=2, cursor='hand2',
                relief='flat', bd=0
            )
            btn.pack(pady=8)
        
        # Status bar
        self.status_var = tk.StringVar(value="✅ Sistema listo")
        tk.Label(self.root, textvariable=self.status_var, 
                bg='#1a1a2e', fg='#4ecca3', font=('Arial', 11)).pack(side='bottom', pady=10)
    
    def iniciar_facial(self):
        self.status_var.set("🎥 Iniciando cámara para reconocimiento facial...")
        
        def ejecutar():
            resultado = self.rf.iniciar_reconocimiento()
            if resultado:
                tipo = resultado['tipo'].upper()
                nombre = resultado['nombre']
                confianza = resultado['confianza']
                msg = f"✅ {tipo} registrada: {nombre} ({confianza:.0%} de coincidencia)"
                self.root.after(0, lambda: self.mostrar_resultado(msg, tipo))
            else:
                self.root.after(0, lambda: self.status_var.set("⚠️ No se pudo identificar al alumno"))
        
        threading.Thread(target=ejecutar, daemon=True).start()
    
    def iniciar_qr(self):
        self.status_var.set("📱 Escanee el código QR...")
        
        def ejecutar():
            alumno, codigo = self.qr.leer_qr_camara()
            if alumno:
                # Determinar entrada/salida
                from reconocimiento_facial import ReconocimientoFacial
                rf = ReconocimientoFacial()
                tipo = rf.determinar_tipo_registro(alumno['id'])
                
                # Registrar
                self.db.ejecutar_query(
                    "INSERT INTO registros (alumno_id, tipo, metodo) VALUES (%s, %s, 'qr')",
                    (alumno['id'], tipo)
                )
                
                nombre = f"{alumno['nombre']} {alumno['apellidos']}"
                msg = f"✅ QR: {tipo.upper()} registrada para {nombre}"
                self.root.after(0, lambda: self.mostrar_resultado(msg, tipo))
        
        threading.Thread(target=ejecutar, daemon=True).start()
    
    def registrar_alumno(self):
        # Formulario de registro
        ventana = tk.Toplevel(self.root)
        ventana.title("Registrar Nuevo Alumno")
        ventana.geometry("400x300")
        ventana.configure(bg='#1a1a2e')
        
        campos = ['Número de Control', 'Nombre', 'Apellidos', 'Carrera']
        entradas = {}
        
        for i, campo in enumerate(campos):
            tk.Label(ventana, text=campo, bg='#1a1a2e', fg='white', 
                    font=('Arial', 11)).grid(row=i, column=0, padx=20, pady=8, sticky='w')
            entrada = tk.Entry(ventana, font=('Arial', 11), width=25)
            entrada.grid(row=i, column=1, padx=10, pady=8)
            entradas[campo] = entrada
        
        def confirmar():
            numero_control = entradas['Número de Control'].get()
            nombre = entradas['Nombre'].get()
            apellidos = entradas['Apellidos'].get()
            carrera = entradas['Carrera'].get()
            
            if all([numero_control, nombre, apellidos, carrera]):
                ventana.destroy()
                self.status_var.set(f"📸 Registrando a {nombre}...")
                
                def ejecutar():
                    exito = self.registro.registrar_alumno(
                        numero_control, nombre, apellidos, carrera
                    )
                    self.rf.cargar_encodings()  # Recargar encodings
                    
                    if exito:
                        self.root.after(0, lambda: messagebox.showinfo(
                            "Éxito", f"✅ Alumno {nombre} registrado correctamente"
                        ))
                    else:
                        self.root.after(0, lambda: messagebox.showerror(
                            "Error", "No se pudo registrar al alumno"
                        ))
                    self.root.after(0, lambda: self.status_var.set("✅ Sistema listo"))
                
                threading.Thread(target=ejecutar, daemon=True).start()
        
        tk.Button(ventana, text="📸 Capturar y Registrar", command=confirmar,
                 bg='#533483', fg='white', font=('Arial', 11)).grid(
                 row=len(campos), column=0, columnspan=2, pady=20)
    
    def ver_registros(self):
        ventana = tk.Toplevel(self.root)
        ventana.title("Registros del Día")
        ventana.geometry("700x400")
        
        columns = ('Nombre', 'Tipo', 'Método', 'Fecha/Hora', 'Confianza')
        tree = ttk.Treeview(ventana, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=130)
        
        registros = self.db.obtener_datos("""
            SELECT CONCAT(a.nombre, ' ', a.apellidos) as nombre, 
                   r.tipo, r.metodo, r.fecha_hora, r.confianza
            FROM registros r
            JOIN alumnos a ON r.alumno_id = a.id
            WHERE DATE(r.fecha_hora) = CURDATE()
            ORDER BY r.fecha_hora DESC
        """)
        
        for reg in registros:
            confianza = f"{reg['confianza']:.0%}" if reg['confianza'] else "QR"
            tree.insert('', 'end', values=(
                reg['nombre'], reg['tipo'].upper(), 
                reg['metodo'].upper(), str(reg['fecha_hora']), confianza
            ))
        
        tree.pack(fill='both', expand=True, padx=10, pady=10)
    
    def ver_alertas(self):
        alertas = self.db.obtener_datos(
            "SELECT * FROM alertas ORDER BY fecha_hora DESC LIMIT 20"
        )
        if alertas:
            msg = "\n".join([f"🚨 {a['tipo_alerta']} - {a['fecha_hora']}" for a in alertas])
        else:
            msg = "✅ No hay alertas registradas"
        messagebox.showinfo("Alertas del Sistema", msg)
    
    def mostrar_resultado(self, mensaje, tipo):
        color = '#00ff88' if tipo == 'ENTRADA' else '#ff6b6b'
        self.status_var.set(mensaje)
        messagebox.showinfo("Registro Exitoso", mensaje)
    
    def ejecutar(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = AppControlServicio()
    app.ejecutar()