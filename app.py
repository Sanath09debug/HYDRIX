
import os
import time
import hmac
from threading import Lock

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Authentication token configured in Render Environment settings.
DEVICE_TOKEN = os.environ.get("HYDRIX_DEVICE_TOKEN", "")

# Data received from the ESP32.
sensor_data = {
    "temperature": None,
    "tds": None,
    "battery": None,
    "connected": False,
    "mode": "DEMO MODE",
}

last_update = 0.0
data_lock = Lock()

DATA_TIMEOUT = 30  # Seconds


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "application": "HYDRIX",
        "status": "running",
        "readings_endpoint": "/api/readings",
    })


@app.route("/api/readings", methods=["POST"])
def receive_readings():
    global last_update

    if not DEVICE_TOKEN:
        return jsonify({
            "success": False,
            "error": "Device token is not configured on the server",
        }), 503

    supplied_token = request.headers.get("X-HYDRIX-TOKEN", "")

    if not hmac.compare_digest(supplied_token, DEVICE_TOKEN):
        return jsonify({
            "success": False,
            "error": "Invalid device token",
        }), 401

    readings = request.get_json(silent=True)

    if not isinstance(readings, dict):
        return jsonify({
            "success": False,
            "error": "Request must contain a JSON object",
        }), 400

    try:
        temperature = float(readings["temperature"])
        tds = int(readings["tds"])
        battery = int(readings["battery"])

        if not (-55 <= temperature <= 125):
            raise ValueError("Temperature is outside the allowed range")

        if not (0 <= tds <= 10000):
            raise ValueError("TDS is outside the allowed range")

        if not (0 <= battery <= 100):
            raise ValueError("Battery must be between 0 and 100")

    except (KeyError, TypeError, ValueError, OverflowError):
        return jsonify({
            "success": False,
            "error": "Invalid temperature, tds, or battery values",
        }), 400

    with data_lock:
        sensor_data.update({
            "temperature": temperature,
            "tds": tds,
            "battery": battery,
            "connected": True,
            "mode": "CONNECTED",
        })
        last_update = time.time()

    return jsonify({
        "success": True,
        "message": "HYDRIX readings received",
    }), 200


@app.route("/api/sensors", methods=["GET"])
def get_sensor_data():
    with data_lock:
        result = sensor_data.copy()
        age = time.time() - last_update if last_update else None

    if age is not None and age <= DATA_TIMEOUT:
        result["connected"] = True
        result["mode"] = "CONNECTED"
        return jsonify(result)

    result.update({
        "connected": False,
        "mode": "DEMO MODE",
    })

    return jsonify(result)


if __name__ == "__main__":
    print("HYDRIX Smart Water Monitoring System")
    print("Device token configured:", bool(DEVICE_TOKEN))

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
    )

