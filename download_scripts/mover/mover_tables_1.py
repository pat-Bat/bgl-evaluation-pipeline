# Download Scripts for MOVER EPIC Tables to determine relevant recordings
#
#
import getpass
import hashlib
import re
import sys
from pathlib import Path
import tarfile
import time

import requests

DATA = Path(__file__).resolve().parents[2] / "dataset_data" / "MOVER"

#BASE = Path(__file__).resolve().parents[1]
TABLES = DATA / "Tables"

BASE   = "https://mover-download.ics.uci.edu/"

#EPIC Part
EMR_TABLES   = "EPIC_EMR.tar.gz"
CHECKSUM = "md5sum_EPIC_EMR.tar.gz.txt"
DECODE_ANNOTATIONS   = "README.tar.gz"
SUBJECT_SURGERY   = "EPIC_MRN_PAT_ID.csv"

#SIS Part
SIS_TABLES = DATA / "SIS" / "Tables"
SIS_EMR = "sis_emr.tar.gz"
SIS_CHECKSUM = "md5sum_sis_emr.tar.gz.txt"

FILES = [EMR_TABLES, CHECKSUM, DECODE_ANNOTATIONS, SUBJECT_SURGERY]

# download url to target, resume if Server cuts connection
def download(session, url, target: Path, tries = 15):
    if target.exists():                          # data exists alreay
        print("existing:", target.name)
        return

    target.parent.mkdir(parents = True, exist_ok = True)
    temp = target.with_suffix(target.suffix + ".part")   # z.B. LABEVENTS.csv.gz.part

    for attempt in range(tries):
        downloaded = temp.stat().st_size if temp.exists() else 0
        headers = {"Range": f"bytes={downloaded}-"} if downloaded else {}
        try:
            with session.get(url, stream = True, timeout = 60, headers = headers) as r:
                if r.status_code == 416: #file complete
                    break
                r.raise_for_status()
                if downloaded and r.status_code != 206: #start over
                    downloaded = 0
                with open(temp, "ab" if downloaded else "wb") as f:
                    done = downloaded
                    for chunk in r.iter_content(chunk_size = 1_000_000):   # 1 MB chunks
                        f.write(chunk)
                        done += len(chunk)
                        print(f"\r  {target.name}: {done / 1e6:.0f} MB", end = "") # progress bar
            break
        except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f"\n connection lost ({type(e).__name__}), retry attempt {attempt + 1}")
            time.sleep(5)
    else:
        raise SystemExit("download failed")
                
    temp.rename(target)                          # rename finally
    print(f"\r  fertig: {target.name}" + " " * 20)


def check_md5(file, md5_info): # checksum check
    expected_cs = md5_info.read_text().split()[0]
    hash = hashlib.md5()
    with open(file, "rb") as f:
        for chunk in iter(lambda: f.read(8_000_000), b""):
            hash.update(chunk)
    return hash.hexdigest() == expected_cs




def main():
    session = requests.Session()
    session.auth = (input("Benutzername: "), getpass.getpass("Passwort: "))
    session.headers["User-Agent"] = "Wget/1.21.4"

    print("1) Download files")
    for f in FILES:
        download(session, BASE + f, TABLES / f)

    print("2) Checksum")
    if not check_md5(TABLES / EMR_TABLES, TABLES / CHECKSUM):
        raise SystemExit("md5 problems")

    print("3) Extract files")
    for f in [EMR_TABLES, DECODE_ANNOTATIONS]:
        target = TABLES / f.replace(".tar.gz", "")
        if target.exists():
            continue
        with tarfile.open(TABLES / f) as tar:
            tar.extractall(target, filter = "data")

    print("4) SIS tables") 
    for f in [SIS_EMR, SIS_CHECKSUM]: 
        download(session, BASE + f, SIS_TABLES / f) 
    if not check_md5(SIS_TABLES / SIS_EMR, SIS_TABLES / SIS_CHECKSUM): 
        raise SystemExit("md5 problems sis_emr") 
    target = SIS_TABLES / "sis_emr" 
    if not target.exists(): 
        with tarfile.open(SIS_TABLES / SIS_EMR) as tar: 
            tar.extractall(target, filter = "data")


if __name__ == "__main__":
    main()