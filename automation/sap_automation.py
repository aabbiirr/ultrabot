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
import asyncio

class SAPBiddingAutomation:
    def __init__(self, num_drivers=1):
        self.drivers = []
        self.waits = []
        self.num_drivers = num_drivers

    def setup_drivers(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        service = Service(ChromeDriverManager().install())

        for _ in range(self.num_drivers):
            driver = webdriver.Chrome(service=service, options=chrome_options)
            wait = WebDriverWait(driver, 1)
            self.drivers.append(driver)
            self.waits.append(wait)

        logging.info(f"Set up {self.num_drivers} drivers")

    def login_all(self, username, password):
        for i, driver in enumerate(self.drivers):
            if (not self.login(driver, self.waits[i], username, password)):
                return False
        return True

    def login(self, driver, wait, username, password):
        driver.get("https://www.eye2serve.com:9001/sap/bc/ui5_ui5/ui2/ushell/shells/abap/FioriLaunchpad.html")
        
        if self.cookies_exist():
            self.load_cookies(driver)
            driver.refresh()
            if self.is_logged_in(driver, wait):
                logging.info(f"Driver {id(driver)} logged in successfully using cookies")
                return True
        
        try:
            username_field = wait.until(EC.presence_of_element_located((By.ID, "USERNAME_FIELD-inner")))
            password_field = wait.until(EC.presence_of_element_located((By.ID, "PASSWORD_FIELD-inner")))
            
            username_field.send_keys(username)
            password_field.send_keys(password)
            
            login_button = wait.until(EC.element_to_be_clickable((By.ID, "LOGIN_LINK")))
            login_button.click()
            
            if self.is_logged_in(driver, wait):
                logging.info(f"Driver {id(driver)} logged in successfully using credentials")
                self.save_cookies(driver)
                return True
            else:
                logging.error(f"Login failed for driver {id(driver)}")
                return False
        except Exception as e:
            logging.error(f"Login error for driver {id(driver)}: {str(e)}")
            return False

    def is_logged_in(self, driver, wait):
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//a[@href='/sap/bc/ui5_ui5/sap/zvc_vendor_app/index.html#/ebidding']")))
            return True
        except:
            return False

    def navigate_to_ebidding_all(self):
        for i, driver in enumerate(self.drivers):
            self.navigate_to_ebidding(driver, self.waits[i])

    def navigate_to_ebidding(self, driver, wait):
        try:
            ebidding_link = wait.until(EC.presence_of_element_located((By.XPATH, "//a[@href='/sap/bc/ui5_ui5/sap/zvc_vendor_app/index.html#/ebidding']")))
            if not ebidding_link:
                raise Exception("eBidding link not found")
            ebidding_url = ebidding_link.get_attribute('href')
            
            driver.get(ebidding_url)
            self.wait_for_page_load(driver)
            
            current_url = driver.current_url
            logging.info(f"Driver {id(driver)} opened eBidding URL: {current_url}")
            
            self.handle_error_dialog(driver, wait)
            
            return current_url
        except Exception as e:
            logging.error(f"Failed to navigate to eBidding tab for driver {id(driver)}: {str(e)}")
            raise

    def click_show_search_all(self):
        for i, driver in enumerate(self.drivers):
            self.click_show_search(driver, self.waits[i], i)

    def click_show_search(self, driver, wait, index):
        try:
            self.handle_error_dialog(driver, self.waits[index])
            show_search_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//bdi[@id='__button0-BDI-content' and text()='Show Search']")))
            show_search_button.click()
            logging.info(f"'Show Search' button clicked successfully for driver {id(driver)}")
        except Exception as e:
            logging.error(f"Failed to click 'Show Search' button for driver {id(driver)}: {str(e)}")
            raise

    def handle_error_dialog_all(self):
        for i, driver in enumerate(self.drivers):
            self.handle_error_dialog(driver, self.waits[i])

    def handle_error_dialog(self, driver, wait):
        try:
            error_dialog = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='alertdialog']//span[contains(text(), 'There are currently two active sessions')]"))
            )
            if error_dialog:
                logging.info(f"Error dialog detected for driver {id(driver)}. Attempting to dismiss it.")
                ok_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//bdi[text()='OK']")))
                if ok_button:
                    ok_button.click()
                    logging.info(f"Error dialog dismissed for driver {id(driver)}.")
                    WebDriverWait(driver, 10).until(
                        EC.invisibility_of_element_located((By.XPATH, "//div[@role='alertdialog']"))
                    )
                else:
                    logging.error(f"Failed to find OK button in error dialog for driver {id(driver)}")
        except TimeoutException:
            logging.info(f"No error dialog detected for driver {id(driver)}")

    def select_dropdown_option(self, driver, wait, dropdown_id, option_text):
        try:
            dropdown_arrow = wait.until(EC.element_to_be_clickable((By.ID, f"{dropdown_id}-arrow")))
            driver.execute_script("arguments[0].click();", dropdown_arrow)
            logging.info(f"Clicked dropdown arrow for {dropdown_id} in driver {id(driver)}")

            dropdown_list_id = "__list0" if "Ship" in dropdown_id else "__list2"
            dropdown_list = wait.until(EC.visibility_of_element_located((By.ID, dropdown_list_id)))
            logging.info(f"Dropdown list visible for {dropdown_id} in driver {id(driver)}")

            options = dropdown_list.find_elements(By.TAG_NAME, "li")
            logging.info(f"Found {len(options)} options for {dropdown_id} in driver {id(driver)}")

            target_option = next((opt for opt in options if option_text in opt.text), None)

            if target_option:
                driver.execute_script("arguments[0].scrollIntoView(true);", target_option)
                time.sleep(0.5)

                try:
                    target_option.click()
                except ElementClickInterceptedException:
                    try:
                        driver.execute_script("arguments[0].click();", target_option)
                    except:
                        ActionChains(driver).move_to_element(target_option).click().perform()

                logging.info(f"Option '{option_text}' selected successfully for {dropdown_id} in driver {id(driver)}")

                wait.until(EC.invisibility_of_element_located((By.ID, dropdown_list_id)))
                logging.info(f"Dropdown closed after selection for {dropdown_id} in driver {id(driver)}")
            else:
                logging.error(f"Option '{option_text}' not found in {dropdown_id} for driver {id(driver)}")
                driver.save_screenshot(f"{dropdown_id}_selection_error_driver_{id(driver)}.png")
        except Exception as e:
            logging.error(f"Failed to select option in {dropdown_id} for driver {id(driver)}: {str(e)}")
            driver.save_screenshot(f"{dropdown_id}_selection_error_driver_{id(driver)}.png")

    def select_ship_from_plant_all(self, plant_name="WEST BENGAL CEMENT WORKS"):
        for i, driver in enumerate(self.drivers):
            self.select_ship_from_plant(driver, self.waits[i], plant_name)

    def select_ship_from_plant(self, driver, wait, plant_name="WEST BENGAL CEMENT WORKS"):
        self.select_dropdown_option(driver, wait, "__xmlview0--ididUtclVCShipFromPlant", plant_name)

    def select_depot_all(self, depot_name):
        for i, driver in enumerate(self.drivers):
            self.select_depot(driver, self.waits[i], depot_name)

    def select_depot(self, driver, wait, depot_name):
        self.select_dropdown_option(driver, wait, "__xmlview0--idUtclVCDepot", depot_name)

    def click_search_all(self):
        for i, driver in enumerate(self.drivers):
            self.click_search(driver, self.waits[i])

    def click_search(self, driver, wait):
        try:
            self.handle_error_dialog(driver, wait)
            search_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//bdi[text()='Search']")))
            search_button.click()
            logging.info(f"Search button clicked successfully for driver {id(driver)}")
            self.wait_for_page_load(driver)
        except Exception as e:
            logging.error(f"Failed to click Search button for driver {id(driver)}: {str(e)}")


    def check_table_data_all(self):
        for i, driver in enumerate(self.drivers):
            self.check_table_data(driver, self.waits[i])

    def check_table_data(self, driver, wait):
        try:
            wait.until(EC.presence_of_element_located((By.ID, "__xmlview0--idUtclVCVendorAssignmentTable-listUl")))
            no_data_row = driver.find_elements(By.XPATH, "//tr[@id='__xmlview0--idUtclVCVendorAssignmentTable-nodata']")
            has_data = len(no_data_row) == 0
            logging.info(f"Table data check for driver {id(driver)}: {'Data found' if has_data else 'No data found'}")
            return has_data
        except TimeoutException:
            logging.error(f"Table not found or loaded within the timeout period for driver {id(driver)}")
            return False

    async def ultra_rapid_bidding(self, max_duration=300, destinations=None, rapidity=0.000000001):
        start_time = time.time()
        total_bids_placed = 0
        all_bid_details = []
        
        tasks = [self.ultra_rapid_bidding_for_driver(driver, start_time, max_duration, destinations, rapidity) 
                 for driver in self.drivers]
        results = await asyncio.gather(*tasks)
        
        for bids_placed, bid_details in results:
            total_bids_placed += bids_placed
            all_bid_details.extend(bid_details)
        
        logging.info(f"Ultra rapid bidding completed. Total bids placed across all drivers: {total_bids_placed}")
        return total_bids_placed, all_bid_details

    async def ultra_rapid_bidding_for_driver(self, driver, start_time, max_duration, destinations, rapidity):
        bids_placed = 0
        bid_details = []
        
        while time.time() - start_time < max_duration:
            try:
                table_data = driver.execute_script("""
                    var table = document.getElementById('__xmlview0--idUtclVCVendorAssignmentTable-listUl');
                    var rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
                    var data = [];
                    for (var i = 0; i < rows.length; i++) {
                        var cells = rows[i].getElementsByTagName('td');
                        data.push({
                            destination: cells[5].textContent.trim(),
                            freight: parseInt(cells[13].textContent.trim()),
                            bidInput: cells[14].getElementsByTagName('input')[0],
                            rankElement: cells[15].getElementsByTagName('span')[0]
                        });
                    }
                    return data;
                """)
                
                for row in table_data:
                    try:
                        if destinations and row['destination'] not in destinations:
                            continue

                        freight = row['freight']
                        bid_input = row['bidInput']
                        current_bid_amount = int(driver.execute_script("return arguments[0].value;", bid_input) or 0)
                        new_bid_amount = max(current_bid_amount, freight - 1)
                        
                        if not driver.execute_script("return arguments[0].disabled;", bid_input):
                            driver.execute_script("""
                                arguments[0].value = arguments[1];
                                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                                var event = new KeyboardEvent('keydown', {
                                    'key': 'Enter',
                                    'code': 'Enter',
                                    'which': 13,
                                    'keyCode': 13,
                                    'bubbles': true
                                });
                                arguments[0].dispatchEvent(event);
                            """, bid_input, str(new_bid_amount))
                            
                            await asyncio.sleep(rapidity)
                            
                            bid_rank = driver.execute_script("return arguments[0].textContent.trim();", row['rankElement'])
                            bid_details.append({
                                'freight': freight,
                                'bid_amount': new_bid_amount,
                                'rank': bid_rank
                            })
                            
                            if bid_rank == "01":
                                logging.info(f"Driver {id(driver)}: Achieved rank 1 with bid of {new_bid_amount} for freight {freight}")
                                bids_placed += 1
                            elif bid_rank:
                                while bid_rank != "01" and new_bid_amount > freight - 1:
                                    new_bid_amount -= 1
                                    driver.execute_script("""
                                        arguments[0].value = arguments[1];
                                        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                                        var event = new KeyboardEvent('keydown', {
                                            'key': 'Enter',
                                            'code': 'Enter',
                                            'which': 13,
                                            'keyCode': 13,
                                            'bubbles': true
                                        });
                                        arguments[0].dispatchEvent(event);
                                    """, bid_input, str(new_bid_amount))
                                    
                                    await asyncio.sleep(rapidity)
                                    bid_rank = driver.execute_script("return arguments[0].textContent.trim();", row['rankElement'])
                                    bid_details[-1] = {
                                        'freight': freight,
                                        'bid_amount': new_bid_amount,
                                        'rank': bid_rank
                                    }
                                if bid_rank == "01":
                                    logging.info(f"Driver {id(driver)}: Achieved rank 1 with bid of {new_bid_amount} for freight {freight}")
                                    bids_placed += 1
                                else:
                                    logging.info(f"Driver {id(driver)}: Could not achieve rank 1. Final bid: {new_bid_amount}, Rank: {bid_rank}")
                    
                    except Exception as e:
                        logging.error(f"Error processing row for driver {id(driver)}: {str(e)}")
                
                await asyncio.sleep(rapidity)
                
            except Exception as e:
                logging.error(f"Error during ultra rapid bidding for driver {id(driver)}: {str(e)}")
            
            self.click_search(driver, self.waits[self.drivers.index(driver)])
        
        return bids_placed, bid_details

    def start_ultra_rapid_bidding(self, max_duration=300, destinations=None, rapidity=0.000000001):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    
        return loop.run_until_complete(self.ultra_rapid_bidding(max_duration, destinations, rapidity))

    def wait_for_page_load(self, driver, timeout=30):
        try:
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            WebDriverWait(driver, timeout).until(
                EC.invisibility_of_element_located((By.CLASS_NAME, "sapUiLocalBusyIndicator"))
            )
            logging.info(f"Page loaded completely for driver {id(driver)}")
        except TimeoutException:
            logging.warning(f"Timeout waiting for page load after {timeout} seconds for driver {id(driver)}")

    def save_cookies(self, driver):
        cookies = driver.get_cookies()
        with open(f"cookies_driver_{id(driver)}.txt", "w") as cookie_file:
            for cookie in cookies:
                cookie_file.write(f"{cookie['name']}={cookie['value']}\n")
        logging.info(f"Cookies saved for driver {id(driver)}")

    def load_cookies(self, driver):
        try:
            with open(f"cookies_driver_{id(driver)}.txt", "r") as cookie_file:
                for line in cookie_file:
                    name, value = line.strip().split("=", 1)
                    driver.add_cookie({'name': name, 'value': value})
            logging.info(f"Cookies loaded successfully for driver {id(driver)}")
        except Exception as e:
            logging.error(f"Failed to load cookies for driver {id(driver)}: {str(e)}")

    def cookies_exist(self):
        return any(os.path.exists(f"cookies_driver_{id(driver)}.txt") for driver in self.drivers)

    def close_all(self):
        for driver in self.drivers:
            driver.quit()
        logging.info("All browsers closed.")

    def aggressive_bidding_all(self, max_duration=300, destinations=None, rapidity=0.1):
        total_bids_placed = 0
        all_bid_details = []
        
        for i, driver in enumerate(self.drivers):
            bids_placed, bid_details = self.aggressive_bidding(driver, self.waits[i], max_duration, destinations, rapidity)
            total_bids_placed += bids_placed
            all_bid_details.extend(bid_details)
        
        return total_bids_placed, all_bid_details

    def aggressive_bidding(self, driver, wait, max_duration=300, destinations=None, rapidity=0.1):
        start_time = time.time()
        bids_placed = 0
        bid_details = []
        
        while time.time() - start_time < max_duration:
            try:
                table = WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.ID, "__xmlview0--idUtclVCVendorAssignmentTable-listUl"))
                )
                rows = table.find_elements(By.XPATH, ".//tbody/tr")
                
                for row in rows:
                    try:
                        if destinations:
                            destination_element = row.find_element(By.XPATH, ".//td[6]//span")
                            destination = destination_element.text.strip()
                            if destination not in destinations:
                                continue

                        freight_element = row.find_element(By.XPATH, ".//td[contains(@headers, '__text23')]//span")
                        bid_input = row.find_element(By.XPATH, ".//td[contains(@headers, '__text24')]//input[@class='sapMInputBaseInner']")
                        bid_rank_element = row.find_element(By.XPATH, ".//td[contains(@headers, '__text26')]//span")
                        
                        freight = int(freight_element.text.strip())
                        current_bid_amount = int(bid_input.get_attribute('value') or 0)
                        new_bid_amount = max(current_bid_amount, freight - 1)
                        
                        if not bid_input.get_attribute('disabled'):
                            bid_input.clear()
                            bid_input.send_keys(str(new_bid_amount))
                            bid_input.send_keys(Keys.ENTER)
                            
                            time.sleep(rapidity)
                            
                            bid_rank = bid_rank_element.text.strip()
                            bid_details.append({
                                'freight': freight,
                                'bid_amount': new_bid_amount,
                                'rank': bid_rank
                            })
                            
                            if bid_rank == "01":
                                logging.info(f"Driver {id(driver)}: Achieved rank 1 with bid of {new_bid_amount} for freight {freight}")
                                bids_placed += 1
                            elif bid_rank:
                                while bid_rank != "01" and new_bid_amount > freight - 1:
                                    new_bid_amount -= 1
                                    bid_input.clear()
                                    bid_input.send_keys(str(new_bid_amount))
                                    bid_input.send_keys(Keys.ENTER)
                                    time.sleep(rapidity)
                                    bid_rank = bid_rank_element.text.strip()
                                    bid_details[-1] = {
                                        'freight': freight,
                                        'bid_amount': new_bid_amount,
                                        'rank': bid_rank
                                    }
                                if bid_rank == "01":
                                    logging.info(f"Driver {id(driver)}: Achieved rank 1 with bid of {new_bid_amount} for freight {freight}")
                                    bids_placed += 1
                                else:
                                    logging.info(f"Driver {id(driver)}: Could not achieve rank 1. Final bid: {new_bid_amount}, Rank: {bid_rank}")
                    
                    except (StaleElementReferenceException, NoSuchElementException):
                        continue
                    except Exception as e:
                        logging.error(f"Error processing row for driver {id(driver)}: {str(e)}")
                
                time.sleep(rapidity)
                
            except Exception as e:
                logging.error(f"Error during aggressive bidding for driver {id(driver)}: {str(e)}")
            
            self.click_search(driver, wait)
        
        logging.info(f"Aggressive bidding completed for driver {id(driver)}. Total bids placed: {bids_placed}")
        return bids_placed, bid_details

    def aggressive_bidding2_all(self, max_duration=300, destinations=None, rapidity=0.1):
        total_bids_placed = 0
        all_bid_details = []
        
        for i, driver in enumerate(self.drivers):
            bids_placed, bid_details = self.aggressive_bidding2(driver, self.waits[i], max_duration, destinations, rapidity)
            total_bids_placed += bids_placed
            all_bid_details.extend(bid_details)
        
        return total_bids_placed, all_bid_details

    def aggressive_bidding2(self, driver, wait, max_duration=300, destinations=None, rapidity=0.1):
        start_time = time.time()
        bids_placed = 0
        bid_details = []
        
        while time.time() - start_time < max_duration:
            try:
                table = WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.ID, "__xmlview0--idUtclVCVendorAssignmentTable-listUl"))
                )
                rows = table.find_elements(By.XPATH, ".//tbody/tr")
                
                for row in rows:
                    try:
                        if destinations:
                            destination_element = row.find_element(By.XPATH, ".//td[6]//span")
                            destination = destination_element.text.strip()
                            if destination not in destinations:
                                continue

                        freight_element = row.find_element(By.XPATH, ".//td[contains(@headers, '__text23')]//span")
                        bid_input = row.find_element(By.XPATH, ".//td[contains(@headers, '__text24')]//input[@class='sapMInputBaseInner']")
                        bid_rank_element = row.find_element(By.XPATH, ".//td[contains(@headers, '__text26')]//span")
                        
                        freight = int(freight_element.text.strip())
                        current_bid_amount = int(bid_input.get_attribute('value') or 0)
                        new_bid_amount = max(current_bid_amount, freight - 1)
                        
                        if not bid_input.get_attribute('disabled'):
                            bid_input.clear()
                            bid_input.send_keys(str(new_bid_amount))
                            
                            # Use JavaScript to trigger Enter key event
                            driver.execute_script("""
                                var event = new KeyboardEvent('keydown', {
                                    'key': 'Enter',
                                    'code': 'Enter',
                                    'which': 13,
                                    'keyCode': 13,
                                    'bubbles': true
                                });
                                arguments[0].dispatchEvent(event);
                            """, bid_input)
                            
                            time.sleep(rapidity)
                            
                            bid_rank = bid_rank_element.text.strip()
                            bid_details.append({
                                'freight': freight,
                                'bid_amount': new_bid_amount,
                                'rank': bid_rank
                            })
                            
                            if bid_rank == "01":
                                logging.info(f"Driver {id(driver)}: Achieved rank 1 with bid of {new_bid_amount} for freight {freight}")
                                bids_placed += 1
                            elif bid_rank:
                                while bid_rank != "01" and new_bid_amount > freight - 1:
                                    new_bid_amount -= 1
                                    bid_input.clear()
                                    bid_input.send_keys(str(new_bid_amount))
                                    
                                    # Use JavaScript to trigger Enter key event again
                                    driver.execute_script("""
                                        var event = new KeyboardEvent('keydown', {
                                            'key': 'Enter',
                                            'code': 'Enter',
                                            'which': 13,
                                            'keyCode': 13,
                                            'bubbles': true
                                        });
                                        arguments[0].dispatchEvent(event);
                                    """, bid_input)
                                    
                                    time.sleep(rapidity)
                                    bid_rank = bid_rank_element.text.strip()
                                    bid_details[-1] = {
                                        'freight': freight,
                                        'bid_amount': new_bid_amount,
                                        'rank': bid_rank
                                    }
                                if bid_rank == "01":
                                    logging.info(f"Driver {id(driver)}: Achieved rank 1 with bid of {new_bid_amount} for freight {freight}")
                                    bids_placed += 1
                                else:
                                    logging.info(f"Driver {id(driver)}: Could not achieve rank 1. Final bid: {new_bid_amount}, Rank: {bid_rank}")
                    
                    except (StaleElementReferenceException, NoSuchElementException):
                        continue
                    except Exception as e:
                        logging.error(f"Error processing row for driver {id(driver)}: {str(e)}")
                
                time.sleep(rapidity)
                
            except Exception as e:
                logging.error(f"Error during aggressive bidding 2 for driver {id(driver)}: {str(e)}")
            
            self.click_search(driver, wait)
        
        logging.info(f"Aggressive bidding 2 completed for driver {id(driver)}. Total bids placed: {bids_placed}")
        return bids_placed, bid_details

    def aggressive_bidding3_all(self, max_duration=300, destinations=None, rapidity=0.1):
        total_bids_placed = 0
        all_bid_details = []
        
        for i, driver in enumerate(self.drivers):
            bids_placed, bid_details = self.aggressive_bidding3(driver, self.waits[i], max_duration, destinations, rapidity)
            total_bids_placed += bids_placed
            all_bid_details.extend(bid_details)
        
        return total_bids_placed, all_bid_details

    def aggressive_bidding3(self, driver, wait, max_duration=300, destinations=None, rapidity=0.1):
        start_time = time.time()
        bids_placed = 0
        bid_details = []
        
        while time.time() - start_time < max_duration:
            try:
                table = WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.ID, "__xmlview0--idUtclVCVendorAssignmentTable-listUl"))
                )
                rows = table.find_elements(By.XPATH, ".//tbody/tr")
                
                for row in rows:
                    try:
                        if destinations:
                            destination_element = row.find_element(By.XPATH, ".//td[6]//span")
                            destination = destination_element.text.strip()
                            if destination not in destinations:
                                continue

                        freight_element = row.find_element(By.XPATH, ".//td[contains(@headers, '__text23')]//span")
                        bid_input = row.find_element(By.XPATH, ".//td[contains(@headers, '__text24')]//input[@class='sapMInputBaseInner']")
                        
                        freight = int(freight_element.text.strip())
                        new_bid_amount = freight - 1
                        
                        if not bid_input.get_attribute('disabled'):
                            current_value = bid_input.get_attribute('value')
                            if current_value != str(new_bid_amount):
                                bid_input.clear()
                                bid_input.send_keys(str(new_bid_amount))
                                
                                # Use JavaScript to trigger Enter key event
                                driver.execute_script("""
                                    var event = new KeyboardEvent('keydown', {
                                        'key': 'Enter',
                                        'code': 'Enter',
                                        'which': 13,
                                        'keyCode': 13,
                                        'bubbles': true
                                    });
                                    arguments[0].dispatchEvent(event);
                                """, bid_input)
                                
                                time.sleep(rapidity)
                                
                                bid_details.append({
                                    'freight': freight,
                                    'bid_amount': new_bid_amount
                                })
                                
                                logging.info(f"Driver {id(driver)}: Placed bid of {new_bid_amount} for freight {freight}")
                                bids_placed += 1
                            else:
                                logging.info(f"Driver {id(driver)}: Bid already set to {new_bid_amount} for freight {freight}")
                        else:
                            logging.info(f"Driver {id(driver)}: Bid input field not enabled for freight {freight}")
                    
                    except (StaleElementReferenceException, NoSuchElementException):
                        continue
                    except Exception as e:
                        logging.error(f"Error processing row for driver {id(driver)}: {str(e)}")
                
                time.sleep(rapidity)
                
            except Exception as e:
                logging.error(f"Error during aggressive bidding 3 for driver {id(driver)}: {str(e)}")
            
            self.click_search(driver, wait)
        
        logging.info(f"Aggressive bidding 3 completed for driver {id(driver)}. Total bids placed: {bids_placed}")
        return bids_placed, bid_details

    def aggressive_bidding4_all(self, max_duration=300, destinations=None, rapidity=0.1):
        total_bids_placed = 0
        all_bid_details = []
        
        for i, driver in enumerate(self.drivers):
            bids_placed, bid_details = self.aggressive_bidding4(driver, self.waits[i], max_duration, destinations, rapidity)
            total_bids_placed += bids_placed
            all_bid_details.extend(bid_details)
        
        return total_bids_placed, all_bid_details

    def aggressive_bidding4(self, driver, wait, max_duration=300, destinations=None, rapidity=0.1):
        start_time = time.time()
        bids_placed = 0
        bid_details = []
        
        while time.time() - start_time < max_duration:
            try:
                table = WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.ID, "__xmlview0--idUtclVCVendorAssignmentTable-listUl"))
                )
                rows = table.find_elements(By.XPATH, ".//tbody/tr")
                
                for row in rows:
                    bid_placed = False
                    attempts = 0
                    max_attempts = 10  # Maximum number of attempts per row
                    
                    while not bid_placed and attempts < max_attempts and time.time() - start_time < max_duration:
                        try:
                            if destinations:
                                destination_element = row.find_element(By.XPATH, ".//td[6]//span")
                                destination = destination_element.text.strip()
                                if destination not in destinations:
                                    bid_placed = True  # Skip this row
                                    continue

                            freight_element = row.find_element(By.XPATH, ".//td[contains(@headers, '__text23')]//span")
                            bid_input = row.find_element(By.XPATH, ".//td[contains(@headers, '__text24')]//input[@class='sapMInputBaseInner']")
                            bid_rank_element = row.find_element(By.XPATH, ".//td[contains(@headers, '__text26')]//span")
                            
                            freight = int(freight_element.text.strip())
                            current_bid_amount = int(bid_input.get_attribute('value') or 0)
                            new_bid_amount = max(current_bid_amount, freight - 1)
                            
                            # Attempt to enable the input if it's disabled
                            if bid_input.get_attribute('disabled'):
                                logging.info(f"Driver {id(driver)}: Attempting to enable bid input for freight {freight}")
                                try:
                                    # Try clicking on the input to enable it
                                    driver.execute_script("arguments[0].click();", bid_input)
                                    
                                    # Try removing the 'disabled' attribute
                                    driver.execute_script("arguments[0].removeAttribute('disabled');", bid_input)
                                    
                                    # Try setting 'disabled' to false
                                    driver.execute_script("arguments[0].disabled = false;", bid_input)
                                    
                                    time.sleep(rapidity)  # Wait for any changes to take effect
                                except Exception as e:
                                    logging.warning(f"Driver {id(driver)}: Failed to enable bid input: {str(e)}")

                            if not bid_input.get_attribute('disabled'):
                                bid_input.clear()
                                bid_input.send_keys(str(new_bid_amount))
                                
                                # Use JavaScript to trigger Enter key event
                                driver.execute_script("""
                                    var event = new KeyboardEvent('keydown', {
                                        'key': 'Enter',
                                        'code': 'Enter',
                                        'which': 13,
                                        'keyCode': 13,
                                        'bubbles': true
                                    });
                                    arguments[0].dispatchEvent(event);
                                """, bid_input)
                                
                                # Also try sending Enter key directly
                                bid_input.send_keys(Keys.ENTER)
                                
                                time.sleep(rapidity)
                                
                                bid_rank = bid_rank_element.text.strip()
                                
                                if bid_rank:
                                    bid_placed = True
                                    bid_details.append({
                                        'freight': freight,
                                        'bid_amount': new_bid_amount,
                                        'rank': bid_rank
                                    })
                                    
                                    if bid_rank == "01":
                                        logging.info(f"Driver {id(driver)}: Achieved rank 1 with bid of {new_bid_amount} for freight {freight}")
                                        bids_placed += 1
                                    else:
                                        logging.info(f"Driver {id(driver)}: Bid placed with rank {bid_rank} for freight {freight}")
                                else:
                                    logging.info(f"Driver {id(driver)}: Bid not registered, retrying for freight {freight}")
                            else:
                                logging.warning(f"Driver {id(driver)}: Bid input still disabled for freight {freight} after attempt to enable")
                        
                        except (StaleElementReferenceException, NoSuchElementException):
                            logging.warning(f"Driver {id(driver)}: Element not found, retrying for freight {freight}")
                        except Exception as e:
                            logging.error(f"Driver {id(driver)}: Error processing row: {str(e)}")
                        
                        attempts += 1
                        if not bid_placed:
                            time.sleep(rapidity)  # Wait before retrying
                    
                    if not bid_placed:
                        logging.warning(f"Driver {id(driver)}: Failed to place bid after {max_attempts} attempts for freight {freight}")
                
                time.sleep(rapidity)
                
            except Exception as e:
                logging.error(f"Error during aggressive bidding 4 for driver {id(driver)}: {str(e)}")
            
            self.click_search(driver, wait)
        
        logging.info(f"Aggressive bidding 4 completed for driver {id(driver)}. Total bids placed: {bids_placed}")
        return bids_placed, bid_details
    

    def aggressive_bidding_with_save_all(self, max_duration=300, destinations=None, rapidity=0.1):
        total_bids_placed = 0
        all_bid_details = []
        
        for i, driver in enumerate(self.drivers):
            bids_placed, bid_details = self.aggressive_bidding_with_save(driver, self.waits[i], max_duration, destinations, rapidity)
            total_bids_placed += bids_placed
            all_bid_details.extend(bid_details)
        
        return total_bids_placed, all_bid_details

    def aggressive_bidding_with_save2(self, driver, wait, max_duration=300, destinations=None, rapidity=0.1):
        start_time = time.time()
        total_bids_placed = 0
        all_bid_details = []
        
        while time.time() - start_time < max_duration:
            try:
                table = WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.ID, "__xmlview0--idUtclVCVendorAssignmentTable-listUl"))
                )
                rows = table.find_elements(By.XPATH, ".//tbody/tr")
                
                bids_placed_this_round = 0
                bid_details_this_round = []
                
                for row in rows:
                    try:
                        if destinations:
                            destination_element = row.find_element(By.XPATH, ".//td[6]//span")
                            destination = destination_element.text.strip()
                            if destination not in destinations:
                                continue

                        freight_element = row.find_element(By.XPATH, ".//td[contains(@headers, '__text23')]//span")
                        bid_input = row.find_element(By.XPATH, ".//td[contains(@headers, '__text24')]//input[@class='sapMInputBaseInner']")
                        
                        freight = int(freight_element.text.strip())
                        current_bid_amount = int(bid_input.get_attribute('value') or 0)
                        new_bid_amount = max(current_bid_amount, freight - 1)
                        
                        if not bid_input.get_attribute('disabled'):
                            bid_input.clear()
                            bid_input.send_keys(str(new_bid_amount))
                            
                            # Use JavaScript to trigger change event
                            driver.execute_script("""
                                var event = new Event('change', { bubbles: true });
                                arguments[0].dispatchEvent(event);
                            """, bid_input)
                            
                            time.sleep(rapidity)
                            
                            bid_details_this_round.append({
                                'freight': freight,
                                'bid_amount': new_bid_amount
                            })
                            
                            logging.info(f"Driver {id(driver)}: Bid amount set to {new_bid_amount} for freight {freight}")
                            bids_placed_this_round += 1
                        else:
                            logging.info(f"Driver {id(driver)}: Bid input disabled for freight {freight}, skipping")
                    
                    except (StaleElementReferenceException, NoSuchElementException):
                        logging.warning(f"Driver {id(driver)}: Element not found, skipping row")
                    except Exception as e:
                        logging.error(f"Driver {id(driver)}: Error processing row: {str(e)}")
                
                # After placing all bids for this round, click the Save button
                if bids_placed_this_round > 0:
                    try:
                        save_button = WebDriverWait(driver, 1).until(
                            EC.element_to_be_clickable((By.ID, "__xmlview0--idUtclsaveTxt"))
                        )
                        save_button.click()
                        logging.info(f"Driver {id(driver)}: Save button clicked successfully")
                        
                        # Wait for save operation to complete
                        time.sleep(2)
                        
                        # Check for any confirmation dialog or message after saving
                        try:
                            confirmation = WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'sapMMsgBoxText')]"))
                            )
                            logging.info(f"Driver {id(driver)}: Save confirmation: {confirmation.text}")
                        except:
                            logging.info(f"Driver {id(driver)}: No save confirmation dialog found")
                        
                        # Add the bids from this round to the total
                        total_bids_placed += bids_placed_this_round
                        all_bid_details.extend(bid_details_this_round)
                        
                    except Exception as e:
                        logging.error(f"Driver {id(driver)}: Error clicking Save button: {str(e)}")
                else:
                    logging.info(f"Driver {id(driver)}: No bids placed in this round, skipping save")
                
                # Click search to refresh the page for the next round
                self.click_search(driver, wait)
                logging.info(f"Driver {id(driver)}: Clicked search for next round of bidding")
                
                time.sleep(rapidity)
                
            except Exception as e:
                logging.error(f"Driver {id(driver)}: Error during bidding process: {str(e)}")
        
        logging.info(f"Driver {id(driver)}: Aggressive bidding with save completed. Total bids placed: {total_bids_placed}")
        return total_bids_placed, all_bid_details
    
