import requests
import json
import random
import string
import time
import paramiko
import re  # ✅ Added Regex for better parsing
from colorama import Fore, Style, init

# Initialize color output
init(autoreset=True)

# ==========================================
# ⚙️ SERVER CONFIGURATION
# ==========================================
SERVER_IP = "100.117.33.69"
SERVER_USER = "root"
SERVER_PASSWORD = "1234"  # ⚠️ ត្រូវប្រាកដថា Password នេះត្រឹមត្រូវ
BASE_URL = "http://100.117.33.69:8888"  # ⚠️ ប្រសិនបើ Docker Map ទៅ 8081 សូមដូរមក 8081

# API ENDPOINTS
AUTH_REGISTER = "/api/auth/register"
AUTH_LOGIN = "/api/auth/login"
ACCOUNT_CREATE = "/api/accounts"
TRANSACTION_API = "/api/transactions"

def log(step, message, status="INFO"):
    if status == "SUCCESS":
        print(f"{Fore.GREEN}[✔] {step}: {message}")
    elif status == "FAIL":
        print(f"{Fore.RED}[✘] {step}: {message}")
    elif status == "WARN":
        print(f"{Fore.YELLOW}[!] {step}: {message}")
    else:
        print(f"{Fore.CYAN}[ℹ] {step}: {message}")

def get_otp_from_server():
    log("SSH", "Hacking into Server Logs to find OTP...", "WARN")
    
    # 💤 Wait for Docker to flush logs
    time.sleep(5)

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(SERVER_IP, username=SERVER_USER, password=SERVER_PASSWORD)
        
        # ✅ FIX: Use 'docker logs' directly (safer than compose)
        # We look at the last 100 lines to be safe
        command = "docker logs --tail 100 titan-core"
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode('utf-8')
        client.close()
        
        # ✅ FIX: Use Regex to find the OTP specifically
        # Pattern looks for "Generated OTP:" followed by spaces and digits
        match = re.search(r"Generated OTP:\s+(\d+)", output)
        
        if match:
            otp_code = match.group(1)
            log("SSH", f"TARGET ACQUIRED! OTP IS: {otp_code}", "SUCCESS")
            return otp_code
        else:
            log("SSH", "Could not find 'Generated OTP' pattern in logs.", "FAIL")
            # print(f"DEBUG: {output[-500:]}") # Uncomment to debug
            return None

    except Exception as e:
        log("SSH", f"Connection Failed: {e}", "FAIL")
        return None

def create_full_user(role_name):
    session = requests.Session()
    rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
    username = f"{role_name}_{rand_suffix}"
    
    # 1. Register
    user_data = {
        "firstname": role_name,
        "lastname": "Bot",
        "username": username,
        "email": f"{username}@titan.com",
        "password": "TitanPass123!",
        "rawPassword": "TitanPass123!", # In case your API needs this
        "pin": "123456"
    }
    
    try:
        res = session.post(f"{BASE_URL}{AUTH_REGISTER}", json=user_data)
        if res.status_code not in [200, 201]:
            log("SETUP", f"Register Failed: {res.text}", "FAIL")
            return None, None, None

        # 2. Login
        res = session.post(f"{BASE_URL}{AUTH_LOGIN}", json={"username": username, "password": "TitanPass123!"})
        token = res.json().get("token") or res.json().get("accessToken")
        
        if not token:
             log("SETUP", f"Login Failed (No Token): {res.text}", "FAIL")
             return None, None, None

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # 3. Account
        res = session.post(f"{BASE_URL}{ACCOUNT_CREATE}", json={"accountType": "SAVINGS", "balance": 0.0}, headers=headers)
        acc_num = res.json().get("accountNumber") or res.json().get("id")
        
        log(f"SETUP_{role_name.upper()}", f"User Ready: {acc_num}", "SUCCESS")
        return session, headers, acc_num
        
    except Exception as e:
        log("SETUP", f"Connection Error: {e}", "FAIL")
        return None, None, None

def run_titan_test():
    print(f"{Fore.MAGENTA}{Style.BRIGHT}=== TITAN SECURITY TEST: OTP INTERCEPTION ===\n")

    # 1. SETUP
    sender_session, sender_headers, sender_acc = create_full_user("Sender")
    _, _, receiver_acc = create_full_user("Receiver")

    if not sender_acc or not receiver_acc: 
        log("STOP", "Cannot proceed without users.", "FAIL")
        return

    # 2. DEPOSIT ($80,000)
    log("DEPOSIT", "Depositing $80,000 to Sender...")
    deposit_payload = {
        "toAccountNumber": sender_acc,
        "amount": 80000.00,
        "transactionType": "DEPOSIT",
        "pin": "123456"
    }
    sender_session.post(f"{BASE_URL}{TRANSACTION_API}/deposit", json=deposit_payload, headers=sender_headers)

    # 3. TRIGGER OTP (Attempt Transfer $20,000 > Threshold)
    log("OTP_TRIGGER", "Attempting Transfer of $20,000 (Expecting OTP Lock)...")
    
    transfer_payload = {
        "fromAccountNumber": sender_acc,
        "toAccountNumber": receiver_acc,
        "amount": 20000.00,
        "transactionType": "TRANSFER",
        "pin": "123456"
    }
    
    res = sender_session.post(f"{BASE_URL}{TRANSACTION_API}/transfer", json=transfer_payload, headers=sender_headers)

    # 🔥 LOGIC CHECK
    # We expect 400 Bad Request with message "OTP REQUIRED"
    if res.status_code == 400 and ("OTP" in res.text or "Required" in res.text):
        log("OTP_TRIGGER", "System Blocked Transaction & Demanded OTP! (Good)", "SUCCESS")
        
        # 4. GET OTP VIA SSH
        otp_code = get_otp_from_server()
        
        if otp_code:
            # 5. RETRY TRANSFER WITH OTP (FINAL SUCCESS)
            log("OTP_VERIFY", f"Resending Transfer with OTP: {otp_code} ...")
            
            # Add OTP to payload
            transfer_payload["otp"] = otp_code
            
            # Send Again
            res_final = sender_session.post(f"{BASE_URL}{TRANSACTION_API}/transfer", json=transfer_payload, headers=sender_headers)
            
            if res_final.status_code in [200, 201]:
                # Extract Transaction ID for proof
                tx_id = res_final.json().get("transactionId") or "Unknown"
                log("OTP_VERIFY", f"Verification Successful! Tx ID: {tx_id}", "SUCCESS")
                print(f"{Fore.GREEN}{Style.BRIGHT} [★] MISSION ACCOMPLISHED [★]")
            else:
                log("OTP_VERIFY", f"Verification Failed: {res_final.text}", "FAIL")
        else:
            log("SSH", "Could not find OTP in logs.", "FAIL")

    elif res.status_code == 200:
         log("OTP_TRIGGER", "SECURITY BREACH! Transferred without OTP!", "FAIL")
    else:
         log("OTP_TRIGGER", f"Unexpected Status: {res.status_code} - {res.text}", "WARN")

if __name__ == "__main__":
    try:
        run_titan_test()
    except KeyboardInterrupt:
        print("\nAborted.")
    except Exception as e:
        print(f"Error: {e}")