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
    BaseExtractor,
    register_extractor,
)

EXTRACTOR_NAME_MUST = "must_extractor"
VERSION = 1

DIR_LABELS = "Labels"
DIR_RAW = "RawData"

STR_LABEL = "label"
STR_SIGNAL = "signal"

COL_ID = "ID"
COL_GENDER = "Gender"
COL_AGE = "Age"
COL_HEIGHT = "Height"
COL_WEIGHT = "Weight"
COL_GLUCOSE = "Glucose"

CONF_INPUT_DIR = "input_dir"
CONF_TARGET_FS = "target_fs"
CONF_ORIG_FS = "orig_fs"

PPG_MODE = "reflective"

@register_extractor(EXTRACTOR_NAME_MUST)
class MUSTExtractor(BaseExtractor):
    """Extract MUST label/signal CSV pairs into the standardized HDF5 schema."""

    def _run_impl(self, out_path: Path) -> Path:
        """Parse per-subject CSV pairs, resample PPG, and persist one group per sample."""
        input_dir = Path(self.config[CONF_INPUT_DIR])
        target_fs = int(self.config.get(CONF_TARGET_FS, 100))
        orig_fs = int(self.config.get(CONF_ORIG_FS, 2175))

        labels_dir = input_dir / DIR_LABELS
        raw_dir = input_dir / DIR_RAW
        csv_files = sorted(labels_dir.glob("*.csv"))

        if not csv_files:
            self.log(f"MUST: no CSV files found in Labels folder: {labels_dir}.")
            return out_path

        with h5py.File(out_path, "w") as f_out:
            f_out.attrs[ATTR_SCHEMA_VERSION] = VERSION
            f_out.attrs[ATTR_EXTRACTOR_TYPE] = EXTRACTOR_NAME_MUST
            f_out.attrs[META_FS_HZ] = target_fs
            f_out.attrs[CONF_ORIG_FS] = orig_fs
            f_out.attrs[ATTR_PPG_MODE] = PPG_MODE

            count = 0
            skipped = 0
            unique_subjects = set()

            pbar = self.pbar(
                csv_files, desc="Extract MUST", total=len(csv_files), unit="file"
            )
            for csv_file in pbar:
                try:
                    df = pd.read_csv(csv_file)
                    if df.empty:
                        skipped += 1
                        continue
                    row = df.iloc[0]

                    base_name = csv_file.stem.lower().replace(STR_LABEL, STR_SIGNAL)
                    sig_csv_path = raw_dir / f"{base_name}.csv"
                    if not sig_csv_path.exists():
                        continue

                    df_sig = pd.read_csv(sig_csv_path)

                    sig_raw = df_sig.iloc[:, 0].values.astype(np.float32)

                    samples_target = int(sig_raw.__len__() * target_fs / orig_fs)
                    if samples_target < 10:
                        skipped += 1
                        continue

                    sig_ppg = scipy.signal.resample(sig_raw, samples_target)

                    # Dataset encodes sex as text; convert to compact binary flag.
                    gender = 1 if str(row.get(COL_GENDER, "")).lower() == "male" else 0
                    height = float(row.get(COL_HEIGHT, 0) or 0)
                    weight = float(row.get(COL_WEIGHT, 0) or 0)
                    bmi = 0.0
                    if height > 0 and weight > 0:
                        h_m = height / 100.0
                        bmi = weight / (h_m * h_m)

                    meta = {
                        META_GLUCOSE: float(row.get(COL_GLUCOSE, np.nan)),
                        #META_CASEID: base_name.split("_")[1],
                        #META_SUBJECTID: base_name.split("_")[2],
                        META_CASEID: int(row.get(COL_ID)) * 1000 + int(base_name.split("_")[2]), #e.g. label_02_0002 -> 2002
                        META_SUBJECTID: int(row.get(COL_ID)),
                        META_FS_HZ: target_fs,
                        META_AGE: float(row.get(COL_AGE, np.nan)),
                        META_GENDER: gender,
                        META_WEIGHT: float(row.get(COL_WEIGHT, np.nan)),
                        META_HEIGHT: float(row.get(COL_HEIGHT, np.nan)),
                        META_BMI: bmi,
                        META_DIABETES: np.nan,  # MUST dataset has no diabetes information
                    }

                    group_name = f"case_{base_name}"
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
