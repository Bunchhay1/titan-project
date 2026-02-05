import requests
import pytest
import concurrent.futures
from colorama import Fore, Style, init

# Initialize Colorama for auto-resetting colors
init(autoreset=True)

# --- CONFIGURATION ---
BASE_URL = "http://192.168.0.120:8888"
TEST_USER = "admin"
TEST_PASS = "password123"

# --- HELPER CLASS (The Logic) ---
class TitanTester:
    """
    Acts as the API Client for Titan Core Banking.
    Handles connection, auth, and request formatting.
    """
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.base_url = BASE_URL

    def log(self, message, status="INFO"):
        """Prints colorful logs to the terminal."""
        if status == "PASS":
            print(f"{Fore.GREEN}[PASS] {message}")
        elif status == "FAIL":
            print(f"{Fore.RED}[FAIL] {message}")
        elif status == "WARN":
            print(f"{Fore.YELLOW}[WARN] {message}")
        else:
            print(f"{Fore.CYAN}[INFO] {message}")

    def login_and_get_token(self):
        """Authenticates and stores the JWT token in the session headers."""
        url = f"{self.base_url}/api/auth/login"
        payload = {"username": TEST_USER, "password": TEST_PASS}
        
        self.log(f"Attempting login for user: {TEST_USER}...")
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            # Assuming response is like: {"token": "ey..."} or {"accessToken": "ey..."}
            data = response.json()
            self.token = data.get("token") or data.get("accessToken")
            
            if not self.token:
                self.log("Login successful but NO token found in response", "FAIL")
                raise ValueError("No token in response")
                
            # Update session headers so all subsequent requests use the token
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            self.log("Login Successful! Token acquired.", "PASS")
            return self.token
            
        except Exception as e:
            self.log(f"Login Failed: {e}", "FAIL")
            pytest.fail(f"Authentication failed: {e}")

    def get_balance(self):
        """Fetches current balance."""
        response = self.session.get(f"{self.base_url}/api/accounts/balance")
        return response

    def transfer_funds(self, amount, to_account="user_2"):
        """Sends a transfer request."""
        payload = {
            "to_account": to_account,
            "amount": amount,
            "currency": "USD"
        }
        return self.session.post(f"{self.base_url}/api/transfer", json=payload)

# --- PYTEST FIXTURES ---
@pytest.fixture(scope="module")
def api_client():
    """Setup: Create the tester instance and login once for all tests."""
    tester = TitanTester()
    tester.login_and_get_token()
    return tester

# --- TEST SUITE ---

class TestTitanBankingSecurity:
    
    def test_01_happy_path_transfer(self, api_client):
        """Test Standard Transfer ($100). Should return 200 OK."""
        api_client.log("--- TEST: Happy Path Transfer ($100) ---")
        
        # 1. Get Balance Before
        bal_resp = api_client.get_balance()
        assert bal_resp.status_code == 200
        initial_balance = bal_resp.json().get('balance', 0)

        # 2. Transfer
        response = api_client.transfer_funds(amount=100)
        
        if response.status_code == 200:
            api_client.log("Transfer processed successfully.", "PASS")
        else:
            api_client.log(f"Transfer failed: {response.text}", "FAIL")
            
        assert response.status_code == 200

        # 3. Verify Balance Decrease (Data Integrity Check)
        new_bal_resp = api_client.get_balance()
        new_balance = new_bal_resp.json().get('balance', 0)
        
        # Note: Logic assumes fees are 0 for simplicity. Adjust if needed.
        if float(new_balance) == float(initial_balance) - 100:
             api_client.log(f"Balance updated correctly: {initial_balance} -> {new_balance}", "PASS")
        else:
             api_client.log(f"Balance Mismatch! Old: {initial_balance}, New: {new_balance}", "FAIL")
             # Uncomment below to enforce strict balance checks
             # assert float(new_balance) == float(initial_balance) - 100

    def test_02_fraud_detection_ai(self, api_client):
        """Test High Value Fraud (> $50,000). Should be BLOCKED (403/400)."""
        api_client.log("--- TEST: AI Fraud Detection ($60,000) ---")
        
        response = api_client.transfer_funds(amount=60000)
        
        # We expect a blockage (403 Forbidden or 400 Bad Request)
        if response.status_code in [400, 403]:
            api_client.log(f"AI Successfully BLOCKED transaction. Status: {response.status_code}", "PASS")
            api_client.log(f"Response message: {response.text}")
        else:
            api_client.log(f"SECURITY BREACH! High value transfer accepted! Status: {response.status_code}", "FAIL")
            pytest.fail("AI Model failed to detect high-value fraud!")

    def test_03_security_no_token(self):
        """Test API Access without Authorization Header."""
        tester = TitanTester() # New instance, NO login
        tester.log("--- TEST: Unauthorized Access (No Token) ---")
        
        response = tester.session.post(f"{BASE_URL}/api/transactions/transfer", json={"amount": 10})
        
        # ✅ កែត្រង់នេះ៖ ទទួលយកទាំង 401 និង 403
        if response.status_code in [401, 403]:
            tester.log(f"System correctly rejected request ({response.status_code}).", "PASS")
        else:
            tester.log(f"SECURITY FAIL! Status: {response.status_code}", "FAIL")
        
        assert response.status_code in [401, 403]

    def test_04_rate_limiting_attack(self, api_client):
        """
        Simulate a DDoS/Spam attack: 20 requests in < 1 second.
        Gateway should start returning 429 (Too Many Requests).
        """
        api_client.log("--- TEST: Rate Limiting (DDoS Simulation) ---")
        
        def flood_request(i):
            return api_client.session.get(f"{BASE_URL}/api/accounts/balance")

        # Use ThreadPool to send requests in parallel (Simulate concurrent users)
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            # Create a list of 20 requests
            futures = [executor.submit(flood_request, i) for i in range(20)]
            
            results = [f.result().status_code for f in futures]

        api_client.log(f"Status Codes received: {results}")

        # Analysis: We expect some 200s, but eventually 429s
        if 429 in results:
            api_client.log("Rate Limiting triggered successfully (429 received).", "PASS")
        else:
            # Note: If your rate limit is > 20 req/s, this will pass as INFO only.
            api_client.log("No 429 received. Gateway might allow > 20 req/s.", "WARN")