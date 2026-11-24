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
import base64
import requests

import numpy as np
import pandas as pd

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

ARCHIVES = {"sis":   SIS_WAVES / SIS_WAVE, "epic1": WAVES / WAVE_ARCHIVE_1, "epic2": WAVES / WAVE_ARCHIVE_2,
            "epic3": WAVES / WAVE_ARCHIVE_3}

EPIC_NAME = re.compile(r"([0-9a-f]{16})(IP|CB)-\d{4}-\d\d-\d\d-\d\d-\d\d-\d\d-\d{3}Z\.xml$")

FS = 100 
MISSING = -32767 # monitor code for no signal
LENGTH = 16
MAX_GAP_S = 300 # maximum seconds, before a PPG section is split into 2 sections if there is no signal in between

TZ = "America/Los_Angeles" # timezone information


def load_glucose(type):
    if type == "sis":
        glucose = pd.read_csv(SIS / "derived" / "glucose_surgery_sis.csv.gz", parse_dates = ["time"])
        glucose["wave_id"] = glucose["PID"] # only operation ID available for Sis Part
        glucose["subject_id"] = glucose["PID"]
        glucose["case_id"] = glucose["PID"]

    else:
        glucose = pd.read_csv(DATA / "derived" / "glucose_surgery.csv.gz", parse_dates = ["time"])
        ids = pd.read_csv(DATA / "Tables" / "EPIC_MRN_PAT_ID.csv", usecols = ["LOG_ID", "PAT_ID"])
        glucose = glucose.merge(ids.drop_duplicates("LOG_ID"), on = "LOG_ID", how = "inner")
        glucose["wave_id"] = glucose["PAT_ID"] # file name equals PAT_ID
        glucose["subject_id"] = glucose["MRN"] # MRN equals subject_id
        glucose["case_id"] = glucose["LOG_ID"] # LOD_ID equals case_id

    utc_info = glucose["time"].dt.tz_localize(TZ, ambiguous = "NaT", nonexistent = "NaT") # adding timezone information
    glucose["time_utc"] = utc_info.dt.tz_convert("UTC").dt.tz_localize(None)
    glucose = glucose.dropna(subset = ["time_utc"])

    return glucose[["wave_id", "subject_id", "case_id", "time", "time_utc", "glucose", "source"]].drop_duplicates()

        
def determine_Path(type): # datermines if given archive is already fully downloaded and returns its file name
    arch = ARCHIVES[type]
    if arch.exists():
        return arch, True
    return arch.with_suffix(arch.suffix + ".part"), False

def extract_ppg_data(xml_file): # extracts the ppg records out of the xml files
    for block in xml_file.split("<cpc ")[1:]:
        mg = re.search(r'<mg name="PLETH">(.*?)</mg>', block, flags = re.S)
        if not mg:
            continue
        dt = re.search(r'datetime="([^"]+)"', block) # timestamps
        wave = re.search(r'<m name="Wave">([^<]*)<', mg.group(1)) # encode waveforms
        if not dt or not wave:
            continue

        gain = re.search(r'<m name="Gain">([^<]*)<', mg.group(1))
        offset = re.search(r'<m name="Offset">([^<]*)<', mg.group(1))
        if (gain and float(gain.group(1)) != 1.0) or (offset and float(offset.group(1)) != 0.0):
            raise ValueError(f"faulty Gain/Offset: {gain.group(1)} / {offset.group(1)}")

        seconds = int(np.datetime64(dt.group(1)[:19], "s").astype(np.int64)) # transform timestamp
        yield seconds, np.frombuffer(base64.b64decode(wave.group(1)), dtype="<i2")

def save_complete_PPG(blocks, path): # stores complete PPG record as npz
    seconds = np.array(sorted(blocks), dtype = np.int64)
    break_sections = np.where(np.diff(seconds) > MAX_GAP_S)[0] + 1
    start = []
    length = []
    data = []
    for segment in np.split(seconds, break_sections):
        arr = np.full((segment[-1] - segment[0] + 1) * FS, MISSING, dtype=np.int16) # create full len array with no signal value
        for s in segment: # calculates the correct position for each second
            x = blocks[s][:FS]
            i = (s - segment[0]) * FS
            arr[i:i + len(x)] = x 
        start.append(segment[0])
        length.append(arr.size)
        data.append(arr)
    np.savez_compressed(path, seg_start = np.array(start), seg_len = np.array(length), data = np.concatenate(data), fs=FS)


def markDone(collected, curr_folder, npz_dir, type, file_done):
    for w_id, blocks in collected.items():
        if blocks:
            save_complete_PPG(blocks, npz_dir / f"{w_id}_{type}.npz")
    with file_done.open("a") as f:
        f.write(curr_folder + "\n")


