import requests
import random
import string
import json
import sys

# ==============================================================================
# ⚙️ CONFIGURATION
# ==============================================================================
# ✅ CORRECT (Target the Debian Server IP)
BASE_URL = "https://quilt-alert-role-ips.trycloudflare.com/api/v1"

HEADERS = {"Content-Type": "application/json"}

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def get_random_suffix():
    return ''.join(random.choices(string.digits, k=4))

def print_header(msg):
    print(f"\n{Colors.CYAN}{'='*60}\n {msg}\n{'='*60}{Colors.RESET}")

def print_step(msg):
    print(f"\n{Colors.BLUE}🔹 {msg}{Colors.RESET}")

def print_success(msg):
    print(f"{Colors.GREEN}   ✅ {msg}{Colors.RESET}")

def print_fail(msg, response=None):
    print(f"{Colors.RED}   ❌ {msg}{Colors.RESET}")
    if response:
        print(f"      Status: {response.status_code}")
        print(f"      Body:   {response.text}") # បន្ថែមជួរនេះដើម្បីមើល Error ពិត
    sys.exit(1)

# ==============================================================================
# 🛠️ HELPER: SAFER JSON PARSER
# ==============================================================================
def safe_json(response):
    """ការពារកុំឱ្យ Script គាំង បើ Server តបមកមិនមែន JSON"""
    try:
        return response.json()
    except:
        return {}

def get_token_safely(response):
    """រក Token គ្រប់ឈ្មោះដែលអាចទៅរួច"""
    data = safe_json(response)
    return data.get("accessToken") or data.get("access_token") or data.get("token")

