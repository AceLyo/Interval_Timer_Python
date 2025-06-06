# Workout Timer

A simple interval timer for workouts, built with Python and PyQt5.

![Screenshot 2025-06-02 213402](https://github.com/user-attachments/assets/3c5e5236-4178-483f-9d72-a78fae17f57e)

## Features

- Customizable workout, rest, and lead-up intervals
- Multiple rounds with automatic progression
- Audio cues for workout, rest, and completion
- Minimalist mode for distraction-free use
- Simple and intuitive UI

## Usage from exe

1.  Unzip downloaded folder
2.  Run exe file in main folder

## Configuration

The program uses the following configuration options:

* `workout_duration`: the length of the workout interval in seconds (default: 60)
* `rest_duration`: the length of the rest interval in seconds (default: 45)
* `lead_up_duration`: the length of the lead-up interval in seconds (default: 5)
* `rounds`: the number of rounds to complete (default: 10)
* `work_finish`: the audio file to play at the end of the workout interval (default: `../work_finish.mp3`)
* `rest_finish`: the audio file to play at the end of the rest interval (default: `../rest_finish.mp3`)

## Dependencies

* PyQt5
* pygame
* Python Standard Library

## License

This program is licensed under the GPL License.
