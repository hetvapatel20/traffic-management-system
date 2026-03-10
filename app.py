from flask import Flask, render_template, Response, jsonify, request, session, redirect, url_for
import cv2
from ai_engine.detector import TrafficDetector
from ai_engine.traffic_logic import TrafficController
import database
from functools import wraps 
import os
from ultralytics import YOLO

# --- 🛠️ SYSTEM OPTIMIZATION (Fix for Lag) ---
# OpenCV threads ko disable karte hain taaki Flask crash na ho
cv2.setNumThreads(0) 
# --------------------------------------------

app = Flask(__name__)
app.secret_key = "SUPER_SECRET_KEY_FOR_VIVA" # Session Security Key

# --- ⚙️ PERFORMANCE CONFIG (Speed Control) ---
FRAME_SKIP = 7        # Har 7th frame process hoga (jitna bada number, utna fast PC)
JPEG_QUALITY = 70     # Video quality 70% (Network lag kam karega)
RESIZE_DIM = (640, 360) # Standard Resolution

# --- 🔒 ADMIN CREDENTIALS ---
ADMIN_USER = "admin"
ADMIN_PASS = "admin123" 

# --- 📹 LOAD VIDEOS ---
# Make sure ye files 'static' folder mein hon
VIDEOS = [
    "static/traffic1.mp4",
    "static/traffic2.mp4",
    "static/traffic3.mp4",
    "static/traffic4.mp4"
]

# FFmpeg backend use kar rahe hain taaki video fast load ho
cameras = [cv2.VideoCapture(v, cv2.CAP_FFMPEG) for v in VIDEOS]

# --- 🧠 AI ENGINES INITIALIZATION ---
print("⏳ Initializing AI Engines...")
detector = TrafficDetector()
controller = TrafficController()
print("✅ AI Engines Ready!")

# --- 📊 GLOBAL STATE (Database in Memory) ---
current_state = {
    "lanes": [
        {"id": 1, "pcu": 0, "counts": {}, "signal": "RED", "timer": 0, "is_service": False},
        {"id": 2, "pcu": 0, "counts": {}, "signal": "RED", "timer": 0, "is_service": False},
        {"id": 3, "pcu": 0, "counts": {}, "signal": "RED", "timer": 0, "is_service": False},
        {"id": 4, "pcu": 0, "counts": {}, "signal": "RED", "timer": 0, "is_service": False}
    ],
    "priority_lane": 0,
    "accident_mode": False
}

# --- 🔐 SECURITY DECORATOR (Login Check) ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- 📹 VIDEO GENERATOR FUNCTION ---
def generate_frames(lane_id):
    cam = cameras[lane_id]
    frame_counter = 0
    last_processed_frame = None # Cache for skipped frames

    while True:
        success, frame = cam.read()
        if not success: 
            cam.set(cv2.CAP_PROP_POS_FRAMES, 0) # Video khatam hone par wapas loop karo
            continue
        
        # Resize first to save CPU
        frame = cv2.resize(frame, RESIZE_DIM) 
        frame_counter += 1
        
        lane_data = current_state["lanes"][lane_id]
        signal = lane_data["signal"]
        is_service_mode = lane_data["is_service"]
        
        # Global Accident Override
        if current_state["accident_mode"]: 
            signal = "RED"

        # --- SMART SKIPPING LOGIC ---
        # AI ko har baar run nahi karenge, sirf kabhi-kabhi (Optimization)
        if frame_counter % FRAME_SKIP == 0:
            processed_frame, counts, pcu, is_emergency = detector.process_frame(frame, only_emergency=is_service_mode)
            
            # --- Visual Overlays (Red/Green Box) ---
            if signal == "RED":
                overlay = processed_frame.copy()
                # Red Tint
                cv2.rectangle(overlay, (0, 0), RESIZE_DIM, (0, 0, 100), -1) 
                cv2.addWeighted(overlay, 0.3, processed_frame, 0.7, 0, processed_frame)
                cv2.putText(processed_frame, "HALT", (250, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 4)
            else:
                # Green Status
                cv2.putText(processed_frame, "GO", (270, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 4)

            # Update Global State
            current_state["lanes"][lane_id]["pcu"] = pcu
            current_state["lanes"][lane_id]["counts"] = counts
            current_state["lanes"][lane_id]["emergency"] = is_emergency
            
            last_processed_frame = processed_frame
        else:
            # Skip AI, purana frame dikhao (Fast Speed)
            processed_frame = last_processed_frame if last_processed_frame is not None else frame

        # Accident Text Override
        if current_state["accident_mode"]:
            cv2.putText(processed_frame, "ACCIDENT MODE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

        # Encode Frame to JPEG
        ret, buffer = cv2.imencode('.jpg', processed_frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# --- 🧠 LOGIC UPDATER ---
def update_logic():
    if current_state["accident_mode"]:
        for i in range(4): current_state["lanes"][i]["signal"] = "RED"
        return

    # Data extract karo controller ke liye
    lane_data = [{"pcu": l["pcu"], "emergency": l.get("emergency", False)} for l in current_state["lanes"]]
    
    # AI Decision lo
    signals, timers, active_idx = controller.decide_signal(lane_data)

    # State Update karo
    for i in range(4):
        current_state["lanes"][i]["signal"] = signals[i]
        current_state["lanes"][i]["timer"] = timers[i]
    current_state["priority_lane"] = active_idx

# --- 🌐 WEB ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username') # Naye design me agar form use ho raha hai
        # Agar JSON request hai (naye JS fetch ke through)
        if not user and request.is_json:
            data = request.get_json()
            user = data.get('username')
            pw = data.get('password')
        else:
            pw = request.form.get('password')

        if user == ADMIN_USER and pw == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="🚫 Invalid Credentials!")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required 
def index(): 
    return render_template('dashboard.html')

@app.route('/video_feed_<int:lane_id>')
@login_required
def video_feed(lane_id): 
    # Lane ID 1-4 hai, list index 0-3 hai isliye -1 kiya
    return Response(generate_frames(lane_id-1), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_stats')
@login_required
def get_stats():
    update_logic() # Har baar status update karo
    return jsonify(current_state)

@app.route('/toggle_service_mode/<int:lane_id>', methods=['POST'])
@login_required
def toggle_service_mode(lane_id):
    current_state["lanes"][lane_id-1]["is_service"] = not current_state["lanes"][lane_id-1]["is_service"]
    return jsonify({"status": "success", "new_mode": current_state["lanes"][lane_id-1]["is_service"]})

@app.route('/toggle_accident', methods=['POST'])
@login_required
def toggle_accident():
    current_state["accident_mode"] = not current_state["accident_mode"]
    return jsonify({"status": current_state["accident_mode"]})

# --- 🚀 MAIN ENTRY POINT ---
if __name__ == "__main__":
    database.init_db()
    
    # Check for SSL Certificates
    if not os.path.exists("cert.pem") or not os.path.exists("key.pem"):
        print("⚠️ WARNING: Certificates not found! HTTPS might fail.")
        print("👉 Run 'python gen_cert.py' first.")

    print("\n" + "="*50)
    print("🔒 SECURE TRAFFIC AI SERVER STARTING...")
    print(f"🚀 PERFORMANCE CONFIG: Skip={FRAME_SKIP}, Quality={JPEG_QUALITY}%")
    print(f"🌍 SERVER URL: https://127.0.0.1:5000")
    print("="*50 + "\n")

if __name__ == "__main__":
    database.init_db()
    app.run(host="0.0.0.0", port=10000, debug=False)