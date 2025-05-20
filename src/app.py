import time
import pygame
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QProgressBar,
    QLineEdit
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import (
    QPixmap, QTransform, QFont, QIntValidator,
    QColor, QIcon
)

from .utils import resource_path
from .config import Settings
from .timer_state import TimerState
from .widgets import MinimalistWidget

class WorkoutTimer(QMainWindow):
    def __init__(self):
        super().__init__()
        # --- Settings & State ---
        self.settings = Settings.load_from_file()
        self.workout_duration   = self.settings.workout_duration
        self.rest_duration      = self.settings.rest_duration
        self.lead_up_duration   = self.settings.lead_up_duration
        self.rounds             = self.settings.rounds
        self.current_round      = 0
        self.remaining_time     = 0
        self.state              = TimerState.Idle
        self.start_time         = None
        self.fanfare_start_time = None
        self.pause_elapsed      = 0

        # --- Audio ---
        pygame.mixer.init()
        self.work_finish_audio     = "work_finish.mp3"
        self.rest_finish_audio     = "rest_finish.mp3"
        self.complete_finish_audio = "complete_finish.mp3"

        # --- Minimalist mode ---
        self.minimalist_mode        = False
        self.minimalist_widget      = None

        # --- UI setup ---
        self.initUI()

        # apply initial toggles
        if self.settings.always_on_top:
            self.toggle_always_on_top()
        if self.settings.minimize_after_complete:
            self.minimize_after_complete_toggle.setChecked(True)

        # timer loop
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(100)

    def initUI(self):
        self.setWindowTitle("Workout Timer")
        self.setWindowIcon(QIcon(resource_path("icon.ico")))
        self.setGeometry(100, 100, 450, 450)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)

        # Fonts
        font_heading = QFont(); font_heading.setPointSize(24)
        font_label   = QFont(); font_label.setPointSize(18)
        font_button  = QFont(); font_button.setPointSize(20)
        font_small   = QFont(); font_small.setPointSize(9)

        # Heading
        self.heading = QLabel("Workout Interval Timer")
        self.heading.setFont(font_heading)
        layout.addWidget(self.heading)

        # Sliders + TextBoxes
        for text, attr in [
            ("Workout (sec)", "workout_duration"),
            ("Rest (sec)",    "rest_duration"),
            ("Rounds",        "rounds"),
            ("Lead-up (sec)", "lead_up_duration"),
        ]:
            h = QHBoxLayout()
            lbl = QLabel(text)
            h.addWidget(lbl)

            slider = QSlider(Qt.Horizontal)
            minv = 2 if "duration" in attr else 1
            maxv = (
                180 if attr=="workout_duration" else
                 90 if attr=="rest_duration" else
                 50 if attr=="rounds" else
                 10
            )
            slider.setMinimum(minv)
            slider.setMaximum(maxv)
            slider.setValue(getattr(self, attr))
            slider.setPageStep(1)
            slider.setMinimumWidth(240)
            slider.valueChanged.connect(self.slider_changed)
            setattr(self, f"{attr}_slider", slider)
            slider.setStyleSheet("""
                QSlider::groove:horizontal { height:15px; margin:0; }
                QSlider::handle:horizontal { background:#222; border:2px solid #555; width:18px; }
                QSlider::handle:horizontal:hover { background:#888; }
            """)
            h.addWidget(slider)

            tb = QLineEdit(str(getattr(self, attr)))
            tb.setFixedWidth(50)
            tb.setValidator(QIntValidator(minv, maxv))
            tb.editingFinished.connect(lambda a=attr, t=tb: self.text_box_changed(a, t))
            setattr(self, f"{attr}_text_box", tb)
            slider.valueChanged.connect(lambda v, t=tb: t.setText(str(v)))
            h.addWidget(tb)

            layout.addLayout(h)

        # Control Buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        self.start_button  = QPushButton("Start");  self.start_button.setFont(font_button);  self.start_button.clicked.connect(self.start_timer);  btn_row.addWidget(self.start_button)
        self.pause_button  = QPushButton("Pause");  self.pause_button.setFont(font_button);  self.pause_button.clicked.connect(self.pause_timer);  btn_row.addWidget(self.pause_button)
        self.resume_button = QPushButton("Resume"); self.resume_button.setFont(font_button); self.resume_button.clicked.connect(self.resume_timer); btn_row.addWidget(self.resume_button)
        self.stop_button   = QPushButton("Stop");   self.stop_button.setFont(font_button);   self.stop_button.clicked.connect(self.stop_timer);   btn_row.addWidget(self.stop_button)
        layout.addLayout(btn_row)

        # Status Labels & ProgressBar
        self.round_label = QLabel(); self.round_label.setFont(font_label); layout.addWidget(self.round_label)
        self.state_label = QLabel(); self.state_label.setFont(font_label); layout.addWidget(self.state_label)
        self.time_label  = QLabel(); self.time_label.setFont(font_label);  layout.addWidget(self.time_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)

        layout.addSpacing(15)

        # Toggle Buttons row 1
        row1 = QHBoxLayout(); row1.setSpacing(10)
        # Always on Top
        self.always_on_top = QPushButton("Always on Top")
        self.always_on_top.setCheckable(True)
        self.always_on_top.setChecked(self.settings.always_on_top)
        self.always_on_top.setFont(font_small)
        self.always_on_top.setFixedWidth(180)
        self.always_on_top.clicked.connect(self.toggle_always_on_top)
        self.always_on_top.setStyleSheet("""
            QPushButton { padding:5px; border:2px solid #666; border-radius:15px; background-color:#444; }
            QPushButton:checked { background-color:#2a5699; border-color:#1a3b6d; }
            QPushButton:hover { background-color:#555; }
            QPushButton:checked:hover { background-color:#366bb8; }
        """)
        row1.addWidget(self.always_on_top)

        # Minimize after complete
        self.minimize_after_complete_toggle = QPushButton("Minimize After Complete")
        self.minimize_after_complete_toggle.setCheckable(True)
        self.minimize_after_complete_toggle.setFont(font_small)
        self.minimize_after_complete_toggle.setFixedWidth(180)
        self.minimize_after_complete_toggle.clicked.connect(self.toggle_minimize_after_complete)
        self.minimize_after_complete_toggle.setStyleSheet(self.always_on_top.styleSheet())
        row1.addWidget(self.minimize_after_complete_toggle)

        layout.addLayout(row1)

        # Toggle Buttons row 2
        row2 = QHBoxLayout()
        self.minimalist_button = QPushButton("Minimalist Mode")
        self.minimalist_button.setCheckable(True)
        self.minimalist_button.setFont(font_small)
        self.minimalist_button.setFixedWidth(180)
        self.minimalist_button.clicked.connect(self.toggle_minimalist_mode)
        self.minimalist_button.setStyleSheet(self.always_on_top.styleSheet())
        row2.addWidget(self.minimalist_button)

        layout.addLayout(row2)

        # Fanfare
        self.fanfare_label = QLabel(); self.fanfare_label.setAlignment(Qt.AlignCenter); layout.addWidget(self.fanfare_label)
        self.star_pixmap = QPixmap("star.png")

        # Final UI sync
        self.update_ui_elements()

    # --- Event handlers for sliders/textboxes ---
    def text_box_changed(self, attr, text_box):
        try:
            val = int(text_box.text())
            getattr(self, f"{attr}_slider").setValue(val)
            setattr(self, attr, val)
            self._save_settings()
        except ValueError:
            pass

    def slider_changed(self):
        self.workout_duration = self.workout_duration_slider.value()
        self.rest_duration    = self.rest_duration_slider.value()
        self.rounds           = self.rounds_slider.value()
        self.lead_up_duration = self.lead_up_duration_slider.value()
        self._save_settings()

    def _save_settings(self):
        self.settings = Settings(
            workout_duration=self.workout_duration,
            rest_duration=self.rest_duration,
            lead_up_duration=self.lead_up_duration,
            rounds=self.rounds,
            minimalist_mode_size=self.settings.minimalist_mode_size,
            always_on_top=self.settings.always_on_top,
            minimize_after_complete=self.settings.minimize_after_complete
        )
        self.settings.save_to_file()

    # --- Timer controls ---
    def start_timer(self):
        self.current_round = 0
        if self.lead_up_duration > 0:
            self.state = TimerState.LeadUp
            self.remaining_time = self.lead_up_duration
        else:
            self.state = TimerState.Workout
            self.remaining_time = self.workout_duration
        self.start_time    = time.monotonic()
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
        self.paused_time_left = self.remaining_time
        self.start_time = None
        self.update_ui_elements()

    def resume_timer(self):
        if self.state not in (
            TimerState.PausedLeadUp,
            TimerState.PausedWorkout,
            TimerState.PausedRest
        ):
            return
        if self.state == TimerState.PausedLeadUp:
            self.remaining_time = max(self.lead_up_duration - int(self.pause_elapsed), 0)
            self.state = TimerState.LeadUp
        elif self.state == TimerState.PausedWorkout:
            self.remaining_time = max(self.workout_duration - int(self.pause_elapsed), 0)
            self.state = TimerState.Workout
        else:
            self.remaining_time = max(self.rest_duration - int(self.pause_elapsed), 0)
            self.state = TimerState.Rest

        self.start_time = time.monotonic() - self.pause_elapsed
        self.pause_elapsed = 0
        self.update_ui_elements()

    def stop_timer(self):
        self.state = TimerState.Idle
        self.start_time = None
        self.remaining_time = 0
        self.current_round = 0
        self.update_ui_elements()

    def play_sound(self, is_work: bool, is_all_complete: bool):
        try:
            if is_all_complete:
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

    # --- Toggles ---
    def toggle_always_on_top(self):
        self.settings.always_on_top = self.always_on_top.isChecked()
        self.settings.save_to_file()
        if self.settings.always_on_top:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

    def toggle_minimize_after_complete(self):
        self.settings.minimize_after_complete = self.minimize_after_complete_toggle.isChecked()
        self.settings.save_to_file()

    def toggle_minimalist_mode(self):
        if not self.minimalist_mode:
            self.minimalist_mode = True
            if not self.minimalist_widget:
                self.minimalist_widget = MinimalistWidget(self)
                self.minimalist_widget.move(self.x(), self.y())
            self.minimalist_widget.show()
            self.hide()
            self.minimalist_button.setChecked(True)
        else:
            self.minimalist_mode = False
            if self.minimalist_widget:
                self.minimalist_widget.hide()
            self.show()
            self.minimalist_button.setChecked(False)

    def toggle_round_display(self):
        # Get the current round number and total number of rounds
        current_round = self.current_round
        total_rounds = self.rounds
        
        # Calculate the number of rounds left
        rounds_left = total_rounds - current_round
        
        # Display the number of rounds left in the minimalist mode widget
        if not hasattr(self, 'rounds_left_label'):
            self.rounds_left_label = QLabel()
            self.layout().addWidget(self.rounds_left_label)
        self.rounds_left_label.setText(f"{rounds_left}")

    def toggle_time_display(self):
        # Get the current time remaining
        current_time = self.remaining_time
        
        # Convert the time remaining to minutes and seconds
        mins, secs = divmod(current_time, 60)
        
        # Display the time remaining in the minimalist mode widget
        self.time_remaining_label = QLabel(f"{mins:02}:{secs:02}")
        self.layout().addWidget(self.time_remaining_label)

    # will toggle between the default circle shape of minimalist mode and a floating progress bar
    def toggle_shape(self):
        # Get the current shape of the minimalist mode widget
        if self.minimalist_widget.shape == "circle":
            # Change to floating progress bar
            self.minimalist_widget.shape = "floating_progress_bar"
            self.minimalist_widget.setStyleSheet("background-color: transparent;")
        else:
            # Change back to circle shape
            self.minimalist_widget.shape = "circle"
            self.minimalist_widget.setStyleSheet("background-color: transparent;")

        # Update the minimalist mode widget
        self.minimalist_widget.update()

    # --- Main timer loop & UI refresh ---
    def update_timer(self):
        if self.start_time is not None:
            elapsed = int(time.monotonic() - self.start_time)
            # Lead-up
            if self.state == TimerState.LeadUp:
                self.remaining_time = max(self.lead_up_duration - elapsed, 0)
                if elapsed >= self.lead_up_duration:
                    self.state = TimerState.Workout
                    self.start_time = time.monotonic()
                    self.remaining_time = self.workout_duration
                    self.play_sound(is_work=False, is_all_complete=False)

            # Workout
            elif self.state == TimerState.Workout:
                self.remaining_time = max(self.workout_duration - elapsed, 0)
                if elapsed >= self.workout_duration:
                    self.state = TimerState.Rest
                    self.start_time = time.monotonic()
                    self.remaining_time = self.rest_duration
                    self.play_sound(is_work=True, is_all_complete=False)

            # Rest
            elif self.state == TimerState.Rest:
                self.remaining_time = max(self.rest_duration - elapsed, 0)
                if elapsed >= self.rest_duration:
                    if self.current_round + 1 < self.rounds:
                        self.current_round += 1
                        self.state = TimerState.Workout
                        self.start_time = time.monotonic()
                        self.remaining_time = self.workout_duration
                        self.play_sound(is_work=False, is_all_complete=False)
                    else:
                        self.state = TimerState.Idle
                        self.start_time = None
                        self.current_round = 0
                        self.play_sound(is_work=False, is_all_complete=True)
                        self.trigger_visual_fanfare()
                        if self.minimize_after_complete_toggle.isChecked():
                            self.showMinimized()

        # refresh UI
        self.update_ui_elements()

        # visual fanfare
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
        # labels
        self.round_label.setText(f"Round: {self.current_round+1}/{self.rounds}")
        self.state_label.setText(f"State: {self.state.name}")
        mins, secs = divmod(self.remaining_time, 60)
        self.time_label.setText(f"Time remaining: {mins:02}:{secs:02}")

        # progress styling
        orange, green, blue, gray = "#E29A14", "#16A33E", "#1273B5", "#5A5177"
        if self.state in (TimerState.LeadUp, TimerState.PausedLeadUp):
            prog = 1 - (self.remaining_time/self.lead_up_duration) if self.lead_up_duration else 1
            color = orange
        elif self.state in (TimerState.Workout, TimerState.PausedWorkout):
            prog = 1 - (self.remaining_time/self.workout_duration)
            color = green
        elif self.state in (TimerState.Rest, TimerState.PausedRest):
            prog = 1 - (self.remaining_time/self.rest_duration)
            color = blue
        else:
            prog = 0
            color = gray

        self.progress_bar.setValue(int(prog*100))
        self.progress_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; }}")

        # button visibility
        self.start_button.setVisible(self.state == TimerState.Idle)
        self.pause_button.setVisible(self.state in (TimerState.LeadUp, TimerState.Workout, TimerState.Rest))
        self.resume_button.setVisible(self.state in (TimerState.PausedLeadUp, TimerState.PausedWorkout, TimerState.PausedRest))
        self.stop_button.setVisible(self.state != TimerState.Idle)

        # minimalist color sync
        if self.minimalist_mode and self.minimalist_widget:
            self.minimalist_widget.color = QColor(color)
            self.minimalist_widget.update()
