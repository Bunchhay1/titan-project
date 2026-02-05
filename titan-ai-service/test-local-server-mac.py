import requests
import random
import string
import sys
import time
import json

# ==============================================================================
# ⚙️ COMMANDER CONFIGURATION
# ==============================================================================
# 🎯 TARGET: Java Core running locally on Mac
BASE_URL = "http://localhost:8080/api/v1"

# 🛑 AI THRESHOLD: Any transfer above this should trigger Titan AI
HIGH_RISK_THRESHOLD = 10000.00 

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# ==============================================================================
# 🛠️ TACTICAL HELPERS
# ==============================================================================
def get_random_user():
    suffix = ''.join(random.choices(string.digits, k=4))
    return f"mac_user_{suffix}", "password123"

def print_step(step, msg):
    print(f"\n{Colors.CYAN}🔹 [STEP {step}] {msg}{Colors.ENDC}")

def assert_response(res, expected_codes, success_msg):
    if res.status_code in expected_codes:
        print(f"{Colors.GREEN}   ✅ {success_msg}{Colors.ENDC}")
        return True
    else:
        print(f"{Colors.FAIL}   ❌ FAILED! Status: {res.status_code}{Colors.ENDC}")
        try:
            print(f"      Response: {json.dumps(res.json(), indent=2)}")
        except:
            print(f"      Response: {res.text}")
        sys.exit(1)

# ==============================================================================
# 🚀 MISSION EXECUTION
# ==============================================================================

