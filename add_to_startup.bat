@echo off
REM Tambahkan Mochi ke Windows Startup
set STARTUP_DIR="%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
copy /Y "C:\Users\clara\desktop-pet\Mochi.vbs" %STARTUP_DIR%\Mochi.vbs
echo ✅ Mochi added to Windows Startup!
echo.
echo Pet akan otomatis jalan setiap kali Windows nyala.
pause
