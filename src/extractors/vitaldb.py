import gc
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import vitaldb

from .base import (
    ATTR_EXTRACTOR_TYPE,
    ATTR_SCHEMA_VERSION,
    ATTR_TOTAL_RECS,
    ATTR_TOTAL_SUBJS,
    ATTR_PPG_MODE,
    COMPRESSION_ALGO,
    DT_NONE,
    DT_UNSPECIFIED,
    META_AGE,
    META_BMI,
    META_CASEID,
    META_FS_HZ,
    META_GENDER,
    META_GLUCOSE,
    META_SUBJECTID,
    META_DIABETES,
    BaseExtractor,
    register_extractor,
)

VITALDB_LAB = "https://api.vitaldb.net/labs"
VITALDB_CASES = "https://api.vitaldb.net/cases"
EXTRACTOR_NAME = "vitaldb_extractor"
VERSION = 2

DEFAULT_MAX_WORKERS = 16
DEFAULT_TOTAL_WINDOW_MIN = 16
DEFAULT_FS_HZ = 100

CONF_MAX_CASES = "max_cases"
CONF_TOTAL_WINDOW_MIN = "minute_window"
CONF_FS_HZ = "target_fs"
CONF_MAX_WORKERS = "max_workers"

PPG_MODE = "transmissive"

SIGNAL_CONFIG = {
    "ppg": {"track": "SNUADC/PLETH", "required": True, "index": 0},
    "spo2": {"track": "Solar8000/PLETH_SPO2", "required": True, "index": 1},
    "temp": {
        "track": "Solar8000/BT",
        "required": False,
        "index": 2,
        "stats": ["mean", "std", "min", "max"],
    },
}

REQUIRED_TRACKS = [cfg["track"] for cfg in SIGNAL_CONFIG.values()]


