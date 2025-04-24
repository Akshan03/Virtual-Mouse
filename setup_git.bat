@echo off
echo Setting up Git repository for Virtual Mouse...

REM Initialize Git repository if not already initialized
if not exist .git (
    echo Initializing Git repository...
    git init
) else (
    echo Git repository already initialized.
)

REM Add all files to Git
echo Adding files to Git...
git add .

REM Create initial commit
echo Creating initial commit...
git commit -m "Initial commit: Hand Gesture Mouse Control"

REM Add GitHub remote
echo Adding GitHub remote...
git remote add origin https://github.com/Akshan03/Virtual-Mouse.git

echo.
echo Repository setup complete!
echo.
echo To push to GitHub, run:
echo git push -u origin main
echo.
echo Note: You may need to authenticate with GitHub.
echo If you're using a personal access token, you'll be prompted for it.
echo.
pause
