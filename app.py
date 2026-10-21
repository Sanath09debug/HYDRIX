from flask import Flask, jsonify, render_template
import random
import serial
import threading
import time
import json

# ==========================================
# HYDRIX - Smart Water Monitoring System
# ==========================================

app = Flask(__name__)

# Arduino serial configuration
ARDUINO_PORT = "COM6"
BAUD_RATE = 9600

# Sensor data storage
sensor_data_store = {
    "temperature": None,
    "tds": None,
    "battery": None,
    "connected": False,
    "mode": "DEMO MODE"
}

data_lock = threading.Lock()


# ==========================================
# Read data from Arduino
# ==========================================

def read_arduino():
    while True:
        try:
            print(f"[HYDRIX] Connecting to Arduino on {ARDUINO_PORT}...")

            with serial.Serial(
                ARDUINO_PORT,
                BAUD_RATE,
                timeout=2
            ) as arduino:

                # Allow the Arduino to reset after serial connection
                time.sleep(2)

                print("[HYDRIX] Arduino connected!")

                while True:
                    line = arduino.readline().decode(
                        "utf-8",
                        errors="ignore"
                    ).strip()

                    if not line:
                        continue

                    try:
                        readings = json.loads(line)

                        temperature = readings.get("temperature")
                        tds = readings.get("tds")
                        battery = readings.get("battery")

                        with data_lock:
                            if temperature is not None:
                                sensor_data_store["temperature"] = float(
                                    temperature
                                )

                            if tds is not None:
                                sensor_data_store["tds"] = int(tds)

                            if battery is not None:
                                sensor_data_store["battery"] = int(battery)

                            sensor_data_store["connected"] = True
                            sensor_data_store["mode"] = "CONNECTED"

                    except (
                        json.JSONDecodeError,
                        ValueError,
                        TypeError
                    ):
                        # Ignore serial messages that aren't valid JSON
                        continue

        except (serial.SerialException, OSError) as error:
            print(f"[HYDRIX] Arduino unavailable: {error}")

            with data_lock:
                sensor_data_store["connected"] = False
                sensor_data_store["mode"] = "DEMO MODE"

            time.sleep(3)


# ==========================================
# Main dashboard
# ==========================================

@app.route("/")
def home():
    return render_template("index.html")


# ==========================================
# Sensor API
# ==========================================

@app.route("/api/sensors")
def get_sensor_data():
    with data_lock:
        current = sensor_data_store.copy()

    # Return actual Arduino readings when connected
    if current["connected"]:
        return jsonify(current)

    # Demo mode when Arduino is unavailable
    return jsonify({
        "temperature": round(random.uniform(24, 30), 1),
        "tds": random.randint(200, 450),
        "battery": random.randint(65, 100),
        "connected": False,
        "mode": "DEMO MODE"
    })


# ==========================================
# Application health check
# ==========================================

@app.route("/api/health")
def health_check():
    return jsonify({
        "application": "HYDRIX",
        "status": "running"
    })


# ==========================================
# Start HYDRIX
# ==========================================

if __name__ == "__main__":
    print("=" * 45)
    print("  HYDRIX Smart Water Monitoring System")
    print("=" * 45)

    # Start Arduino reader in the background
    reader_thread = threading.Thread(
        target=read_arduino,
        daemon=True
    )

    reader_thread.start()

    # Start Flask server
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        use_reloader=False
    )