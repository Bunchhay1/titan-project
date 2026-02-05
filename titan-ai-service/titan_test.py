import requests
import json
import uuid
import time
import sys

# --- CONFIGURATION ---
# យើងតេស្តទៅកាន់ Core Service ផ្ទាល់ (8080) ដើម្បីប្រាកដថាវាដើរ
# បើ Core ដើរ ទើបយើងសាក Gateway (8888) តាមក្រោយ
BASE_URL = "http://100.117.33.69:8080"

# ពណ៌សម្រាប់មើលងាយស្រួល
class Colors:
    HEADER = '\033[95m'
    OKGREEN = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_pass(message):
    print(f"{Colors.OKGREEN}[PASS] {message}{Colors.ENDC}")

def print_fail(message, error=None):
    print(f"{Colors.FAIL}[FAIL] {message}{Colors.ENDC}")
    if error:
        print(f"       Error: {error}")

def get_random_user():
    unique_id = str(uuid.uuid4())[:8]
    return {
        "username": f"user_{unique_id}",
        "password": "password123",
        "email": f"user_{unique_id}@titan.com",
        "fullName": "Titan Tester"
    }

# --- TEST 1: SERVER CHECK ---
def test_server_connectivity():
    print(f"{Colors.HEADER}--- TEST 1: Checking Server Connection ---{Colors.ENDC}")
    try:
        # យើងគ្រាន់តែ Ping ទៅ Root
        response = requests.get(f"{BASE_URL}/actuator/health", timeout=5)
        # ឬបើគ្មាន actuator, គ្រាន់តែ connect ទៅ root
        if response.status_code in [200, 401, 403, 404]: 
            print_pass(f"Server is reachable at {BASE_URL}")
            return True
    except requests.exceptions.ConnectionError:
        print_fail("Connection Refused! Server is DOWN or Port is Closed.")
        print("       -> Check: docker compose ps")
        print("       -> Check: Firewall on 192.168.0.120")
        return False
    except Exception as e:
        print_fail("Unknown Error", e)
        return False
    return True

# --- TEST 2: REGISTER ---
def test_register(user_data):
    print(f"\n{Colors.HEADER}--- TEST 2: Register API ---{Colors.ENDC}")
    url = f"{BASE_URL}/api/auth/register"
    try:
        response = requests.post(url, json=user_data)
        if response.status_code == 200 or response.status_code == 201:
            print_pass(f"User '{user_data['username']}' created successfully.")
            return True
        else:
            print_fail(f"Status: {response.status_code}", response.text)
            return False
    except Exception as e:
        print_fail("Request Failed", e)
        return False

# --- TEST 3: LOGIN ---
def test_login(user_data):
    print(f"\n{Colors.HEADER}--- TEST 3: Login API ---{Colors.ENDC}")
    url = f"{BASE_URL}/api/auth/login"
    try:
        payload = {
            "username": user_data['username'],
            "password": user_data['password']
        }
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            # ស្វែងរក Token (កែតាម Response ជាក់ស្តែងរបស់ API អ្នក)
            token = data.get("token") or data.get("accessToken")
            if token:
                print_pass("Login successful! Token received.")
                return token
            else:
                print_fail("Login success but NO TOKEN found in response.", data)
                return None
        else:
            print_fail(f"Login Failed: {response.status_code}", response.text)
            return None
    except Exception as e:
        print_fail("Request Failed", e)
        return None

# --- TEST 4: PROTECTED RESOURCE (Profile) ---
def test_profile(token):
    print(f"\n{Colors.HEADER}--- TEST 4: Protected API (Get Profile) ---{Colors.ENDC}")
    # សាកល្បង Endpoint ទូទៅ (កែតាមជាក់ស្តែង)
    endpoints = ["/api/users/me", "/api/users/profile", "/api/accounts/balance"]
    
    headers = {"Authorization": f"Bearer {token}"}
    
    for endpoint in endpoints:
        url = f"{BASE_URL}{endpoint}"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                print_pass(f"Access Granted to {endpoint}")
                print(f"       Data: {json.dumps(response.json(), indent=2)}")
                return True
        except:
            pass
    
    print_fail("Could not access any protected profile endpoint (403/404).")
    return False

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print(f"{Colors.BOLD}🚀 STARTING TITAN SYSTEM AUTO-TEST{Colors.ENDC}\n")
    
    if not test_server_connectivity():
        sys.exit(1)

    test_user = get_random_user()
    
    if test_register(test_user):
        token = test_login(test_user)
        if token:
            test_profile(token)
    
    print(f"\n{Colors.BOLD}✅ TEST COMPLETED.{Colors.ENDC}")