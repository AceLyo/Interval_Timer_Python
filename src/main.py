import sys
import time
import logging

logging.basicConfig(filename="startup.log", level=logging.INFO)
start_time = time.perf_counter()
logging.info("App start")

from PyQt5.QtWidgets import QApplication
logging.info(f"After PyQt5 import: {time.perf_counter() - start_time:.2f}s")

from PyQt5.QtGui import QPalette, QColor

from src.utils import resource_path
from src.app import WorkoutTimer
from src.config import Config
logging.info(f"After app imports: {time.perf_counter() - start_time:.2f}s")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    logging.info(f"After QApplication: {time.perf_counter() - start_time:.2f}s")
    app.setStyle("Fusion")

    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window,        QColor(45, 45, 45))
    dark_palette.setColor(QPalette.WindowText,    QColor(225, 225, 225))
    dark_palette.setColor(QPalette.Base,          QColor(30, 30, 30))
    dark_palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.ToolTipBase,   QColor(225, 225, 225))
    dark_palette.setColor(QPalette.ToolTipText,   QColor(225, 225, 225))
    dark_palette.setColor(QPalette.Text,          QColor(225, 225, 225))
    dark_palette.setColor(QPalette.Button,        QColor(45, 45, 45))
    dark_palette.setColor(QPalette.ButtonText,    QColor(225, 225, 225))
    app.setPalette(dark_palette)
    logging.info(f"After palette set: {time.perf_counter() - start_time:.2f}s")

    # load external QSS
    style_file = resource_path("style.qss")
    with open(style_file, "r") as f:
        app.setStyleSheet(f.read())
    logging.info(f"After loading QSS: {time.perf_counter() - start_time:.2f}s")

    # Initialize the main window
    window = WorkoutTimer()
    logging.info(f"After WorkoutTimer init: {time.perf_counter() - start_time:.2f}s")
    if not window.settings.minimalist_mode_active:
        window.show()
    sys.exit(app.exec_())