def aggressive_bidding_with_save(self, driver, wait, max_duration=300, destinations=None, rapidity=0.00001):
    start_time = time.time()
    total_bids_placed = 0
    all_bid_details = []
    
    while time.time() - start_time < max_duration:
        try:
            table_data = driver.execute_script("""
                var table = document.getElementById('__xmlview0--idUtclVCVendorAssignmentTable-listUl');
                var rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
                var data = [];
                for (var i = 0; i < rows.length; i++) {
                    var cells = rows[i].getElementsByTagName('td');
                    data.push({
                        destination: cells[5].textContent.trim(),
                        freight: parseInt(cells[13].textContent.trim()),
                        bidInput: cells[14].getElementsByTagName('input')[0],
                        rankElement: cells[15].getElementsByTagName('span')[0]
                    });
                }
                return data;
            """)
            
            bids_placed_this_round = 0
            bid_details_this_round = []
            
            for row in table_data:
                try:
                    if destinations and row['destination'] not in destinations:
                        continue

                    freight = row['freight']
                    bid_input = row['bidInput']
                    rank_element = row['rankElement']
                    
                    current_bid_amount = int(driver.execute_script("return arguments[0].value;", bid_input) or 0)
                    new_bid_amount = max(current_bid_amount, freight - 1)
                    
                    # Always try to set the bid amount, even if the input is disabled
                    driver.execute_script("""
                        var input = arguments[0];
                        var newValue = arguments[1];
                        input.value = newValue;
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                        var enterEvent = new KeyboardEvent('keydown', {
                            key: 'Enter',
                            code: 'Enter',
                            which: 13,
                            keyCode: 13,
                            bubbles: true
                        });
                        input.dispatchEvent(enterEvent);
                    """, bid_input, str(new_bid_amount))
                    
                    # Check if the bid was actually placed (input not disabled)
                    if not driver.execute_script("return arguments[0].disabled;", bid_input):
                        bid_rank = driver.execute_script("return arguments[0].textContent.trim();", rank_element)
                        bid_details_this_round.append({
                            'freight': freight,
                            'bid_amount': new_bid_amount,
                            'rank': bid_rank
                        })
                        
                        if bid_rank == "01":
                            logging.info(f"Driver {id(driver)}: Achieved rank 1 with bid of {new_bid_amount} for freight {freight}")
                            bids_placed_this_round += 1
                        elif bid_rank:
                            logging.info(f"Driver {id(driver)}: Placed bid of {new_bid_amount} for freight {freight}, current rank: {bid_rank}")
                            # If not rank 1, immediately try to outbid
                            while bid_rank != "01" and new_bid_amount > freight - 1:
                                new_bid_amount -= 1
                                driver.execute_script("""
                                    arguments[0].value = arguments[1];
                                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                                    var event = new KeyboardEvent('keydown', {
                                        'key': 'Enter',
                                        'code': 'Enter',
                                        'which': 13,
                                        'keyCode': 13,
                                        'bubbles': true
                                    });
                                    arguments[0].dispatchEvent(event);
                                """, bid_input, str(new_bid_amount))
                                
                                time.sleep(rapidity)
                                bid_rank = driver.execute_script("return arguments[0].textContent.trim();", rank_element)
                                bid_details_this_round[-1] = {
                                    'freight': freight,
                                    'bid_amount': new_bid_amount,
                                    'rank': bid_rank
                                }
                                if bid_rank == "01":
                                    logging.info(f"Driver {id(driver)}: Achieved rank 1 with bid of {new_bid_amount} for freight {freight}")
                                    bids_placed_this_round += 1
                                    break
                    
                    time.sleep(rapidity)
                    
                except Exception as e:
                    logging.error(f"Driver {id(driver)}: Error processing row: {str(e)}")
            
            # After placing all bids for this round, click the Save button
            if bids_placed_this_round > 0:
                try:
                    driver.execute_script("""
                        var saveButton = document.getElementById('__xmlview0--idUtclsaveTxt');
                        if (saveButton) saveButton.click();
                    """)
                    logging.info(f"Driver {id(driver)}: Save button clicked successfully")
                    
                    # Wait for save operation to complete
                    time.sleep(0.5)
                    
                    # Add the bids from this round to the total
                    total_bids_placed += bids_placed_this_round
                    all_bid_details.extend(bid_details_this_round)
                    
                except Exception as e:
                    logging.error(f"Driver {id(driver)}: Error clicking Save button: {str(e)}")
            else:
                logging.info(f"Driver {id(driver)}: No bids placed in this round, skipping save")
            
            # Click search to refresh the page for the next round
            driver.execute_script("""
                var searchButton = document.querySelector('button[data-sap-ui="__xmlview0--idUtclsearchBtnTxt"]');
                if (searchButton) searchButton.click();
            """)
            logging.info(f"Driver {id(driver)}: Clicked search for next round of bidding")
            
            time.sleep(rapidity)
            
        except Exception as e:
            logging.error(f"Driver {id(driver)}: Error during bidding process: {str(e)}")
    
    logging.info(f"Driver {id(driver)}: Aggressive bidding with save completed. Total bids placed: {total_bids_placed}")
    return total_bids_placed, all_bid_details