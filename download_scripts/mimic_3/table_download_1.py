# Download Scripts for MIMIC-III and MIMIC-III Waveform Database Tables
#
#
import getpass
import re
import sys
from pathlib import Path

import requests

DATA = Path(__file__).resolve().parents[3] / "Data" / "mimic3"

#BASE = Path(__file__).resolve().parents[1]
CLIN = DATA / "clinical"
GLU = DATA / "glucose"
WAV = DATA / "waves"

MIMIC   = "https://physionet.org/files/mimiciii/1.4/"
GLUCOSE = "https://physionet.org/files/glucose-management-mimic/1.0.0/Datasets/"
WAVES   = "https://physionet.org/files/mimic3wdb-matched/1.0/"

# Patient data, Hospital stays, ICU stays, Diagnoses, Lab events(everything), Mapping ItemId -> Name
TABLES = ["PATIENTS", "ADMISSIONS", "ICUSTAYS", "DIAGNOSES_ICD", "D_ICD_DIAGNOSES", "LABEVENTS", "D_LABITEMS", "D_ITEMS"]

# download url to target
def download(session, url, target: Path):
    if target.exists():                          # data exists alreay
        print("existing:", target.name)
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".part")   # z.B. LABEVENTS.csv.gz.part

    with session.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()                     # error
        with open(temp, "wb") as f:
            done = 0
            for chunk in r.iter_content(chunk_size=1_000_000):   # 1 MB chunks
                f.write(chunk)
                done += len(chunk)
                print(f"\r  {target.name}: {done / 1e6:.0f} MB", end="") # progress bar
                
    temp.rename(target)                          # rename finally
    print(f"\r  fertig: {target.name}" + " " * 20)






def main():
    session = requests.Session()
    session.auth = (input("Benutzername: "), getpass.getpass("Passwort: "))
    session.headers["User-Agent"] = "Wget/1.21.4"

    print("1) clinical tables")
    for t in TABLES:
        download(session, f"{MIMIC}{t}.csv.gz", CLIN / f"{t}.csv.gz")

    print("2) curated glucose dataset")
    # glucose and insulin data from ICU stays
    download(session, GLUCOSE + "glucose_insulin_ICU.csv", DATA / "glucose" / "Datasets" / "glucose_insulin_ICU.csv")

    print("3) waveform records")
    # list of waveform records and their corresponding waveforms
    for name in ["RECORDS", "RECORDS-waveforms"]:
        download(session, WAVES + name, DATA / "waves" / name)


if __name__ == "__main__":
    main()