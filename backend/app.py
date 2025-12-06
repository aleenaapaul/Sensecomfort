# dashboard/backend/app.py
import os
from datetime import datetime
from collections import deque

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import joblib
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(__file__)
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))
MODEL_PATH = os.path.join(BASE_DIR, "multiuser_logreg_5d.pkl")  # optional model bundle

# Flask app serves static frontend files from FRONTEND_DIR
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

# Simple in-memory history and last prediction
HISTORY = deque(maxlen=120)
LAST_PRED = None

# Load model bundle if present (expects dict with keys: model, scaler, features)
model = scaler = feat_list = None
if os.path.exists(MODEL_PATH):
    try:
        bundle = joblib.load(MODEL_PATH)
        model = bundle.get("model")
        scaler = bundle.get("scaler")
        feat_list = bundle.get("features")
        app.logger.info("Loaded model bundle with features: %s", feat_list)
    except Exception as e:
        app.logger.error("Failed to load model: %s", e)

# Utility: safe send for frontend assets (prevents directory traversal)
def safe_send_frontend(filename):
    safe_path = os.path.normpath(os.path.join(FRONTEND_DIR, filename))
    if not safe_path.startswith(FRONTEND_DIR):
        app.logger.warning("Blocked attempt to access outside frontend dir: %s", safe_path)
        return "Forbidden", 403
    if not os.path.exists(safe_path):
        app.logger.error("Frontend file missing: %s", safe_path)
        return "Not found", 404
    return send_from_directory(FRONTEND_DIR, filename)

# Serve index.html at root
@app.route("/", methods=["GET"])
def index():
    return safe_send_frontend("index.html")

# Serve frontend static assets (css/js/images)
@app.route("/<path:filename>", methods=["GET"])
def serve_frontend_file(filename):
    return safe_send_frontend(filename)

# Healthcheck
@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "pong"}), 200

def build_features_from_history(history_list):
    """
    Simple feature builder that mimics rolling windows used at training.
    Replace/extend to exactly match your training pipeline.
    Expects history_list as list of dicts with 'timestamp' and 'resistance'.
    """
    if not history_list:
        return None
    df = pd.DataFrame(history_list)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["resistance"] = df["resistance"].astype(float)
    df["diff_1"] = df["resistance"].diff().fillna(0)
    df["roll_mean_3"] = df["resistance"].rolling(3, min_periods=1).mean()
    df["roll_std_3"] = df["resistance"].rolling(3, min_periods=1).std().fillna(0)
    df["roll_min_7"] = df["resistance"].rolling(7, min_periods=1).min()
    df["roll_mean_7"] = df["resistance"].rolling(7, min_periods=1).mean()
    last = df.iloc[-1]
    features = {
        "resistance": float(last["resistance"]),
        "diff_1": float(last["diff_1"]),
        "roll_mean_3": float(last["roll_mean_3"]),
        "roll_std_3": float(last["roll_std_3"]),
        "roll_min_7": float(last["roll_min_7"]),
        "roll_mean_7": float(last["roll_mean_7"]),
        "day_of_week": int(last["timestamp"].weekday()),
        "day_of_month": int(last["timestamp"].day),
    }
    return features

# Prediction endpoint
@app.route("/predict", methods=["POST"])
def predict():
    # Accept JSON like {"resistance": 210.5}
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "invalid json"}), 400

    if isinstance(payload, (int, float)):
        resistance = float(payload)
    elif isinstance(payload, dict) and "resistance" in payload:
        try:
            resistance = float(payload["resistance"])
        except Exception:
            return jsonify({"error": "invalid resistance value"}), 400
    else:
        return jsonify({"error": "missing resistance"}), 400

    # optional debug log for incoming posts
    app.logger.info("Received /predict: resistance=%s", resistance)

    ts = datetime.utcnow().isoformat()
    HISTORY.append({"timestamp": ts, "resistance": resistance})

    features = build_features_from_history(list(HISTORY))
    if features is None:
        return jsonify({"error": "not enough history"}), 400

    # Use model if available, else fallback heuristic
    try:
        if model is not None and scaler is not None and feat_list is not None:
            x = np.array([features.get(f, 0.0) for f in feat_list]).reshape(1, -1)
            x_scaled = scaler.transform(x)
            prob = float(model.predict_proba(x_scaled)[0, 1])
            cls = int(model.predict(x_scaled)[0])
        else:
            raise RuntimeError("No model available")
    except Exception as e:
        app.logger.debug("Model prediction not used/failed: %s", e)
        prob = min(max(0.0, -features["diff_1"] / 100.0 + 0.5), 1.0)
        cls = int(prob > 0.6)
    print("MODEL PROB:", prob)

    if prob > 0.9:
        status = "Detected"
        days_left = 0
    elif prob > 0.6:
        status = "Approaching"
        days_left = 1
    elif prob > 0.4:
        status = "Approaching"
        days_left = 2
    else:
        status = "Normal"
        days_left = None

    resp = {
        "probability": round(prob, 4),
        "class": cls,
        "status": status,
        "days_left": days_left,
        "history": list(HISTORY),
        "timestamp": ts,
    }

    # store latest prediction for dashboard polling
    global LAST_PRED
    LAST_PRED = resp

    return jsonify(resp), 200

# New route to return the latest prediction
@app.route("/latest", methods=["GET"])
def latest():
    """
    Return the last prediction made by /predict.
    Useful for dashboards that only read server state (ESP posts).
    """
    if LAST_PRED is None:
        # 204 No Content is appropriate when there's no data; include a small message if desired
        return jsonify({"status": "no_data", "message": "No sensor data received yet."}), 204
    return jsonify(LAST_PRED), 200

if __name__ == "__main__":
    # debug-based dev server; accessible on LAN
    app.run(host="0.0.0.0", port=5000, debug=True)
