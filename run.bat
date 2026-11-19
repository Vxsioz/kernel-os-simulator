@echo off
cd /d "%~dp0"
set "PYTHON_EXE="
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%~D\python.exe" set "PYTHON_EXE=%%~D\python.exe"
)
if defined PYTHON_EXE (
    "%PYTHON_EXE%" kernel_app.py
) else (
    python kernel_app.py
)
if errorlevel 1 pause
