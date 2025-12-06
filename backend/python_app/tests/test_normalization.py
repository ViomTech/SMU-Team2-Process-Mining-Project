# test_normalization.py

import requests
import os
import json

# --- Configuration ---
BASE_URL = "http://127.0.0.1:5000"
ENDPOINT = "/api/normalize/start-mining"
FULL_URL = f"{BASE_URL}{ENDPOINT}"

# --- List of Real Log Files to Test ---
LOG_FOLDER_PATH = "../sample_logs/" # <-- CORRECTED PATH
FILES_TO_TEST = [
    f"{LOG_FOLDER_PATH}APIGateway.log",
    f"{LOG_FOLDER_PATH}UnderwriterConsole.log",
    f"{LOG_FOLDER_PATH}DocVerifier.log",
    f"{LOG_FOLDER_PATH}LoanProcessor.log",
    f"{LOG_FOLDER_PATH}NotificationService.log",
    f"{LOG_FOLDER_PATH}KYCService.log",
    f"{LOG_FOLDER_PATH}PaymentGateway.log",
    f"{LOG_FOLDER_PATH}CRM.log",
    f"{LOG_FOLDER_PATH}CreditCheck.log"
]

def run_test():
    """
    Sends the real log files to the endpoint and prints the result.
    """
    print(f"🚀 Starting test with real log files: Sending to {FULL_URL}")

    files_to_upload = []
    file_objects = []

    try:
        # 1. Prepare the log files for upload
        print("\n1. Preparing local log files for upload...")
        for filename in FILES_TO_TEST:
            if not os.path.exists(filename):
                print(f"   - ⚠️ WARNING: File '{filename}' not found. Skipping.")
                continue
            
            file_obj = open(filename, "rb")
            file_objects.append(file_obj)
            files_to_upload.append(('files[]', (filename, file_obj, 'text/plain')))
        
        if not files_to_upload:
            print("\n❌ ERROR: No log files found to upload. Please copy them to the tests folder.")
            return

        # 2. Send the POST request
        print("\n2. Sending request to the backend...")
        response = requests.post(FULL_URL, files=files_to_upload)
        
        # 3. Analyze the response
        print("\n3. Analyzing response from the server...")
        print(f"   - HTTP Status Code: {response.status_code}")

        if response.status_code == 200:
            print("   - ✅ Request was successful (200 OK)")
            response_data = response.json()
            
            print("\n--- Server Response ---")
            print(f"Message: {response_data.get('message')}")
            
            event_log_str = response_data.get('event_log', '[]')
            event_log = json.loads(event_log_str)
            print(f"Normalized Event Count: {len(event_log)}")
            
            print(f"Invalid Entries Count: {response_data.get('invalid_entries_count')}")
            
            # --- THIS IS THE NEW PART ---
            print("\n--- Full Event Log (JSON Output) ---")
            print(json.dumps(event_log, indent=2))
            
        else:
            print(f"   - ❌ Test Failed. Status code was {response.status_code}.")
            print("   - Server Response Body:", response.text)

    except requests.exceptions.ConnectionError:
        print("\n❌ CONNECTION ERROR: Could not connect to the server.")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
    finally:
        # 4. Clean up by closing file objects
        for f_obj in file_objects:
            f_obj.close()
        print("\n✅ Test finished.")

if __name__ == "__main__":
    run_test()