def save_ppg_per_subject(type, subjects, npz_dir):
    arch, finished = determine_Path(type)
    file_done = npz_dir.parent / f"{type}_done"
    done = set(file_done.read_text().split()) if file_done.exists() else set()
    print(f"A) {arch.name}: {len(done)} sets done")

    curr_folder = None
    collected = {}
    complete = False

    try:
        with tarfile.open(arch, mode="r|gz") as tar:
            for part in tar:
                if not part.isfile() or not part.name.endswith(".xml"):
                    continue
                folder = part.name.rsplit("/", 1) [0] 
                if folder != curr_folder:
                    if curr_folder is not None and curr_folder not in done:
                        markDone(collected, curr_folder, npz_dir, type, file_done)
                        done.add(curr_folder)
                    curr_folder = folder
                    collected = {}
                    print(f"\r  {len(done):,} folders done", end="")

                if curr_folder in done:
                    continue

                if type == "sis":
                    w_id = folder.rsplit("/", 1) [-1]
                else:
                    p = EPIC_NAME.search(part.name)
                    w_id = p.group(1) if p else None
                if w_id not in subjects:
                    continue
                xml = tar.extractfile(part).read().decode("utf-8", "replace")
                if '<mg name="PLETH">' not in xml:
                    continue
                blocks = collected.setdefault(w_id, {})
                for seconds, samples in extract_ppg_data(xml):
                    blocks.setdefault(seconds, samples)
        complete = finished
    except (EOFError, tarfile.ReadError, OSError):
        print("\n end of downloaded part reached")
    except KeyboardInterrupt:
        print("stopped by user")

    if complete and curr_folder not in done and curr_folder is not None:
        markDone(collected, curr_folder, npz_dir, type, file_done)
        done.add(curr_folder)
    print(f"\n  phase A: {len(done)} folders done, {len(list(npz_dir.glob('*.npz')))} IDs with PLETH")
    if complete:
        print("  archive completely processed")

def load_segments(w_id, npz_dir): # loads all ppg segments of a subject
    segments = []
    for path in sorted(npz_dir.glob(f"{w_id}_*.npz")):
        with np.load(path) as d:
            parts = np.split(d["data"], np.cumsum(d["seg_len"])[:-1])
            segments += list(zip(d["seg_start"].tolist(), parts))
    return segments

def cut_single_window(segments, time_utc, half):
    t = int(pd.Timestamp(time_utc).timestamp())
    for start, arr in segments:
        end = start +  arr.size // FS
        if start <= t < end:
            clipped = False

            want_from = int(t - half - start) * FS # desired window of datapoints
            want_to = int(t + half - start) * FS
            sampfrom = max(0, want_from)
            sampto = min(arr.size, want_to)
            clipped = (sampfrom != want_from) or (sampto != want_to) # true if windows were clipped

            raw = arr[sampfrom:sampto]
            ppg = raw.astype(np.float32)
            ppg[raw == MISSING] = np.nan
            offset = (t - start) - sampfrom / FS
            return ppg, offset, clipped
    return None
            

def cut_windows(glucose, ppg_dir):
    npz_dir = ppg_dir / "full"
    window_dir = ppg_dir / "windows"
    window_dir.mkdir(parents = True, exist_ok = True)

    have = {p.name.split("_")[0] for p in npz_dir.glob("*.npz")} # ids with ppg 
    gluc = glucose[glucose["wave_id"].isin(have)].copy()
    gluc["name"] = [f"{s}_{t:%Y%m%d_%H%M%S}_{src}.npz" for s, t, src in zip(gluc["subject_id"], gluc["time"], gluc["source"])]

    n_gluc = gluc.groupby("name")["glucose"].transform("nunique")
    dup = gluc.loc[n_gluc > 1, "name"].drop_duplicates()
    dup.to_frame().to_csv(ppg_dir / "duplicate_windows.csv", index = False)
    gluc = gluc[n_gluc == 1].drop_duplicates("name")

    todo = gluc[~gluc["name"].map(lambda x: (window_dir / x).exists())]
    print(f"{len(gluc):,} windows, {len(todo)} new, {len(dup)} dropped")

    index_file = ppg_dir / "windows_index.csv"
    half = (LENGTH * 60) / 2
    rows = []

    for w_id, part in todo.groupby("wave_id"):
        segments = load_segments(w_id, npz_dir)
        for r in part.itertuples():
            result = cut_single_window(segments, r.time_utc, half)
            if result is None:
                continue
            ppg, offset, clipped = result

            nan_frac = float(np.isnan(ppg).mean()) if ppg.size else 1.0

            np.savez_compressed(window_dir / r.name, ppg = ppg, fs = float(FS), glucose = r.glucose,
                                source = r.source, subject_id = str(r.subject_id), case_id = str(r.case_id),
                                record = str(w_id), time = str(r.time), time_utc = str(r.time_utc),
                                offset_sec = offset, clipped = clipped)

            rows.append({"file": r.name, "subject_id": r.subject_id, "case_id": r.case_id, "record": w_id,
            "time": r.time, "glucose": r.glucose, "source": r.source, "fs": FS,
            "n_samples": ppg.size, "clipped": clipped, "nan_fraction": round(nan_frac, 3)})

    if rows:
        pd.DataFrame(rows).to_csv(index_file, mode = "a", header = not index_file.exists(), index = False)
    print(f"{len(rows)} windows saved")

    if index_file.exists():
        index = pd.read_csv(index_file)
        usable = index[index["nan_fraction"] <= 0.05]
        n = usable.groupby("subject_id")["time"].nunique()
        print(f"{len(usable)} of {len(index)} windows usable, {(n >= 2).sum()} for subjects with >= 2 measurements")


def main():
    type = sys.argv[1] if len(sys.argv) > 1 else "sis"
    if type not in ARCHIVES:
        raise SystemExit(f"unknown {type}")
    
    ppg_dir = (SIS if type == "sis" else DATA) / "derived" / "ppg"
    npz_dir = ppg_dir / "full"

    npz_dir.mkdir(parents = True, exist_ok = True)

    glucose = load_glucose(type)
    save_ppg_per_subject(type, set(glucose["wave_id"]), npz_dir)
    cut_windows(glucose, ppg_dir)




if __name__ == "__main__":
    main()