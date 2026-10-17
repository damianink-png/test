@echo off
setlocal
if not defined DS_COMPARE_SOURCE exit /b 21
if not defined DS_COMPARE_OUT exit /b 22
cl.exe /nologo /std:c++17 /EHsc /O2 /W4 /MT /utf-8 /DUNICODE /D_UNICODE /LD "%DS_COMPARE_SOURCE%\bridge\DSAssemblyCompare2019.cpp" /link /NOLOGO /MACHINE:X64 /OUT:"%DS_COMPARE_OUT%\DSAssemblyCompare2019.dll" psapi.lib user32.lib kernel32.lib shell32.lib
if errorlevel 1 exit /b 23
if not exist "%DS_COMPARE_OUT%\DSAssemblyCompare2019.dll" exit /b 24
exit /b 0
