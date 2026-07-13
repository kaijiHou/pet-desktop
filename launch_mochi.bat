@echo off
REM Mochi Desktop Pet 🐱
REM Launches Mochi with proper Qt environment

SET "QT_QPA_PLATFORM_PLUGIN_PATH=C:\Users\clara\AppData\Local\Python\pythoncore-3.11-64\Lib\site-packages\PyQt5\Qt5\plugins\platforms"
CD /D "C:\Users\clara\desktop-pet"

START "" /MIN "C:\Users\clara\AppData\Local\Python\pythoncore-3.11-64\pythonw.exe" "C:\Users\clara\desktop-pet\main.py"
