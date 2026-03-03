import os
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from functools import wraps
from datetime import datetime, timedelta
import json

app = Flask(__name__, static_folder='../public', static_url_path='/', template_folder='../public')
app.secret_key = os.environ.get("SECRET_KEY", "traffic-system-secret-key")

# ===== CONFIG =====
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")

# ===== IN-MEMORY STATE (Reset on each deployment) =====
current_state = {
    "lanes": [
        {"id": 1, "pcu": 0, "counts": {}, "signal": "RED", "timer": 0, "is_service": False},
        {"id": 2, "pcu": 0, "counts": {}, "signal": "RED", "timer": 0, "is_service": False},
        {"id": 3, "pcu": 0, "counts": {}, "signal": "RED", "timer": 0, "is_service": False},
        {"id": 4, "pcu": 0, "counts": {}, "signal": "RED", "timer": 0, "is_service": False}
    ],
    "priority_lane": 0,
    "accident_mode": False,
    "last_update": datetime.now().isoformat()
}

# ===== SECURITY DECORATOR =====
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ===== ROUTES =====

@app.route('/')
def index():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return redirect('/index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        user = data.get('username', '')
        pwd = data.get('password', '')
        
        if user == ADMIN_USER and pwd == ADMIN_PASS:
            session['logged_in'] = True
            if request.is_json:
                return jsonify({"status": "success"})
            return redirect(url_for('index'))
        else:
            if request.is_json:
                return jsonify({"status": "error", "message": "Invalid credentials"}), 401
            return redirect(url_for('login'))
    
    return send_file('../public/login.html', mimetype='text/html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    \"\"\"Return current traffic state\"\"\"\n    current_state['last_update'] = datetime.now().isoformat()
    return jsonify(current_state)

@app.route('/api/detect', methods=['POST'])
@login_required
def detect_frame():
    \"\"\"Process uploaded frame for vehicle detection\"\"\"\n    try:
        # Get image from request
        if 'frame' not in request.files:
            return jsonify({"error": "No frame provided"}), 400
        
        file = request.files['frame']
        lane_id = request.form.get('lane_id', 0, type=int)
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        import cv2
        import numpy as np
        
        # Read image
        img_array = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({"error": "Invalid image"}), 400
        
        # Simplified detection (lightweight)\n        from ultralytics import YOLO
        model = YOLO('yolov8n.pt')
        results = model(frame, imgsz=320, verbose=False, conf=0.3)
        
        counts = {\"car\": 0, \"bike\": 0, \"bus\": 0, \"truck\": 0}\n        pcu = 0.0\n        \n        for r in results:\n            for box in r.boxes:\n                cls = int(box.cls[0])\n                conf = float(box.conf[0])\n                \n                # COCO class mappings\n                if cls == 2: counts[\"car\"] += 1; pcu += 1.0\n                elif cls == 3: counts[\"bike\"] += 1; pcu += 0.5\n                elif cls == 5: counts[\"bus\"] += 1; pcu += 3.0\n                elif cls == 7: counts[\"truck\"] += 1; pcu += 2.5\n        \n        # Update state\n        if 0 <= lane_id < 4:\n            current_state[\"lanes\"][lane_id][\"counts\"] = counts\n            current_state[\"lanes\"][lane_id][\"pcu\"] = pcu\n        \n        return jsonify({\"counts\": counts, \"pcu\": pcu, \"lane\": lane_id})\n    \n    except Exception as e:\n        return jsonify({\"error\": str(e)}), 500

@app.route('/api/service/<int:lane_id>', methods=['POST'])
@login_required\ndef toggle_service(lane_id):
    \"\"\"Toggle service lane mode\"\"\"\n    if 0 < lane_id <= 4:\n        current_state[\"lanes\"][lane_id-1][\"is_service\"] = not current_state[\"lanes\"][lane_id-1][\"is_service\"]\n        return jsonify({\"status\": \"success\", \"mode\": current_state[\"lanes\"][lane_id-1][\"is_service\"]})\n    return jsonify({\"error\": \"Invalid lane\"}), 400

@app.route('/api/accident', methods=['POST'])\n@login_required\ndef toggle_accident():\n    \"\"\"Toggle emergency/accident mode\"\"\"\n    current_state[\"accident_mode\"] = not current_state[\"accident_mode\"]\n    return jsonify({\"status\": \"success\", \"mode\": current_state[\"accident_mode\"]})\n\n@app.route('/api/signal/<int:lane_id>/<signal>', methods=['POST'])\n@login_required\ndef set_signal(lane_id, signal):\n    \"\"\"Manually set signal for testing\"\"\"\n    if 0 < lane_id <= 4 and signal in [\"RED\", \"GREEN\", \"YELLOW\"]:\n        current_state[\"lanes\"][lane_id-1][\"signal\"] = signal\n        return jsonify({\"status\": \"success\"})\n    return jsonify({\"error\": \"Invalid parameters\"}), 400\n\n# ===== HEALTH CHECK =====\n@app.route('/api/health', methods=['GET'])\ndef health():\n    return jsonify({\"status\": \"ok\", \"timestamp\": datetime.now().isoformat()})\n\n# ===== ERROR HANDLERS =====\n@app.errorhandler(404)\ndef not_found(error):\n    return jsonify({\"error\": \"Not found\"}), 404\n\n@app.errorhandler(500)\ndef server_error(error):\n    return jsonify({\"error\": \"Server error\"}), 500\n