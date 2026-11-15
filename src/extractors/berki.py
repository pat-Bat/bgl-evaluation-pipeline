from __future__ import annotations

from pathlib import Path

import wfdb
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
    DT_T1,
    DT_NONE,
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

EXTRACTOR_NAME_BERKI = "berki_extractor"
VERSION = 1


COL_ID = "id"
COL_GENDER = "sex"
COL_AGE = "age"
COL_HEIGHT = "height"
COL_WEIGHT = "weight"
COL_NAME = "name"
COL_DIABETES = "diabetes"

CONF_INPUT_DIR = "input_dir"
CONF_TARGET_FS = "target_fs"

PPG_MODE = "reflective"

GLUC_CONVERSION = 18.016

@register_extractor(EXTRACTOR_NAME_BERKI)
class BERKIExtractor(BaseExtractor):
    """Extract BERKI hea files into the standardized HDF5 schema."""

    def _run_impl(self, out_path: Path) -> Path:
        """Parse per-subject CSV pairs, resample PPG, and persist one group per sample."""
        input_dir = Path(self.config[CONF_INPUT_DIR])
        target_fs = int(self.config.get(CONF_TARGET_FS, 100))
        



        subjects = pd.read_csv(input_dir / "subjects.csv").set_index(COL_NAME)
        hea_files = sorted(input_dir.glob("Subject_*/*.hea"))
        

        if not hea_files:
            self.log(f"BERKI: no hea files found in Labels folder: {input_dir}.")
            return out_path

        with h5py.File(out_path, "w") as f_out:
            f_out.attrs[ATTR_SCHEMA_VERSION] = VERSION
            f_out.attrs[ATTR_EXTRACTOR_TYPE] = EXTRACTOR_NAME_BERKI
            f_out.attrs[META_FS_HZ] = target_fs
            
            f_out.attrs[ATTR_PPG_MODE] = PPG_MODE

            count = 0
            skipped = 0
            unique_subjects = set()

            pbar = self.pbar(
                hea_files, desc="Extract BERKI", total=len(hea_files), unit="file"
            )
            for hea in pbar:
                try:
                    rec_path = str(hea.with_suffix(""))
                    rec = wfdb.rdrecord(rec_path)
                    anno = wfdb.rdann(rec_path, "atr")
                    sub = subjects.loc[hea.parent.name]
                    sig_raw = rec.p_signal[:, rec.sig_name.index("IR1")]





                    samples_target = int(sig_raw.__len__() * target_fs / rec.fs)
                    if samples_target < 10:
                        skipped += 1
                        continue

                    sig_ppg = scipy.signal.resample(sig_raw, samples_target)

                    
                    gender = 1 if str(sub.get(COL_GENDER, "")).lower() == "m" else 0
                    height = float(sub.get(COL_HEIGHT, 0) or 0)
                    weight = float(sub.get(COL_WEIGHT, 0) or 0)
                    bmi = 0.0
                    if height > 0 and weight > 0:
                        h_m = height / 100.0
                        bmi = weight / (h_m * h_m)

                    meta = {
                        META_GLUCOSE: float(anno.aux_note[0].split()[1]) * GLUC_CONVERSION, # 1 mmol/L ≈ 18,016 mg/dL
                        META_CASEID: int(rec.record_name.replace("data", "")),
                        META_SUBJECTID: int(sub.get(COL_ID)),
                        META_FS_HZ: target_fs,
                        META_AGE: float(sub.get(COL_AGE, np.nan)),
                        META_GENDER: gender,
                        META_WEIGHT: float(sub.get(COL_WEIGHT, np.nan)),
                        META_HEIGHT: float(sub.get(COL_HEIGHT, np.nan)),
                        META_BMI: bmi,
                        META_DIABETES: DT_T1 if sub[COL_DIABETES] == "Yes" else DT_NONE,  # BERKI dataset has only T1 diabetic subjects
                    }

                    group_name = f"case_{rec.record_name}"
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
