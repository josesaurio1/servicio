import face_recognition
import cv2
import pickle
import os
from database import Database
from qr_manager import QRManager

class RegistroAlumno:
    
    def __init__(self):
        self.db = Database()
        self.qr_manager = QRManager()
        os.makedirs("fotos_alumnos", exist_ok=True)
    
    def capturar_fotos(self, numero_control, n_fotos=5):
        """
        Captura múltiples fotos del alumno desde diferentes ángulos
        para mejor precisión
        """
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
        
        print(f"📸 Capturando {n_fotos} fotos del alumno {numero_control}")
        
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
            if key == ord(' '):  # Espacio para capturar
                path = f"fotos_alumnos/{numero_control}_{count}.jpg"
                cv2.imwrite(path, frame)
                fotos_capturadas.append(path)
                count += 1
                print(f"✅ Foto {count} capturada")
            elif key == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        return fotos_capturadas
    
    def generar_encoding(self, rutas_fotos):
        """Genera el encoding facial promedio de varias fotos"""
        encodings = []
        
        for ruta in rutas_fotos:
            img = face_recognition.load_image_file(ruta)
            face_encodings = face_recognition.face_encodings(img)
            
            if face_encodings:
                encodings.append(face_encodings[0])
                print(f"✅ Encoding generado de {ruta}")
            else:
                print(f"⚠️ No se detectó cara en {ruta}")
        
        if encodings:
            # Promedio de todos los encodings para mayor precisión
            encoding_promedio = sum(encodings) / len(encodings)
            return encoding_promedio
        
        return None
    
    def registrar_alumno(self, numero_control, nombre, apellidos, carrera):
        """Proceso completo de registro de un nuevo alumno"""
        
        # 1. Verificar que no exista
        existente = self.db.obtener_datos(
            "SELECT id FROM alumnos WHERE numero_control=%s",
            (numero_control,)
        )
        if existente:
            print(f"❌ El alumno {numero_control} ya existe")
            return False
        
        # 2. Capturar fotos
        print("\n📸 CAPTURA DE FOTOS")
        fotos = self.capturar_fotos(numero_control)
        
        if not fotos:
            print("❌ No se capturaron fotos")
            return False
        
        # 3. Generar encoding facial
        print("\n🧠 Procesando reconocimiento facial...")
        encoding = self.generar_encoding(fotos)
        
        if encoding is None:
            print("❌ No se pudo generar el encoding facial")
            return False
        
        # 4. Guardar en BD
        encoding_bytes = pickle.dumps(encoding)
        cursor = self.db.ejecutar_query(
            """INSERT INTO alumnos (numero_control, nombre, apellidos, carrera, 
               foto_path, encoding_facial) VALUES (%s, %s, %s, %s, %s, %s)""",
            (numero_control, nombre, apellidos, carrera, fotos[0], encoding_bytes)
        )
        
        # Obtener ID del alumno recién registrado
        alumno = self.db.obtener_datos(
            "SELECT id FROM alumnos WHERE numero_control=%s",
            (numero_control,)
        )
        
        if alumno:
            alumno_id = alumno[0]['id']
            # 5. Generar QR
            codigo_qr, path_qr = self.qr_manager.generar_qr(alumno_id, numero_control)
            print(f"\n✅ Alumno registrado exitosamente!")
            print(f"   Nombre: {nombre} {apellidos}")
            print(f"   No. Control: {numero_control}")
            print(f"   QR guardado en: {path_qr}")
            return True
        
        return False