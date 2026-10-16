@echo off
setlocal
if not defined DS_COMPARE_VCVARS exit /b 20
call "%DS_COMPARE_VCVARS%" >nul
if errorlevel 1 exit /b 21
call "%DS_COMPARE_SOURCE%\bridge\build_bridge.cmd"
exit /b %ERRORLEVEL%
