# File: gui/login_gui.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox
from PyQt5.QtCore import QThread, pyqtSignal
from automation.sap_automation import SAPBiddingAutomation
import logging
import time
from gui.license_manager import LicenseManager
from PyQt5.QtWidgets import QMessageBox, QInputDialog

class AutomationThread(QThread):
    update_signal = pyqtSignal(str)

    def __init__(self, username, password, ship_from_plant, selected_depot=None, destinations=None):
        super().__init__()
        self.username = username
        self.password = password
        self.ship_from_plant = ship_from_plant
        self.selected_depot = selected_depot
        self.destinations = destinations
        self.stop_flag = False

    def run(self):
        automation = SAPBiddingAutomation()
        try:
            self.update_signal.emit("Setting up WebDriver...")
            automation.setup_driver()
            
            # Login with retry
            max_login_attempts = 3
            for attempt in range(max_login_attempts):
                self.update_signal.emit(f"Attempting login... (Attempt {attempt + 1}/{max_login_attempts})")
                login_success = automation.login(self.username, self.password)
                if login_success:
                    break
                elif attempt < max_login_attempts - 1:
                    self.update_signal.emit("Login failed. Retrying in 5 seconds...")
                    time.sleep(5)
            
            if not login_success:
                self.update_signal.emit("Login failed after multiple attempts. Please check your credentials.")
                return

            # Navigate to eBidding page with retry
            max_navigation_attempts = 3
            for attempt in range(max_navigation_attempts):
                try:
                    self.update_signal.emit(f"Navigating to eBidding page... (Attempt {attempt + 1}/{max_navigation_attempts})")
                    ebidding_url = automation.navigate_to_ebidding()
                    self.update_signal.emit(f"Opened eBidding URL: {ebidding_url}")
                    break
                except Exception as e:
                    if attempt < max_navigation_attempts - 1:
                        self.update_signal.emit(f"Navigation failed. Retrying in 5 seconds... Error: {str(e)}")
                        time.sleep(5)
                    else:
                        self.update_signal.emit(f"Navigation failed after multiple attempts. Error: {str(e)}")
                        return

            # Handle error dialogs and click 'Show Search' button with retry
            max_show_search_attempts = 3
            for attempt in range(max_show_search_attempts):
                try:
                    self.update_signal.emit(f"Handling error dialogs and clicking 'Show Search' button... (Attempt {attempt + 1}/{max_show_search_attempts})")
                    
                    # Handle error dialogs
                    max_dialog_attempts = 3
                    for dialog_attempt in range(max_dialog_attempts):
                        dialog_handled = automation.handle_error_dialog()
                        if not dialog_handled:
                            break
                        self.update_signal.emit(f"Handled an error dialog. Checking for more... (Attempt {dialog_attempt + 1}/{max_dialog_attempts})")
                        time.sleep(1)  # Short delay before checking for another dialog
                    
                    # Click 'Show Search' button
                    automation.click_show_search()
                    self.update_signal.emit("Successfully clicked 'Show Search' button.")
                    break
                except Exception as e:
                    if attempt < max_show_search_attempts - 1:
                        self.update_signal.emit(f"Failed to handle dialogs or click 'Show Search' button. Retrying in 5 seconds... Error: {str(e)}")
                        time.sleep(5)
                    else:
                        self.update_signal.emit(f"Failed to handle dialogs or click 'Show Search' button after multiple attempts. Error: {str(e)}")
                        return

            self.update_signal.emit(f"Selecting Ship From Plant: {self.ship_from_plant}")
            automation.select_ship_from_plant(self.ship_from_plant)
            
            depots = ["DEOGARH", "DHANBAD", "BANKURA", "BERHAMPORE", "BURDWAN", "COSSIPORE", 
                      "DANKUNI", "KALIGHAT", "KHARAGPUR", "KRISHNANAGAR", "SAINTHIA", "SHALIMAR", 
                      "DIAMOND HARBOUR", "BARASAT"]
            depot_index = 0
            
            while not self.stop_flag:
                self.update_signal.emit("Handling any error dialogs before depot selection...")
                automation.handle_error_dialog()
                
                if self.selected_depot:
                    current_depot = self.selected_depot
                else:
                    current_depot = depots[depot_index]
                    depot_index = (depot_index + 1) % len(depots)

                self.update_signal.emit(f"Selecting Depot: {current_depot}")
                automation.select_depot(current_depot)
                
                self.update_signal.emit("Clicking Search...")
                automation.click_search()
                
                if automation.check_table_data():
                    self.update_signal.emit(f"Data found for {current_depot}. Starting aggressive bidding process...")
                    bids_placed, bid_details = automation.aggressive_bidding(max_duration=300, destinations=self.destinations)
                    self.update_signal.emit(f"Bidding session completed for {current_depot}.")
                    self.update_signal.emit(f"Total bids placed: {bids_placed}")
                    for detail in bid_details:
                        self.update_signal.emit(f"Freight: {detail['freight']}, Bid: {detail['bid_amount']}, Rank: {detail['rank']}")
                    rank_1_bids = sum(1 for detail in bid_details if detail['rank'] == '01')
                    self.update_signal.emit(f"Bids with Rank 1: {rank_1_bids}")
                else:
                    self.update_signal.emit(f"No data found for {current_depot}.")
                
                if self.selected_depot:
                    self.update_signal.emit("Waiting 1 second before searching again...")
                    time.sleep(1)
                else:
                    self.update_signal.emit(f"Moving to next depot. Next index: {depot_index}")
                    time.sleep(2)  # Short delay before trying next option

        except Exception as e:
            self.update_signal.emit(f"Error: {str(e)}")
        finally:
            self.update_signal.emit("Automation stopped. Browser remains open.")

    def stop(self):
        self.stop_flag = True

