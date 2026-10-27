@echo off
python --version >nul 2>&1
if errorlevel 1 goto errorNoPython
python -m venv idom-smart-venv-win
echo Virtual environment 'idom-smart-venv-win' created.
call idom-smart-venv-win\Scripts\activate.bat
echo Virtual environment 'idom-smart-venv-win' activated.
echo Updating pip.
python -m pip install --upgrade pip
echo Done updating pip.
echo Installing required python modules.
python -m pip install -r requirements.txt
echo Required python modules installed.
jupyter trust idom-smart.ipynb
echo idom-smart is now trusted.
echo My work is done here. You can open the idom-smart tool using the provided running script (remember to change paths to python venv and smart).
goto:eof
:errorNoPython
echo.
echo Error^: Python is not installed or is not in path. Please install python for windows or add it to path.
