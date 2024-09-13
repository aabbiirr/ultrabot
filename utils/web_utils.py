# File: utils/web_utils.py

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

import logging

def safe_find_element(driver, by, value, timeout=10):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    except Exception as e:
        logging.error(f"Failed to find element: {by}={value}. Error: {str(e)}")
        return None

def safe_click(element):
    try:
        element.click()
    except Exception as e:
        logging.error(f"Failed to click element. Error: {str(e)}")

def wait_for_page_load(driver, timeout=30):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script('return jQuery.active') == 0
        )
        
        WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, 'sapUiLocalBusyIndicator'))
        )
        
        logging.info("Page loaded completely")
    except Exception as e:
        logging.warning(f"Timeout waiting for page load: {str(e)}")
