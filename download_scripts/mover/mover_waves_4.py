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
WAVES = DATA / "Waves"
SIS_WAVES = DATA / "SIS" / "Waves"


SIS_WAVE = "sis_wave_v2.tar.gz"
SIS_WAVE_CHECKSUM = "md5sum_sis_wave_v2.tar.gz.txt"

BASE   = "https://mover-download.ics.uci.edu/"

WAVE_ARCHIVE_1   = "epic_wave_1_v2.tar.gz"
WAVE_ARCHIVE_2   = "epic_wave_2_v2.tar.gz"
WAVE_ARCHIVE_3   = "epic_wave_3_v2.tar.gz"

WAVE_CHECKSUM_1   = "md5sum_epic_wave_1_v2.tar.gz.txt"
WAVE_CHECKSUM_2   = "md5sum_epic_wave_2_v2.tar.gz.txt"
WAVE_CHECKSUM_3   = "md5sum_epic_wave_3_v2.tar.gz.txt"

ARCHIVE_1 = [WAVE_ARCHIVE_1, WAVE_CHECKSUM_1]
ARCHIVE_2 = [WAVE_ARCHIVE_2, WAVE_CHECKSUM_2] 
ARCHIVE_3 = [WAVE_ARCHIVE_3, WAVE_CHECKSUM_3]

# download url to target, resume if Server cuts connection
def download(session, url, target: Path):
    if target.exists():                          # data exists alreay
        print("existing:", target.name)
        return

    target.parent.mkdir(parents = True, exist_ok = True)
    temp = target.with_suffix(target.suffix + ".part")   # z.B. LABEVENTS.csv.gz.part

    while True:
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
            print(f"\n connection lost ({type(e).__name__}), retry")
            time.sleep(0.1)
                
    temp.rename(target)                          # rename finally
    print(f"\r  fertig: {target.name}" + " " * 20)


def check_md5(file, md5_info): # checksum check
    expected_cs = md5_info.read_text().split()[0]
    hash = hashlib.md5()
    with open(file, "rb") as f:
        for chunk in iter(lambda: f.read(8_000_000), b""):
            hash.update(chunk)
    return hash.hexdigest() == expected_cs

def has_md5(archive, md5_info):
    name = archive.with_name(archive.name + ".md5Done")
    if name.exists():
        print(f"md5 checksum already checked for {archive.name}")
        return
    if not check_md5(archive, md5_info):
        raise SystemExit(f"md5 problems for {archive.name}")
    name.touch()




def main():
    session = requests.Session()
    session.auth = (input("Benutzername: "), getpass.getpass("Passwort: "))
    session.headers["User-Agent"] = "Wget/1.21.4"

    print("0) Download SIS archive") 
    for f in [SIS_WAVE_CHECKSUM, SIS_WAVE]: 
        download(session, BASE + f, SIS_WAVES / f) 

    print("0) Checksum") 
    has_md5(SIS_WAVES / SIS_WAVE, SIS_WAVES / SIS_WAVE_CHECKSUM)

    print("1) Download first archive")
    for f in ARCHIVE_1:
        download(session, BASE + f, WAVES / f)

    print("1) Checksum")
    has_md5(WAVES / WAVE_ARCHIVE_1, WAVES / WAVE_CHECKSUM_1)

    print("2) Download second archive")
    for f in ARCHIVE_2:
        download(session, BASE + f, WAVES / f)

    print("2) Checksum")
    has_md5(WAVES / WAVE_ARCHIVE_2, WAVES / WAVE_CHECKSUM_2)

    print("2) Download third archive")
    for f in ARCHIVE_3:
        download(session, BASE + f, WAVES / f)

    print("3) Checksum")
    has_md5(WAVES / WAVE_ARCHIVE_3, WAVES / WAVE_CHECKSUM_3)


if __name__ == "__main__":
    main()