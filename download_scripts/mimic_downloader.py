import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
MIMIC = "mimic_3"
MOVER = "mover"

def main():
    subprocess.run([sys.executable, str(BASE / MIMIC / "table_download_1.py")], check=True)
    subprocess.run([sys.executable, str(BASE / MIMIC / "select_patients_2.py")], check=True)
    subprocess.run([sys.executable, str(BASE / MIMIC / "waveform_check_3.py")], check=True)
    subprocess.run([sys.executable, str(BASE / MIMIC / "download_ppg_windows_4.py"), "--workers", "8"], check=True)


if __name__ == "__main__":
    main()