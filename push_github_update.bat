@echo off
setlocal

cd /d "%~dp0"

echo ========================================
echo GitHub update helper
echo ========================================
echo.

git status --short
echo.

set /p COMMIT_MESSAGE=Commit message (blank = Update app): 
if "%COMMIT_MESSAGE%"=="" set "COMMIT_MESSAGE=Update app"

echo.
echo Adding changes...
git add .
if errorlevel 1 goto :error

echo.
echo Committing...
git commit -m "%COMMIT_MESSAGE%"
if errorlevel 1 (
    echo.
    echo Commit was skipped or failed.
    echo If there were no changes to commit, this is expected.
)

echo.
echo Pushing to GitHub...
git push
if errorlevel 1 goto :error

echo.
echo Done. Refresh GitHub and Streamlit Cloud if needed.
pause
goto :eof

:error
echo.
echo Git operation failed.
pause
exit /b 1
