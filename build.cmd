@call .venv\Scripts\activate.bat
chcp 65001


pyinstaller --onefile snap-contract-files.py

pyinstaller --onefile -F -w ui/convert_contract_snapshots.py


@call .venv\Scripts\deactivate.bat