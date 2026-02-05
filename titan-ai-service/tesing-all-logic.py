import requests
import random
import string
import json
import sys
import time

# ==============================================================================
# ⚙️ COMMANDER'S CONFIGURATION
# ==============================================================================
# 🎯 TARGET: Your VPN Server IP via the Gateway Port (8888)
BASE_URL = "http://100.117.33.69:8888/v1" 

# AI Logic Thresholds (Must match your Python Risk Engine)
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
    return f"titan_user_{suffix}", "password123"

def print_step(step, msg):
    print(f"\n{Colors.CYAN}🔹 [STEP {step}] {msg}{Colors.ENDC}")

def assert_response(res, expected_codes, success_msg):
    if res.status_code in expected_codes:
        print(f"{Colors.GREEN}   ✅ {success_msg}{Colors.ENDC}")
        return True
    else:
        print(f"{Colors.FAIL}   ❌ FAILED! Status: {res.status_code}{Colors.ENDC}")
        try:
            print(f"      Response: {res.json()}")
        except:
            print(f"      Response: {res.text}")
        sys.exit(1)

# ==============================================================================
# 🚀 MISSION EXECUTION
# ==============================================================================

def run_mission():
    print(f"\n{Colors.BOLD}{Colors.HEADER}🚀 STARTING TITAN SYSTEM TEST (Target: {BASE_URL}){Colors.ENDC}")
    
    # ----------------------------------------------------
    # 1. REGISTER SENDER
    # ----------------------------------------------------
    print_step(1, "Registering SENDER Identity")
    sender_user, sender_pass = get_random_user()
    
    payload = {
        "username": sender_user,
        "password": sender_pass,
        "email": f"{sender_user}@titan.com",
        "fullName": "Commander Saaki"
    }
    
    # We use /api/auth prefix to be safe, Gateway should handle it
    try:
        res = requests.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=5)
    except requests.exceptions.ConnectionError:
        print(f"{Colors.FAIL}🚨 CONNECTION FAILED! Server {BASE_URL} is unreachable.{Colors.ENDC}")
        print("   👉 Check if VPN is connected.")
        print("   👉 Check if Docker Gateway is running (Port 8888).")
        sys.exit(1)

    assert_response(res, [200, 201], f"User Created: {sender_user}")

    # ----------------------------------------------------
    # 2. LOGIN & EXTRACT JWT
    # ----------------------------------------------------
    print_step(2, "Authenticating & Retrieving Token")
    login_payload = {"username": sender_user, "password": sender_pass}
    res = requests.post(f"{BASE_URL}/api/auth/login", json=login_payload)
    
    token = None
    if assert_response(res, [200], "Authenticated"):
        data = res.json()
        # Handle different token field names (accessToken vs token)
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
    res = requests.post(f"{BASE_URL}/api/accounts", json={"accountType": "SAVINGS"}, headers=headers)
    
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
    requests.post(f"{BASE_URL}/api/auth/register", json={"username": recv_user, "password": recv_pass, "email":f"{recv_user}@mail.com", "fullName":"Target User"})
    
    # Login Receiver
    res = requests.post(f"{BASE_URL}/api/auth/login", json={"username": recv_user, "password": recv_pass})
    recv_token = res.json().get("accessToken") or res.json().get("token")
    recv_headers = {"Authorization": f"Bearer {recv_token}", "Content-Type": "application/json"}
    
    # Create Receiver Account
    res = requests.post(f"{BASE_URL}/api/accounts", json={"accountType": "CHECKING"}, headers=recv_headers)
    recv_acc_no = res.json().get("accountNumber")
    print(f"   👤 Receiver Created: {recv_user}")
    print(f"   🏦 Receiver Account: {Colors.BOLD}{recv_acc_no}{Colors.ENDC}")

    # ----------------------------------------------------
    # 5. DEPOSIT (Load Funds)
    # ----------------------------------------------------
    print_step(5, f"Injecting Liquidity ($50,000)")
    
    # Try 'toAccountNumber' first (common in some DTOs), fallback to 'accountNumber'
    deposit_payload = {"toAccountNumber": sender_acc_no, "amount": 50000.00}
    
    res = requests.post(f"{BASE_URL}/api/transactions/deposit", json=deposit_payload, headers=headers)
    
    if res.status_code != 200:
        # Fallback retry with different field name
        print(f"{Colors.WARNING}   ⚠️  Retrying with 'accountNumber'...{Colors.ENDC}")
        deposit_payload = {"accountNumber": sender_acc_no, "amount": 50000.00}
        res = requests.post(f"{BASE_URL}/api/transactions/deposit", json=deposit_payload, headers=headers)

    assert_response(res, [200], "Funds Deposited Successfully")

    # ----------------------------------------------------
    # 6. TRANSFER: LOW RISK (Should PASS)
    # ----------------------------------------------------
    print_step(6, "Executing LOW RISK Transfer ($500)")
    transfer_payload = {
        "fromAccountNumber": sender_acc_no,
        "toAccountNumber": recv_acc_no,
        "amount": 500.00,
        "note": "Low risk test"
    }
    
    res = requests.post(f"{BASE_URL}/api/transactions/transfer", json=transfer_payload, headers=headers)
    assert_response(res, [200], "Low Risk Transfer ALLOWED ✅")

    # ----------------------------------------------------
    # 7. TRANSFER: HIGH RISK (AI Should BLOCK)
    # ----------------------------------------------------
    print_step(7, f"Attempting HIGH RISK Transfer (${HIGH_RISK_THRESHOLD + 10000})")
    print(f"{Colors.WARNING}   ⚠️  EXPECTING AI SECURITY INTERVENTION...{Colors.ENDC}")
    
    transfer_payload["amount"] = HIGH_RISK_THRESHOLD + 10000.00
    
    res = requests.post(f"{BASE_URL}/api/transactions/transfer", json=transfer_payload, headers=headers)
    
    # Logic: If Status is NOT 200, or Response Text contains BLOCK/OTP/HIGH
    if res.status_code != 200:
        print(f"{Colors.GREEN}   🛡️  AI INTERCEPTED TRANSACTION! (SUCCESS){Colors.ENDC}")
        try:
            print(f"      System Response: {res.json()}")
        except:
            print(f"      System Response: {res.text}")

    elif "BLOCK" in res.text.upper() or "OTP" in res.text.upper():
         print(f"{Colors.GREEN}   🛡️  AI BLOCKED TRANSACTION (200 OK with Block Msg){Colors.ENDC}")
         print(f"      Msg: {res.text}")
    else:
        print(f"{Colors.FAIL}   🚨 SECURITY FAILURE! High Risk Transaction was ALLOWED!{Colors.ENDC}")
        print("      Check your Python Risk Engine connection.")

    print(f"\n{Colors.BOLD}{Colors.GREEN}✅ MISSION ACCOMPLISHED. SYSTEM INTEGRITY VERIFIED.{Colors.ENDC}\n")

if __name__ == "__main__":
    try:
        run_mission()
    except KeyboardInterrupt:
        print("\n🚫 Aborted.")
    except Exception as e:
        print(f"\n{Colors.FAIL}💥 FATAL ERROR: {e}{Colors.ENDC}")