@call .venv\Scripts\activate.bat
chcp 65001


pyinstaller --onefile snap-contract-files.py

pyinstaller --onefile convert-to-docx.py

pyinstaller --onefile -F -w ui/main_convert_to_snapshots.py

pyinstaller --onefile -F -w ui/main_convert_to_docx.py

pyinstaller --onefile -F -w ui/main_snapshot_tools.py

@call .venv\Scripts\deactivate.bat