import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
MIMIC = "mimic_3"
MOVER = "mover"

def main():
    subprocess.run([sys.executable, str(BASE / MOVER / "mover_tables_1.py")], check=True)
    subprocess.run([sys.executable, str(BASE / MOVER / "filter_glucose_2.py")], check=True)
    subprocess.run([sys.executable, str(BASE / MOVER / "select_patients_3.py")], check=True)



if __name__ == "__main__":
    main()