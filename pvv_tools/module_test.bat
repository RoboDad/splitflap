@echo off
setlocal
REM ============================================================
REM  62-flap module acceptance protocol (see pvv_tools/README.md)
REM
REM  Usage:  module_test.bat [COMport] [moduleIndex]
REM          module_test.bat            (defaults: COM5, module 0)
REM          module_test.bat COM7 2
REM
REM  Protocol (established 2026-08-02, module 1 bring-up):
REM    1. COLD spin      - baseline home-arrival offset
REM    2. Warm-up        - a few minutes of motion
REM    3. WARM jumps     - the go/no-go (warm margins are the real ones)
REM    4. Tour --confirm - operator-verified full character set
REM  Run on the chainlink_pvv62_diag firmware so DIAG arrival lines
REM  are printed; reflash chainlink_pvv62 for service afterwards.
REM ============================================================

set PORT=%1
if "%PORT%"=="" set PORT=COM5
set MODULE=%2
if "%MODULE%"=="" set MODULE=0

pushd "%~dp0.."

set PY=.venv\Scripts\python.exe
set PIO=%USERPROFILE%\.platformio\penv\Scripts\pio.exe

if not exist "%PY%" (
    echo ERROR: .venv not found. From the repo root run:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r pvv_tools\requirements.txt
    popd
    exit /b 1
)

echo.
echo Module acceptance test -- port %PORT%, module index %MODULE%
echo (Close the PlatformIO serial monitor and any web-app tab first --
echo  only one program can hold %PORT%.)
echo.

choice /C YN /M "Flash diag firmware (chainlink_pvv62_diag) now"
if errorlevel 2 goto skipflash
"%PIO%" run -e chainlink_pvv62_diag -t upload
if errorlevel 1 (
    echo ERROR: diag firmware flash failed.
    popd
    exit /b 1
)
:skipflash

echo.
echo ============================================================
echo  STEP 1 of 4: COLD SPIN  (module should be cold / idle 30+ min)
echo  PASS: DIAG arrival CONSTANT small offset (e.g. +3 every rev),
echo        missed=0.  A rising staircase = mechanical drag -- check
echo        the flap contact surface at the window (PLA-CF abrades).
echo ============================================================
pause
"%PY%" -m pvv_tools.flap_tester spin --port %PORT% --module %MODULE% --revs 10

echo.
echo ============================================================
echo  STEP 2 of 4: WARM-UP  (~3 minutes of motion, results ignored)
echo ============================================================
pause
"%PY%" -m pvv_tools.flap_tester jumps --port %PORT% --module %MODULE% --count 30 --seed 7 --dwell 0.5

echo.
echo ============================================================
echo  STEP 3 of 4: WARM JUMPS  -- THE GO/NO-GO
echo  PASS: DIAG arrivals stay FLAT (no rev-over-rev growth),
echo        zero missed/unexpected home counter changes.
echo  FAIL: staircase arrivals or counter ticks = losing steps warm;
echo        lower PVV_MAX_ACCEL_STEP or fix friction, then re-run.
echo ============================================================
pause
"%PY%" -m pvv_tools.flap_tester jumps --port %PORT% --module %MODULE% --count 40 --seed 1

echo.
echo ============================================================
echo  STEP 4 of 4: FULL CHARACTER TOUR  (operator confirm)
echo  At each flap: Enter = correct, or type the char actually shown.
echo  PASS: zero mismatches in the end summary.
echo ============================================================
pause
"%PY%" -m pvv_tools.flap_tester tour --port %PORT% --module %MODULE% --dwell 1.5 --confirm

echo.
echo ============================================================
echo  Protocol complete. If all four steps passed, flash the
echo  production firmware for service.
echo ============================================================
choice /C YN /M "Flash production firmware (chainlink_pvv62) now"
if errorlevel 2 goto done
"%PIO%" run -e chainlink_pvv62 -t upload

:done
popd
endlocal
