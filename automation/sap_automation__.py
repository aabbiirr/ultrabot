# File: automation/sap_automation.py

import logging
import time
import os
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException, JavascriptException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

class SAPBiddingAutomation:
    def __init__(self):
        self.driver = None
        self.wait = None

    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)

    def login(self, username, password):
        self.driver.get("https://www.eye2serve.com:9001/sap/bc/ui5_ui5/ui2/ushell/shells/abap/FioriLaunchpad.html")
        
        if self.cookies_exist():
            self.load_cookies()
            self.driver.refresh()
            if self.is_logged_in():
                logging.info("Logged in successfully using cookies")
                return True
        
        try:
            username_field = self.wait.until(EC.presence_of_element_located((By.ID, "USERNAME_FIELD-inner")))
            password_field = self.wait.until(EC.presence_of_element_located((By.ID, "PASSWORD_FIELD-inner")))
            
            username_field.send_keys(username)
            password_field.send_keys(password)
            
            login_button = self.wait.until(EC.element_to_be_clickable((By.ID, "LOGIN_LINK")))
            login_button.click()
            
            if self.is_logged_in():
                logging.info("Logged in successfully using credentials")
                self.save_cookies()
                return True
            else:
                logging.error("Login failed")
                return False
        except Exception as e:
            logging.error(f"Login error: {str(e)}")
            return False

    def is_logged_in(self):
        try:
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[@href='/sap/bc/ui5_ui5/sap/zvc_vendor_app/index.html#/ebidding']")))
            return True
        except:
            return False
        
    def inject_test_data(self):
        try:
            sample_data = [
                {"freight": "465", "bid_amount": ""},
                {"freight": "500", "bid_amount": ""}
            ]
            sample_data_json = json.dumps(sample_data)
            script = """
            var sampleData = JSON.parse(arguments[0]);
            var table = document.querySelector('#__xmlview0--idUtclVCVendorAssignmentTable-listUl');
            if (!table) {
                throw new Error("Table not found");
            }
            var tbody = table.querySelector('tbody');
            if (!tbody) {
                throw new Error("Table body not found");
            }
            tbody.innerHTML = '';
            
            sampleData.forEach(function(row, index) {
                var tr = document.createElement('tr');
                tr.id = `__item${index}-__xmlview0--idUtclVCVendorAssignmentTable-${index}`;
                tr.className = 'sapMLIB sapMLIB-CTX sapMLIBShowSeparator sapMLIBTypeInactive sapMListTblRow';
                tr.setAttribute('tabindex', '-1');

                for (var i = 0; i < 13; i++) {
                    var td = document.createElement('td');
                    td.className = 'sapMListTblCell';
                    td.textContent = `Placeholder ${i+1}`;
                    tr.appendChild(td);
                }

                var freightTd = document.createElement('td');
                freightTd.className = 'sapMListTblCell';
                freightTd.innerHTML = `<span class="sapMText sapMTextMaxWidth sapUiSelectable">${row.freight}</span>`;
                tr.appendChild(freightTd);

                var bidTd = document.createElement('td');
                bidTd.className = 'sapMListTblCell';
                bidTd.innerHTML = `<input type="text" value="${row.bid_amount}" disabled class="sapMInputBaseInner">`;
                tr.appendChild(bidTd);

                for (var i = 0; i < 9; i++) {
                    var td = document.createElement('td');
                    td.className = 'sapMListTblCell';
                    td.textContent = `Placeholder ${i+15}`;
                    tr.appendChild(td);
                }

                tbody.appendChild(tr);
            });
            return tbody.children.length;
            """
            rows_injected = self.driver.execute_script(script, sample_data_json)
            logging.info(f"Test data injection completed. Rows injected: {rows_injected}")

            table = self.driver.find_element(By.ID, "__xmlview0--idUtclVCVendorAssignmentTable-listUl")
            rows = table.find_elements(By.XPATH, ".//tbody/tr")
            logging.info(f"Rows found after injection: {len(rows)}")

            if len(rows) != len(sample_data):
                logging.warning(f"Mismatch in number of rows. Expected: {len(sample_data)}, Found: {len(rows)}")

            for i, row in enumerate(rows):
                freight = row.find_element(By.XPATH, ".//td[14]//span").text
                bid_input = row.find_element(By.XPATH, ".//td[15]//input").get_attribute("value")
                logging.info(f"Row {i+1}: Freight = {freight}, Bid Amount = {bid_input}")

        except JavascriptException as js_error:
            logging.error(f"JavaScript error during data injection: {str(js_error)}")
        except Exception as e:
            logging.error(f"Error injecting test data: {str(e)}")

    def enable_bid_inputs(self):
        try:
            script = """
            var inputs = document.querySelectorAll('#__xmlview0--idUtclVCVendorAssignmentTable-listUl tbody input');
            inputs.forEach(function(input) {
                input.disabled = false;
            });
            return inputs.length;
            """
            enabled_inputs = self.driver.execute_script(script)
            logging.info(f"Bid input fields enabled. Total enabled inputs: {enabled_inputs}")
        except Exception as e:
            logging.error(f"Error enabling bid input fields: {str(e)}")

    def navigate_to_ebidding(self):
        try:
            ebidding_link = self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[@href='/sap/bc/ui5_ui5/sap/zvc_vendor_app/index.html#/ebidding']")))
            if not ebidding_link:
                raise Exception("eBidding link not found")
            ebidding_url = ebidding_link.get_attribute('href')
            
            self.driver.get(ebidding_url)
            self.wait_for_page_load()
            
            current_url = self.driver.current_url
            logging.info(f"Opened eBidding URL: {current_url}")
            
            self.handle_error_dialog()
            
            return current_url
        except Exception as e:
            logging.error(f"Failed to navigate to eBidding tab: {str(e)}")
            raise

    def click_show_search(self):
        try:
            show_search_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//bdi[@id='__button0-BDI-content' and text()='Show Search']")))
            show_search_button.click()
            logging.info("'Show Search' button clicked successfully")
        except Exception as e:
            logging.error(f"Failed to click 'Show Search' button: {str(e)}")
            raise

    def handle_error_dialog(self):
        try:
            error_dialog = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='alertdialog']//span[contains(text(), 'There are currently two active sessions')]"))
            )
            if error_dialog:
                logging.info("Error dialog detected. Attempting to dismiss it.")
                ok_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//bdi[text()='OK']")))
                if ok_button:
                    ok_button.click()
                    logging.info("Error dialog dismissed.")
                    WebDriverWait(self.driver, 10).until(
                        EC.invisibility_of_element_located((By.XPATH, "//div[@role='alertdialog']"))
                    )
                else:
                    logging.error("Failed to find OK button in error dialog")
        except TimeoutException:
            logging.info("No error dialog detected")
            
    def select_dropdown_option(self, dropdown_id, option_text):
        try:
            dropdown_arrow = self.wait.until(EC.element_to_be_clickable((By.ID, f"{dropdown_id}-arrow")))
            self.driver.execute_script("arguments[0].click();", dropdown_arrow)
            logging.info(f"Clicked dropdown arrow for {dropdown_id}")

            dropdown_list_id = "__list0" if "Ship" in dropdown_id else "__list2"
            dropdown_list = self.wait.until(EC.visibility_of_element_located((By.ID, dropdown_list_id)))
            logging.info(f"Dropdown list visible for {dropdown_id}")

            options = dropdown_list.find_elements(By.TAG_NAME, "li")
            logging.info(f"Found {len(options)} options for {dropdown_id}")

            target_option = next((opt for opt in options if option_text in opt.text), None)

            if target_option:
                self.driver.execute_script("arguments[0].scrollIntoView(true);", target_option)
                time.sleep(0.5)

                try:
                    target_option.click()
                except ElementClickInterceptedException:
                    try:
                        self.driver.execute_script("arguments[0].click();", target_option)
                    except:
                        ActionChains(self.driver).move_to_element(target_option).click().perform()

                logging.info(f"Option '{option_text}' selected successfully for {dropdown_id}")

                self.wait.until(EC.invisibility_of_element_located((By.ID, dropdown_list_id)))
                logging.info(f"Dropdown closed after selection for {dropdown_id}")
            else:
                logging.error(f"Option '{option_text}' not found in {dropdown_id}")
                self.driver.save_screenshot(f"{dropdown_id}_selection_error.png")
        except Exception as e:
            logging.error(f"Failed to select option in {dropdown_id}: {str(e)}")
            self.driver.save_screenshot(f"{dropdown_id}_selection_error.png")

    def select_ship_from_plant(self, plant_name="WEST BENGAL CEMENT WORKS"):
        self.select_dropdown_option("__xmlview0--ididUtclVCShipFromPlant", plant_name)

    def select_depot(self, depot_name):
        self.select_dropdown_option("__xmlview0--idUtclVCDepot", depot_name)

    def click_search(self):
        try:
            self.handle_error_dialog()
            search_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//bdi[text()='Search']")))
            search_button.click()
            logging.info("Search button clicked successfully")
            self.wait_for_page_load()
        except Exception as e:
            logging.error(f"Failed to click Search button: {str(e)}")

    def check_table_data(self):
        try:
            self.wait.until(EC.presence_of_element_located((By.ID, "__xmlview0--idUtclVCVendorAssignmentTable-listUl")))
            no_data_row = self.driver.find_elements(By.XPATH, "//tr[@id='__xmlview0--idUtclVCVendorAssignmentTable-nodata']")
            has_data = len(no_data_row) == 0
            logging.info(f"Table data check: {'Data found' if has_data else 'No data found'}")
            return has_data
        except TimeoutException:
            logging.error("Table not found or loaded within the timeout period")
            return False

    def rapid_bidding(self):
        max_attempts = 100
        attempts = 0
        
        while attempts < max_attempts:
            try:
                table = WebDriverWait(self.driver, 2).until(
                    EC.presence_of_element_located((By.ID, "__xmlview0--idUtclVCVendorAssignmentTable-listUl"))
                )
                rows = table.find_elements(By.XPATH, ".//tbody/tr")
                
                all_bids_placed = True
                for row in rows:
                    try:
                        freight_element = row.find_element(By.XPATH, ".//td[contains(@headers, '__text23')]//span")
                        bid_input = row.find_element(By.XPATH, ".//td[contains(@headers, '__text24')]//input")
                        
                        if bid_input.is_enabled():
                            freight = int(freight_element.text.strip())
                            bid_amount = freight - 1
                            
                            current_value = bid_input.get_attribute('value')
                            if current_value != str(bid_amount):
                                bid_input.clear()
                                bid_input.send_keys(str(bid_amount))
                                bid_input.send_keys(Keys.ENTER)
                                logging.info(f"Placed bid of {bid_amount} for freight {freight}")
                        else:
                            all_bids_placed = False
                            break
                    except (StaleElementReferenceException, NoSuchElementException):
                        all_bids_placed = False
                        break
                    except Exception as e:
                        logging.error(f"Error processing row: {str(e)}")
                        all_bids_placed = False
                        break
                
                if all_bids_placed:
                        logging.info("All bids placed successfully")
                        return
                    
            except Exception as e:
                logging.error(f"Error during rapid bidding: {str(e)}")
                
                # If we reach here, not all bids were placed, so we click search and try again
                self.click_search()
                attempts += 1
                time.sleep(0.5)  # Small delay to prevent overwhelming the server
            
            logging.warning(f"Max attempts ({max_attempts}) reached without placing all bids")

        def continuous_single_depot_search_and_bid(self, depot_name):
            while True:
                try:
                    logging.info(f"Selecting depot: {depot_name}")
                    self.select_depot(depot_name)
                    self.click_search()
                    
                    if self.check_table_data():
                        logging.info(f"Table data found for {depot_name}. Starting bidding process.")
                        self.rapid_bidding()
                    else:
                        logging.info(f"No table data found for {depot_name}. Retrying in 5 seconds.")
                        time.sleep(5)
                except Exception as e:
                    logging.error(f"Error during continuous search and bid for {depot_name}: {str(e)}")
                    time.sleep(5)

        def wait_for_page_load(self, timeout=30):
            try:
                WebDriverWait(self.driver, timeout).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
                WebDriverWait(self.driver, timeout).until(
                    EC.invisibility_of_element_located((By.CLASS_NAME, "sapUiLocalBusyIndicator"))
                )
                logging.info("Page loaded completely")
            except TimeoutException:
                logging.warning(f"Timeout waiting for page load after {timeout} seconds")

        def save_cookies(self):
            cookies = self.driver.get_cookies()
            with open("cookies.txt", "w") as cookie_file:
                for cookie in cookies:
                    cookie_file.write(f"{cookie['name']}={cookie['value']}\n")
            logging.info("Cookies saved")

        def load_cookies(self):
            try:
                with open("cookies.txt", "r") as cookie_file:
                    for line in cookie_file:
                        name, value = line.strip().split("=", 1)
                        self.driver.add_cookie({'name': name, 'value': value})
                logging.info("Cookies loaded successfully")
            except Exception as e:
                logging.error(f"Failed to load cookies: {str(e)}")

        def cookies_exist(self):
            return os.path.exists("cookies.txt")

        def close(self):
            if self.driver:
                self.driver.quit()
            logging.info("Browser closed.")

        def run_automation(self, username, password, depot_name):
            try:
                self.setup_driver()
                if self.login(username, password):
                    self.navigate_to_ebidding()
                    self.click_show_search()
                    self.select_ship_from_plant()
                    self.continuous_single_depot_search_and_bid(depot_name)
                else:
                    logging.error("Login failed. Automation stopped.")
            except Exception as e:
                logging.error(f"Error during automation: {str(e)}")
            finally:
                self.close()

    if __name__ == "__main__":
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        # automation = SAPBiddingAutomation()
        # automation.run_automation("your_username", "your_password", "Your Depot Name")