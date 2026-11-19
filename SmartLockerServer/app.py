from flask import Flask, request, jsonify, render_template_string
import random
import time
import os
import requests

app = Flask(__name__)

# قاعدة بيانات مؤقتة في الذاكرة لإدارة الصندوقين بشكل مستقل
boxes_db = {
    "box_1": {"otp": None, "expires_at": 0, "phone": None},
    "box_2": {"otp": None, "expires_at": 0, "phone": None}
}

# قراءة المفاتيح السرية من Environment Variables في Render بأمان
WHATSAPP_API_URL = os.environ.get("WHATSAPP_API_URL", "")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
ESP_API_KEY = os.environ.get("ESP_API_KEY", "")  # مفتاح حماية بين الـ ESP32 والسيرفر

def send_whatsapp_message(phone, box_name, otp, hours):
    if not WHATSAPP_API_URL or not WHATSAPP_TOKEN or not phone:
        print(f"[WhatsApp Simulation] To: {phone} | Box: {box_name} | OTP: {otp} | Hours: {hours}")
        return False
    
    message = (
        f"أهلاً بك في نظام الصناديق الذكية 📦\n"
        f"تم تأكيد حجزك بنجاح!\n"
        f"• الصندوق: {box_name}\n"
        f"• مدة الإيجار: {hours} ساعة\n"
        f"• رمز الفتح السري (OTP): *{otp}*\n"
        f"يرجى إدخال الرمز في لوحة الصندوق للفتح."
    )
    payload = {
        "token": WHATSAPP_TOKEN,
        "to": phone,
        "body": message
    }
    try:
        response = requests.post(WHATSAPP_API_URL, data=payload, timeout=5)
        print("WhatsApp API Response:", response.text)
        return True
    except Exception as e:
        print("WhatsApp Error:", e)
        return False

STORE_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>متجر تأجير الصناديق الذكية</title>
    <style>
        body { font-family: Tahoma, Arial, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; text-align: center; }
        .container { max-width: 450px; margin: auto; background: #fff; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        h2 { color: #1e293b; margin-bottom: 20px; }
        label { display: block; text-align: right; margin: 12px 0 5px; font-weight: bold; color: #334155; }
        select, input, button { width: 100%; padding: 12px; margin-bottom: 10px; border-radius: 8px; border: 1px solid #cbd5e1; box-sizing: border-box; font-size: 15px; }
        button { background: #2563eb; color: white; border: none; font-weight: bold; cursor: pointer; margin-top: 10px; }
        button:hover { background: #1d4ed8; }
        .result { margin-top: 20px; padding: 15px; background: #ecfdf5; border: 1px solid #10b981; border-radius: 8px; display: none; color: #065f46; }
        .otp-code { font-size: 28px; font-weight: bold; letter-spacing: 4px; color: #047857; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h2>📦 نظام تأجير الصناديق الذكية</h2>
        <label>اختر الصندوق:</label>
        <select id="boxId">
            <option value="box_1">الصندوق الأول (Box 1)</option>
            <option value="box_2">الصندوق الثاني (Box 2)</option>
        </select>

        <label>مدة الإيجار:</label>
        <select id="hours">
            <option value="1">ساعة واحدة (10 ريال)</option>
            <option value="2">ساعتان (18 ريال)</option>
            <option value="5">5 ساعات (40 ريال)</option>
            <option value="24">يوم كامل (80 ريال)</option>
        </select>

        <label>رقم الواتساب (مع رمز الدولة مثل 9665XXXXXXXX):</label>
        <input type="text" id="phone" placeholder="966500000000" required>

        <button onclick="rentBox()">💳 دفع وتأكيد الحجز</button>

        <div class="result" id="resultBox">
            <div>✅ تم الدفع وتفعيل الصندوق بنجاح!</div>
            <div class="otp-code" id="otpDisplay">----</div>
            <div id="infoDisplay" style="font-size: 13px;"></div>
        </div>
    </div>

    <script>
        async function rentBox() {
            const boxId = document.getElementById('boxId').value;
            const hours = document.getElementById('hours').value;
            const phone = document.getElementById('phone').value;

            if (!phone) { alert("يرجى إدخال رقم الجوال"); return; }

            const res = await fetch('/api/generate-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ box_id: boxId, hours: parseFloat(hours), phone: phone })
            });

            const data = await res.json();
            if (data.status === 'success') {
                document.getElementById('resultBox').style.display = 'block';
                document.getElementById('otpDisplay').innerText = data.otp;
                document.getElementById('infoDisplay').innerText = `صالح لـ ${data.box_id} لمدة ${hours} ساعة (تم الإرسال للواتساب)`;
            } else {
                alert("حدث خطأ: " + data.message);
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(STORE_HTML)

@app.route('/api/generate-otp', methods=['POST'])
def generate_otp():
    data = request.get_json(silent=True) or {}
    box_id = data.get('box_id', 'box_1')
    hours = float(data.get('hours', 1))
    phone = data.get('phone', '')

    if box_id not in boxes_db:
        return jsonify({"status": "error", "message": "Invalid box_id"}), 400

    new_otp = str(random.randint(1000, 9999))
    expiry_timestamp = time.time() + (hours * 3600)

    boxes_db[box_id] = {
        "otp": new_otp,
        "expires_at": expiry_timestamp,
        "phone": phone
    }

    box_label = "الصندوق الأول (Box 1)" if box_id == "box_1" else "الصندوق الثاني (Box 2)"
    send_whatsapp_message(phone, box_label, new_otp, hours)

    print(f"[{box_id}] New OTP: {new_otp} | Valid for: {hours}h")
    return jsonify({
        "status": "success",
        "box_id": box_id,
        "otp": new_otp,
        "expires_in_hours": hours
    }), 200

@app.route('/api/verify', methods=['POST'])
def verify_code():
    # التحقق من مفتاح الحماية القادم من الـ ESP32 (إذا تم ضبطه في Render)
    if ESP_API_KEY:
        client_key = request.headers.get('X-API-KEY', '')
        if client_key != ESP_API_KEY:
            print("Unauthorized ESP32 Request!")
            return jsonify({"status": "denied", "message": "Unauthorized Device"}), 401

    data = request.get_json(silent=True) or {}
    box_id = data.get('box_id', 'box_1')
    entered_code = str(data.get('code', '')).strip()

    if box_id not in boxes_db:
        return jsonify({"status": "denied", "message": "Unknown Box"}), 400

    box_info = boxes_db[box_id]
    current_time = time.time()

    if box_info["otp"] and entered_code == box_info["otp"]:
        if current_time <= box_info["expires_at"]:
            print(f"[{box_id}] Access Granted!")
            return jsonify({"status": "open", "message": "Access Granted"}), 200
        else:
            print(f"[{box_id}] Access Denied: OTP Expired!")
            return jsonify({"status": "denied", "message": "OTP Expired"}), 403
    else:
        print(f"[{box_id}] Access Denied: Wrong OTP!")
        return jsonify({"status": "denied", "message": "Invalid OTP"}), 401

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
