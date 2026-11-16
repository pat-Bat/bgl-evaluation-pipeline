# Checks for each relevant subject if there is waveform data available during the time of glucose measurements
#
#
import getpass
import re
import sys
from pathlib import Path
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

from numpy import rec
import pandas as pd
import wfdb

DATA = Path(__file__).resolve().parents[2] / "dataset_data" / "mimic3"
WAV = DATA / "waves"
OUT = DATA / "derived"
CLIN = DATA / "clinical"
DB = "mimic3wdb-matched/1.0"
WORKERS = 12

def load_diabetes():

    dx = pd.read_csv(CLIN / "DIAGNOSES_ICD.csv.gz",
                     usecols=["SUBJECT_ID", "ICD9_CODE"], dtype={"ICD9_CODE": str})
    dx = dx[dx["ICD9_CODE"].str.startswith("250", na=False)].copy()
    dx["typ"] = dx["ICD9_CODE"].str[4].map({"0": "T2", "2": "T2", "1": "T1", "3": "T1"})

    def status(typen):
        t = set(typen)
        if not t: return "unspecified"
        if t == {"T1"}: return "T1"
        if t == {"T2"}: return "T2"
        return "mixed"

    return dx.groupby("SUBJECT_ID")["typ"].agg(status).to_dict()

def add_diabetes():
    overlaps = pd.read_csv(OUT / "overlaps.csv")
    diabetes = load_diabetes()
    overlaps["diabetes"] = overlaps["subject_id"].map(diabetes).fillna("none")
    overlaps.to_csv(OUT / "overlaps.csv", index=False)
    print(overlaps.drop_duplicates("subject_id")["diabetes"].value_counts())

def load_record_index():
    # lists recordings per subject 
    index = {}
    for line in (WAV / "RECORDS-waveforms").read_text().split():
        parts = line.strip().split("/")
        subject_id = int(parts[1][1:])  # p000020 -> 20
        index.setdefault(subject_id, []).append(parts[2])  #p00/p000020/p000020-2183-04-28-17-47 -> parts[2] = p000020-2183-04-28-17-47.
    return index

def signal_names(head, pn_dir): #  lists signal names for a record (in header for multiple segments)
    segments = getattr(head, "seg_name", None)  # list of segments
    if not segments:                                 # single segment recording
        return head.sig_name or []
    for segment in segments:
        if segment.endswith("_layout"):
            return wfdb.rdheader(segment, pn_dir=pn_dir).sig_name
    return []

def check_waveform(subject_id, records, glucose_time): #reads headers of all rec of each subject
    sub = f"p{subject_id:06d}"
    pn_dir = f"{DB}/{sub[:3]}/{sub}"
    rows = []
    for record in records:
        record_start = datetime.strptime(record.split("-", 1)[1], "%Y-%m-%d-%H-%M")
        if record_start > glucose_time.max():          
            continue #recording starts after last glucose measurement

        head = wfdb.rdheader(record, pn_dir=pn_dir)
        start_time = datetime.combine(head.base_date, head.base_time)
        end_time = start_time + timedelta(seconds=head.sig_len / head.fs)

        has_gluc = ((glucose_time >= start_time) & (glucose_time <= end_time)).any()

        if has_gluc:
            signal_names_list = signal_names(head, pn_dir)
            has_pleth = "PLETH" in signal_names_list
        else:
            signal_names_list = []
            has_pleth = None

        rows.append({"subject_id": subject_id, "record": record, "pn_dir": pn_dir, "fs": head.fs, "start": start_time, 
                     "end": end_time, "has_pleth": has_pleth, "signals": " ".join(signal_names_list)})

    return rows


def find_overlaps(records, glucose_df): #finds overlaps between glucose measurements and waveform data
    overlaps = []
    for record in records:
        if not record["has_pleth"]:
            continue
        inside = glucose_df[(glucose_df["time"] >= record["start"]) & (glucose_df["time"] <= record["end"])]
        for _, g in inside.iterrows():
            overlaps.append({"subject_id": record["subject_id"], "record": record["record"],
                             "pn_dir": record["pn_dir"], "fs": record["fs"],
                             "record_start": record["start"], "record_end": record["end"],
                             "time": g["time"], "glucose": g["glucose"], "source": g["source"]})
    return overlaps


def main():
    candidates = pd.read_csv(OUT / "candidates.csv")
    glucose = pd.read_csv(OUT / "glucose_values.csv")
    glucose["time"] = pd.to_datetime(glucose["time"])
    glucose_by_patient = dict(list(glucose.groupby("subject_id")))
    record_index = load_record_index()


    # skip patients that were already checked
    done_file = OUT / "checked_subjects.txt"
    done = set(map(int, done_file.read_text().split())) if done_file.exists() else set()
    todo = [s for s in candidates["subject_id"] if s not in done]
    print(len(done), "already checked,", len(todo), "to check")


    def work(subject):
        g = glucose_by_patient[subject]
        records = check_waveform(subject, record_index.get(subject, []), g["time"])
        return subject, records, find_overlaps(records, g)

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = [ex.submit(work, s) for s in todo]
        for i, fut in enumerate(as_completed(futures), 1):
            try:
                subject, records, overlaps = fut.result()
            except Exception as e:
                print(f"[{i}/{len(todo)}] error ({e}) -> retry next turn")
                continue
            for name, rows in [("waveform_records.csv", records), ("overlaps.csv", overlaps)]:
                if rows:
                    path = OUT / name
                    pd.DataFrame(rows).to_csv(path, mode="a", header=not path.exists(), index=False)
            with done_file.open("a") as f:
                f.write(f"{subject}\n")
            print(f"[{i}/{len(todo)}] subject {subject}: {len(records)} recordings, "
                  f"{len(overlaps)} glucose values with waveform data")
    add_diabetes()


if __name__ == "__main__":
    main()
