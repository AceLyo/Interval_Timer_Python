from PyQt5.QtWidgets import QWidget, QMenu
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QBrush, QColor
from PyQt5.QtWidgets import QApplication

from .timer_state import TimerState

class MinimalistWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent  # QMainWindow reference

        # compute size
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        size = min(self.parent_window.settings.minimalist_mode_size,
                   screen_geometry.width(), screen_geometry.height())
        self.setFixedSize(size, size)
        self.setMinimumSize(20, 20)
        self.setMaximumSize(500, 500)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # default circle color
        self.color = QColor("#3D3D3D")

        # build context menu
        self.context_menu = QMenu(self)
        self.start_timer      = self.context_menu.addAction("Start Timer")
        self.pause_timer      = self.context_menu.addAction("Pause Timer")
        self.resume_timer     = self.context_menu.addAction("Resume Timer")
        self.stop_timer       = self.context_menu.addAction("Stop Timer")
        # widget customization submenu
        self.customize_menu   = self.context_menu.addMenu("Customize")
        self.toggle_round_text   = self.customize_menu.addAction("Toggle Round Display")
        self.toggle_time_text    = self.customize_menu.addAction("Toggle Time Display")
        self.toggle_shape     = self.customize_menu.addAction("Toggle Shape")
        # widget size submenu
        self.size_menu        = self.context_menu.addMenu("Adjust Size")
        self.increase_size_5  = self.size_menu.addAction("Increase Size by 5px")
        self.increase_size_10 = self.size_menu.addAction("Increase Size by 10px")
        self.increase_size_20 = self.size_menu.addAction("Increase Size by 20px")
        self.increase_size_50 = self.size_menu.addAction("Increase Size by 50px")
        self.size_menu.addSeparator()
        self.decrease_size_5  = self.size_menu.addAction("Decrease Size by 5px")
        self.decrease_size_10 = self.size_menu.addAction("Decrease Size by 10px")
        self.decrease_size_20 = self.size_menu.addAction("Decrease Size by 20px")
        self.decrease_size_50 = self.size_menu.addAction("Decrease Size by 50px")
        # after submenus
        self.minimize_to_taskbar = self.context_menu.addAction("Minimize to Taskbar")
        self.exit_minimalist     = self.context_menu.addAction("Exit Minimalist Mode")
        self.exit_app            = self.context_menu.addAction("Exit Application")

        # wire up context actions
        self.start_timer.triggered.connect(self.parent().start_timer)
        self.pause_timer.triggered.connect(self.parent().pause_timer)
        self.resume_timer.triggered.connect(self.parent().resume_timer)
        self.stop_timer.triggered.connect(self.parent().stop_timer)
        self.toggle_round_text.triggered.connect(self.parent().toggle_round_display)
        self.toggle_time_text.triggered.connect(self.parent().toggle_time_display)
        self.toggle_shape.triggered.connect(self.parent().toggle_shape)
        self.minimize_to_taskbar.triggered.connect(self.exit_minimalist_and_minimize)
        self.exit_minimalist.triggered.connect(self.parent().toggle_minimalist_mode)
        self.exit_app.triggered.connect(QApplication.quit)

        # size adjustments
        for action, delta in (
            (self.increase_size_5, +5),
            (self.increase_size_10, +10),
            (self.increase_size_20, +20),
            (self.increase_size_50, +50),
            (self.decrease_size_5, -5),
            (self.decrease_size_10, -10),
            (self.decrease_size_20, -20),
            (self.decrease_size_50, -50),
        ):
            action.triggered.connect(lambda _, d=delta: self.adjust_size(d))

        # style
        self.context_menu.setStyleSheet("""
            QMenu::separator {
                height: 2px;
                background: #444;
                margin: 5px 10px;
            }
        """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(self.color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, self.width(), self.height())

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.update_context_menu()
            self.context_menu.exec_(self.mapToGlobal(event.pos()))
        else:
            self.old_pos = event.globalPos()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            parent = self.parent()
            if parent:
                parent.minimalist_mode = True
                parent.toggle_minimalist_mode()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            delta = QPoint(event.globalPos() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()

    def update_context_menu(self):
        st = self.parent().state
        self.start_timer.setVisible(st == TimerState.Idle)
        self.pause_timer.setVisible(st in (TimerState.LeadUp, TimerState.Workout, TimerState.Rest))
        self.resume_timer.setVisible(st in (TimerState.PausedLeadUp, TimerState.PausedWorkout, TimerState.PausedRest))
        self.stop_timer.setVisible(st not in (TimerState.Idle, TimerState.PausedLeadUp, TimerState.PausedWorkout, TimerState.PausedRest))

    def adjust_size(self, delta: int):
        new_size = min(500, max(20, self.width() + delta))
        self.setFixedSize(new_size, new_size)
        self.update()
        self.parent_window.settings.minimalist_mode_size = new_size
        self.parent_window.settings.save_to_file()

    def exit_minimalist_and_minimize(self):
        self.parent().toggle_minimalist_mode()
        self.parent().showMinimized()