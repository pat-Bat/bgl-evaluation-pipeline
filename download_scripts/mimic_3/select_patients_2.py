# Determines relevant patients with >= 2 glucose measuements
#
#
import getpass
import re
import sys
from pathlib import Path
import argparse

import pandas as pd

DATA = Path(__file__).resolve().parents[2] / "dataset_data" / "mimic3"

#BASE = Path(__file__).resolve().parents[1]
CLIN = DATA / "clinical"
GLU = DATA / "glucose"
WAV = DATA / "waves"
OUT = DATA / "derived"

# glucose IDs for glucose measurements
GLUCOSE_ITEMIDS = {50931: "lab", 50809: "bloodgas"}
MIN_MEASUREMENTS = 2

def load_lab_data(): #Lab and blood gas data 
    parts = []
    for chunk in pd.read_csv(CLIN / "LABEVENTS.csv.gz", usecols=["SUBJECT_ID", "ITEMID", "CHARTTIME", "VALUENUM"], chunksize=2_000_000):
        parts.append(chunk[chunk["ITEMID"].isin(GLUCOSE_ITEMIDS.keys())])

    lab_data = pd.concat(parts).dropna(subset=["VALUENUM"])

    lab_data["CHARTTIME"] = pd.to_datetime(lab_data["CHARTTIME"])
    lab_data["source"] = lab_data["ITEMID"].map(GLUCOSE_ITEMIDS)

    lab = lab_data.rename(columns={"SUBJECT_ID": "subject_id", "CHARTTIME": "time",
                              "VALUENUM": "glucose"})

    print("Lab values:", len(lab))
    return lab[["subject_id", "time", "glucose", "source"]]


def load_fingerstick_data(): #fingerstick data
    fingerstick = pd.read_csv(GLU / "Datasets" / "glucose_insulin_ICU.csv",
                     usecols=["SUBJECT_ID", "GLCTIMER", "GLC", "GLCSOURCE"])
    fingerstick = fingerstick[fingerstick["GLCSOURCE"] == "FINGERSTICK"].dropna(subset=["GLC"])

    fingerstick["source"] = "fingerstick"
    fingerstick["time"] = pd.to_datetime(fingerstick["GLCTIMER"].str.replace(" UTC", ""))  # remove " UTC" or error!
    fingerstick = fingerstick.rename(columns={"SUBJECT_ID": "subject_id", "GLC": "glucose"})
    print("Fingerstick values:", len(fingerstick))
    return fingerstick[["subject_id", "time", "glucose", "source"]]


def waveform_subjects():
    lines = (WAV / "RECORDS").read_text().split()
    # lines like "p00/p000020/" -> 20
    return {int(l.strip("/").split("/")[-1][1:]) for l in lines if l.strip()}




def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # concatenate lab and fingerstick data
    glucose = pd.concat([load_lab_data(), load_fingerstick_data()], ignore_index=True)
    glucose = glucose.drop_duplicates()
    print("Concatinated:", len(glucose))

    # filter patients with waveforms
    glucose = glucose[glucose["subject_id"].isin(waveform_subjects())]
    glucose = glucose.sort_values(["subject_id", "time"])   
    print("With waveform data:", len(glucose), "values from",
         glucose["subject_id"].nunique(), "patients")
    print(glucose["source"].value_counts().to_string())

    # determine patients with >=2 measurements
    count = glucose.groupby("subject_id").size()
    relevant_patients = count[count >= MIN_MEASUREMENTS].index
    glucose_relevant = glucose[glucose["subject_id"].isin(relevant_patients)]
    print("With >=2 measurements:", len(glucose_relevant), "values from",
          glucose_relevant["subject_id"].nunique(), "patients")

    #save data to csv
    glucose.to_csv(OUT / "glucose_values.csv", index=False)
    count[count >= MIN_MEASUREMENTS].rename("n_glucose").to_csv(OUT / "candidates.csv")

if __name__ == "__main__":
    main()