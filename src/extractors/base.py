from pathlib import Path
from typing import Dict, Optional, Union

import numpy as np

from src.progressbar import ProgressReporter

KEY_PPG_RAW = "ppg_signal_raw"
KEY_SPO2_RAW = "spo2_signal_raw"
ADDITIONAL_SIG_NAME = "_signal_raw"

META_GLUCOSE = "glucose"
META_CASEID = "caseid"
META_FS_HZ = "fs_hz"
META_AGE = "age"
META_GENDER = "gender"
META_HEIGHT = "height"
META_WEIGHT = "weight"
META_BMI = "BMI"
META_SUBJECTID = "subjectid"
META_DIABETES = "diabetes_type"
META_NAN_FRACTION = "nan_fraction"

DT_NONE = 0 #no diabetes
DT_T1 = 1 #type 1 diabetes
DT_T2 = 2 #type 2 diabetes
DT_UNSPECIFIED = 3 #dianbetes type not specified


ATTR_AVAIL_PREFIX = "avail_"
ATTR_AVAIL_SPO2 = "avail_spo2_signal"
ATTR_SCHEMA_VERSION = "schema_version"
ATTR_EXTRACTOR_TYPE = "extractor_type"
ATTR_TOTAL_RECS = "total_recordings"
ATTR_TOTAL_SUBJS = "total_subjects"
ATTR_ADDITIONAL_SIG = "additional_signal_names"
ATTR_PPG_MODE = "ppg_mode"


COMPRESSION_ALGO = "gzip"
STEP_NAME_EXTRACTOR = "extractor"

EXTRACTORS: Dict[str, type] = {}


def register_extractor(name):
    def decorator(cls):
        EXTRACTORS[name] = cls
        return cls

    return decorator


class BaseExtractor(ProgressReporter):
    def __init__(self, config):
        self.config = config
        super().__init__()

    def run(
        self,
        name: str,
        out_path: Union[str, Path],
        **kwargs,
    ) -> Path:
        """Run the extractor implementation with standardized logging.

        Args:
            name: Extractor name for logs.
            out_path: Output HDF5 path.
            **kwargs: Extra runtime arguments accepted by subclasses.

        Returns:
            Path to the produced artifact.
        """
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        t0 = self.run_start(step=STEP_NAME_EXTRACTOR, name=name, out_path=out_path)

        try:
            result = self._run_impl(out_path)
            self.run_end(STEP_NAME_EXTRACTOR, t0=t0)
            return Path(result)

        except Exception as e:
            self.handle_exception(e, context=f"Extractor Step [{name}]")
            raise e

    def _run_impl(self, out_path: Path) -> Path:
        """Implement extractor-specific logic in subclasses.

        Args:
            out_path: Destination path.

        Returns:
            Path to the written artifact.
        """
        raise NotImplementedError

    def _save_standardized_group(
        self,
        *,
        f_out,
        group_name,
        ppg,
        meta,
        additional_signals: Optional[Dict[str, np.ndarray]] = None,
    ):
        """Write one recording group with standardized datasets and metadata.

        Args:
            f_out: Open HDF5 output file handle.
            group_name: Group key for the recording.
            ppg: Primary PPG signal array.
            meta: Recording metadata dictionary.
            additional_signals: Optional aligned extra signals.
        """
        if group_name in f_out:
            return

        if ppg is None or len(ppg) == 0:
            return

        grp = f_out.create_group(group_name)

        grp.create_dataset(
            KEY_PPG_RAW, data=ppg.astype(np.float32), compression=COMPRESSION_ALGO
        )

        current_signals = list(f_out.attrs.get(ATTR_ADDITIONAL_SIG, []))
        new_signals_found = False

        if additional_signals:
            for sig_name, sig_data in additional_signals.items():
                # Additional signals must be aligned to PPG and contain real values.
                valid = (
                    sig_data is not None
                    and len(sig_data) == len(ppg)
                    and not np.all(np.isnan(sig_data))
                )

                if valid:
                    ds_name = f"{sig_name}{ADDITIONAL_SIG_NAME}"
                    grp.create_dataset(
                        ds_name,
                        data=sig_data.astype(np.float32),
                        compression=COMPRESSION_ALGO,
                    )
                    grp.attrs[f"{ATTR_AVAIL_PREFIX}{sig_name}_signal"] = True
                    if sig_name not in current_signals:
                        current_signals.append(sig_name)
                        new_signals_found = True
                else:
                    reason = (
                        "Length mismatch"
                        if sig_data is not None and len(sig_data) != len(ppg)
                        else "NaN only or None"
                    )
                    self.log(
                        f"Skipping signal '{sig_name}' for group {group_name}: {reason}",
                        level="debug",
                    )
                    grp.attrs[f"{ATTR_AVAIL_PREFIX}{sig_name}_signal"] = False

        if new_signals_found:
            f_out.attrs[ATTR_ADDITIONAL_SIG] = current_signals

        required_meta = {
            META_GLUCOSE: np.nan,
            META_CASEID: -1,
            META_SUBJECTID: -1,
            META_FS_HZ: 100,
            META_AGE: np.nan,
            META_GENDER: np.nan,
            #META_BMI: np.nan,
        }

        final_meta = required_meta.copy()
        final_meta.update(meta)

        missing = []
        for k, default in required_meta.items():
            v = final_meta.get(k, default)

            invalid = (
                v is None
                or (isinstance(v, float) and np.isnan(v))
                or (isinstance(v, int) and v == -1)
            )

            if invalid:
                missing.append(k)

        if missing:
            raise ValueError(
                f"Missing required meta fields for group '{group_name}': {missing}"
            )

        for key, val in final_meta.items():
            is_valid = (
                val is not None
                and not (isinstance(val, float) and np.isnan(val))
                and val != -1
            )

            if key in [META_CASEID, META_GENDER, META_FS_HZ]:
                val_clean = int(val) if is_valid else -1
            else:
                val_clean = float(val)

            grp.attrs[key] = val_clean

            attr_valid = False
            if (
                isinstance(val_clean, (int, float))
                and not np.isnan(val_clean)
                and val_clean != -1
            ):
                attr_valid = True

            grp.attrs[f"{ATTR_AVAIL_PREFIX}{key}"] = bool(attr_valid)
