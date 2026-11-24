from __future__ import annotations

from pathlib import Path

import re
import h5py
import numpy as np
import pandas as pd
import scipy.io
import scipy.signal

from .base import (
    ATTR_EXTRACTOR_TYPE,
    ATTR_SCHEMA_VERSION,
    ATTR_TOTAL_RECS,
    ATTR_TOTAL_SUBJS,
    ATTR_PPG_MODE,
    ATTR_PART,
    KEY_PPG_RAW,
    KEY_SPO2_RAW,
    DT_T1,
    DT_NONE,
    DT_T2,
    DT_UNSPECIFIED,
    META_AGE,
    META_BMI,
    META_CASEID,
    META_FS_HZ,
    META_GENDER,
    META_GLUCOSE,
    META_HEIGHT,
    META_SUBJECTID,
    META_WEIGHT,
    META_DIABETES,
    META_NAN_FRACTION,
    META_INSULIN,
    BaseExtractor,
    register_extractor,
)

EXTRACTOR_NAME_MOVER = "mover_extractor"
VERSION = 1

SIS_WINDOWS = "SIS/derived/ppg/windows"
SIS_INDEX = "SIS/derived/ppg/windows_index.csv"
SIS_DEMOGRAPHICS = "SIS/Tables/sis_emr/EMR/patient_information.csv"
SIS_GLUCOSE = "SIS/derived/glucose_surgery_sis.csv.gz"

EPIC_WINDOWS = "derived/ppg/windows"
EPIC_INDEX = "derived/ppg/windows_index.csv"
EPIC_DEMOGRAPHICS = "Tables/EPIC_EMR/EPIC_EMR/EMR/patient_information.csv"
EPIC_GLUCOSE = "derived/glucose_surgery.csv.gz"

COL_ID = "ID"
COL_GENDER = "Gender"
COL_AGE = "Age"
COL_HEIGHT = "Height"
COL_WEIGHT = "Weight"
COL_GLUCOSE = "Glucose"

CONF_INPUT_DIR = "input_dir"
CONF_TARGET_FS = "target_fs"
#CONF_ORIG_FS = "orig_fs"

PPG_MODE = "transmissive"
CONF_MAX_NAN_FRAC = "max_nan_frac"
CONF_MIN_WINDOWS = "min_windows"

CONF_PART = "part" #epic or sis

AGE_MAX = 100
HEIGHT_RANGE = (50, 250)    # cm
WEIGHT_RANGE = (2, 300)     # kg
OZ_PER_KG = 35.274

DM_MAP = {"none": DT_NONE, "T1": DT_T1, "T2": DT_T2, "unspecified": DT_UNSPECIFIED, "other": DT_UNSPECIFIED, "mixed": DT_UNSPECIFIED}


def _range(x, lower_bound, upper_bound):
    return x.where((x <= upper_bound) & (x >= lower_bound))

def _feet_in_cm(val):
    h = re.match(r"\s*(\d+)'\s*(\d+)?", str(val))
    if not h:
        return np.nan
    else:
        return (int(h.group(1)) * 12 + int(h.group(2) or 0)) * 2.54

def _load_demographics(part, path):
    if part == "sis":
        d = pd.read_csv(path, usecols=["PID", "Age", "Ht", "Wt", "Gender"])
        demo = pd.DataFrame({"case_id": d["PID"], "age": pd.to_numeric(d["Age"], errors="coerce"),
                            "height": pd.to_numeric(d["Ht"], errors="coerce"), "weight": pd.to_numeric(d["Wt"], errors="coerce"),
                            "gender": d["Gender"].str.strip().map({"M": 1, "F": 0})})
    else:
        d = pd.read_csv(path, usecols=["LOG_ID", "BIRTH_DATE", "HEIGHT", "WEIGHT", "SEX"])
        demo = pd.DataFrame({"case_id": d["LOG_ID"], "age": pd.to_numeric(d["BIRTH_DATE"], errors="coerce"),
                            "height": d["HEIGHT"].map(_feet_in_cm), "weight": pd.to_numeric(d["WEIGHT"], errors="coerce") / OZ_PER_KG,
                            "gender": d["SEX"].str.strip().map({"Male": 1, "Female": 0})})
        
    demo["age"] = demo["age"].where(demo["age"] <= AGE_MAX)
    demo["height"] = _range(demo["height"], *HEIGHT_RANGE)
    demo["weight"] = _range(demo["weight"], *WEIGHT_RANGE)
    demo["bmi"] = demo["weight"] / (demo["height"] / 100) ** 2
    return demo.drop_duplicates("case_id").set_index("case_id")


