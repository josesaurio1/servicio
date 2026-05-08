import face_recognition
import cv2
import pickle
import os
from database import Database
from qr_manager import QRManager

CARRERAS = [
    "Ingenieria en Sistemas Computacionales",
    "Ingenieria Industrial",
    "Ingenieria en Gestion Empresarial",
    "Ingenieria en Informatica",
    "Contador Publico"
]

class RegistroAlumno:
    
    def __init__(self):
        self.db = Database()
        self.qr_manager = QRManager()
        os.makedirs("fotos_alumnos", exist_ok=True)
    
    def capturar_fotos(self, numero_control, n_fotos=5):
        cap = cv2.VideoCapture(0)
        fotos_capturadas = []
        count = 0
        instrucciones = [
            "Mire al frente",
            "Gire ligeramente a la derecha",
            "Gire ligeramente a la izquierda",
            "Levante un poco la cara",
            "Baje un poco la cara"
        ]
        while count < n_fotos:
            ret, frame = cap.read()
            if not ret:
                break
            instruccion = instrucciones[count] if count < len(instrucciones) else "Mire al frente"
            cv2.putText(frame, f"Foto {count+1}/{n_fotos}: {instruccion}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, "Presione ESPACIO para capturar", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            cv2.imshow("Registro de Alumno", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):
                path = f"fotos_alumnos/{numero_control}_{count}.jpg"
                cv2.imwrite(path, frame)
                fotos_capturadas.append(path)
                count += 1
            elif key == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()
        return fotos_capturadas
    
    def generar_encoding(self, rutas_fotos):
        encodings = []
        for ruta in rutas_fotos:
            img = face_recognition.load_image_file(ruta)
            face_encodings = face_recognition.face_encodings(img)
            if face_encodings:
                encodings.append(face_encodings[0])
        if encodings:
            import numpy as np
            encoding_promedio = np.mean(encodings, axis=0)
            return encoding_promedio
        return None
    
    def registrar_alumno(self, numero_control, nombre, apellidos, carrera):
        existente = self.db.obtener_datos(
            "SELECT id FROM alumnos WHERE numero_control=%s", (numero_control,)
        )
        if existente:
            return False, "El alumno ya existe"
        
        fotos = self.capturar_fotos(numero_control)
        if not fotos:
            return False, "No se capturaron fotos"
        
        encoding = self.generar_encoding(fotos)
        if encoding is None:
            return False, "No se pudo generar encoding facial"
        
        encoding_bytes = pickle.dumps(encoding)
        self.db.ejecutar_query(
            """INSERT INTO alumnos (numero_control, nombre, apellidos, carrera, 
               foto_path, encoding_facial) VALUES (%s, %s, %s, %s, %s, %s)""",
            (numero_control, nombre, apellidos, carrera, fotos[0], encoding_bytes)
        )
        
        alumno = self.db.obtener_datos(
            "SELECT id FROM alumnos WHERE numero_control=%s", (numero_control,)
        )
        
        if alumno:
            alumno_id = alumno[0]['id']
            codigo_qr, path_qr = self.qr_manager.generar_qr(alumno_id, numero_control)
            # Generar PDF del QR
            pdf_path = self.qr_manager.generar_pdf_qr(
                alumno_id, numero_control, nombre, apellidos, carrera, path_qr
            )
            return True, pdf_path
        
        return False, "Error al guardar en BD"