# The rest of the SAPLoginGUI class remains unchanged

# The rest of the SAPLoginGUI class remains unchanged

# The rest of the SAPLoginGUI class remains unchanged

class SAPLoginGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.default_username = "2203498"  # Set your default username here
        self.default_password = "UtclAks@2025"  # Set your default password here
        self.license_manager = LicenseManager()
        if not self.check_license():
            self.terminate_program()
        self.initUI()

    def check_license(self):
        is_valid, message = self.license_manager.check_license()
        if not is_valid:
            return self.show_activation_dialog(message)
        else:
            QMessageBox.information(self, "License Status", message)
            return True

    def show_activation_dialog(self, message):
        key, ok = QInputDialog.getText(self, "License Activation", message + "\nEnter activation key:")
        if ok:
            if self.license_manager.activate_license(key):
                QMessageBox.information(self, "License Activation", "License activated successfully!")
                return True
            else:
                QMessageBox.critical(self, "License Activation", "Invalid activation key. The program will now exit.")
                return False
        else:
            QMessageBox.critical(self, "License Activation", "License activation cancelled. The program will now exit.")
            return False

    def terminate_program(self):
        QMessageBox.critical(self, "Program Termination", "The program will now exit due to license issues.")
        self.close()
        import sys
        sys.exit()

    def start_automation(self):
        is_valid, _ = self.license_manager.check_license()
        if not is_valid:
            QMessageBox.critical(self, "License Error", "Your license has expired. The program will now exit.")
            self.terminate_program()


    def initUI(self):
        main_layout = QVBoxLayout()

        # Username input
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        username_layout.addWidget(self.username_input)
        main_layout.addLayout(username_layout)

        # Password input
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("Password:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter your password")
        password_layout.addWidget(self.password_input)
        main_layout.addLayout(password_layout)

        # Ship From Plant selection
        ship_from_plant_layout = QHBoxLayout()
        ship_from_plant_layout.addWidget(QLabel("Ship From Plant:"))
        self.ship_from_plant_combo = QComboBox()
        self.ship_from_plant_combo.addItem("WEST BENGAL CEMENT WORKS")
        ship_from_plant_layout.addWidget(self.ship_from_plant_combo)
        main_layout.addLayout(ship_from_plant_layout)

        # Depot selection (optional)
        depot_layout = QHBoxLayout()
        depot_layout.addWidget(QLabel("Select Depot (optional):"))
        self.depot_combo = QComboBox()
        self.depot_combo.addItem("All Depots (Rotational)")
        self.depot_combo.addItems(["DEOGARH", "DHANBAD", "BANKURA", "BERHAMPORE", "BURDWAN", "COSSIPORE", 
                                   "DANKUNI", "KALIGHAT", "KHARAGPUR", "KRISHNANAGAR", "SAINTHIA", "SHALIMAR", 
                                   "DIAMOND HARBOUR", "BARASAT"])
        depot_layout.addWidget(self.depot_combo)
        main_layout.addLayout(depot_layout)

        # Add Destination input
        destination_layout = QHBoxLayout()
        # destination_layout.addWidget(QLabel("Destinations (comma-separated):"))
        self.destination_input = QLineEdit()
        self.destination_input.setPlaceholderText("Enter destinations, e.g. City1, City2, City3")
        destination_layout.addWidget(self.destination_input)
        main_layout.addLayout(destination_layout)


        # Start button
        self.start_button = QPushButton("Start Automation")
        self.start_button.clicked.connect(self.start_automation)
        main_layout.addWidget(self.start_button)

        # Stop button
        self.stop_button = QPushButton("Stop Automation")
        self.stop_button.clicked.connect(self.stop_automation)
        self.stop_button.setEnabled(False)
        main_layout.addWidget(self.stop_button)

        # Log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        main_layout.addWidget(self.log_area)

        self.setLayout(main_layout)
        self.setWindowTitle('SAP Automation')
        self.setGeometry(300, 300, 400, 500)

    def start_automation(self):
        username = self.username_input.text() or self.default_username
        password = self.password_input.text() or self.default_password
        ship_from_plant = self.ship_from_plant_combo.currentText()
        selected_depot = self.depot_combo.currentText()
        destinations = [dest.strip() for dest in self.destination_input.text().split(',') if dest.strip()]
        
        if selected_depot == "All Depots (Rotational)":
            selected_depot = None

        self.thread = AutomationThread(username, password, ship_from_plant, selected_depot, destinations)
        self.thread.update_signal.connect(self.update_log)
        self.thread.start()
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_automation(self):
        if hasattr(self, 'thread'):
            self.thread.stop()
            self.stop_button.setEnabled(False)
            self.start_button.setEnabled(True)

    def update_log(self, message):
        self.log_area.append(message)
        logging.info(message)