@register_extractor(EXTRACTOR_NAME_MOVER)
class MOVERExtractor(BaseExtractor):
    """Extract MOVER signal npz into the standardized HDF5 schema and filters out nan windows."""

    def _run_impl(self, out_path: Path) -> Path:
        """Resample the signal"""
        input_dir = Path(self.config[CONF_INPUT_DIR])
        target_fs = int(self.config.get(CONF_TARGET_FS, 100))
        #orig_fs = int(self.config.get(CONF_ORIG_FS, 125))
        max_nan = float(self.config.get(CONF_MAX_NAN_FRAC, 0.05))
        part = self.config.get(CONF_PART)
        min_windows = int(self.config.get(CONF_MIN_WINDOWS, 2))


        if part == "sis":
            window_dir = input_dir / SIS_WINDOWS
            index_file = input_dir / SIS_INDEX
            demographic_file = input_dir / SIS_DEMOGRAPHICS
            glucose_file = input_dir / SIS_GLUCOSE
        else:
            window_dir = input_dir / EPIC_WINDOWS
            index_file = input_dir / EPIC_INDEX
            demographic_file = input_dir / EPIC_DEMOGRAPHICS
            glucose_file = input_dir / EPIC_GLUCOSE

        if not index_file.exists():
            self.log(f"MOVER {part}: no index file found: {index_file}")
            return out_path


        index = pd.read_csv(index_file, dtype = {"subject_id": str, "case_id": str})
        index = index.drop_duplicates("file")
        index = index[index["nan_fraction"] <= max_nan]
        n = index.groupby("subject_id")["time"].nunique()
        index = index[index["subject_id"].isin(n[n >= min_windows].index)]
        index = index[index["file"].map(lambda f: (window_dir / f).exists())]
        self.log(f"{part}: {len(index)} windows of {index['subject_id'].nunique()} subjects with <= {max_nan:.0%} NaN and >= {min_windows} windows")
        if index.empty:
            return out_path

        subject_map = {s: i for i, s in enumerate(sorted(index["subject_id"].unique()))}
        case_map = {c: i for i, c in enumerate(sorted(index["case_id"].unique()))}

        index[["subject_id", "case_id"]].drop_duplicates().assign(
            subject_nr = lambda d: d["subject_id"].map(subject_map),
            case_nr = lambda d: d["case_id"].map(case_map),
            ).to_csv(out_path.with_name(out_path.stem + "_id_map.csv"), index=False)


        demo = _load_demographics(part, demographic_file)
        glucose_table = pd.read_csv(glucose_file)

        if part == "sis":
            diabetes = pd.Series(dtype = object)
            insulin = glucose_table.drop_duplicates("PID").set_index("PID")["insulin_intraop"]
        else:
            diabetes = glucose_table.drop_duplicates("MRN").set_index("MRN")["diabetes"]
            insulin = pd.Series(dtype = float)

        with h5py.File(out_path, "w") as f_out:
            f_out.attrs[ATTR_SCHEMA_VERSION] = VERSION
            f_out.attrs[ATTR_EXTRACTOR_TYPE] = EXTRACTOR_NAME_MOVER
            f_out.attrs[META_FS_HZ] = target_fs
            #f_out.attrs[CONF_ORIG_FS] = orig_fs
            f_out.attrs[ATTR_PPG_MODE] = PPG_MODE
            f_out.attrs[ATTR_PART] = part


            count = 0
            skipped = 0
            no_demographics = 0
            unique_subjects = set()

            pbar = self.pbar(
                index.itertuples(), desc=f"Extract MOVER {part}", total=len(index), unit="file"
            )

            for row in pbar:
                try:
                    with np.load(window_dir / row.file) as d:
                        sig_raw = d["ppg"]
                        orig_fs = float(d["fs"])
                        gluc = float(d["glucose"])

                    nan_frac = float(np.isnan(sig_raw).mean()) 
                    if nan_frac > max_nan: #skips windows with to many nan values
                        skipped = skipped + 1
                        continue
                    sig_raw = pd.Series(sig_raw).ffill().bfill().to_numpy() #fills remaining nan values with last correct val

                    if orig_fs != target_fs:
                        samples_target = int(sig_raw.__len__() * target_fs / orig_fs)
                        sig_ppg = scipy.signal.resample(sig_raw, samples_target)
                    else:
                        sig_ppg = sig_raw
                    if len(sig_ppg) < 10:
                        skipped += 1
                        continue

                    if row.case_id not in demo.index:
                        no_demographics += 1
                        continue
                    p = demo.loc[row.case_id]
                    if np.isnan(p["age"]) or np.isnan(p["gender"]):
                        no_demographics += 1
                        continue


                    meta = {
                        META_GLUCOSE: gluc,
                        META_CASEID: case_map[row.case_id],
                        META_SUBJECTID: subject_map[row.subject_id],
                        META_FS_HZ: target_fs,
                        META_AGE: float(p["age"]),
                        META_GENDER: float(p["gender"]),
                        META_WEIGHT: float(p["weight"]),
                        META_HEIGHT: float(p["height"]),
                        META_BMI: float(p["bmi"]),
                        META_DIABETES: DM_MAP.get(diabetes.get(row.subject_id), np.nan), 
                        META_NAN_FRACTION: nan_frac,
                    }

                    if part == "sis":
                        meta[META_INSULIN] = float(bool(insulin.get(row.case_id, False)))

                    self._save_standardized_group(
                        f_out = f_out, group_name = Path(row.file).stem, ppg = sig_ppg, meta = meta
                    )
                    count += 1
                    unique_subjects.add(meta[META_SUBJECTID])

                except Exception as e:
                    self.handle_exception(e)
                    skipped += 1
                    continue

            f_out.attrs[ATTR_TOTAL_RECS] = int(count)
            f_out.attrs[ATTR_TOTAL_SUBJS] = int(len(unique_subjects))


        self.log(f"MOVER {part}: {count} windows, {no_demographics} without age/gender, {skipped} skipped")
        return out_path