# ==============================================================================
# 🚀 MAIN TEST LOGIC
# ==============================================================================
def run_test():
    suffix = get_random_suffix()
    sender = f"boss_{suffix}"
    receiver = f"staff_{suffix}"
    password = "password123"

    print_header(f"🚀 STARTING TITAN SYSTEM TEST (ID: {suffix})")
    print(f"   👤 Sender: {sender} | 👤 Receiver: {receiver}")

    # ------------------------------------------------------------------
    # 1. REGISTER SENDER
    # ------------------------------------------------------------------
    print_step("Step 1: Register Sender")
    res = requests.post(f"{BASE_URL}/auth/register", json={
        "username": sender, "password": password,
        "fullName": "Big Boss", "email": f"{sender}@titan.com", "pin": "123456"
    }, headers=HEADERS)
    
    if res.status_code in [200, 201]:
        print_success(f"User Created: {sender}")
    else:
        print_fail("Registration Failed", res)

    # ------------------------------------------------------------------
    # 2. LOGIN SENDER & GET TOKEN
    # ------------------------------------------------------------------
    print_step("Step 2: Login Sender")
    res = requests.post(f"{BASE_URL}/auth/login", json={"username": sender, "password": password}, headers=HEADERS)
    
    token_sender = get_token_safely(res)
    if token_sender:
        print_success(f"Token Captured! ({token_sender[:10]}...)")
    else:
        print_fail("Login OK but Token Missing!", res)

    auth_sender = {"Authorization": f"Bearer {token_sender}", "Content-Type": "application/json"}

    # ------------------------------------------------------------------
    # 3. CREATE ACCOUNT SENDER
    # ------------------------------------------------------------------
    print_step("Step 3: Create Sender Account")
    res = requests.post(f"{BASE_URL}/accounts", json={"accountType": "SAVINGS", "accountName": "Titan Vault"}, headers=auth_sender)
    
    if res.status_code in [200, 201]:
        acc_sender = safe_json(res).get("accountNumber")
        print_success(f"Sender Account: {acc_sender}")
    else:
        print_fail("Create Account Failed", res)

    # ------------------------------------------------------------------
    # 4. PREPARE RECEIVER (Auto-Setup)
    # ------------------------------------------------------------------
    print_step("Step 4: Auto-Setup Receiver")
    
    # 4.1 Register Receiver
    res = requests.post(f"{BASE_URL}/auth/register", json={
        "username": receiver, "password": password, "fullName": "Staff", "email": f"{receiver}@titan.com", "pin": "123456"
    }, headers=HEADERS)
    if res.status_code not in [200, 201]:
        print_fail("Receiver Register Failed", res)

    # 4.2 Login Receiver
    res = requests.post(f"{BASE_URL}/auth/login", json={"username": receiver, "password": password}, headers=HEADERS)
    token_receiver = get_token_safely(res)
    
    if not token_receiver:
        print_fail("Receiver Login Failed (No Token)", res)

    auth_receiver = {"Authorization": f"Bearer {token_receiver}", "Content-Type": "application/json"}
    
    # 4.3 Create Receiver Account (This is where it crashed before)
    res = requests.post(f"{BASE_URL}/accounts", json={"accountType": "SAVINGS", "accountName": "Salary"}, headers=auth_receiver)
    if res.status_code in [200, 201]:
        acc_receiver = safe_json(res).get("accountNumber")
        print_success(f"Receiver Ready: {acc_receiver}")
    else:
        print_fail("Receiver Account Creation Failed", res)

    # ------------------------------------------------------------------
    # 5. DEPOSIT MONEY
    # ------------------------------------------------------------------
   # ------------------------------------------------------------------
    # 5. DEPOSIT MONEY (DIAGNOSTIC MODE 🛠️)
    # ------------------------------------------------------------------
    print_step("Step 5: Deposit $50,000 to Sender")
    
    # ជម្រើសទី ១: សាកល្បងប្រើ "toAccountNumber"
    payload = {"toAccountNumber": acc_sender, "amount": 50000.00}
    
    print(f"   ⏳ Sending Deposit Request... Payload: {payload}")
    
    # សាកល្បងជាមួយ Token
    res = requests.post(f"{BASE_URL}/transactions/deposit", json=payload, headers=auth_sender)
    
    if res.status_code == 200:
        print_success("Deposit Success!")
    else:
        # 🔴 បើបរាជ័យ វាបង្ហាញមូលហេតុច្បាស់ៗ
        print(f"{Colors.YELLOW}   ⚠️ Failed with 'toAccountNumber'. Status: {res.status_code}")
        print(f"      Response: {res.text}{Colors.RESET}")

        # ជម្រើសទី ២: សាកល្បងប្តូរឈ្មោះ Field ទៅជា "accountNumber" (ក្រែង Java ត្រូវការឈ្មោះនេះ)
        print("   🔄 Retrying with 'accountNumber'...")
        payload_v2 = {"accountNumber": acc_sender, "amount": 50000.00}
        res_v2 = requests.post(f"{BASE_URL}/transactions/deposit", json=payload_v2, headers=auth_sender)

        if res_v2.status_code == 200:
             print_success("Deposit Success (Fixed Field Name)!")
        else:
             print_fail("Deposit Failed Completely!", res_v2)
    # ------------------------------------------------------------------
    # 6. TEST LOW RISK TRANSFER ($500)
    # ------------------------------------------------------------------
    print_step("Step 6: Testing Low Risk Transfer ($500)")
    payload = {
        "fromAccountNumber": acc_sender, "toAccountNumber": acc_receiver,
        "amount": 500.00, "pin": "123456", "note": "Coffee Money"
    }
    res = requests.post(f"{BASE_URL}/transactions/transfer", json=payload, headers=auth_sender)
    
    if res.status_code == 200:
        print_success("Transfer Allowed ✅")
    else:
        print_fail("Unexpected Error! Low risk should be allowed.", res)

    # ------------------------------------------------------------------
    # 7. TEST HIGH RISK TRANSFER ($20,000)
    # ------------------------------------------------------------------
    print_step("Step 7: Testing High Risk Transfer ($20,000)")
    print(f"   ⏳ Waiting for Python AI to judge...")
    payload["amount"] = 200000.00
    res = requests.post(f"{BASE_URL}/transactions/transfer", json=payload, headers=auth_sender)

    # We expect AI to BLOCK (Error 400 or 500)
    if res.status_code != 200:
        body_text = res.text.upper()
        msg = safe_json(res).get('message', res.text)
        
        if "BLOCK" in body_text or "HIGH" in body_text:
             print_success(f"AI BLOCKED THE TRANSACTION! 🛡️ (Correct)")
             print(f"      Message: {msg}")
        else:
             print(f"{Colors.YELLOW}   ⚠️ Blocked, but check message: {msg}{Colors.RESET}")
    else:
        print_fail("🚨 SECURITY FAILURE! AI did NOT block the transaction!", res)

    print_header("🎉🎉 CONGRATULATIONS! SYSTEM IS FULLY OPERATIONAL! 🎉🎉")

if __name__ == "__main__":
    try:
        run_test()
    except requests.exceptions.ConnectionError:
        print(f"\n{Colors.RED}❌ ERROR: Cannot connect to Java Server on port 8080! Is it running?{Colors.RESET}")