@register_extractor(EXTRACTOR_NAME)
class VitalDBExtractor(BaseExtractor):
    """Extract and align VitalDB waveform windows around glucose measurement times."""

    @staticmethod
    def _download_task(caseid, tracks, interval):
        """Download one case and convert requested tracks to a NumPy array.

        Args:
            caseid: VitalDB case identifier.
            tracks: List of track names to fetch.
            interval: Sampling interval in seconds.

        Returns:
            Tuple ``(caseid, values, download_seconds, error)``.
        """
        try:
            start_dl = time.time()
            case = vitaldb.VitalFile(caseid, tracks)
            vals = case.to_numpy(tracks, interval=interval)
            return caseid, vals, time.time() - start_dl, None
        except Exception as e:
            return caseid, None, 0, e

    def _run_impl(self, out_path: Path) -> Path:
        """Run VitalDB extraction and write standardized groups into an HDF5 file.

        Args:
            out_path: Destination HDF5 path.

        Returns:
            Path to the written HDF5 artifact.
        """
        max_cases = self.config.get(CONF_MAX_CASES, 0)
        total_win = self.config.get(CONF_TOTAL_WINDOW_MIN, DEFAULT_TOTAL_WINDOW_MIN)
        fs_hz = int(self.config.get(CONF_FS_HZ, DEFAULT_FS_HZ))
        max_workers = self.config.get(CONF_MAX_WORKERS, DEFAULT_MAX_WORKERS)

        df_labs = pd.read_csv(VITALDB_LAB)
        df_cases = pd.read_csv(VITALDB_CASES)
        gluc_df = df_labs[df_labs["name"] == "gluc"].sort_values(["caseid", "dt"])

        half_win_sec = (total_win / 2) * 60

        case_groups = list(gluc_df.groupby("caseid", sort=True))
        if max_cases > 0:
            case_groups = case_groups[:max_cases]

        with h5py.File(out_path, "w") as f_out:
            f_out.attrs[ATTR_SCHEMA_VERSION] = VERSION
            f_out.attrs[ATTR_EXTRACTOR_TYPE] = EXTRACTOR_NAME
            f_out.attrs[META_FS_HZ] = fs_hz
            f_out.attrs[ATTR_PPG_MODE] = PPG_MODE

            interval = 1.0 / fs_hz
            case_map = {cid: g for cid, g in case_groups}
            case_iterator = iter(case_groups)
            running_futures = {}  # fut -> caseid mapping
            total_recordings = 0
            unique_subjects = set()

            pbar = self.pbar(case_groups, desc="Extract VitalDB", unit="case")

            executor = ThreadPoolExecutor(max_workers=max_workers)
            try:

                def submit_next():
                    try:
                        caseid, _ = next(case_iterator)
                        fut = executor.submit(
                            VitalDBExtractor._download_task,
                            caseid,
                            REQUIRED_TRACKS,
                            interval,
                        )
                        running_futures[fut] = caseid
                        return True
                    except StopIteration:
                        self.log(
                            "No more cases to submit to executor",
                            level="debug",
                        )
                        return False

                for _ in range(max_workers):
                    if not submit_next():
                        break

                while running_futures:
                    done, _ = wait(
                        running_futures, return_when=FIRST_COMPLETED, timeout=150
                    )

                    # timeout hit with no completions -> mark pending downloads as skipped
                    if not done:
                        self.log(
                            f"Download timeout - skipping {len(running_futures)} stuck downloads",
                            level="warning",
                        )
                        for fut in list(running_futures):
                            caseid = running_futures[fut]
                            cancel_requested = fut.cancel()
                            self.log(
                                (
                                    f"Skipping case {caseid} - download timeout "
                                    f"(cancel_requested={cancel_requested})"
                                ),
                                level="warning",
                            )
                            pbar.update(1)
                        running_futures.clear()

                    for fut in done:
                        caseid = running_futures.pop(fut)
                        submit_next()
                        try:
                            caseid, vals, dl_time, err = fut.result()
                            if err or vals is None:
                                self.log(
                                    f"Case {caseid} download failed: {err}",
                                    level="warning",
                                )
                                pbar.update(1)
                                continue

                            proc_start = time.time()
                            group_df = case_map[caseid]
                            row_data = df_cases.loc[df_cases["caseid"] == caseid]

                            if not row_data.empty:
                                row = row_data.iloc[0]
                                unique_subjects.add(caseid)
                                signals = {}
                                for name, cfg in SIGNAL_CONFIG.items():
                                    raw_series = pd.Series(vals[:, cfg["index"]])
                                    raw_series = raw_series.ffill().bfill()
                                    signals[name] = raw_series.to_numpy()

                                for dt, gluc in group_df[["dt", "result"]].itertuples(
                                    index=False
                                ):
                                    # Build a symmetric time window around each lab event.
                                    center_idx = int(dt * fs_hz)
                                    start_idx = center_idx - int(half_win_sec * fs_hz)
                                    end_idx = center_idx + int(half_win_sec * fs_hz)

                                    if start_idx < 0 or end_idx > len(signals["ppg"]):
                                        continue

                                    if np.isnan(
                                        vals[
                                            start_idx:end_idx,
                                            SIGNAL_CONFIG["ppg"]["index"],
                                        ]
                                    ).all():
                                        continue

                                    meta = {
                                        META_GLUCOSE: gluc,
                                        META_CASEID: caseid,
                                        META_SUBJECTID: row["subjectid"],
                                        META_FS_HZ: fs_hz,
                                        META_AGE: row["age"],
                                        META_GENDER: (
                                            1 if str(row["sex"]).upper() == "M" else 0
                                        ),
                                        META_DIABETES: (np.nan if pd.isna(row["preop_dm"])
                                                        else DT_UNSPECIFIED if row["preop_dm"] == 1 else DT_NONE), #Type unspecified for VitalDB
                                        META_BMI: row["bmi"],
                                        "dt_sec": dt,
                                        "height": row["height"],
                                        "weight": row["weight"],
                                        "preop_dm": row["preop_dm"],
                                        "dt_sec": dt,
                                    }

                                    add_sigs = {
                                        name: signals[name][start_idx:end_idx]
                                        for name in SIGNAL_CONFIG
                                        if name not in ["ppg"]
                                    }

                                    self._save_standardized_group(
                                        f_out=f_out,
                                        group_name=f"case{caseid}_t{int(dt)}",
                                        ppg=signals["ppg"][start_idx:end_idx],
                                        meta=meta,
                                        additional_signals=add_sigs,
                                    )
                                    total_recordings += 1

                                del signals, vals
                            else:
                                self.log(
                                    f"Case {caseid} missing metadata row in cases table; skipping",
                                    level="debug",
                                )

                        except Exception as e:
                            self.handle_exception(e, context=f"Case {caseid}")

                        pbar.update(1)

                    if total_recordings % 50 == 0:
                        f_out.flush()
                        gc.collect()
            finally:
                self.log(
                    "Shutting down download executor (wait=False, cancel_futures=True)",
                    level="debug",
                )
                executor.shutdown(wait=False, cancel_futures=True)
                self.log("Download executor shutdown requested", level="debug")

            f_out.attrs[ATTR_TOTAL_RECS] = int(total_recordings)
            f_out.attrs[ATTR_TOTAL_SUBJS] = int(len(unique_subjects))

        return out_path
