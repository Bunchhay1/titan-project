import requests
import threading
import time

# 🎯 គោលដៅ: Gateway របស់អ្នក
BASE_URL = "http://192.168.0.120:8000/api/v1"
# ចំនួន Requests ដែលត្រូវបញ្ជូន
TOTAL_REQUESTS = 100
# ចំនួន Thread (រត់ស្របគ្នា) ដើម្បីបង្កើនសម្ពាធ
CONCURRENT_THREADS = 10

def send_request(thread_id):
    for i in range(TOTAL_REQUESTS // CONCURRENT_THREADS):
        try:
            # តេស្តហៅទៅ Health Check ឬ Auth
            response = requests.get(f"{BASE_URL}/auth/register") 
            print(f"Thread-{thread_id} | Request {i} | Status: {response.status_code}")
        except Exception as e:
            print(f"Error on Thread-{thread_id}: {e}")

if __name__ == "__main__":
    print(f"🚀 STARTING STRESS TEST ON {BASE_URL}...")
    start_time = time.time()
    
    threads = []
    for i in range(CONCURRENT_THREADS):
        t = threading.Thread(target=send_request, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    end_time = time.time()
    print(f"\n✅ STRESS TEST COMPLETE!")
    print(f"⏱️ Time taken: {end_time - start_time:.2f} seconds")