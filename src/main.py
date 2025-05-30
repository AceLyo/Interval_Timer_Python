import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor

from src.utils import resource_path
from src.app import WorkoutTimer

if __name__ == "__main__":
    app = QApplication(sys.argv)
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

    # load external QSS
    style_file = resource_path("style.qss")
    with open(style_file, "r") as f:
        app.setStyleSheet(f.read())

    window = WorkoutTimer()
    window.show()
    sys.exit(app.exec_())
