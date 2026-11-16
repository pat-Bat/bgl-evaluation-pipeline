from __future__ import annotations

from pathlib import Path

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
    BaseExtractor,
    register_extractor,
)

EXTRACTOR_NAME_MIMIC3 = "mimic3_extractor"
VERSION = 1



STR_WAVES = "waves"
STR_DER = "derived"
STR_CLINICAL = "clinical"
FILE_PATIENTS = "PATIENTS.csv.gz"
FILE_OVERLAPS = "overlaps.csv"
FILE_DUPLICATES = "duplicate_windows.csv"

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
MAX_AGE_CAP = 90 

@register_extractor(EXTRACTOR_NAME_MIMIC3)
class MIMIC3Extractor(BaseExtractor):
    """Extract MIMIC3 signal npz into the standardized HDF5 schema and filters out nan windows."""

    def _run_impl(self, out_path: Path) -> Path:
        """Resample the signal"""
        input_dir = Path(self.config[CONF_INPUT_DIR])
        target_fs = int(self.config.get(CONF_TARGET_FS, 100))
        #orig_fs = int(self.config.get(CONF_ORIG_FS, 125))
        max_nan = float(self.config.get(CONF_MAX_NAN_FRAC, 0.05))

        waves_dir = input_dir / STR_WAVES
        derived_dir = input_dir / STR_DER

        subjects = pd.read_csv(input_dir / STR_CLINICAL / FILE_PATIENTS, usecols=["SUBJECT_ID", "GENDER", "DOB"],
                               parse_dates = ["DOB"]).set_index("SUBJECT_ID")

        diabetes = pd.read_csv( derived_dir / FILE_OVERLAPS, 
                               usecols=["subject_id", "diabetes"]).drop_duplicates("subject_id").set_index("subject_id")["diabetes"]


        npz_files = sorted((waves_dir / "windows").glob("*.npz"))
        #drops windows with multiple glucose values at the same timestamp
        duplicate_names = set(pd.read_csv(derived_dir / FILE_DUPLICATES)["name"])
        npz_files = [f for f in npz_files if f.name not in duplicate_names]
        self.log(f"{len(npz_files)} remaining after duplicate filtering")

        if not npz_files:
            self.log(f"MIMIC3: no npz files found in waves folder: {waves_dir}.")
            return out_path

        with h5py.File(out_path, "w") as f_out:
            f_out.attrs[ATTR_SCHEMA_VERSION] = VERSION
            f_out.attrs[ATTR_EXTRACTOR_TYPE] = EXTRACTOR_NAME_MIMIC3
            f_out.attrs[META_FS_HZ] = target_fs
            #f_out.attrs[CONF_ORIG_FS] = orig_fs
            f_out.attrs[ATTR_PPG_MODE] = PPG_MODE

            count = 0
            skipped = 0
            unique_subjects = set()

            pbar = self.pbar(
                npz_files, desc="Extract MIMIC3", total=len(npz_files), unit="file"
            )

            dm_map = {"none": DT_NONE, "T1": DT_T1, "T2": DT_T2, "mixed": DT_UNSPECIFIED}
            for npz_file in pbar:
                try:
                    with np.load(npz_file) as d:
                        d = np.load(npz_file)
                        sig_raw = d["ppg"]
                        orig_fs = float(d["fs"])
                        gluc = float(d["glucose"])
                        subject_id = int(d["subject_id"])
                        #gluc_source = str(d["source"])
                        time = pd.Timestamp(str(d["time"]))

                        sub = subjects.loc[subject_id]

                    nan_frac = float(np.isnan(sig_raw).mean()) 
                    if nan_frac > max_nan: #skips windows with to many nan values
                        skipped = skipped + 1
                        continue
                    sig_raw = pd.Series(sig_raw).ffill().bfill().to_numpy() #fills remaining nan values with last correct val

                    samples_target = int(sig_raw.__len__() * target_fs / orig_fs)
                    if samples_target < 10:
                        skipped += 1
                        continue
                    sig_ppg = scipy.signal.resample(sig_raw, samples_target)

                    date_birth = sub["DOB"]
                    age = time.year - date_birth.year - ((time.month, time.day) < (date_birth.month, date_birth.day))
                    age = min(age, MAX_AGE_CAP) #subjects over 89 are assigned a false age, so it's set here to 90
                    gender = 1 if sub["GENDER"] == "M" else 0

                    dm = dm_map.get(diabetes.get(subject_id), np.nan)
                    meta = {
                        META_GLUCOSE: gluc,
                        META_CASEID: count,
                        META_SUBJECTID: subject_id,
                        META_FS_HZ: target_fs,
                        META_AGE: age,
                        META_GENDER: gender,
                        #META_WEIGHT: float(row.get(COL_WEIGHT, np.nan)),
                        #META_HEIGHT: float(row.get(COL_HEIGHT, np.nan)),
                        META_BMI: np.nan,
                        META_DIABETES: dm, 
                        META_NAN_FRACTION: nan_frac,
                    }

                    group_name = npz_file.stem
                    self._save_standardized_group(
                        f_out=f_out, group_name=group_name, ppg=sig_ppg, meta=meta
                    )
                    count += 1
                    unique_subjects.add(meta[META_SUBJECTID])

                except Exception as e:
                    self.handle_exception(e)
                    skipped += 1
                    continue

            f_out.attrs[ATTR_TOTAL_RECS] = int(count)
            f_out.attrs[ATTR_TOTAL_SUBJS] = int(len(unique_subjects))

        return out_path
