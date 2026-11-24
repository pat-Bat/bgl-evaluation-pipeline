# download PPG data from MIMIC-III waveform database for all glucose values from overlaps.csv
# 16 min window arround glucose measurement, 8 min before and 8 min after
# no further processing, just download the data

import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import wfdb


DATA = Path(__file__).resolve().parents[2] / "dataset_data" / "mimic3"

#BASE = Path(__file__).resolve().parents[1]
CLIN = DATA / "clinical"
GLU = DATA / "glucose"
WAV = DATA / "waves"
OUT = DATA / "derived"
WIN = DATA / "waves" / "windows"


def fetch_window(row, half): # fetches a PPG window for a glucose measurement, saves it to file and returns info
    name = f"{row['subject_id']}_{row['time']:%Y%m%d_%H%M%S}_{row['source']}.npz" # file name
    fs = float(row["fs"]) # sampling frequency
    rec_len = int((row["record_end"] - row["record_start"]).total_seconds() * fs) # number of requested datapoints
    center = (row["time"] - row["record_start"]).total_seconds() * fs 
    want_from = int(center - half * fs)
    want_to = int(center + half * fs) # desired window of datapoints
    sampfrom = max(0, want_from)
    sampto = min(rec_len, want_to) # edge case (exceding the rec length)
    clipped = (sampfrom != want_from) or (sampto != want_to) # true if windows were clipped


    for attempt in range(3): # 3 tries to download record
        try:
            rec = wfdb.rdrecord(row["record"], pn_dir=row["pn_dir"], # reads PLETH record from website folder
                                sampfrom=sampfrom, sampto=sampto,
                                channel_names=["PLETH"])
            break
        except Exception as e:
            if attempt == 2:
                return name, None, str(e)
            time.sleep(3 * (attempt + 1))
    ppg = np.asarray(rec.p_signal[:, 0], dtype=np.float32) # transform to numpy array

    np.savez_compressed(WIN / name, ppg=ppg, fs=fs, #compress and save the window to file
                        glucose=row["glucose"], source=row["source"],
                        subject_id=row["subject_id"], record=row["record"],
                        time=str(row["time"]),
                        offset_sec=(center - sampfrom) / fs, clipped=clipped)
    nan_frac = float(np.isnan(ppg).mean()) if ppg.size else 1.0 # fraction of NaN values in the window
    info = {"file": name, "subject_id": row["subject_id"], "record": row["record"],
            "time": row["time"], "glucose": row["glucose"], "source": row["source"],
            "fs": fs, "n_samples": ppg.size, "clipped": clipped,
            "nan_fraction": round(nan_frac, 3)}
    return name, info, None


def main():
    ap = argparse.ArgumentParser()

    # window size (in minutes) around glucose measurement, default 16 min (8 min before and 8 min after)
    ap.add_argument("--minutes", type=float, default=16, help="windowlength in minutes")

    # number of parallel downloads, default 4
    ap.add_argument("--workers", type=int, default=4,
                    help="parallel download workers (default 4)")
    ap.add_argument("--min-per-subject", type=int, default=2)
    args = ap.parse_args()



    ovl = pd.read_csv(OUT / "overlaps.csv")             # loads table from script 3, every line is a glucose value with a PLETH window
    for c in ["time", "record_start", "record_end"]:     # formats time
        ovl[c] = pd.to_datetime(ovl[c], format="mixed")
    ovl = ovl.drop_duplicates()

    ovl["name"] = ovl.apply(lambda r: f"{r['subject_id']}_{r['time']:%Y%m%d_%H%M%S}_{r['source']}.npz", # how many done/todo
                      axis=1)


    # drops windows with non unique glucose measurement
    n_gluc = ovl.groupby("name")["glucose"].transform("nunique")
    dup = ovl.loc[n_gluc > 1, "name"].drop_duplicates()
    dup.to_csv(OUT / "duplicate_windows.csv", index=False)
    before = len(ovl)
    ovl = ovl[n_gluc == 1]

    ovl = ovl.drop_duplicates("name").reset_index(drop=True)
    print(f"duplicate free:{len(ovl):,} from {before:,} rows, {len(dup)} faulty windows")


    n = ovl.groupby("subject_id")["time"].transform("nunique") # counts unique glucose times per patient
    ovl = ovl[n >= args.min_per_subject].reset_index(drop=True) # filters patients with at least min_per_subject glucose values


    todo = ovl[~ovl["name"].map(lambda x: (WIN / x).exists())]
    print(f"{len(ovl):,} windows for {ovl['subject_id'].nunique():,} subjects, "
          f"with {len(todo):,} todo ({args.workers} parallel)")

    index_file = OUT / "windows_index.csv"
    half = args.minutes * 60 / 2 #480 sec on each side
    t0, done, errors = time.time(), 0, 0

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(fetch_window, row, half) for _, row in todo.iterrows()]
        for fut in as_completed(futures):
            name, info, err = fut.result()
            done += 1
            if err:
                errors += 1
                print(f"[{done}/{len(todo)}] {name}: error ({err}) - try again next time")
                continue
            pd.DataFrame([info]).to_csv(index_file, mode="a",
                                        header=not index_file.exists(), index=False)
            per = (time.time() - t0) / done
            eta_h = per * (len(todo) - done) / 3600
            print(f"[{done}/{len(todo)}] {name}: NaN {info['nan_fraction']:.0%} | "
                  f"{per:.2f} s/window, Rest ca. {eta_h:.1f} h")
    print(f"done. {errors}.")


if __name__ == "__main__":
    main()
 