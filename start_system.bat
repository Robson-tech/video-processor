@echo off
echo Starting Video Processing System...
start "Server" start_server.bat
timeout /t 3 /nobreak > nul
start "Client" start_client.bat
