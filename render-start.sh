#!/bin/bash
# Lance un écran virtuel pour headless=False
Xvfb :99 -screen 0 1280x800x24 &
export DISPLAY=:99
python main.py
