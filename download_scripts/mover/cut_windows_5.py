# Cuting out the relevant PPG windows around every glucose measurement with the smae output format as mimic.
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
SIS = DATA / "SIS"
SIS_WAVES = SIS / "Waves"

SIS_WAVE = "sis_wave_v2.tar.gz"
SIS_WAVE_CHECKSUM = "md5sum_sis_wave_v2.tar.gz.txt"

BASE   = "https://mover-download.ics.uci.edu/"

WAVE_ARCHIVE_1   = "epic_wave_1_v2.tar.gz"
WAVE_ARCHIVE_2   = "epic_wave_2_v2.tar.gz"
WAVE_ARCHIVE_3   = "epic_wave_3_v2.tar.gz"

FS = 100 
MISSING = -32767 # monitor code for no signal
LENGTH = 16

TZ = "America/Los_Angeles" # timezone information


def load_glucose(type):
    if type == "sis":
        glucose = pd.read_csv(SIS / "derived" / "glucose_surgery_sis.csv.gz", parse_dates=["time"])
        glucose["wave_id"] = glucose["PID"] # only operation ID available for Sis Part
        glucose["subject_id"] = glucose["PID"]
        glucose["case_id"] = glucose["PID"]

    else:
        glucose = pd.read_csv(DATA / "derived" / "glucose_surgery.csv.gz", parse_dates=["time"])
        id = pd.read_csv(DATA / "Tables" / "EPIC_MRN_PAT_ID.csv", usecols=["LOG_ID", "PAT_ID"])
        glucose = glucose.merge(id.drop_duplicates("LOG_ID"), on="LOG_ID", how="inner")
        glucose["wave_id"] = glucose["PAT_ID"] # file name equals PAT_ID
        glucose["subject_id"] = glucose["MRN"] # MRN equals subject_id
        glucose["case_id"] = glucose["LOG_ID"] # LOD_ID equals case_id

        utc_info = glucose["time"].dt.tz_localize(LOCAL_TZ, ambiguous="NaT", nonexistent="NaT") # adding timezone information
        glucose["time_utc"] = utc_info.dt.tz_convert("UTC").dt.tz_localize(None)
        glucose = glucose.dropna("time_utc")

        return glucose[["wave_id", "subject", "case", "time", "time_utc", "glucose", "source"]].drop_duplicates()
        



if __name__ == "__main__":
    main()