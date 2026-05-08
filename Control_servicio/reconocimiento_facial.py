import face_recognition
import cv2
import numpy as np
import pickle
import os
from database import Database
from liveness_detector import LivenessDetector
from datetime import datetime

class ReconocimientoFacial:
    
    def __init__(self):
        self.db = Database()
        self.liveness = LivenessDetector()
        self.conocidos_encodings = []
        self.conocidos_ids = []
        self.conocidos_nombres = []
        self.frames_buffer = []
        self.parpadeos = 0
        
        # Cargar encodings desde BD
        self.cargar_encodings()
    
    def cargar_encodings(self):
        """Carga los encodings faciales desde la base de datos"""
        alumnos = self.db.obtener_datos(
            "SELECT id, nombre, apellidos, encoding_facial FROM alumnos WHERE activo=1 AND encoding_facial IS NOT NULL"
        )
        
        self.conocidos_encodings = []
        self.conocidos_ids = []
        self.conocidos_nombres = []
        
        for alumno in alumnos:
            if alumno['encoding_facial']:
                encoding = pickle.loads(alumno['encoding_facial'])
                self.conocidos_encodings.append(encoding)
                self.conocidos_ids.append(alumno['id'])
                self.conocidos_nombres.append(f"{alumno['nombre']} {alumno['apellidos']}")
        
        print(f"✅ {len(self.conocidos_encodings)} alumnos cargados en memoria")
    
    def registrar_acceso(self, alumno_id, tipo, confianza, frame):
        """Registra entrada o salida en la BD"""
        # Guardar captura
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        img_path = f"capturas/{alumno_id}_{timestamp}.jpg"
        cv2.imwrite(img_path, frame)
        
        self.db.ejecutar_query(
            "INSERT INTO registros (alumno_id, tipo, metodo, confianza, imagen_captura) VALUES (%s, %s, 'facial', %s, %s)",
            (alumno_id, tipo, confianza, img_path)
        )
    
    def determinar_tipo_registro(self, alumno_id):
        """Determina si es entrada o salida según último registro"""
        ultimo = self.db.obtener_datos(
            "SELECT tipo FROM registros WHERE alumno_id=%s ORDER BY fecha_hora DESC LIMIT 1",
            (alumno_id,)
        )
        
        if not ultimo or ultimo[0]['tipo'] == 'salida':
            return 'entrada'
        return 'salida'
    
    def iniciar_reconocimiento(self, callback_resultado=None):
        """
        Inicia la cámara y el proceso de reconocimiento
        con verificación de vida
        """
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        resultado_final = None
        frames_procesados = 0
        FRAMES_PARA_VERIFICAR = 30  # ~3 segundos a 10fps
        
        print("🎥 Iniciando reconocimiento... Mire a la cámara")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_display = frame.copy()
            
            # Buffer de frames para análisis de movimiento
            self.frames_buffer.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
            if len(self.frames_buffer) > 15:
                self.frames_buffer.pop(0)
            
            frames_procesados += 1
            
            # Detectar caras
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            
            if face_locations:
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                
                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    
                    # ============ VERIFICACIÓN DE VIDA ============
                    es_real, resultados_liveness, mensajes = self.liveness.verificacion_completa(
                        frame[top:bottom, left:right],
                        self.frames_buffer,
                        self.parpadeos
                    )
                    
                    color_rectangulo = (0, 255, 0) if es_real else (0, 0, 255)
                    cv2.rectangle(frame_display, (left, top), (right, bottom), color_rectangulo, 2)
                    
                    if not es_real:
                        cv2.putText(frame_display, "⚠️ TRAMPA DETECTADA", (left, top - 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        # Registrar alerta
                        self.registrar_alerta("Liveness failed", str(mensajes), frame)
                        continue
                    
                    # ============ RECONOCIMIENTO ============
                    if self.conocidos_encodings:
                        distancias = face_recognition.face_distance(
                            self.conocidos_encodings, face_encoding
                        )
                        mejor_idx = np.argmin(distancias)
                        confianza = 1 - distancias[mejor_idx]
                        
                        # Umbral de confianza (0.6 = 60% similar)
                        if confianza > 0.6:
                            alumno_id = self.conocidos_ids[mejor_idx]
                            nombre = self.conocidos_nombres[mejor_idx]
                            tipo = self.determinar_tipo_registro(alumno_id)
                            
                            texto = f"{nombre} - {tipo.upper()} ({confianza:.0%})"
                            cv2.putText(frame_display, texto, (left, top - 10),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            
                            # Si llevamos suficientes frames y es persona real
                            if frames_procesados >= FRAMES_PARA_VERIFICAR:
                                self.registrar_acceso(alumno_id, tipo, confianza, frame)
                                resultado_final = {
                                    'alumno_id': alumno_id,
                                    'nombre': nombre,
                                    'tipo': tipo,
                                    'confianza': confianza
                                }
                                cap.release()
                                cv2.destroyAllWindows()
                                if callback_resultado:
                                    callback_resultado(resultado_final)
                                return resultado_final
                        else:
                            cv2.putText(frame_display, "Alumno no reconocido", (left, top - 10),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
            
            # Mostrar instrucciones en pantalla
            instruccion = f"Parpadeos: {self.parpadeos}/1 | Frames: {frames_procesados}/{FRAMES_PARA_VERIFICAR}"
            cv2.putText(frame_display, instruccion, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            cv2.putText(frame_display, "Parpadee para verificar que es usted", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            cv2.imshow("Control de Acceso - TECNM", frame_display)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        return None
    
    def registrar_alerta(self, tipo, descripcion, frame):
        """Guarda alertas de intentos de trampa"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        img_path = f"capturas/ALERTA_{timestamp}.jpg"
        cv2.imwrite(img_path, frame)
        
        self.db.ejecutar_query(
            "INSERT INTO alertas (tipo_alerta, descripcion, imagen_evidencia) VALUES (%s, %s, %s)",
            (tipo, descripcion, img_path)
        )
        print(f"🚨 ALERTA registrada: {tipo}")