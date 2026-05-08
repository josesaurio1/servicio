import face_recognition
import cv2
import numpy as np
import pickle
import os
import dlib
from imutils import face_utils
from scipy.spatial import distance
from database import Database
from datetime import datetime
from PIL import Image

class ReconocimientoFacial:
    
    def __init__(self):
        self.db = Database()
        self.conocidos_encodings = []
        self.conocidos_ids = []
        self.conocidos_nombres = []
        
        # Cargar detector de puntos faciales para parpadeo
        self.detector_dlib = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
        
        # Índices de los ojos en los 68 puntos
        (self.lStart, self.lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
        (self.rStart, self.rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]
        
        self.cargar_encodings()
    
    def cargar_encodings(self):
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
    
    def registrar_acceso(self, alumno_id, tipo, frame):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        img_path = f"capturas/{alumno_id}_{timestamp}.jpg"
        os.makedirs("capturas", exist_ok=True)
        cv2.imwrite(img_path, frame)
        self.db.ejecutar_query(
            "INSERT INTO registros (alumno_id, tipo, metodo, imagen_captura) VALUES (%s, %s, 'facial', %s)",
            (alumno_id, tipo, img_path)
        )
    
    def determinar_tipo_registro(self, alumno_id):
        ultimo = self.db.obtener_datos(
            "SELECT tipo FROM registros WHERE alumno_id=%s ORDER BY fecha_hora DESC LIMIT 1",
            (alumno_id,)
        )
        if not ultimo or ultimo[0]['tipo'] == 'salida':
            return 'entrada'
        return 'salida'
    
    def eye_aspect_ratio(self, eye):
        A = distance.euclidean(eye[1], eye[5])
        B = distance.euclidean(eye[2], eye[4])
        C = distance.euclidean(eye[0], eye[3])
        return (A + B) / (2.0 * C)
    
    def cargar_logo(self, path, altura=55):
        try:
            img_pil = Image.open(path).convert("RGBA")
            ratio = altura / img_pil.height
            nuevo_ancho = int(img_pil.width * ratio)
            img_pil = img_pil.resize((nuevo_ancho, altura), Image.LANCZOS)
            return np.array(img_pil)
        except:
            return None
    
    def pegar_logo(self, frame, logo_rgba, x, y):
        if logo_rgba is None:
            return frame
        h, w = logo_rgba.shape[:2]
        fh, fw = frame.shape[:2]
        if x + w > fw: x = fw - w - 5
        if y + h > fh: y = fh - h - 5
        if x < 0: x = 0
        if y < 0: y = 0
        roi = frame[y:y+h, x:x+w]
        logo_bgr = logo_rgba[:, :, :3][:, :, ::-1]
        alpha = logo_rgba[:, :, 3] / 255.0
        for c in range(3):
            roi[:, :, c] = (alpha * logo_bgr[:, :, c] + (1 - alpha) * roi[:, :, c])
        frame[y:y+h, x:x+w] = roi
        return frame

    def iniciar_reconocimiento(self, callback_resultado=None):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # Colores oficiales TECNM en BGR
        AZUL_TECNM = (106, 57, 27)
        GRIS_TECNM = (130, 126, 128)
        BLANCO     = (255, 255, 255)
        VERDE_OK   = (0, 200, 80)
        NARANJA_NO = (0, 165, 255)
        ROJO       = (0, 0, 220)

        # Umbrales parpadeo
        EAR_THRESH       = 0.20  # Si EAR baja de esto = ojo cerrado
        EAR_CONSEC_FRAMES = 3    # Frames consecutivos con ojo cerrado
        PARPADEOS_REQUERIDOS = 3  # Parpadeos necesarios para confirmar

        logo = self.cargar_logo("logo_tecnm_frame.png", altura=55)

        resultado_final    = None
        frame_count        = 0
        frames_reconocido  = 0
        FRAMES_PARA_CONFIRMAR = 8

        face_locations     = []
        nombre_detectado   = ""
        tipo_detectado     = ""
        alumno_id_detectado = None
        color_rect         = AZUL_TECNM

        # Variables parpadeo
        ear_counter  = 0
        parpadeos    = 0
        parpadeo_ok  = False

        print("🎥 Iniciando reconocimiento... Mire a la cámara y parpadee")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            frame_display = frame.copy()
            frame_count += 1
            fh, fw = frame.shape[:2]

            # ===== BARRA SUPERIOR =====
            cv2.rectangle(frame_display, (0, 0), (fw, 70), AZUL_TECNM, -1)
            cv2.putText(frame_display, "Control de Servicio Social",
                       (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, BLANCO, 2)
            cv2.putText(frame_display, "Coloque su rostro y parpadee 2 veces",
                       (10, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 210, 230), 1)

            # ===== LOGO =====
            if logo is not None:
                lh, lw = logo.shape[:2]
                self.pegar_logo(frame_display, logo, fw - lw - 10, 7)

            cv2.line(frame_display, (0, 70), (fw, 70), GRIS_TECNM, 2)

            # ===== DETECCIÓN DE PARPADEO con dlib =====
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rostros_dlib = self.detector_dlib(gray,0)

            for rostro in rostros_dlib:
                shape = self.predictor(gray, rostro)
                shape = face_utils.shape_to_np(shape)

                ojo_izq = shape[self.lStart:self.lEnd]
                ojo_der = shape[self.rStart:self.rEnd]

                ear_izq = self.eye_aspect_ratio(ojo_izq)
                ear_der = self.eye_aspect_ratio(ojo_der)
                ear     = (ear_izq + ear_der) / 2.0

                # Dibujar contorno de ojos
                hull_izq = cv2.convexHull(ojo_izq)
                hull_der = cv2.convexHull(ojo_der)
                cv2.drawContours(frame_display, [hull_izq], -1, VERDE_OK if parpadeo_ok else GRIS_TECNM, 1)
                cv2.drawContours(frame_display, [hull_der], -1, VERDE_OK if parpadeo_ok else GRIS_TECNM, 1)

                if ear < EAR_THRESH:
                    ear_counter += 1
                else:
                    if ear_counter >= EAR_CONSEC_FRAMES:
                        parpadeos += 1
                        if parpadeos >= PARPADEOS_REQUERIDOS:
                            parpadeo_ok = True
                    ear_counter = 0

            # ===== RECONOCIMIENTO FACIAL cada 3 frames =====
            if frame_count % 3 == 0:
                small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_small, model="hog")

                if face_locations and self.conocidos_encodings:
                    face_encodings = face_recognition.face_encodings(rgb_small, face_locations)

                    for face_encoding in face_encodings:
                        distancias = face_recognition.face_distance(
                            self.conocidos_encodings, face_encoding
                        )
                        mejor_idx = np.argmin(distancias)
                        confianza = 1 - distancias[mejor_idx]

                        if confianza > 0.55:
                            alumno_id_detectado = self.conocidos_ids[mejor_idx]
                            nombre_detectado    = self.conocidos_nombres[mejor_idx]
                            tipo_detectado      = self.determinar_tipo_registro(alumno_id_detectado)
                            color_rect          = VERDE_OK if parpadeo_ok else NARANJA_NO
                            if parpadeo_ok:
                                frames_reconocido += 1
                        else:
                            nombre_detectado  = "No reconocido"
                            color_rect        = ROJO
                            frames_reconocido = 0
                else:
                    frames_reconocido = 0

            # ===== DIBUJAR ROSTRO =====
            for (top, right, bottom, left) in face_locations:
                top    = top * 4 + 70
                bottom = bottom * 4 + 70
                left   = left * 4
                right  = right * 4

                cv2.rectangle(frame_display, (left, top), (right, bottom), color_rect, 2)

                etiqueta = nombre_detectado if nombre_detectado else "Detectando..."
                (tw, th), _ = cv2.getTextSize(etiqueta, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(frame_display, (left, bottom), (left + tw + 10, bottom + 28), color_rect, -1)
                cv2.putText(frame_display, etiqueta, (left + 5, bottom + 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, BLANCO, 2)

            # ===== INDICADOR DE PARPADEOS =====
            estado_parpadeo = f"Parpadeos: {min(parpadeos, PARPADEOS_REQUERIDOS)}/{PARPADEOS_REQUERIDOS}"
            color_parpadeo  = VERDE_OK if parpadeo_ok else NARANJA_NO
            cv2.putText(frame_display, estado_parpadeo, (10, 95),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.55, color_parpadeo, 2)

            if not parpadeo_ok:
                cv2.putText(frame_display, "Parpadee para verificar que es usted",
                           (10, 118), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 210, 230), 1)
            else:
                cv2.putText(frame_display, "✓ Verificacion de vida OK",
                           (10, 118), cv2.FONT_HERSHEY_SIMPLEX, 0.42, VERDE_OK, 1)

            # ===== BARRA INFERIOR con progreso =====
            cv2.rectangle(frame_display, (0, fh - 45), (fw, fh), AZUL_TECNM, -1)
            progreso    = min(frames_reconocido, FRAMES_PARA_CONFIRMAR)
            ancho_barra = int((progreso / FRAMES_PARA_CONFIRMAR) * (fw - 20))
            cv2.rectangle(frame_display, (10, fh - 35), (fw - 10, fh - 15), (50, 70, 100), -1)
            cv2.rectangle(frame_display, (10, fh - 35), (10 + ancho_barra, fh - 15), VERDE_OK, -1)

            estado = "Verificando identidad..." if frames_reconocido > 0 else "Esperando rostro..."
            cv2.putText(frame_display, estado, (15, fh - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 210, 230), 1)
            cv2.putText(frame_display, "Q = Cancelar", (fw - 100, fh - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 210, 230), 1)

            # ===== CONFIRMAR solo si parpadeo_ok =====
            if frames_reconocido >= FRAMES_PARA_CONFIRMAR and parpadeo_ok and alumno_id_detectado:
                self.registrar_acceso(alumno_id_detectado, tipo_detectado, frame)
                resultado_final = {
                    'alumno_id': alumno_id_detectado,
                    'nombre':    nombre_detectado,
                    'tipo':      tipo_detectado,
                }
                cap.release()
                cv2.destroyAllWindows()
                if callback_resultado:
                    callback_resultado(resultado_final)
                return resultado_final

            cv2.imshow("Control de Acceso - TECNM", frame_display)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        return None