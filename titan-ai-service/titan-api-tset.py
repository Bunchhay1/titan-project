import requests
import uuid
import json
import sys
import time

# ==========================================
# ⚙️ CONFIGURATION (TARGET: SERVER IP)
# ==========================================
BASE_URL = "hhttp://192.168.0.120:8080"  # Gateway Port
HEADERS = {"Content-Type": "application/json"}

# ពណ៌សម្រាប់មើលងាយស្រួល
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def log(message, color=RESET):
    print(f"{color}{message}{RESET}")

# ==========================================
# 1. 🏥 HEALTH CHECK
# ==========================================
def check_health():
    url = f"{BASE_URL}/actuator/health"
    log(f"--- 🏥 Checking System Health at {url} ---", YELLOW)
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        
        status = data.get("status", "UNKNOWN")
        redis_status = data.get("components", {}).get("redis", {}).get("status", "UNKNOWN")
        db_status = data.get("components", {}).get("db", {}).get("status", "UNKNOWN")

        if status == "UP":
            log(f"✅ SYSTEM: UP | DB: {db_status} | REDIS: {redis_status}", GREEN)
            return True
        else:
            log(f"❌ SYSTEM UNSTABLE: {json.dumps(data, indent=2)}", RED)
            # បើ Redis នៅ Down យើងព្រមាន តែនៅតែសាកល្បងទៅមុខ
            if redis_status == "DOWN":
                log("⚠️ WARNING: Redis is DOWN! Titan Core might fail to cache.", RED)
            return True # ដាក់ True ដើម្បីបង្ខំតេស្តបន្ត
    except Exception as e:
        log(f"❌ CONNECTION FAILED: {str(e)}", RED)
        log("💡 Hint: Check VPN, Wifi, or run 'ufw allow 8080' on server.", YELLOW)
        return False

# ==========================================
# 2. 📝 REGISTER USER
# ==========================================
def register_user():
    # បង្កើតឈ្មោះចៃដន្យរាល់ដង ដើម្បីកុំឱ្យជាន់គ្នា
    random_id = str(uuid.uuid4())[:8]
    username = f"user_{random_id}"
    email = f"{username}@titan.com"
    password = "password123"
    
    url = f"{BASE_URL}/auth/register"
    payload = {
        "username": username,
        "email": email,
        "password": password,
        "fullName": "Titan Commander",
        "pin": "123456"
    }
    
    log(f"\n--- 📝 Registering User: {username} ---", YELLOW)
    try:
        response = requests.post(url, json=payload, headers=HEADERS, timeout=10)
        if response.status_code in [200, 201]:
            log(f"✅ Registration Success! ID: {response.json().get('id')}", GREEN)
            return username, password
        else:
            log(f"❌ Register Failed: {response.status_code} - {response.text}", RED)
            return None, None
    except Exception as e:
        log(f"❌ Register Error: {str(e)}", RED)
        return None, None

# ==========================================
# 3. 🔐 LOGIN USER
# ==========================================
def login_user(username, password):
    url = f"{BASE_URL}/auth/login"
    payload = {
        "username": username,
        "password": password
    }
    
    log(f"\n--- 🔐 Logging in... ---", YELLOW)
    try:
        response = requests.post(url, json=payload, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            token = response.json().get("token")
            log(f"✅ Login Success! Token acquired.", GREEN)
            return token
        else:
            log(f"❌ Login Failed: {response.status_code} - {response.text}", RED)
            return None
    except Exception as e:
        log(f"❌ Login Error: {str(e)}", RED)
        return None

# ==========================================
# 4. 💰 CHECK BALANCE (Protected Route)
# ==========================================
# ==========================================
# 4. 💰 CHECK BALANCE (Protected Route)
# ==========================================
def check_balance(token):
    # ❌ ពីមុន (ខុស):
    # url = f"{BASE_URL}/accounts"
    
    # ✅ កែទៅជា (ត្រូវ): ថែម /api នៅខាងមុខ
    url = f"{BASE_URL}/api/accounts" 
    
    auth_headers = HEADERS.copy()
    auth_headers["Authorization"] = f"Bearer {token}"
    
    log(f"\n--- 💰 Checking Account Balance... ---", YELLOW)
    try:
        response = requests.get(url, headers=auth_headers, timeout=10)
        # ... (កូដនៅសល់ទុកដដែល)
        response = requests.get(url, headers=auth_headers, timeout=10)
        if response.status_code == 200:
            accounts = response.json()
            if accounts:
                log(f"✅ Access Granted! Found {len(accounts)} accounts.", GREEN)
                for acc in accounts:
                    log(f"   🏦 Account: {acc.get('accountNumber')} | Balance: ${acc.get('balance')}", GREEN)
            else:
                log(f"✅ Access Granted but no accounts found (create one via API).", GREEN)
        else:
            log(f"❌ Balance Check Failed: {response.status_code} - {response.text}", RED)
    except Exception as e:
        log(f"❌ Balance Error: {str(e)}", RED)

# ==========================================
# 🚀 MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    log("🚀 STARTING TITAN AUTOMATION TEST\n=================================", YELLOW)
    
    # 1. Check Health
    if check_health():
        # 2. Register
        user, pwd = register_user()
        if user:
            # 3. Login
            token = login_user(user, pwd)
            if token:
                # 4. Check Balance
                check_balance(token)
    
    log("\n=================================\n🏁 TEST COMPLETED", YELLOW)