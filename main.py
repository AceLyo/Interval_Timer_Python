import sys
import json
import os
import time
from enum import Enum
from dataclasses import dataclass, asdict

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QProgressBar, QLineEdit, QMenu
)
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPixmap, QTransform, QFont, QIntValidator, QPalette, QColor, QPainter, QPen, QBrush, QIcon

import pygame

# ------------------------------
# Utility Function for Resource Path
# ------------------------------
def resource_path(relative_path):
    """Get the absolute path to a resource, works for dev and PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        # Running as a PyInstaller executable
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# ------------------------------
# Timer State Enumeration
# ------------------------------
class TimerState(Enum):
    Idle = 0
    LeadUp = 1
    Workout = 2
    Rest = 3
    PausedWorkout = 4
    PausedRest = 5
    PausedLeadUp = 6

# ------------------------------
# Settings Persistence (Load/Save)
# ------------------------------
@dataclass
class Settings:
    workout_duration: int = 60   # in seconds
    rest_duration: int = 45      # in seconds
    lead_up_duration: int = 5    # in seconds
    rounds: int = 10

    @staticmethod
    def load_from_file(filename: str = "settings.json") -> 'Settings':
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    data = json.load(f)
                return Settings(**data)
            except (json.JSONDecodeError, TypeError, ValueError):
                default = Settings()
                default.save_to_file(filename)
                return default
        else:
            default = Settings()
            default.save_to_file(filename)
            return default

    def save_to_file(self, filename: str = "settings.json"):
        try:
            with open(filename, "w") as f:
                json.dump(asdict(self), f, indent=4)
        except Exception as e:
            print("Error saving settings:", e)

# ------------------------------
# Minimalist Widget
# ------------------------------
class MinimalistWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.color = QColor("#3D3D3D")
        
        # Create context menu
        self.context_menu = QMenu(self)
        self.exit_minimalist = self.context_menu.addAction("Exit Minimalist Mode")
        self.exit_app = self.context_menu.addAction("Exit Application")
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw circle
        painter.setBrush(QBrush(self.color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 40, 40)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            # Show context menu
            action = self.context_menu.exec_(self.mapToGlobal(event.pos()))
            if action == self.exit_minimalist:
                # Signal parent to exit minimalist mode
                self.parent().toggle_minimalist_mode()
            elif action == self.exit_app:
                QApplication.quit()
        else:
            self.old_pos = event.globalPos()
            
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Get parent QMainWindow and toggle minimalist mode
            parent = self.parent()
            if parent:
                parent.minimalist_mode = True  # Ensure mode is set before toggling
                parent.toggle_minimalist_mode()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.old_pos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_pos = event.globalPos()

# ------------------------------
# Main Workout Timer Application
# ------------------------------
class WorkoutTimer(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set the window icon
        self.setWindowIcon(QIcon(resource_path("icon.ico")))

        # Load settings
        self.settings = Settings.load_from_file()
        self.workout_duration = self.settings.workout_duration
        self.rest_duration = self.settings.rest_duration
        self.rounds = self.settings.rounds
        self.lead_up_duration = self.settings.lead_up_duration

        self.current_round = 0
        self.remaining_time = 0
        self.state = TimerState.Idle
        self.start_time = None
        self.fanfare_start_time = None
        self.pause_elapsed = 0

        # Initialize pygame mixer for audio playback
        pygame.mixer.init()
        self.work_finish_audio = "work_finish.mp3"
        self.rest_finish_audio = "rest_finish.mp3"
        self.complete_finish_audio = "complete_finish.mp3"

        # Minimalist mode
        self.minimalist_mode = False
        self.minimalist_widget = None

        # Setup the GUI
        self.initUI()

        # Setup a timer to call update_timer() every 100 ms
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(100)

    def initUI(self):
        self.setWindowTitle("Workout Timer")
        self.setGeometry(100, 100, 450, 450)
        # self.setMinimumSize(300, 300)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)

        # Fonts
        font_heading = QFont()
        font_heading.setPointSize(24)
        font_label = QFont()
        font_label.setPointSize(18)
        font_button = QFont()
        font_button.setPointSize(20)
        font_button_small = QFont()
        font_button_small.setPointSize(9)

        # Heading
        self.heading = QLabel("Workout Interval Timer")
        self.heading.setFont(font_heading)
        layout.addWidget(self.heading)

        # Sliders and text boxes for settings
        for label_text, attr in [("Workout (sec)", 'workout_duration'),
                                 ("Rest (sec)", 'rest_duration'),
                                 ("Rounds", 'rounds'),
                                 ("Lead-up (sec)", 'lead_up_duration')]:
            hbox = QHBoxLayout()
            label = QLabel(label_text)
            hbox.addWidget(label)

            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(2 if 'duration' in attr else 1)
            slider.setMaximum(180 if attr == 'workout_duration' else 90 if attr == 'rest_duration' else 50 if attr == 'rounds' else 10)
            slider.setValue(getattr(self, attr))
            slider.setMinimumWidth(240)
            slider.valueChanged.connect(self.slider_changed)
            setattr(self, f"{attr}_slider", slider)
            slider.setStyleSheet("""
                QSlider::groove:horizontal {
                    height: 15px;
                    margin: 0px;
                }
                QSlider::handle:horizontal {
                    background: #222;
                    border: 2px solid #555;
                    width: 18px;
                }
                QSlider::handle:horizontal:hover {
                    background: #888;
                }
            """)
                                 
            hbox.addWidget(slider)

            text_box = QLineEdit()
            text_box.setFixedWidth(50)
            text_box.setText(str(getattr(self, attr)))
            text_box.setValidator(QIntValidator(slider.minimum(), slider.maximum()))
            text_box.editingFinished.connect(lambda attr=attr, text_box=text_box: self.text_box_changed(attr, text_box))
            setattr(self, f"{attr}_text_box", text_box)
            hbox.addWidget(text_box)

            slider.valueChanged.connect(lambda value, text_box=text_box: text_box.setText(str(value)))
            layout.addLayout(hbox)

        # Buttons for control
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.start_button = QPushButton("Start")
        self.start_button.setFont(font_button)
        self.start_button.clicked.connect(self.start_timer)
        btn_layout.addWidget(self.start_button)

        self.pause_button = QPushButton("Pause")
        self.pause_button.setFont(font_button)
        self.pause_button.clicked.connect(self.pause_timer)
        btn_layout.addWidget(self.pause_button)

        self.resume_button = QPushButton("Resume")
        self.resume_button.setFont(font_button)
        self.resume_button.clicked.connect(self.resume_timer)
        btn_layout.addWidget(self.resume_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setFont(font_button)
        self.stop_button.clicked.connect(self.stop_timer)
        btn_layout.addWidget(self.stop_button)

        layout.addLayout(btn_layout)

        # Labels for status
        self.round_label = QLabel()
        self.round_label.setFont(font_label)
        layout.addWidget(self.round_label)
        self.state_label = QLabel()
        self.state_label.setFont(font_label)
        layout.addWidget(self.state_label)
        self.time_label = QLabel()
        self.time_label.setFont(font_label)
        layout.addWidget(self.time_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)

        layout.addSpacing(15)

        # Create horizontal layout for toggle buttons
        toggle_layout = QHBoxLayout()
        toggle_layout.setSpacing(10)

        # Add Always on Top toggle
        self.always_on_top = QPushButton("Always on Top")
        self.always_on_top.setCheckable(True)
        self.always_on_top.setFont(font_button_small)
        self.always_on_top.setFixedWidth(180)
        self.always_on_top.clicked.connect(self.toggle_always_on_top)
        self.always_on_top.setStyleSheet("""
            QPushButton {
                padding: 5px;
                border: 2px solid #666;
                border-radius: 15px;
                background-color: #444;
            }
            QPushButton:checked {
                background-color: #2a5699;
                border-color: #1a3b6d;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:checked:hover {
                background-color: #366bb8;
            }
        """)
        toggle_layout.addWidget(self.always_on_top)

        # Add Minimalist Mode toggle
        self.minimalist_button = QPushButton("Minimalist Mode")
        self.minimalist_button.setCheckable(True)
        self.minimalist_button.setFont(font_button_small)
        self.minimalist_button.setFixedWidth(180)
        self.minimalist_button.clicked.connect(self.toggle_minimalist_mode)
        self.minimalist_button.setStyleSheet("""
            QPushButton {
                padding: 5px;
                border: 2px solid #666;
                border-radius: 15px;
                background-color: #444;
            }
            QPushButton:checked {
                background-color: #2a5699;
                border-color: #1a3b6d;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:checked:hover {
                background-color: #366bb8;
            }
        """)
        toggle_layout.addWidget(self.minimalist_button)

        # Add toggle layout to main layout
        layout.addLayout(toggle_layout)
        
        # Fanfare display
        self.fanfare_label = QLabel()
        self.fanfare_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.fanfare_label)
        self.star_pixmap = QPixmap("star.png")

        # Initial UI update
        self.update_ui_elements()

    def text_box_changed(self, attr, text_box):
        try:
            value = int(text_box.text())
            slider = getattr(self, f"{attr}_slider")
            slider.setValue(value)
            setattr(self, attr, value)
            self.settings = Settings(self.workout_duration, self.rest_duration, self.rounds, self.lead_up_duration)
            self.settings.save_to_file()
        except ValueError:
            pass

    def slider_changed(self):
        self.workout_duration = self.workout_duration_slider.value()
        self.rest_duration = self.rest_duration_slider.value()
        self.rounds = self.rounds_slider.value()
        self.lead_up_duration = self.lead_up_duration_slider.value()
        self.settings = Settings(self.workout_duration, self.rest_duration, self.rounds, self.lead_up_duration)
        self.settings.save_to_file()

    def start_timer(self):
        self.current_round = 0
        if self.lead_up_duration > 0:
            self.state = TimerState.LeadUp
            self.remaining_time = self.lead_up_duration
        else:
            self.state = TimerState.Workout
            self.remaining_time = self.workout_duration
        self.start_time = time.monotonic()
        self.pause_elapsed = 0
        self.update_ui_elements()

    def pause_timer(self):
        if self.start_time is None:
            return
        elapsed = time.monotonic() - self.start_time
        if self.state == TimerState.LeadUp:
            self.state = TimerState.PausedLeadUp
        elif self.state == TimerState.Workout:
            self.state = TimerState.PausedWorkout
        elif self.state == TimerState.Rest:
            self.state = TimerState.PausedRest
        self.pause_elapsed = elapsed
        self.start_time = None
        self.update_ui_elements()

    def resume_timer(self):
        if self.state not in [TimerState.PausedLeadUp, TimerState.PausedWorkout, TimerState.PausedRest]:
            return
        # Compute new start_time to account for paused duration
        if self.state == TimerState.PausedLeadUp:
            self.remaining_time = max(self.lead_up_duration - int(self.pause_elapsed), 0)
            self.state = TimerState.LeadUp
            total = self.lead_up_duration
        elif self.state == TimerState.PausedWorkout:
            self.remaining_time = max(self.workout_duration - int(self.pause_elapsed), 0)
            self.state = TimerState.Workout
            total = self.workout_duration
        else:
            self.remaining_time = max(self.rest_duration - int(self.pause_elapsed), 0)
            self.state = TimerState.Rest
            total = self.rest_duration
        self.start_time = time.monotonic() - self.pause_elapsed
        self.pause_elapsed = 0
        self.update_ui_elements()

    def stop_timer(self):
        self.state = TimerState.Idle
        self.start_time = None
        self.remaining_time = 0
        self.current_round = 0
        self.update_ui_elements()

    def play_sound(self, is_work: bool, is_complete: bool):
        try:
            if is_complete:
                audio_file = self.complete_finish_audio
            elif is_work:
                audio_file = self.work_finish_audio
            else:
                audio_file = self.rest_finish_audio
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
        except Exception as e:
            print("Error playing sound:", e)

    def trigger_visual_fanfare(self):
        self.fanfare_start_time = time.monotonic()

    def toggle_always_on_top(self):
        if self.always_on_top.isChecked():
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()  # show the window again

    def toggle_minimalist_mode(self):
        if not self.minimalist_mode:  # Entering minimalist mode
            self.minimalist_mode = True
            if not self.minimalist_widget:
                self.minimalist_widget = MinimalistWidget(self)
                self.minimalist_widget.move(self.x(), self.y())
            self.minimalist_widget.show()
            self.hide()
            self.minimalist_button.setChecked(True)
        else:  # Exiting minimalist mode
            self.minimalist_mode = False
            if self.minimalist_widget:
                self.minimalist_widget.hide()
            self.show()
            self.minimalist_button.setChecked(False)

    def update_timer(self):
        # Timing logic
        if self.start_time is not None:
            elapsed = int(time.monotonic() - self.start_time)
            if self.state == TimerState.LeadUp:
                self.remaining_time = max(self.lead_up_duration - elapsed, 0)
                if elapsed >= self.lead_up_duration:
                    self.state = TimerState.Workout
                    self.start_time = time.monotonic()
                    self.remaining_time = self.workout_duration
            elif self.state == TimerState.Workout:
                self.remaining_time = max(self.workout_duration - elapsed, 0)
                if elapsed >= self.workout_duration:
                    self.state = TimerState.Rest
                    self.start_time = time.monotonic()
                    self.remaining_time = self.rest_duration
                    self.play_sound(is_work=True, is_complete=False)
            elif self.state == TimerState.Rest:
                self.remaining_time = max(self.rest_duration - elapsed, 0)
                if elapsed >= self.rest_duration:
                    if self.current_round + 1 < self.rounds:
                        self.current_round += 1
                        self.state = TimerState.Workout
                        self.start_time = time.monotonic()
                        self.remaining_time = self.workout_duration
                        self.play_sound(is_work=False, is_complete=False)
                    else:
                        self.state = TimerState.Idle
                        self.start_time = None
                        self.current_round = 0
                        self.play_sound(is_work=False, is_complete=True)
                        self.trigger_visual_fanfare()

        # GUI updates
        self.update_ui_elements()

        # Visual fanfare
        if self.fanfare_start_time:
            elapsed_fan = time.monotonic() - self.fanfare_start_time
            if elapsed_fan < 2.0:
                angle = elapsed_fan * 360
                transform = QTransform().rotate(angle)
                rotated = self.star_pixmap.transformed(transform, Qt.SmoothTransformation)
                self.fanfare_label.setPixmap(rotated)
                self.fanfare_label.setText(f"Congratulations, you completed {self.rounds} rounds!")
            else:
                self.fanfare_start_time = None
                self.fanfare_label.clear()

    def update_ui_elements(self):
        # Update labels
        self.round_label.setText(f"Round: {self.current_round + 1}/{self.rounds}")
        self.state_label.setText(f"State: {self.state.name}")
        mins, secs = divmod(self.remaining_time, 60)
        self.time_label.setText(f"Time remaining: {mins:02}:{secs:02}")

        # Progress bar value & color
        if self.state in [TimerState.LeadUp, TimerState.PausedLeadUp]:
            prog = 1.0 - (self.remaining_time / self.lead_up_duration) if self.lead_up_duration else 1.0
            color = "#FFA500"  # Orange
        elif self.state in [TimerState.Workout, TimerState.PausedWorkout]:
            prog = 1.0 - (self.remaining_time / self.workout_duration)
            color = "#3BA458"  # Green
        elif self.state in [TimerState.Rest, TimerState.PausedRest]:
            prog = 1.0 - (self.remaining_time / self.rest_duration)
            color = "#3877A2"  # Blue
        else:
            prog = 0.0
            color = "#3D3D3D"  # Gray
        self.progress_bar.setValue(int(prog * 100))
        self.progress_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; }}")

        # Button visibility
        self.start_button.setVisible(self.state == TimerState.Idle)
        self.pause_button.setVisible(self.state in [TimerState.LeadUp, TimerState.Workout, TimerState.Rest])
        self.resume_button.setVisible(self.state in [TimerState.PausedLeadUp, TimerState.PausedWorkout, TimerState.PausedRest])
        self.stop_button.setVisible(self.state != TimerState.Idle)

        # Update Minimalist Widget color
        if self.minimalist_mode and self.minimalist_widget:
            if self.state in [TimerState.LeadUp, TimerState.PausedLeadUp]:
                self.minimalist_widget.color = QColor("#FFA500")
            elif self.state in [TimerState.Workout, TimerState.PausedWorkout]:
                self.minimalist_widget.color = QColor("#3BA458")
            elif self.state in [TimerState.Rest, TimerState.PausedRest]:
                self.minimalist_widget.color = QColor("#3877A2")
            else:
                self.minimalist_widget.color = QColor("#3D3D3D")
            self.minimalist_widget.update()


if __name__ == "__main__":
    # Theme setup
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

    # Load the style.qss file
    style_file = resource_path("style.qss")
    with open(style_file, "r") as f:
        app.setStyleSheet(f.read())

    # Create the application and main window
    window = WorkoutTimer()
    window.show()
    sys.exit(app.exec_())
