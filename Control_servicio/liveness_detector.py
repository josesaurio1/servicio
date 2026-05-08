import cv2
import numpy as np
from scipy.spatial import distance

class LivenessDetector:
    """
    Detecta intentos de trampa:
    - Foto impresa
    - Video en pantalla
    - Máscara
    """
    
    def __init__(self):
        # Umbrales de detección
        self.EYE_AR_THRESH = 0.25      # Umbral parpadeo
        self.EYE_AR_CONSEC_FRAMES = 2  # Frames consecutivos
        self.BLINK_COUNT_MIN = 1       # Mínimo de parpadeos requeridos
        
        # Cargar detector de puntos faciales
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        self.blink_counter = 0
        self.total_blinks = 0
        self.frame_counter = 0
        
    def eye_aspect_ratio(self, eye):
        """Calcula el ratio del ojo para detectar parpadeo"""
        A = distance.euclidean(eye[1], eye[5])
        B = distance.euclidean(eye[2], eye[4])
        C = distance.euclidean(eye[0], eye[3])
        ear = (A + B) / (2.0 * C)
        return ear
    
    def detectar_textura(self, frame):
        """
        Detecta si la cara es real o una foto/pantalla
        analizando la textura y reflexión de luz
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Análisis de Laplaciano (varianza de bordes)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Una foto/pantalla tiene patrones de textura diferentes
        # Valores muy bajos = imagen plana (posible foto)
        if laplacian_var < 50:
            return False, f"Textura sospechosa (varianza: {laplacian_var:.1f})"
        
        return True, f"Textura OK (varianza: {laplacian_var:.1f})"
    
    def detectar_profundidad(self, frame):
        """
        Analiza si hay dimensión real en la imagen
        usando análisis de gradiente
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Gradiente Sobel para detectar profundidad
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=5)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=5)
        
        gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
        mean_gradient = np.mean(gradient_magnitude)
        
        if mean_gradient < 15:
            return False, "Posible imagen 2D detectada"
        
        return True, "Profundidad OK"
    
    def verificar_movimiento(self, frames_buffer):
        """
        Verifica que haya movimiento natural
        Una foto no tiene movimiento
        """
        if len(frames_buffer) < 5:
            return None, "Recopilando frames..."
        
        diferencias = []
        for i in range(1, len(frames_buffer)):
            diff = cv2.absdiff(frames_buffer[i-1], frames_buffer[i])
            diferencias.append(np.mean(diff))
        
        promedio_movimiento = np.mean(diferencias)
        
        # Muy poco movimiento = foto
        # Demasiado movimiento = video pregrabado en movimiento
        if promedio_movimiento < 1.0:
            return False, "Sin movimiento detectado (posible foto)"
        elif promedio_movimiento > 50.0:
            return False, "Movimiento anormal detectado"
        
        return True, f"Movimiento natural: {promedio_movimiento:.2f}"
    
    def analizar_reflexion_luz(self, frame):
        """
        Las pantallas y fotos brillantes tienen 
        reflexión de luz diferente a piel real
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Canal V (brillo)
        v_channel = hsv[:,:,2]
        
        # Detectar zonas de alto brillo (reflexión de pantalla)
        bright_pixels = np.sum(v_channel > 240)
        total_pixels = v_channel.size
        bright_ratio = bright_pixels / total_pixels
        
        # Si más del 10% son píxeles muy brillantes, puede ser pantalla
        if bright_ratio > 0.10:
            return False, f"Reflexión de pantalla detectada ({bright_ratio:.2%})"
        
        return True, "Reflexión normal"
    
    def verificacion_completa(self, frame, frames_buffer, parpadeos_detectados):
        """
        Realiza todas las verificaciones y devuelve resultado
        """
        resultados = {}
        es_real = True
        mensajes = []
        
        # 1. Verificar parpadeo (requiere dlib para puntos faciales)
        if parpadeos_detectados < self.BLINK_COUNT_MIN:
            resultados['parpadeo'] = False
            mensajes.append("⚠️ No se detectó parpadeo")
            es_real = False
        else:
            resultados['parpadeo'] = True
        
        # 2. Análisis de textura
        real_textura, msg_textura = self.detectar_textura(frame)
        resultados['textura'] = real_textura
        mensajes.append(msg_textura)
        if not real_textura:
            es_real = False
        
        # 3. Análisis de profundidad
        real_prof, msg_prof = self.detectar_profundidad(frame)
        resultados['profundidad'] = real_prof
        mensajes.append(msg_prof)
        if not real_prof:
            es_real = False
        
        # 4. Análisis de movimiento
        real_mov, msg_mov = self.verificar_movimiento(frames_buffer)
        if real_mov is not None:
            resultados['movimiento'] = real_mov
            mensajes.append(msg_mov)
            if not real_mov:
                es_real = False
        
        # 5. Reflexión de luz
        real_luz, msg_luz = self.analizar_reflexion_luz(frame)
        resultados['reflexion'] = real_luz
        mensajes.append(msg_luz)
        if not real_luz:
            es_real = False
        
        return es_real, resultados, mensajes