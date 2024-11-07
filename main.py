import os
import re
import serial
import psycopg2
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException
import logging

app = FastAPI()
logger = logging.getLogger("uvicorn")

# Configuración del puerto serial
serial_port = 'COM5'  # Cambia esto al puerto correcto
baud_rate = 115200

# Configuración de la base de datos PostgreSQL desde variables de entorno
db_host = os.getenv('DB_HOST', 'localhost')
db_name = os.getenv('DB_NAME', 'iot_monitoring')
db_user = os.getenv('DB_USER', 'postgres')
db_password = os.getenv('DB_PASSWORD', 'arqui123')

def get_db_connection():
    return psycopg2.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password
    )

def insertar_datos(x, temp, timestamp):
    conn = get_db_connection()
    cur = conn.cursor()
    query = """
    INSERT INTO sensor_data (position_x, temperature, timestamp)
    VALUES (%s, %s, %s)
    RETURNING id
    """
    cur.execute(query, (x, temp, timestamp))
    inserted_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return inserted_id

def insertar_datos(x, temp, timestamp):
    conn = get_db_connection()
    cur = conn.cursor()
    query = """
    INSERT INTO sensor_data (position_x, temperature, timestamp)
    VALUES (%s, %s, %s)
    RETURNING id
    """
    cur.execute(query, (x, temp, timestamp))
    inserted_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return inserted_id

def leer_datos_serial():
    ser = serial.Serial(serial_port, baud_rate)
    try:
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').rstrip()
                logger.info(f"Datos recibidos: {line}")
                
                # Analizar la cadena de texto recibida
                match = re.match(r'PosX: (\d+) Temp: ([\d.]+)', line)
                if match:
                    x = int(match.group(1))
                    temp = float(match.group(2))
                    timestamp = datetime.now().isoformat()

                    inserted_id = insertar_datos(x, temp, timestamp)
                    logger.info(f"Datos insertados en la BD: id={inserted_id}, x={x}, temp={temp}, timestamp={timestamp}")
                else:
                    logger.warning(f"Formato de datos no reconocido: {line}")

    except KeyboardInterrupt:
        logger.info("Interrupción del usuario")

    finally:
        ser.close()

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up the application")

@app.get("/prueba")
async def prueba():
    return {"status": "success", "message": "Prueba exitosa"}

@app.get("/health")
async def health():
    return {"status": "success", "message": "El servidor está funcionando correctamente"}

@app.post("/post-sensor")
async def post_sensor(data: dict):
    try:
        x = data.get('x')
        temp = data.get('temp')

        if x is None or temp is None:
            raise ValueError("Invalid data format")

        timestamp = datetime.now().isoformat()
        inserted_id = insertar_datos(x, temp, timestamp)
        
        logger.info(f"Datos insertados en la BD: id={inserted_id}, x={x}, temp={temp}, timestamp={timestamp}")
        return {"status": "success", "message": "Datos del sensor guardados", "id": inserted_id}

    except Exception as e:
        logger.error(f"Error guardando datos del sensor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/datos-sensor")
async def get_sensor_data():
    logger.info("Fetching all sensor data")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id, position_x, temperature, timestamp FROM sensor_data")
        rows = cur.fetchall()
        
        sensor_data = [
            {"id": row[0], "position_x": row[1], "temperature": row[2], "timestamp": row[3]}
            for row in rows
        ]
        
        cur.close()
        conn.close()
        
        return {"status": "success", "data": sensor_data}
    except Exception as e:
        logger.error(f"Error fetching sensor data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save-camera-data")
async def save_camera_data(data: dict):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            INSERT INTO camera_data (image_size, timestamp)
            VALUES (%s, %s)
            RETURNING id
            """,
            (data['image_size'], data['timestamp'])
        )
        
        inserted_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Saved camera data with id: {inserted_id}")
        return {"status": "success", "message": "Camera data saved", "id": inserted_id}
    except Exception as e:
        logger.error(f"Error saving camera data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/datos-camera")
async def get_camera_data():
    logger.info("Fetching all camera data")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id, image_size, timestamp FROM camera_data")
        rows = cur.fetchall()
        
        camera_data = [
            {"id": row[0], "image_size": row[1], "timestamp": row[2]}
            for row in rows
        ]
        
        cur.close()
        conn.close()
        
        return {"status": "success", "data": camera_data}
    except Exception as e:
        logger.error(f"Error fetching camera data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":  # Nota: corregido de "_main_" a "__main__"
    import uvicorn
    from threading import Thread

    # Iniciar la lectura del puerto serial en un hilo separado
    serial_thread = Thread(target=leer_datos_serial)
    serial_thread.start()

    # Iniciar el servidor FastAPI - asegurando que escuche en todas las interfaces
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")