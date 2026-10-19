from flask import Flask, request, jsonify
import random

app = Flask(__name__)

# تخزين مؤقت للرمز النشط حالياً (للتوضيح في مشروع التخرج)
current_otp = "1234" 

@app.route('/')
def home():
    return "Smart Locker Server is Running!"

# مسار لتوليد رمز جديد وإرساله
@app.route('/api/generate-otp', methods=['POST'])
def generate_otp():
    global current_otp
    current_otp = str(random.randint(1000, 9999))
    print(f"Generated New OTP: {current_otp}")
    return jsonify({"status": "success", "otp": current_otp}), 200

# مسار يتحقق من الرمز المدخل من الـ ESP32
@app.route('/api/verify', methods=['POST'])
def verify_code():
    data = request.json
    entered_code = data.get('code')
    
    if entered_code == current_otp:
        print("Access Granted: Correct OTP!")
        return jsonify({"status": "open", "message": "Access Granted"}), 200
    else:
        print("Access Denied: Wrong OTP!")
        return jsonify({"status": "denied", "message": "Invalid OTP"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)