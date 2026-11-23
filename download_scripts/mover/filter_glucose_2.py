"""
Filters the glucose rows out of the large laboratory results table and saves them as csv.
"""
from pathlib import Path 
import os
import pandas as pd

DATA = Path(__file__).resolve().parents[2] / "dataset_data" / "MOVER"
EMR = DATA / "Tables" / "EPIC_EMR" / "EPIC_EMR" / "EMR"
OUT = DATA / "derived"

LABS = EMR / "patient_labs.csv"
TARGET = OUT / "compact_glucose.csv.gz"

COLUMNS = {"LOG_ID": "LOG_ID", "MRN": "MRN", "Lab Code": "code", "Lab Name": "name",
           "Observation Value": "value", "Measurement Units": "unit", "Collection Datetime": "time"}

def main():
    if TARGET.exists():
        print(f"existing: {TARGET.name}")
        return
    OUT.mkdir(parents = True, exist_ok = True)

    parts = []
    n_total = 0
    for chunk in pd.read_csv(LABS, usecols = list(COLUMNS), dtype=str, chunksize=1_000_000):
        n_total += len(chunk)
        is_glucose = (chunk["Lab Code"].fillna("").str.contains("gluc", case = False) |
                      chunk["Lab Name"].fillna("").str.contains("gluc", case = False))
        parts.append(chunk[is_glucose])
        print(f"read {n_total:,} rows, {sum(map(len, parts)):,} with glucose")


    glucose = pd.concat(parts, ignore_index = True).rename(columns = COLUMNS)
    glucose.to_csv(TARGET, index = False, compression = "gzip")
    print(f"saved {TARGET.name} with {len(glucose)} rows")
    print(glucose["code"].value_counts().head(10).to_string())


if __name__ == "__main__":
    main()