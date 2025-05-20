from enum import Enum

class TimerState(Enum):
    Idle = 0
    LeadUp = 1
    Workout = 2
    Rest = 3
    PausedWorkout = 4
    PausedRest = 5
    PausedLeadUp = 6
