import requests
import json
import os
import datetime

class LicenseManager:
    def __init__(self):
        self.license_file = 'license.json'
        self.trial_days = 3
        self.github_raw_url = "https://raw.githubusercontent.com/aabbiirr/c/refs/heads/main/valid_keys.json"

    def check_license(self):
        if not os.path.exists(self.license_file):
            self.create_trial_license()
        
        with open(self.license_file, 'r') as f:
            license_data = json.load(f)
        
        if license_data['type'] == 'trial':
            start_date = datetime.datetime.strptime(license_data['start_date'], '%Y-%m-%d')
            days_left = self.trial_days - (datetime.datetime.now() - start_date).days
            if days_left <= 0:
                return False, "Trial period expired. Please enter an activation key."
            return True, f"Trial period: {days_left} days left"
        elif license_data['type'] == 'full':
            return True, "Full version activated"
        else:
            return False, "Invalid license"

    def create_trial_license(self):
        license_data = {
            'type': 'trial',
            'start_date': datetime.datetime.now().strftime('%Y-%m-%d')
        }
        with open(self.license_file, 'w') as f:
            json.dump(license_data, f)

    def activate_license(self, key):
        if self.validate_key(key):
            license_data = {
                'type': 'full',
                'key': key
            }
            with open(self.license_file, 'w') as f:
                json.dump(license_data, f)
            return True
        return False

    def validate_key(self, key):
        try:
            response = requests.get(self.github_raw_url)
            response.raise_for_status()  # Raises an HTTPError for bad responses
            valid_keys = response.json()
            return key in valid_keys
        except requests.RequestException as e:
            print(f"Error validating key: {e}")
            return False