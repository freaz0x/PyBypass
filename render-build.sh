#!/bin/bash
pip install -r requirements.txt
playwright install chromium
playwright install-deps chromium
apt-get install -y xvfb
