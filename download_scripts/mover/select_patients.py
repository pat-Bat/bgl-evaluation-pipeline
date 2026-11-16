# Determines relevant patients with >= 2 glucose measuements
# tables already locally present, mover servers temporarily down
#
import getpass
import re
import sys
from pathlib import Path
import argparse
import re

import pandas as pd


DATA = Path(__file__).resolve().parents[2] / "dataset_data" / "MOVER"

EMR = DATA / "EPIC_EMR" / "EPIC_EMR" / "EMR"
OUT = DATA / "derived"

# glucose IDs for glucose measurements
GLUCOSE_CODES = {"2339-0": "wholeblood", "2345-7": "serum"}
MIN_MEASUREMENTS = 2

def glucose_data(): 
    gluc = pd.read_csv(DATA / "glucose_compact.csv.gz")
    gluc = gluc[gluc["code"].isin(GLUCOSE_CODES)].copy() # only keep relevant glucose code rows
    gluc["glucose"] = pd.to_numeric(gluc["value"], errors="coerce")
    gluc = gluc[gluc["glucose"] < 9999999] # remove place holder values
    gluc["source"] = gluc["code"].map(GLUCOSE_CODES)
    gluc["time"] = pd.to_datetime(gluc["time"])
    return gluc[["LOG_ID", "MRN","time", "glucose", "source"]].drop_duplicates() #Operation ID, Subject ID, time, glucose value, source


def load_surgeries():
    surge = pd.read_csv(EMR / "patient_information.csv", usecols=["LOG_ID", "MRN", "IN_OR_DTTM", "OUT_OR_DTTM"])
    surge = surge.rename(columns={"IN_OR_DTTM": "start_time", "OUT_OR_DTTM": "end_time"})
    for c in ["start_time", "end_time"]:
        surge[c] = pd.to_datetime(surge[c], format="%m/%d/%y %H:%M", errors="coerce") # format time
    return surge.dropna().drop_duplicates(subset=["LOG_ID"]) # drop faulty and duplicate Operation IDs

def text_type(name): #helper for diabetes desc type detection
    if "gestational" in name or "(gdm)" in name:          # gestational diabetes -> do not count
        return None
    if re.search(r"type (1|i)\b", name):                  # type 1 / type I
        return "T1"
    if re.search(r"type (2|ii)\b", name) or "dm ii" in name:   # type 2 / type II / DM II
        return "T2"
    if any(k in name for k in ("underlying condition", "steroid-induced",
                               "other specified", "other type")):
        return "other"                                    # secondary Diabetes
    return "unspecified"


def diabetes_type(code, name): #diabetes type from ICD9 code and description
    code = str(code).replace(".", "")      # "250.13" -> "25013"
    name = str(name).lower()

    if code.startswith("249"):             # secondary Diabetes
        return "other"
    if code in ("", "nan"):                # no code -> description only
        if "diabet" not in name or "prediabet" in name or "pre-diabet" in name:
            return None
        return text_type(name)
    if not code.startswith("250"):
        return None
    if code[4:5] in ("1", "3"):            # Type 1
        return "T1"
    # Code is 250.x0 / 250.x2 = "Type 2 or unspecified" -> check description
    if "type 1" in name:
        return "T1"
    if "type 2" in name:
        return "T2"
    return "unspecified"

def load_diabetes():
    cols = ["mrn", "diagnosis_code", "dx_name"]
    visit = pd.read_csv(EMR / "patient_visit.csv", usecols=cols, dtype={"diagnosis_code": str})
    history = pd.read_csv(EMR / "patient_history.csv", usecols=cols, dtype={"diagnosis_code": str})
    dx = pd.concat([visit, history], ignore_index=True).drop_duplicates()

    dx["type"] = [diabetes_type(c, n) for c, n in zip(dx["diagnosis_code"], dx["dx_name"])]
    dx = dx.dropna(subset=["type"])
    return dx.groupby("mrn")["type"].agg(summarize).to_dict() #returns dict with MRN and diabetes type


def summarize(types):
    t = set(types)
    if {"T1", "T2"} <= t: return "mixed"
    if "T1" in t: return "T1"
    if "T2" in t: return "T2"
    if "unspecified" in t: return "unspecified"
    return "other"

def main():
    OUT.mkdir(exist_ok=True)
    glucose = glucose_data().merge(load_surgeries(), on=["LOG_ID", "MRN"], how="inner") # inner join glucose and surgery data
    glucose = glucose[(glucose["time"] >= glucose["start_time"]) & (glucose["time"] <= glucose["end_time"])] # values during surgery

    n = glucose.groupby("MRN")["time"].transform("nunique") # counts unique glucose times
    glucose = glucose[n >= MIN_MEASUREMENTS].sort_values(["MRN", "time"])

    glucose["diabetes"] = glucose["MRN"].map(load_diabetes()).fillna("none")

    glucose.to_csv(OUT / "glucose_surgery.csv.gz", index=False)
    print(f"{len(glucose):,} glucose values, {glucose['LOG_ID'].nunique():,} operations, {glucose['MRN'].nunique():,} patients")
    print(glucose.drop_duplicates("MRN")["diabetes"].value_counts())

if __name__ == "__main__":
    main()