# type: ignore
import time
import pygame
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QApplication, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QProgressBar,
    QLineEdit, QToolTip, QMenu, QAction, QSizePolicy, QSystemTrayIcon
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import (
    QFont, QIntValidator, QColor, QIcon, QCursor
)
from .utils import resource_path
from .config import Config
from .timer_state import TimerState
from .widgets import MinimalistWidget

QToolTip.showTime = 4000  # Set tooltip display time

class WorkoutTimer(QMainWindow):
    def __init__(self):
        """Initialize the Workout Timer application."""
        super().__init__()
        # --- Settings from settings.json ---
        self.settings = Config.load_from_file()
        self.minimalist_widget = None
        # Tray icon (created lazily when needed)
        self.tray_icon = None

        # --- Status Bar (pre-created to avoid layout jump when messages appear)
        self.status_bar = self.statusBar()  # create once so central widget always reserves space
        self.status_bar.setFixedHeight(22)  # keep constant height to prevent squeezing
        self.status_bar.clearMessage()

        # --- Timer State ---
        self.current_round = 0
        self.remaining_time = 0
        self.state = TimerState.Idle
        self.start_time = None
        self.fanfare_start_time = None
        self.paused_time = 0 

        # --- Audio ---
        pygame.mixer.init()
        self.work_finish_audio     = resource_path("work_finish.mp3")
        self.rest_finish_audio     = resource_path("rest_finish.mp3")
        self.complete_finish_audio = resource_path("complete_finish.mp3")


        #####################################
        # UI Setup
        #####################################
        self.initUI()

        # --- Timer Loop ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(100)

    def initUI(self):
        self.setWindowTitle("Workout Timer")
        self.setWindowIcon(QIcon(resource_path("icon.ico")))
        self.setGeometry(100, 100, 400, 550)
        self.setMinimumSize(400, 540)  # Allow smaller minimum size

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)

        # Fonts
        font_heading = QFont(); font_heading.setPointSize(24)
        font_label   = QFont(); font_label.setPointSize(18)
        font_button  = QFont(); font_button.setPointSize(20); font_button.setBold(True)
        font_toggle   = QFont(); font_toggle.setPointSize(9)

        # --- Preset Dropdown Button ---
        preset_row = QHBoxLayout()
        # Fanfare: Visual fanfare message (placed to the left of the preset button)
        self.fanfare_label = QLabel()
        # Align left within the row
        self.fanfare_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        preset_row.addWidget(self.fanfare_label)
        # Spacer pushes the preset button to the far right
        preset_row.addStretch()
        self.preset_button = QPushButton("☰")
        self.preset_button.setFixedWidth(50)
        self.preset_button.setFixedHeight(25)
        self.preset_button.setToolTip("Presets: Save or load up to 3 timer settings")
        self.preset_menu = QMenu(self)
        # Add actions for 3 slots
        self.preset_actions = []
        for i in range(3):
            load_action = QAction(f"Load Preset {i+1}", self)
            save_action = QAction(f"Save Current to Preset {i+1}", self)
            self.preset_menu.addAction(load_action)
            self.preset_menu.addAction(save_action)
            if i < 2:
                self.preset_menu.addSeparator()
            load_action.triggered.connect(lambda _, idx=i: self.load_preset(idx))
            save_action.triggered.connect(lambda _, idx=i: self.save_preset(idx))
            self.preset_actions.append((load_action, save_action))
        self.preset_button.setMenu(self.preset_menu)
        # Show tooltips when hovering over menu actions
        self.preset_menu.hovered.connect(self._show_preset_action_tooltip)
        # Update tooltips and enabled states based on saved presets
        self.update_preset_tooltips()
        preset_row.addWidget(self.preset_button)
        layout.addLayout(preset_row)

        # Sliders + TextBoxes: Workout, Rest, Rounds, Lead-up
        for text, attr in [
            ("Workout (sec)", "workout_duration"),
            ("Rest (sec)",    "rest_duration"),
            ("Rounds",        "rounds"),
            ("Lead-up (sec)", "lead_up_duration"),
        ]:
            h = QHBoxLayout()
            lbl = QLabel(text)
            lbl.setMinimumWidth(80)
            lbl.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
            h.addWidget(lbl)

            # Set ranges(min, max) for each slider
            slider = QSlider(Qt.Horizontal)
            minv = (
                2 if attr=="workout_duration" else
                 2 if attr=="rest_duration" else
                 1 if attr=="rounds" else
                 0 if attr=="lead_up_duration" 
                else 0
            )
            maxv = (
                180 if attr=="workout_duration" else
                 90 if attr=="rest_duration" else
                 50 if attr=="rounds" else
                 30 if attr=="lead_up_duration"
                else 100
            )
            slider.setMinimum(minv)
            slider.setMaximum(maxv)
            slider.setValue(getattr(self.settings, attr))
            slider.setPageStep(1)
            slider.setMinimumWidth(120)  # Reduced from 240 for better scaling
            slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            slider.valueChanged.connect(self.slider_changed)
            setattr(self, f"{attr}_slider", slider)
            slider.setStyleSheet("""
                QSlider::groove:horizontal { height:15px; margin:0; }
                QSlider::handle:horizontal { background:#222; border:2px solid #555; width:18px; }
                QSlider::handle:horizontal:hover { background:#888; }
            """)
            h.addWidget(slider)

            tb = QLineEdit(str(getattr(self.settings, attr)))
            tb.setFixedWidth(50)
            tb.setValidator(QIntValidator(minv, maxv))
            tb.editingFinished.connect(lambda a=attr, t=tb: self.text_box_changed(a, t))
            setattr(self, f"{attr}_text_box", tb)
            slider.valueChanged.connect(lambda v, t=tb: t.setText(str(v)))
            h.addWidget(tb)

            layout.addLayout(h)
        
        # Control Buttons: Start, Pause, Resume, Stop
        control_button_height = 40
        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        # Start button
        self.start_button  = QPushButton("Start");  self.start_button.setFont(font_button);  
        self.start_button.clicked.connect(self.start_timer);  btn_row.addWidget(self.start_button)
        self.start_button.setToolTip("Start the timer with current settings")
        self.start_button.setFixedHeight(control_button_height)
        # Pause button
        self.pause_button  = QPushButton("Pause");  self.pause_button.setFont(font_button);  
        self.pause_button.clicked.connect(self.pause_timer);  btn_row.addWidget(self.pause_button)
        self.pause_button.setToolTip("Pause the timer")
        self.pause_button.setFixedHeight(control_button_height)
        # Resume button
        self.resume_button = QPushButton("Resume"); self.resume_button.setFont(font_button); 
        self.resume_button.clicked.connect(self.resume_timer); btn_row.addWidget(self.resume_button)
        self.resume_button.setToolTip("Resume the timer from a paused state")
        self.resume_button.setFixedHeight(control_button_height)
        # Stop button
        self.stop_button   = QPushButton("Stop");   self.stop_button.setFont(font_button); 
        self.stop_button.clicked.connect(self.stop_timer);   btn_row.addWidget(self.stop_button)
        self.stop_button.setToolTip("Stop the timer and reset all states")
        self.stop_button.setFixedHeight(control_button_height)
        # Add buttons to layout
        layout.addLayout(btn_row)

        # Add margin above status labels
        layout.addSpacing(10)

        # Status Labels & ProgressBar: Round, State, Time Remaining
        self.round_label = QLabel(); self.round_label.setFont(font_label); layout.addWidget(self.round_label)
        self.state_label = QLabel(); self.state_label.setFont(font_label); layout.addWidget(self.state_label)
        self.time_label  = QLabel(); self.time_label.setFont(font_label);  layout.addWidget(self.time_label)
        # Need to prevent cropping of time label
        self.time_label.setFixedHeight(38)

        # Add margin above progress bar
        layout.addSpacing(10)

        # ProgressBar: Progress of the timer
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)

        layout.addSpacing(15)

        # Toggle Buttons row 1: Always on Top, Minimize After Complete
        row1 = QHBoxLayout(); row1.setSpacing(10)
        # Always on Top
        self.always_on_top = QPushButton("Always on Top")
        self.always_on_top.setCheckable(True)
        self.always_on_top.setChecked(self.settings.always_on_top)
        self.always_on_top.setFont(font_toggle)
        self.always_on_top.clicked.connect(self.toggle_always_on_top)
        self.always_on_top.setToolTip("Keep the timer window always on top of other windows")
        self.always_on_top.setStyleSheet("""
            QPushButton { padding:5px; solid #666; background-color:#444; }
            QPushButton:checked { background-color:#2a5699; border-color:#1a3b6d; }
            QPushButton:hover { background-color:#555; }
            QPushButton:checked:hover { background-color:#366bb8; }
        """)
        row1.addWidget(self.always_on_top)

        # Minimize after complete
        self.minimize_after_complete_toggle = QPushButton("Minimize After Complete")
        self.minimize_after_complete_toggle.setCheckable(True)
        self.minimize_after_complete_toggle.setFont(font_toggle)
        self.minimize_after_complete_toggle.clicked.connect(self.toggle_minimize_after_complete)
        self.minimize_after_complete_toggle.setToolTip("Minimize the timer window after completing all rounds")
        self.minimize_after_complete_toggle.setStyleSheet(self.always_on_top.styleSheet())
        row1.addWidget(self.minimize_after_complete_toggle)

        layout.addLayout(row1)

        # Toggle Buttons row 2: Minimalist Mode
        row2 = QHBoxLayout()
        self.minimalist_button = QPushButton("Minimalist Mode")
        self.minimalist_button.setCheckable(True)
        self.minimalist_button.setFont(font_toggle)
        self.minimalist_button.clicked.connect(self.toggle_minimalist_mode)
        self.minimalist_button.setToolTip("Switch to minimalist mode for a smaller and cleaner interface\n(cannot set sliders/textboxes in this mode)")
        self.minimalist_button.setStyleSheet(self.always_on_top.styleSheet())
        row2.addWidget(self.minimalist_button)

        layout.addLayout(row2)

        # Final UI sync
        self.apply_initial_toggles()
        self.update_ui_elements()


    ###############################################
    # For intializing toggles from settings.json
    ###############################################
    def apply_initial_toggles(self):
        """Apply initial toggles from settings.json"""
        if self.settings.always_on_top:
            self.always_on_top.setChecked(True)
        if self.settings.minimize_after_complete:
            self.minimize_after_complete_toggle.setChecked(True)
        if self.settings.minimalist_mode_active:
            # Defer minimalist mode activation until after event loop starts
            QTimer.singleShot(0, lambda: self.set_minimalist_mode(True))

    def set_minimalist_mode(self, enable: bool):
        """Show or hide minimalist mode and sync state/settings/UI."""
        self.settings.minimalist_mode_active = enable
        self.settings.save_to_file()
        if enable:
            if not self.minimalist_widget:
                self.minimalist_widget = MinimalistWidget(self)
                self.minimalist_widget.move(self.x(), self.y())
            self.minimalist_widget.setToolTip("Right-click for context menu\nDouble Left-click to exit minimalist mode")
            self.minimalist_widget.setToolTipDuration(2400)
            self.minimalist_widget.show()
            self.hide()
            # Ensure tray icon is visible while in minimalist mode
            self._show_tray_icon()
            self.minimalist_button.setChecked(True)
        else:
            if self.minimalist_widget:
                self.minimalist_widget.hide()
            self.show()
            # Hide tray icon when exiting minimalist mode
            if self.tray_icon:
                self.tray_icon.hide()
            self.minimalist_button.setChecked(False)


    #####################################
    # Event handlers for sliders/textboxes
    #####################################
    def text_box_changed(self, attr, text_box):
        """Update the slider and settings based on text box input."""
        try:
            val = int(text_box.text())
            getattr(self, f"{attr}_slider").setValue(val)
            setattr(self.settings, attr, val)
            self._save_settings()
        except ValueError:
            pass

    def slider_changed(self):
        """Update the settings based on slider values."""
        self.settings.workout_duration = self.workout_duration_slider.value()
        self.settings.rest_duration    = self.rest_duration_slider.value()
        self.settings.rounds           = self.rounds_slider.value()
        self.settings.lead_up_duration = self.lead_up_duration_slider.value()
        self._save_settings()

    def _save_settings(self):
        """Save the current settings to the settings.json file."""
        self.settings.save_to_file()


    #####################################
    # Timer controls 
    #####################################
    def start_timer(self):
        """Start the timer with initial settings."""
        self.current_round = 0
        if self.settings.lead_up_duration > 0:
            self.state = TimerState.LeadUp
            self.remaining_time = self.settings.lead_up_duration
        else:
            self.state = TimerState.Workout
            self.remaining_time = self.settings.workout_duration
        self.start_time = time.monotonic()
        self.paused_time = 0
        self.update_ui_elements()

    def pause_timer(self):
        """Pause the timer and save the elapsed time."""
        if self.start_time is None:
            return
        self.paused_time = time.monotonic() - self.start_time
        if self.state == TimerState.LeadUp:
            self.state = TimerState.PausedLeadUp
        elif self.state == TimerState.Workout:
            self.state = TimerState.PausedWorkout
        elif self.state == TimerState.Rest:
            self.state = TimerState.PausedRest
        self.start_time = None
        self.update_ui_elements()

    def resume_timer(self):
        """Resume the timer from a paused state."""
        if self.state not in (
            TimerState.PausedLeadUp,
            TimerState.PausedWorkout,
            TimerState.PausedRest
        ):
            return
        if self.state == TimerState.PausedLeadUp:
            self.state = TimerState.LeadUp
        elif self.state == TimerState.PausedWorkout:
            self.state = TimerState.Workout
        else:
            self.state = TimerState.Rest

        self.start_time = time.monotonic() - self.paused_time
        self.paused_time = 0
        self.update_ui_elements()

    def stop_timer(self):
        """Stop the timer and reset all states."""
        self.state = TimerState.Idle
        self.start_time = None
        self.remaining_time = 0
        self.current_round = 0
        self.update_ui_elements()

    def play_sound(self, is_work: bool, is_all_complete: bool):
        """Play the appropriate sound based on the timer state."""
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


    #####################################
    # Main Menu Toggle methods 
    #####################################
    def toggle_always_on_top(self):
        """Toggle the 'Always on Top' setting."""
        self.settings.always_on_top = self.always_on_top.isChecked()
        self.settings.save_to_file()
        if self.settings.always_on_top:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

    def toggle_minimize_after_complete(self):
        """Toggle the 'Minimize After Complete' setting."""
        self.settings.minimize_after_complete = self.minimize_after_complete_toggle.isChecked()
        self.settings.save_to_file()

    # Helper ------------------------------------------------------------
    def _minimize_after_complete(self):
        """Minimize either the main window or the minimalist widget based on current mode."""
        if self.settings.minimalist_mode_active and self.minimalist_widget:
            # Hide minimalist widget first (so it won't linger on screen)
            self.minimalist_widget.hide()
            # Minimize the main window instead – it will appear in taskbar properly
            # self.showMinimized()
            # Tray icon so user can restore
            self._show_tray_icon()
        else:
            self.showMinimized()
         
    def toggle_minimalist_mode(self):
        """Toggle the 'Minimalist Mode' setting."""
        new_value = not self.settings.minimalist_mode_active
        self.set_minimalist_mode(new_value)


    ############################################
    # Main timer loop
    ############################################
    def update_timer(self):
        """Main timer loop that updates the timer state and UI."""
        if self.start_time is not None:
            elapsed = int(time.monotonic() - self.start_time)
            # Lead-up
            if self.state == TimerState.LeadUp:
                self.remaining_time = max(self.settings.lead_up_duration - elapsed, 0)
                if elapsed >= self.settings.lead_up_duration:
                    self.state = TimerState.Workout
                    self.start_time = time.monotonic()
                    self.remaining_time = self.settings.workout_duration
                    self.play_sound(is_work=False, is_all_complete=False)

            # Workout
            elif self.state == TimerState.Workout:
                self.remaining_time = max(self.settings.workout_duration - elapsed, 0)
                if elapsed >= self.settings.workout_duration:
                    self.state = TimerState.Rest
                    self.start_time = time.monotonic()
                    self.remaining_time = self.settings.rest_duration
                    self.play_sound(is_work=True, is_all_complete=False)

            # Rest
            elif self.state == TimerState.Rest:
                self.remaining_time = max(self.settings.rest_duration - elapsed, 0)
                if elapsed >= self.settings.rest_duration:
                    if self.current_round + 1 < self.settings.rounds:
                        self.current_round += 1
                        self.state = TimerState.Workout
                        self.start_time = time.monotonic()
                        self.remaining_time = self.settings.workout_duration
                        self.play_sound(is_work=False, is_all_complete=False)
                    else:
                        self.state = TimerState.Idle
                        self.start_time = None
                        self.current_round = 0
                        self.play_sound(is_work=False, is_all_complete=True)
                        if not self.settings.minimalist_mode_active:
                            self.trigger_visual_fanfare()
                        if self.minimize_after_complete_toggle.isChecked():
                            self._minimize_after_complete()

        # refresh UI
        self.update_ui_elements()

        # visual fanfare
        if self.fanfare_start_time:
            elapsed_fanfare_time = time.monotonic() - self.fanfare_start_time
            if elapsed_fanfare_time < 2.0:
                self.fanfare_label.setText(f"Congratulations, you completed {self.settings.rounds} rounds!")
            else:
                self.fanfare_start_time = None
                self.fanfare_label.clear()
    

    #####################################
    # Update UI Elements
    #####################################
    def update_ui_elements(self):
        """Update all UI elements based on the current state."""
        # labels
        self.round_label.setText(f"Round: {self.current_round+1}/{self.settings.rounds}")
        self.state_label.setText(f"State: {self.state.name}")
        mins, secs = divmod(self.remaining_time, 60)
        self.time_label.setText(f"Time remaining: {mins:02}:{secs:02}")

        # progress styling
        orange, green, blue, gray = "#E29A14", "#16A33E", "#1273B5", "#5A5177"
        if self.state in (TimerState.LeadUp, TimerState.PausedLeadUp):
            prog = 1 - (self.remaining_time/self.settings.lead_up_duration) if self.settings.lead_up_duration else 1
            color = orange
        elif self.state in (TimerState.Workout, TimerState.PausedWorkout):
            prog = 1 - (self.remaining_time/self.settings.workout_duration)
            color = green
        elif self.state in (TimerState.Rest, TimerState.PausedRest):
            prog = 1 - (self.remaining_time/self.settings.rest_duration)
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

        # minimalist color & progress bar sync
        if self.settings.minimalist_mode_active and self.minimalist_widget:            
            if self.state in (TimerState.LeadUp, TimerState.PausedLeadUp):
                prog = 1 - (self.remaining_time/self.settings.lead_up_duration) if self.settings.lead_up_duration else 1
                color = orange
            elif self.state in (TimerState.Workout, TimerState.PausedWorkout):
                prog = 1 - (self.remaining_time/self.settings.workout_duration)
                color = green
            elif self.state in (TimerState.Rest, TimerState.PausedRest):
                prog = 1 - (self.remaining_time/self.settings.rest_duration)
                color = blue
            else:
                prog = 0
                color = gray

            # Update minimalist widget properties
            self.minimalist_widget.progress = prog
            self.minimalist_widget.active_color = QColor(color)
            self.minimalist_widget.current_state = self.state
            self.minimalist_widget.remaining_time = self.remaining_time
            self.minimalist_widget.current_round = self.current_round
            self.minimalist_widget.total_rounds = self.settings.rounds
            self.minimalist_widget.update()

    def save_preset(self, idx):
        """Save current timer settings to a preset slot."""
        preset = {
            "workout_duration": self.settings.workout_duration,
            "rest_duration": self.settings.rest_duration,
            "lead_up_duration": self.settings.lead_up_duration,
            "rounds": self.settings.rounds
        }
        self.settings.presets[idx] = preset
        self.settings.save_to_file()
        self.statusBar().showMessage(f"Preset {idx+1} saved!", 2000)
        # Refresh tooltips and enabled states
        self.update_preset_tooltips()

    def load_preset(self, idx):
        """Load timer settings from a preset slot."""
        preset = self.settings.presets[idx]
        if not preset:
            self.statusBar().showMessage(f"Preset {idx+1} is empty.", 2000)
            return
        # Update settings and UI
        for key in ["workout_duration", "rest_duration", "lead_up_duration", "rounds"]:
            setattr(self.settings, key, preset[key])
            slider = getattr(self, f"{key}_slider")
            text_box = getattr(self, f"{key}_text_box")
            slider.setValue(preset[key])
            text_box.setText(str(preset[key]))
        self.settings.save_to_file()
        self.statusBar().showMessage(f"Preset {idx+1} loaded!", 2000)
        self.update_ui_elements()
        # Ensure tooltips are up to date (in case preset was previously empty)
        self.update_preset_tooltips()

    # ---------------- Tray icon management ------------------
    def _show_tray_icon(self):
        """Create and display a system-tray icon for quick restore."""
        if self.tray_icon is None:
            icon_path = resource_path("icon.ico")
            self.tray_icon = QSystemTrayIcon(QIcon(icon_path), self)

            # Context menu for the tray icon
            tray_menu = QMenu()
            restore_action = tray_menu.addAction("Restore")
            restore_action.triggered.connect(self._restore_from_tray)
            exit_action = tray_menu.addAction("Exit")
            exit_action.triggered.connect(QApplication.quit)
            self.tray_icon.setContextMenu(tray_menu)

            # Double-click (or single depending on OS) also restores
            self.tray_icon.activated.connect(lambda reason: self._restore_from_tray() if reason == QSystemTrayIcon.Trigger else None)

        self.tray_icon.show()

    def _restore_from_tray(self):
        """Restore the timer from the tray icon."""
        if self.settings.minimalist_mode_active and self.minimalist_widget:
            self.minimalist_widget.show()
        else:
            self.showNormal()
        # Hide tray icon only if not remaining in minimalist mode
        if self.tray_icon and not self.settings.minimalist_mode_active:
            self.tray_icon.hide()

    def update_preset_tooltips(self):
        """Update tooltips and enabled state for preset actions."""
        for idx, (load_action, _save_action) in enumerate(self.preset_actions):
            preset = self.settings.presets[idx]
            normal_text = f"Load Preset {idx+1}"
            if preset:
                # Enabled + regular font
                load_action.setEnabled(True)
                load_action.setText(normal_text)
                normal_font = load_action.font()
                load_action.setFont(normal_font)
                tt = (
                    f"Workout: {preset['workout_duration']}s\n"
                    f"Rest: {preset['rest_duration']}s\n"
                    f"Lead-up: {preset['lead_up_duration']}s\n"
                    f"Rounds: {preset['rounds']}"
                )
                load_action.setToolTip(tt)
            else:
                # Disabled + dimmer text 
                load_action.setEnabled(True)
                load_action.setText(f"{normal_text} (empty)")
                normal_font = load_action.font()
                normal_font.setItalic(True)
                load_action.setFont(normal_font)
                load_action.setToolTip("(empty)")

    def _show_preset_action_tooltip(self, action):
        """Display tooltip for the hovered preset menu action manually."""
        tooltip = action.toolTip()
        if tooltip:
            QToolTip.showText(QCursor.pos(), tooltip, self.preset_menu)