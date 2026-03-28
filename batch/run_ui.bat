@echo off
setlocal

cd /d "%~dp0.."

set "PYTHON_EXE=C:\Users\gotta\anaconda3\python.exe"

if exist "%PYTHON_EXE%" (
    "%PYTHON_EXE%" -m streamlit run app\ui.py
    goto :eof
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -m streamlit run app\ui.py
    goto :eof
)

where python >nul 2>nul
if %errorlevel%==0 (
    python -m streamlit run app\ui.py
    goto :eof
)

echo Python could not be found.
echo Install Python or Anaconda, then try again.
pause
