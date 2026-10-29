@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m ai_gym_td.scripts.play --agent manual --seed 42 --speed 1
if errorlevel 1 pause
