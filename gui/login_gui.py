# File: gui/login_gui.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox
from PyQt5.QtCore import QThread, pyqtSignal
from automation.sap_automation import SAPBiddingAutomation
import logging
import time

class AutomationThread(QThread):
    update_signal = pyqtSignal(str)

    def __init__(self, username, password, ship_from_plant, selected_depot=None):
        super().__init__()
        self.username = username
        self.password = password
        self.ship_from_plant = ship_from_plant
        self.selected_depot = selected_depot
        self.stop_flag = False

    def run(self):
        automation = SAPBiddingAutomation()
        try:
            self.update_signal.emit("Setting up WebDriver...")
            automation.setup_driver()
            
            self.update_signal.emit("Attempting login...")
            login_success = automation.login(self.username, self.password)
            
            if login_success:
                self.update_signal.emit("Login successful. Navigating to eBidding page...")
                ebidding_url = automation.navigate_to_ebidding()
                self.update_signal.emit(f"Opened eBidding URL: {ebidding_url}")
                
                self.update_signal.emit("Clicking 'Show Search' button...")
                automation.click_show_search()
                
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
                        self.update_signal.emit(f"Data found for {current_depot}. Starting bidding process...")
                        bid_start_time = time.time()
                        while not self.stop_flag and (time.time() - bid_start_time) < 300:  # Bid for 5 minutes
                            bids_placed = automation.place_bids()
                            self.update_signal.emit(f"Placed {bids_placed} bids. Waiting for 5 seconds before next attempt...")
                            time.sleep(5)
                        self.update_signal.emit(f"Finished bidding for {current_depot}.")
                    else:
                        self.update_signal.emit(f"No data found for {current_depot}.")
                    
                    if self.selected_depot:
                        self.update_signal.emit("Waiting 30 seconds before searching again...")
                        time.sleep(1)
                    else:
                        self.update_signal.emit(f"Moving to next depot. Next index: {depot_index}")
                        time.sleep(2)  # Short delay before trying next option
            else:
                self.update_signal.emit("Login failed. Please check your credentials.")

        except Exception as e:
            self.update_signal.emit(f"Error: {str(e)}")
        finally:
            self.update_signal.emit("Automation stopped. Browser remains open.")

    def stop(self):
        self.stop_flag = True

class SAPLoginGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()

        # Username input
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        username_layout.addWidget(self.username_input)
        main_layout.addLayout(username_layout)

        # Password input
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("Password:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
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
        self.setWindowTitle('SAP Bidding Automation')
        self.setGeometry(300, 300, 400, 500)

    def start_automation(self):
        username = self.username_input.text()
        password = self.password_input.text()
        ship_from_plant = self.ship_from_plant_combo.currentText()
        selected_depot = self.depot_combo.currentText()
        
        if selected_depot == "All Depots (Rotational)":
            selected_depot = None

        self.thread = AutomationThread(username, password, ship_from_plant, selected_depot)
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