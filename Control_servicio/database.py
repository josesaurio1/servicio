import mysql.connector
from mysql.connector import Error

class Database:
    def __init__(self):
        self.host = "localhost"
        self.database = "control_servicio"
        self.user = "root"
        self.password = ""  # Tu password de XAMPP
        
    def conectar(self):
        try:
            conn = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password
            )
            return conn
        except Error as e:
            print(f"Error de conexión: {e}")
            return None
    
    def ejecutar_query(self, query, params=None):
        conn = self.conectar()
        if conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(query, params or ())
                conn.commit()
                return cursor
            except Error as e:
                print(f"Error en query: {e}")
                return None
            finally:
                conn.close()
    
    def obtener_datos(self, query, params=None):
        conn = self.conectar()
        if conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(query, params or ())
                return cursor.fetchall()
            except Error as e:
                print(f"Error: {e}")
                return []
            finally:
                conn.close()