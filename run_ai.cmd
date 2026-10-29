@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m ai_gym_td.scripts.play --agent ppo --seed 42 --speed 4
if errorlevel 1 pause
