# File: main.py

import sys
from PyQt5.QtWidgets import QApplication
from gui.login_gui import SAPLoginGUI
from utils.logger import setup_logger

def main():
    setup_logger()
    app = QApplication(sys.argv)
    gui = SAPLoginGUI()
    gui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()