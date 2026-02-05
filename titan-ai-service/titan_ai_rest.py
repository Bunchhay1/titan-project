from flask import Flask, request, jsonify
import logging

# បង្កើត Web Server
app = Flask(__name__)

# កំណត់ Log ឱ្យឃើញច្បាស់
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

print("-------------------------------------------------------")
print("🤖 TITAN AI (REST EDITION) IS STARTING...")
print("📡 Listening on Port: 50051")
print("-------------------------------------------------------")

@app.route('/analyze', methods=['POST'])
def analyze():
    # 1. ទទួលទិន្នន័យពី Java
    data = request.json
    username = data.get('username', 'Unknown')
    amount = float(data.get('amount', 0))

    print(f"\n🔍 Analyzing Transaction: User={username}, Amount=${amount}")

    # 2. Logic របស់ AI (Simple Rule)
    # បើលើសពី $10,000 -> BLOCK
    if amount > 10000:
        print(f"   🚨 HIGH RISK DETECTED! Verdict: BLOCK 🛑")
        return jsonify({
            "verdict": "BLOCK",
            "riskScore": 0.95,
            "reason": "Amount exceeds high-risk threshold"
        })
    else:
        print(f"   ✅ LOW RISK. Verdict: PASS 🟢")
        return jsonify({
            "verdict": "PASS",
            "riskScore": 0.1,
            "reason": "Safe transaction"
        })

if __name__ == '__main__':
    # Run នៅលើ Port 50051 ដើម្បីឱ្យត្រូវគ្នាជាមួយ Java Config
    app.run(host='0.0.0.0', port=50051, debug=True)