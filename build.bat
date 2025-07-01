@echo off
set PYTHONPATH=src
set MAIN_SCRIPT=src\main.py
set DIST_DIR=dist
set EXE_NAME=file-poller
set DEST_DIR=C:\Portable\FilePoller

echo Building the executable...
pyinstaller --onefile --name %EXE_NAME% %MAIN_SCRIPT%

echo Cleaning up temporary files...
rmdir /S /Q build
del /Q %EXE_NAME%.spec

echo Done. Check the %DIST_DIR%\ folder for %EXE_NAME%.exe

set /p MOVE_EXE=Do you want to move and override %EXE_NAME%.exe to %DEST_DIR%? (y/n): 
if /I "%MOVE_EXE%"=="y" (
    echo Moving the executable...
    copy /Y "%DIST_DIR%\%EXE_NAME%.exe" "%DEST_DIR%\"
    echo File copied to %DEST_DIR%
)

set /p MOVE_EXE=Do you want to move and override config.json to %DEST_DIR%? (y/n): 
if /I "%MOVE_EXE%"=="y" (
    echo Moving the executable...
    copy /Y "config.json" "%DEST_DIR%\"
    echo File copied to %DEST_DIR%
)
pause