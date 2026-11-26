import os
import time
import random
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# قاعدة بيانات مؤقتة لإدارة الصندوقين بالوقت الفعلي
boxes_db = {
    "box_1": {"otp": None, "expires_at": 0, "phone": None, "unlock_seconds": 5},
    "box_2": {"otp": None, "expires_at": 0, "phone": None, "unlock_seconds": 5},
}

# قراءة المفاتيح السرية من Environment Variables في Render
WHATSAPP_API_URL = os.environ.get("WHATSAPP_API_URL", "")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
ESP_API_KEY = os.environ.get("ESP_API_KEY", "")


def send_whatsapp_message(phone, box_name, otp, duration_label):
    if not WHATSAPP_API_URL or not WHATSAPP_TOKEN or not phone:
        print(f"[Whatsapp Simulation] To: {phone} | Box: {box_name} | OTP: {otp} | Duration: {duration_label}")
        return False

    message = (
        "أهلاً بك في نظام الصناديق الذكية\n"
        "تم تأكيد حجزك بنجاح!\n"
        f"الصندوق: {box_name}\n"
        f"رمز الدخول (OTP): {otp}\n"
        f"المدة: {duration_label}"
    )

    try:
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "phone": phone,
            "message": message,
        }
        resp = requests.post(WHATSAPP_API_URL, json=payload, headers=headers, timeout=10)
        return resp.status_code in (200, 201)
    except Exception as e:
        print(f"[Whatsapp Error] {e}")
        return False


def normalize_box_id(raw_box):
    if not raw_box:
        return None
    cleaned = str(raw_box).strip().lower().replace("-", "_").replace(" ", "_")
    mapping = {
        "box_1": "box_1",
        "box1": "box_1",
        "1": "box_1",
        "box_2": "box_2",
        "box2": "box_2",
        "2": "box_2",
    }
    return mapping.get(cleaned)


def compute_unlock_seconds(data):
    for key in ["duration_sec", "unlock_duration", "duration", "seconds"]:
        if key in data and data[key] is not None:
            try:
                val = int(float(data[key]))
                if val > 0:
                    return max(2, min(60, val))
            except (ValueError, TypeError):
                pass

    if "duration_min" in data and data["duration_min"] is not None:
        try:
            mins = float(data["duration_min"])
            if mins > 0:
                return max(2, min(60, int(mins * 60)))
        except (ValueError, TypeError):
            pass

    if "hours" in data and data["hours"] is not None:
        try:
            hrs = float(data["hours"])
            if hrs > 0:
                return max(5, min(60, int(hrs * 10)))
        except (ValueError, TypeError):
            pass

    return 5


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "online",
        "boxes": list(boxes_db.keys()),
    }), 200


@app.route("/api/generate-otp", methods=["POST"])
def generate_otp():
    data = request.get_json(silent=True) or {}
    box_id = normalize_box_id(data.get("box_id") or data.get("boxId") or data.get("box"))
    if not box_id or box_id not in boxes_db:
        return jsonify({"success": False, "valid": False, "message": "Unknown Box"}), 400

    phone = data.get("phone")
    otp = str(data.get("otp") or random.randint(1000, 9999)).strip()
    unlock_seconds = compute_unlock_seconds(data)
    duration_label = data.get("duration_label") or f"{unlock_seconds}s"

    ttl_seconds = int(data.get("ttl_seconds", 600))
    boxes_db[box_id] = {
        "otp": otp,
        "expires_at": time.time() + ttl_seconds,
        "phone": phone,
        "unlock_seconds": unlock_seconds,
    }

    if phone:
        send_whatsapp_message(phone, box_id, otp, duration_label)

    return jsonify({
        "success": True,
        "valid": True,
        "box_id": box_id,
        "otp": otp,
        "duration_sec": unlock_seconds,
        "unlock_duration": unlock_seconds,
        "message": f"OTP generated for {box_id}"
    }), 200


@app.route("/api/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json(silent=True) or {}

    incoming_key = (
        request.headers.get("X-API-Key")
        or request.headers.get("Authorization", "").replace("Bearer ", "").strip()
        or data.get("api_key")
    )
    if ESP_API_KEY and incoming_key and incoming_key != ESP_API_KEY:
        return jsonify({"success": False, "valid": False, "message": "Unauthorized"}), 401

    raw_box = data.get("box_id") or data.get("boxId") or data.get("box")
    box_id = normalize_box_id(raw_box)
    otp = str(data.get("otp") or data.get("code") or "").strip()

    if not box_id or box_id not in boxes_db:
        return jsonify({"success": False, "valid": False, "message": "Unknown Box"}), 400

    if not otp:
        return jsonify({"success": False, "valid": False, "message": "OTP required"}), 400

    record = boxes_db[box_id]
    if not record.get("otp") or record["otp"] != otp:
        return jsonify({"success": False, "valid": False, "message": "Invalid OTP"}), 401

    if time.time() > record.get("expires_at", 0):
        boxes_db[box_id]["otp"] = None
        return jsonify({"success": False, "valid": False, "message": "OTP Expired"}), 401

    unlock_seconds = int(record.get("unlock_seconds", 5))
    boxes_db[box_id]["otp"] = None
    boxes_db[box_id]["expires_at"] = 0

    return jsonify({
        "success": True,
        "valid": True,
        "box_id": box_id,
        "duration_sec": unlock_seconds,
        "unlock_duration": unlock_seconds,
        "message": "Access Granted"
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