def run_mission():
    print(f"\n{Colors.BOLD}{Colors.HEADER}🚀 STARTING TITAN SYSTEM TEST (Target: {BASE_URL}){Colors.ENDC}")
    
    # ----------------------------------------------------
    # 0. HEALTH CHECK
    # ----------------------------------------------------
    try:
        # Just checking if server is up (Login endpoint is usually public)
        requests.post(f"{BASE_URL}/auth/login", json={}) 
    except requests.exceptions.ConnectionError:
        print(f"{Colors.FAIL}🚨 CRITICAL ERROR: Connection Refused!{Colors.ENDC}")
        print(f"   👉 Java App is NOT running on {BASE_URL}")
        print("   👉 Please run: ./gradlew bootRun")
        sys.exit(1)

    # ----------------------------------------------------
    # 1. REGISTER SENDER
    # ----------------------------------------------------
    print_step(1, "Registering SENDER Identity")
    sender_user, sender_pass = get_random_user()
    
    # 💣 UNIVERSAL PAYLOAD: Sending both keys to ensure compatibility
    payload = {
        "firstname": "Commander",
        "lastname": "Saaki",
        "username": sender_user,
        "email": f"{sender_user}@local.com",
        "fullName": "Commander Saaki",
        "pin": "1234",
        
        # 👇 The Shotgun: Sending ALL possible password field names
        "password": sender_pass,
        "rawPassword": sender_pass
    }
    
    res = requests.post(f"{BASE_URL}/auth/register", json=payload)
    assert_response(res, [200, 201], f"User Created: {sender_user}")

    # ----------------------------------------------------
    # 2. LOGIN & EXTRACT JWT
    # ----------------------------------------------------
    print_step(2, "Authenticating & Retrieving Token")
    
    login_payload = {
        "username": sender_user, 
        "password": sender_pass,
        "rawPassword": sender_pass
    }
    
    res = requests.post(f"{BASE_URL}/auth/login", json=login_payload)
    
    token = None
    if assert_response(res, [200], "Authenticated"):
        data = res.json()
        token = data.get("accessToken") or data.get("token")
    
    if not token:
        print(f"{Colors.FAIL}🚨 NO TOKEN FOUND IN RESPONSE!{Colors.ENDC}")
        sys.exit(1)
        
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print(f"   🔑 Token: {token[:15]}... (Secure)")

    # ----------------------------------------------------
    # 3. CREATE ACCOUNT (SENDER)
    # ----------------------------------------------------
    print_step(3, "Initializing Asset Vault (Sender)")
    res = requests.post(f"{BASE_URL}/accounts", json={"accountType": "SAVINGS"}, headers=headers)
    
    sender_acc_no = None
    if assert_response(res, [200, 201], "Vault Opened"):
        sender_acc_no = res.json().get("accountNumber")
        print(f"   🏦 Sender Account: {Colors.BOLD}{sender_acc_no}{Colors.ENDC}")

    # ----------------------------------------------------
    # 4. SETUP RECEIVER (Shadow User)
    # ----------------------------------------------------
    print_step(4, "Setting up Receiver (Target)")
    recv_user, recv_pass = get_random_user()
    
    # Register Receiver
    recv_payload = {
        "firstname": "Target", "lastname": "User",
        "username": recv_user, "email":f"{recv_user}@local.com", "fullName":"Local Target",
        "password": recv_pass, "rawPassword": recv_pass, "pin": "0000"
    }
    requests.post(f"{BASE_URL}/auth/register", json=recv_payload)
    
    # Login Receiver
    res = requests.post(f"{BASE_URL}/auth/login", json={"username": recv_user, "password": recv_pass, "rawPassword": recv_pass})
    recv_token = res.json().get("accessToken") or res.json().get("token")
    recv_headers = {"Authorization": f"Bearer {recv_token}", "Content-Type": "application/json"}
    
    # Create Receiver Account
    res = requests.post(f"{BASE_URL}/accounts", json={"accountType": "CHECKING"}, headers=recv_headers)
    recv_acc_no = res.json().get("accountNumber")
    print(f"   👤 Receiver Created: {recv_user}")
    print(f"   🏦 Receiver Account: {Colors.BOLD}{recv_acc_no}{Colors.ENDC}")

    # ----------------------------------------------------
    # 5. DEPOSIT (Load Funds)
    # ----------------------------------------------------
    print_step(5, f"Injecting Liquidity ($50,000)")
    
    deposit_payload = {"accountNumber": sender_acc_no, "amount": 50000.00}
    res = requests.post(f"{BASE_URL}/transactions/deposit", json=deposit_payload, headers=headers)
    
    # Fallback if API uses 'toAccountNumber'
    if res.status_code != 200:
        deposit_payload = {"toAccountNumber": sender_acc_no, "amount": 50000.00}
        res = requests.post(f"{BASE_URL}/transactions/deposit", json=deposit_payload, headers=headers)

    assert_response(res, [200], "Funds Deposited Successfully")

    # ----------------------------------------------------
    # 6. TRANSFER: LOW RISK (Should PASS)
    # ----------------------------------------------------
    print_step(6, "Executing LOW RISK Transfer ($500)")
    transfer_payload = {
        "fromAccountNumber": sender_acc_no,
        "toAccountNumber": recv_acc_no,
        "amount": 500.00,
        "note": "Low risk test from Mac",
        "pin": "1234"   # <--- ✅ ត្រូវតែថែម PIN បើមិនចឹងទេនឹងជាប់ Error ថ្មី
    }
    
    res = requests.post(f"{BASE_URL}/transactions/transfer", json=transfer_payload, headers=headers)
    assert_response(res, [200], "Low Risk Transfer ALLOWED ✅")

    # ----------------------------------------------------
    # 7. TRANSFER: HIGH RISK (AI Should BLOCK)
    # ----------------------------------------------------
    print_step(7, f"Attempting HIGH RISK Transfer (${HIGH_RISK_THRESHOLD + 5000})")
    print(f"{Colors.WARNING}   ⚠️  EXPECTING AI SECURITY INTERVENTION...{Colors.ENDC}")
    
    # Increase amount to trigger AI
    transfer_payload["amount"] = HIGH_RISK_THRESHOLD + 5000.00
    
    res = requests.post(f"{BASE_URL}/transactions/transfer", json=transfer_payload, headers=headers)
    
    # We expect HTTP 406 (Not Acceptable) or a JSON body saying "BLOCK"
    response_text = res.text.upper()
    
    if res.status_code == 406 or "BLOCK" in response_text or "FRAUD" in response_text:
         print(f"{Colors.GREEN}   🛡️  AI SUCCESSFULLY BLOCKED TRANSACTION!{Colors.ENDC}")
         print(f"      AI Verdict: {res.text}")
    else:
        print(f"{Colors.FAIL}   🚨 SECURITY FAILURE! High Risk Transaction was ALLOWED!{Colors.ENDC}")
        print(f"      Status: {res.status_code}")
        print(f"      Response: {res.text}")
        print("      Check if Titan AI Service (Port 50051) is connected in Java logs.")

    print(f"\n{Colors.BOLD}{Colors.GREEN}✅ SYSTEM TEST COMPLETE.{Colors.ENDC}\n")

if __name__ == "__main__":
    try:
        run_mission()
    except KeyboardInterrupt:
        print("\n🚫 Aborted.")
    except Exception as e:
        print(f"\n{Colors.FAIL}💥 FATAL ERROR: {e}{Colors.ENDC}")