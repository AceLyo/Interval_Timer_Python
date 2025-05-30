from PyQt5.QtWidgets import QWidget, QMenu, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QBrush, QColor
from PyQt5.QtWidgets import QApplication

from .timer_state import TimerState
from .config import Config

class MinimalistWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent  # QMainWindow reference
        self.settings = Config.load_from_file()

        # Set up a layout for the widget
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        # compute size
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        size = min(self.parent_window.settings.minimalist_mode_size,
                   screen_geometry.width(), screen_geometry.height())
        self.setFixedSize(size, size)
        self.setMinimumSize(20, 20)
        self.setMaximumSize(500, 500)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Load saved display preferences
        self.show_round_text = self.settings.minimalist_rounds_active
        self.show_time_text = self.settings.minimalist_time_active
        self.is_circle = not self.settings.minimalist_progressbar_active

        # Apply saved shape
        if not self.is_circle:
            self.setFixedSize(size * 2, size // 2)

        # default circle color
        grey = "#3D3D3D"
        self.color = QColor(grey)
        # Add progress bar colors
        self.progress_bg_color = QColor(grey)
        self.progress_fill_color = QColor("#FFA500")

        # Add these properties
        self.progress = 0
        self.active_color = QColor(grey)
        self.bg_color = QColor("#5A5177")
        self.current_state = None
        self.remaining_time = 0
        self.current_round = 0
        self.total_rounds = 0

        # build context menu
        self.context_menu = QMenu(self)
        self.start_timer      = self.context_menu.addAction("Start Timer")
        self.pause_timer      = self.context_menu.addAction("Pause Timer")
        self.resume_timer     = self.context_menu.addAction("Resume Timer")
        self.stop_timer       = self.context_menu.addAction("Stop Timer")
        # widget customization submenu
        self.customize_menu   = self.context_menu.addMenu("Customize Display")
        self.toggle_round_text   = self.customize_menu.addAction("Toggle Round Display")
        self.toggle_time_text    = self.customize_menu.addAction("Toggle Time Display")
        self.shape_toggle_action = self.customize_menu.addAction("Toggle Progress Bar Display")
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
        self.size_menu.addSeparator()
        self.size_to_default = self.size_menu.addAction("Reset to Default Size")
        # after submenus
        self.minimize_to_taskbar = self.context_menu.addAction("Minimize to Taskbar")
        self.exit_minimalist     = self.context_menu.addAction("Exit Minimalist Mode")
        self.exit_app            = self.context_menu.addAction("Exit Application")

        # wire up context actions
        self.start_timer.triggered.connect(self.parent().start_timer)
        self.pause_timer.triggered.connect(self.parent().pause_timer)
        self.resume_timer.triggered.connect(self.parent().resume_timer)
        self.stop_timer.triggered.connect(self.parent().stop_timer)
        self.toggle_round_text.triggered.connect(self.toggle_round_display)
        self.toggle_time_text.triggered.connect(self.toggle_time_display)
        self.shape_toggle_action.triggered.connect(self.toggle_shape)
        self.minimize_to_taskbar.triggered.connect(self.exit_minimalist_and_minimize)
        self.exit_minimalist.triggered.connect(self.parent().toggle_minimalist_mode)
        self.exit_app.triggered.connect(QApplication.quit)

        self.size_to_default.triggered.connect(self.reset_to_default_size)
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
        
        if self.is_circle:
            # Draw background circle
            painter.setBrush(QBrush(self.bg_color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, self.width(), self.height())
            
            # Draw progress arc if there is progress
            if self.progress > 0:
                painter.setBrush(QBrush(self.active_color))
                span_angle = int(-self.progress * 360 * 16)  # QPainter uses 16th of a degree
                painter.drawPie(0, 0, self.width(), self.height(), 90 * 16, span_angle)
        else:
            # Draw progress bar background
            painter.setBrush(QBrush(self.bg_color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(0, 0, self.width(), self.height(), 10, 10) # 
            
            # Draw progress fill
            if self.progress > 0:
                progress_width = int(self.width() * self.progress)
                painter.setBrush(QBrush(self.active_color))
                painter.drawRoundedRect(0, 0, progress_width, self.height(), 10, 10)
        
        # Draw text if enabled
        if self.show_round_text or self.show_time_text:
            text_parts = []
            
            # Configure text appearance
            painter.setPen(Qt.white)
            font = painter.font()
            if self.is_circle:
                font.setPointSize(min(self.width() // 6, 30))
            else: 
                font.setPointSize(min(self.width() // 6, 30) - 10)
            painter.setFont(font)
            
            rect = self.rect()
            
            self.display_round_and_time(painter, rect)

    def display_round_and_time(self, painter, rect):
        # Adjust font size based on widget dimensions and mode
        font = painter.font()
        if self.is_circle:
            font_size = min(self.width() // 6, 30)
        else:
            # For progress bar, use height as the limiting factor
            font_size = min(self.height() // 2, 30)
        font.setPointSize(font_size)
        painter.setFont(font)

        if self.show_round_text and self.show_time_text:
            rounds_left = self.total_rounds - self.current_round
            mins, secs = divmod(self.remaining_time, 60)
                
            if self.is_circle:
                # For circle mode - stack vertically
                bottom_rect = rect.adjusted(0, rect.height()//4, 0, 0)
                top_rect = rect.adjusted(0, 0, 0, -rect.height()//4)
                
                painter.drawText(top_rect, Qt.AlignCenter, f"R:{rounds_left}")
                painter.drawText(bottom_rect, Qt.AlignCenter, f"{mins:02}:{secs:02}")
                
            else:
                # For progress bar mode - position side by side with padding
                padding = rect.width() // 20  # 5% padding on each side
                left_rect = rect.adjusted(padding, 0, -rect.width()//2, 0)
                right_rect = rect.adjusted(rect.width()//2, 0, -padding, 0)
                
                painter.drawText(left_rect, Qt.AlignCenter, f"R:{rounds_left}")
                painter.drawText(right_rect, Qt.AlignCenter, f"{mins:02}:{secs:02}")
        else:
            # Only one enabled - center it
            if self.show_round_text:
                rounds_left = self.total_rounds - self.current_round
                text = f"R:{rounds_left}"
            else:
                mins, secs = divmod(self.remaining_time, 60)
                text = f"{mins:02}:{secs:02}"
            painter.drawText(rect, Qt.AlignCenter, text)

    ###############################
    # Mouse event handlers
    ###############################

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

    ##################################
    # Context menu actions
    ##################################

    def update_context_menu(self):
        st = self.parent().state
        self.start_timer.setVisible(st == TimerState.Idle)
        self.pause_timer.setVisible(st in (TimerState.LeadUp, TimerState.Workout, TimerState.Rest))
        self.resume_timer.setVisible(st in (TimerState.PausedLeadUp, TimerState.PausedWorkout, TimerState.PausedRest))
        self.stop_timer.setVisible(st not in (TimerState.Idle, TimerState.PausedLeadUp, TimerState.PausedWorkout, TimerState.PausedRest))

    def adjust_size(self, delta: int):
        if self.is_circle:
            new_size = min(500, max(20, self.width() + delta))
            self.setFixedSize(new_size, new_size)
        else:
            new_width = min(1000, max(100, self.width() + delta))
            new_height = new_width // 4
            self.setFixedSize(new_width, new_height)
        self.update()
        self.parent_window.settings.minimalist_mode_size = self.width()
        self.parent_window.settings.save_to_file()

    def exit_minimalist_and_minimize(self):
        self.parent().toggle_minimalist_mode()
        self.parent().showMinimized()

    def toggle_round_display(self):
        self.show_round_text = not self.show_round_text
        self.parent_window.settings.minimalist_rounds_active = self.show_round_text
        self.parent_window.settings.save_to_file()
        self.update()

    def toggle_time_display(self):
        self.show_time_text = not self.show_time_text
        self.parent_window.settings.minimalist_time_active = self.show_time_text
        self.parent_window.settings.save_to_file()
        self.update()

    def toggle_shape(self):
        self.is_circle = not self.is_circle
        # Save progress bar state (True if progress bar is shown, i.e., not circle)
        self.parent_window.settings.minimalist_progressbar_active = not self.is_circle
        self.parent_window.settings.save_to_file()
        if self.is_circle:
            # Make it square for circle
            size = self.width()
            self.setFixedSize(size, size)
        else:
            # Make it wider for progress bar
            self.setFixedSize(self.width() * 2, self.height() // 2)
        self.update()

    def reset_to_default_size(self):
        self.setFixedSize(self.parent_window.settings.minimalist_mode_size,
                          self.parent_window.settings.minimalist_mode_size)
        self.update()
        self.parent_window.settings.minimalist_mode_size = self.width()
        self.parent_window.settings.save_to_file()