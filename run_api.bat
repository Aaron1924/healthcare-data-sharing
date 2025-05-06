@echo off
REM Set the MCL_LIB_PATH environment variable
set MCL_LIB_PATH=%~dp0mcl\build\lib

REM Activate the virtual environment
call venv\Scripts\activate.bat

REM Run the FastAPI application
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8001

REM Deactivate the virtual environment
call venv\Scripts\deactivate.bat
