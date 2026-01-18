import requests
import random
import time
import string
import threading

# ✅ គោលដៅ: Global IP របស់អ្នក
BASE_URL = "http://100.117.33.69:8000/api/v1"
THREADS = 10  # ចំនួន Bot ដែលនឹងវាយប្រហារព្រមគ្នា (អាចដំឡើងដល់ 20-50 បើចង់បានខ្លាំង)

def get_random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def bot_attack(bot_id):
    """Bot នីមួយៗនឹងបង្កើតគណនី ហើយធ្វើប្រតិបត្តិការមិនឈប់"""
    username = f"bot_{bot_id}_{get_random_string(4)}"
    password = "password123"
    
    print(f"🤖 Bot-{bot_id}: Joining the system...")
    
    try:
        # 1. Register
        requests.post(f"{BASE_URL}/auth/register", json={
            "username": username, "password": password, "fullName": "Load Tester", 
            "email": f"{username}@test.com", "pin": "123456"
        })
        
        # 2. Login
        res = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
        token = res.json().get("accessToken")
        
        if not token: return
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Create Account
        res = requests.post(f"{BASE_URL}/accounts", json={"accountType": "SAVINGS", "accountName": "Bot Fund"}, headers=headers)
        acc_no = res.json().get("accountNumber")

        # 4. INFINITE LOOP: Deposit & Transfer
        while True:
            action = random.choice(["DEPOSIT", "TRANSFER", "HIGH_RISK"])
            amount = round(random.uniform(10, 5000), 2)
            
            if action == "DEPOSIT":
                requests.post(f"{BASE_URL}/transactions/deposit", json={"accountNumber": acc_no, "amount": amount}, headers=headers)
                print(f"✅ Bot-{bot_id}: Deposited ${amount}")
            
            elif action == "TRANSFER":
                requests.post(f"{BASE_URL}/transactions/transfer", json={
                    "fromAccountNumber": acc_no, "toAccountNumber": acc_no, 
                    "amount": amount, "pin": "123456"
                }, headers=headers)
                print(f"💸 Bot-{bot_id}: Transferred ${amount}")

            elif action == "HIGH_RISK":
                requests.post(f"{BASE_URL}/transactions/transfer", json={
                    "fromAccountNumber": acc_no, "toAccountNumber": acc_no, 
                    "amount": 50000, "pin": "123456"
                }, headers=headers)
                print(f"🛡️ Bot-{bot_id}: Triggered AI Block!")

            time.sleep(random.uniform(0.1, 0.5)) # ល្បឿនបាញ់ (Fast)

    except Exception as e:
        print(f"❌ Bot-{bot_id} Error: {e}")

if __name__ == "__main__":
    print(f"🚀 LAUNCHING MASSIVE TRAFFIC ATTACK ON {BASE_URL}...")
    
    for i in range(THREADS):
        t = threading.Thread(target=bot_attack, args=(i,))
        t.start()