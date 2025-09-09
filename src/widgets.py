# type: ignore
from PyQt5.QtWidgets import QWidget, QMenu, QLabel, QVBoxLayout, QToolTip
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QBrush, QColor, QLinearGradient, QCursor
from PyQt5.QtWidgets import QApplication

from .timer_state import TimerState
from .config import Config

# Minimalist widget for the minimalist mode
class MinimalistWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent  # QMainWindow reference
        self.settings = Config.load_from_file()

        # Set up a layout for the widget
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        # use the same fallback list as the main window style sheet
        self.setStyleSheet('''
            QWidget {
                font-family: "Bahnschrift Light", "Liberation Sans", "Arial";
                font-weight: bold;
            }
            QMenu {
                font-family: "Liberation Sans", "Arial";
                font-weight: normal;
            }
        ''')

        # compute size
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        self.base_size = min(self.parent_window.settings.minimalist_mode_size,
                             screen_geometry.width(), screen_geometry.height())
        self.setMinimumSize(20, 20)
        self.setMaximumSize(500, 500)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Load saved display preferences
        self.show_round_text = self.settings.minimalist_rounds_active
        self.show_time_text = self.settings.minimalist_time_active
        self.is_circle = not self.settings.minimalist_progressbar_active

        # Apply saved shape
        if self.is_circle:
            self.setFixedSize(self.base_size, self.base_size)
        else:
            self.setFixedSize(self.base_size * 2, self.base_size // 2)

        # default circle color without fill
        grey = "#3D3D3D"
        self.color = QColor(grey)
        # Add progress bar colors
        self.progress_bg_color = QColor(grey)
        self.progress_fill_color = QColor("#FFA500")

        # Add these properties
        self.progress = 0
        self.active_color = QColor(grey)
        self.current_state = None
        self.remaining_time = 0
        self.current_round = 0
        self.total_rounds = 0

        # build context menu
        self.context_menu = QMenu(self)
        self.start_timer_button      = self.context_menu.addAction("Start Timer")
        self.pause_timer_button      = self.context_menu.addAction("Pause Timer")
        self.resume_timer_button     = self.context_menu.addAction("Resume Timer")
        self.stop_timer_button       = self.context_menu.addAction("Stop Timer")
        self.context_menu.addSeparator()
        # preset submenu
        self.preset_dropdown = self.context_menu.addMenu("Presets")
        self.load_preset_1_button = self.preset_dropdown.addAction("Load Preset 1")
        self.load_preset_2_button = self.preset_dropdown.addAction("Load Preset 2")
        self.load_preset_3_button = self.preset_dropdown.addAction("Load Preset 3")
        self.preset_dropdown.addSeparator()
        self.save_preset_1_button = self.preset_dropdown.addAction("Save Current to Preset 1")
        self.save_preset_2_button = self.preset_dropdown.addAction("Save Current to Preset 2")
        self.save_preset_3_button = self.preset_dropdown.addAction("Save Current to Preset 3")
        self.context_menu.addSeparator()
        # widget customization submenu
        self.customize_display_dropdown = self.context_menu.addMenu("Customize Display")
        self.toggle_round_text_button   = self.customize_display_dropdown.addAction("Toggle Round Display")
        self.toggle_time_text_button    = self.customize_display_dropdown.addAction("Toggle Time Display")
        self.shape_toggle_button        = self.customize_display_dropdown.addAction("Toggle Progress Bar Display")
        # widget size submenu
        self.size_dropdown           = self.context_menu.addMenu("Adjust Size")
        self.increase_size_5_button  = self.size_dropdown.addAction("Increase Size by 5px")
        self.increase_size_10_button = self.size_dropdown.addAction("Increase Size by 10px")
        self.increase_size_20_button = self.size_dropdown.addAction("Increase Size by 20px")
        self.increase_size_50_button = self.size_dropdown.addAction("Increase Size by 50px")
        self.size_dropdown.addSeparator()
        self.decrease_size_5_button  = self.size_dropdown.addAction("Decrease Size by 5px")
        self.decrease_size_10_button = self.size_dropdown.addAction("Decrease Size by 10px")
        self.decrease_size_20_button = self.size_dropdown.addAction("Decrease Size by 20px")
        self.decrease_size_50_button = self.size_dropdown.addAction("Decrease Size by 50px")
        self.size_dropdown.addSeparator()
        self.size_to_default = self.size_dropdown.addAction("Reset to Default Size")
        self.context_menu.addSeparator()
        # window behavior toggles
        self.always_on_top_checkbox          = self.context_menu.addAction("Always on Top")
        self.always_on_top_checkbox.setCheckable(True)
        self.minimize_after_complete_checkbox = self.context_menu.addAction("Minimize After Complete")
        self.minimize_after_complete_checkbox.setCheckable(True)
        self.context_menu.addSeparator()
        # after submenus
        self.minimize_to_taskbar_button = self.context_menu.addAction("Minimize to Tray")
        self.exit_minimalist_button     = self.context_menu.addAction("Exit Minimalist Mode")
        self.exit_app_button            = self.context_menu.addAction("Exit Application")

        # wire up context actions
        self.start_timer_button.triggered.connect(self.parent().start_timer)
        self.pause_timer_button.triggered.connect(self.parent().pause_timer)
        self.resume_timer_button.triggered.connect(self.parent().resume_timer)
        self.stop_timer_button.triggered.connect(self.parent().stop_timer)
        self.toggle_round_text_button.triggered.connect(self.toggle_round_display)
        self.toggle_time_text_button.triggered.connect(self.toggle_time_display)
        self.shape_toggle_button.triggered.connect(self.toggle_shape)
        self.minimize_to_taskbar_button.triggered.connect(self.minimize_minimalist_mode)
        self.exit_minimalist_button.triggered.connect(self.parent().toggle_minimalist_mode)
        self.exit_app_button.triggered.connect(QApplication.quit)

        self.size_to_default.triggered.connect(self.reset_to_default_size)
        # size adjustments
        for action, delta in (
            (self.increase_size_5_button, +5),
            (self.increase_size_10_button, +10),
            (self.increase_size_20_button, +20),
            (self.increase_size_50_button, +50),
            (self.decrease_size_5_button, -5),
            (self.decrease_size_10_button, -10),
            (self.decrease_size_20_button, -20),
            (self.decrease_size_50_button, -50),
        ):
            action.triggered.connect(lambda _, d=delta: self.adjust_size(d))

        # connect preset load/save actions to main window methods
        for action, idx in (
            (self.load_preset_1_button, 0),
            (self.load_preset_2_button, 1),
            (self.load_preset_3_button, 2),
        ):
            action.triggered.connect(lambda _, i=idx: self.parent_window.load_preset(i))

        for action, idx in (
            (self.save_preset_1_button, 0),
            (self.save_preset_2_button, 1),
            (self.save_preset_3_button, 2),
        ):
            def _save_and_refresh(_, i=idx):
                self.parent_window.save_preset(i)
                self.update_min_preset_tooltips()
            action.triggered.connect(_save_and_refresh)

        # wire window-behavior toggles
        self.always_on_top_checkbox.triggered.connect(self.parent_window.toggle_always_on_top)
        self.minimize_after_complete_checkbox.triggered.connect(self.parent_window.toggle_minimize_after_complete)

        # Apply the same style to sub-menus so their separators are also visible
        self.customize_display_dropdown.setStyleSheet(self.context_menu.styleSheet())
        self.size_dropdown.setStyleSheet(self.context_menu.styleSheet())

        # --- Tooltip handling for preset actions ---
        # collect load/save tuples for easy processing (similar to main window)
        self.min_preset_actions = [
            (self.load_preset_1_button, self.save_preset_1_button),
            (self.load_preset_2_button, self.save_preset_2_button),
            (self.load_preset_3_button, self.save_preset_3_button),
        ]

        # update tooltips initially and whenever presets change
        self.update_min_preset_tooltips()

        # show tooltip when hovering over menu entries
        self.preset_dropdown.hovered.connect(self._show_min_preset_action_tooltip)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create gradient
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(85, 60, 115))  # Top color
        gradient.setColorAt(1, QColor(40, 40, 85))  # Bottom color
        
        if self.is_circle:
            # Draw background circle with gradient
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, self.width(), self.height())
            
            # Draw progress arc if there is progress
            if self.progress > 0:
                painter.setBrush(QBrush(self.active_color))
                span_angle = int(-self.progress * 360 * 16)  # QPainter uses 16th of a degree
                painter.drawPie(0, 0, self.width(), self.height(), 90 * 16, span_angle)
        else:
            # Draw progress bar background with gradient
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            radius = int(self.height() / 1.8)  # Dynamic roundedness
            painter.drawRoundedRect(0, 0, self.width(), self.height(), radius, radius)
            
            # Draw progress fill
            if self.progress > 0:
                progress_width = int(self.width() * self.progress)
                painter.setBrush(QBrush(self.active_color))
                painter.drawRoundedRect(0, 0, progress_width, self.height(), radius, radius)
        
        # Draw text if enabled
        if self.show_round_text or self.show_time_text:           
            # Configure text appearance
            painter.setPen(Qt.white)
            font = painter.font()
            painter.setFont(font)
            rect = self.rect()
            
            self.display_round_and_time(painter, rect)

    def display_round_and_time(self, painter, rect):
        # Adjust font size based on widget dimensions and mode
        font = painter.font()
        if self.is_circle:
            font_size = min(self.width() // 6, 30)
        else:
            # For progress bar
            font_size = min((self.width() // 3) // 4, 30)
        font.setPointSize(font_size)
        painter.setFont(font)

        if self.show_round_text and self.show_time_text:
            mins, secs = divmod(self.remaining_time, 60)
                
            if self.is_circle:
                # For circle mode - stack vertically
                bottom_rect = rect.adjusted(0, rect.height()//4, 0, 0)
                top_rect = rect.adjusted(0, 0, 0, -rect.height()//4)
                
                painter.drawText(top_rect, Qt.AlignCenter, f"{self.current_round + 1}/{self.total_rounds}")
                painter.drawText(bottom_rect, Qt.AlignCenter, f"{mins:02}:{secs:02}")
                
            else:
                # For progress bar mode - position side by side with padding
                padding = rect.width() // 20  # 5% padding on each side
                left_rect = rect.adjusted(padding, 0, -rect.width()//2, 0)
                right_rect = rect.adjusted(rect.width()//2, 0, -padding, 0)
                
                painter.drawText(left_rect, Qt.AlignCenter, f"{self.current_round + 1}/{self.total_rounds}")
                painter.drawText(right_rect, Qt.AlignCenter, f"{mins:02}:{secs:02}")
        else:
            # Only one enabled - center it
            if self.show_round_text:
                text = f"{self.current_round + 1}/{self.total_rounds}"
            else:
                mins, secs = divmod(self.remaining_time, 60)
                text = f"{mins:02}:{secs:02}"
            painter.drawText(rect, Qt.AlignCenter, text)

    ###############################
    # Mouse event handlers
    ###############################
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        # Handle right-click on release for context menu
        if event.button() == Qt.MouseButton.RightButton:
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
        self.start_timer_button.setVisible(st == TimerState.Idle)
        self.pause_timer_button.setVisible(st in (TimerState.LeadUp, TimerState.Workout, TimerState.Rest))
        self.resume_timer_button.setVisible(st in (TimerState.PausedLeadUp, TimerState.PausedWorkout, TimerState.PausedRest))
        self.stop_timer_button.setVisible(st not in (TimerState.Idle, TimerState.PausedLeadUp, TimerState.PausedWorkout, TimerState.PausedRest))

        # sync checkbox states with settings
        self.always_on_top_checkbox.setChecked(self.parent_window.settings.always_on_top)
        self.minimize_after_complete_checkbox.setChecked(self.parent_window.settings.minimize_after_complete)

    def adjust_size(self, delta: int):
        # Always adjust base_size, and use it for both shapes
        if self.is_circle:
            new_base = min(500, max(20, self.base_size + delta))
            self.base_size = new_base
            self.setFixedSize(self.base_size, self.base_size)
        else:
            new_base = min(500, max(20, self.base_size + delta))
            self.base_size = new_base
            self.setFixedSize(self.base_size * 2, self.base_size // 2)
        self.update()
        self.parent_window.settings.minimalist_mode_size = self.base_size
        self.parent_window.settings.save_to_file()

    def minimize_minimalist_mode(self):
        # Hide the minimalist widget itself, then show the parent window's tray icon if not already visible
        self.hide()
        parent = self.parent_window  # main WorkoutTimer window
        # show the tray icon if not already visible
        if hasattr(parent, "_show_tray_icon"):
            parent._show_tray_icon()

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
            # Always use base_size for circle
            self.setFixedSize(self.base_size, self.base_size)
        else:
            # Always use base_size for progress bar
            self.setFixedSize(self.base_size * 2, self.base_size // 2)
        self.update()

    def reset_to_default_size(self):
        self.base_size = Config.minimalist_mode_size
        if self.is_circle:
            self.setFixedSize(self.base_size, self.base_size)
        else:
            self.setFixedSize(self.base_size * 2, self.base_size // 2)
        self.update()
        self.parent_window.settings.minimalist_mode_size = self.base_size
        self.parent_window.settings.save_to_file()

    #############################################
    # Preset tooltip helpers (minimalist widget) #
    #############################################

    def update_min_preset_tooltips(self):
        """Mirror the main-window tooltip/enable behavior for load preset actions."""
        presets = self.parent_window.settings.presets
        for idx, (load_action, _save_action) in enumerate(self.min_preset_actions):
            preset = presets[idx]
            normal_text = f"Load Preset {idx+1}"
            if preset:
                load_action.setEnabled(True)
                load_action.setText(normal_text)
                font = load_action.font(); font.setItalic(False); load_action.setFont(font)
                tt = (
                    f"Workout: {preset['workout_duration']}s\n"
                    f"Rest: {preset['rest_duration']}s\n"
                    f"Lead-up: {preset['lead_up_duration']}s\n"
                    f"Rounds: {preset['rounds']}"
                )
                load_action.setToolTip(tt)
            else:
                load_action.setEnabled(True)  # keep enabled; just indicate empty
                load_action.setText(f"{normal_text} (empty)")
                font = load_action.font(); font.setItalic(True); load_action.setFont(font)
                load_action.setToolTip("(empty)")

    def _show_min_preset_action_tooltip(self, action):
        """Display tooltip for hovered preset menu action."""
        tooltip = action.toolTip()
        if tooltip:
            QToolTip.showText(QCursor.pos(), tooltip, self.preset_dropdown)