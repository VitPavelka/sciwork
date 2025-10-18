# src/sciwork/fs/parsers/uvvis_spc.py

from __future__ import annotations

import struct
from pathlib import Path
from typing import Dict, Tuple, List, Optional, Mapping

import re
import datetime as dt
from zoneinfo import ZoneInfo

from ...imports import numpy as np
from ...imports import pandas as pd

__all__ = ["load_uvvis_spc"]


# --- Tiny Utils ---
def _to_float(m: Optional[re.Match]) -> Optional[float]:
    """Return ``float(m.group(1))`` or ``None`` if not matched/convertible."""
    try:
        return float(m.group(1)) if m else None
    except Exception:
        return None


def _to_int(m: Optional[re.Match]) -> Optional[int]:
    """Return ``int(m.group(1))`` or ``None`` ."""
    try:
        return int(m.group(1)) if m else None
    except Exception:
        return None


def _put(meta: Dict[str, object], key: str, value: object) -> None:
    """Set unconditionally (values may be None to keep explicit keys)."""
    meta[key] = value


def _roughness(arr: np.ndarray) -> float:
    """Mean squared second difference; lower means smoother."""
    d1 = np.diff(arr)
    d2 = np.diff(d1)
    return float(np.mean(d2 * d2)) if len(d2) else float("inf")


def _ascii_runs(b: bytes) -> List[str]:
    """Return a list of printable-ASCII runs (length ≥3) from a byte window."""
    out: List[str] = []
    start = None
    for i, ch in enumerate(b):
        if 32 <= ch <= 126:
            if start is None:
                start = i
        else:
            if start is not None and i - start >= 3:
                out.append(b[start:i].decode("ascii", "ignore"))
            start = None
    if start is not None and len(b) - start >= 3:
        out.append(b[start:].decode("ascii", "ignore"))
    return out


def _first(tokens: List[str], pattern: str) -> Optional[str]:
    """Return first token matching ``pattern`` (regex), else ``None``."""
    rx = re.compile(pattern)
    for t in tokens:
        if rx.search(t):
            return t
    return None


def _nearest(tokens: List[str], anchor: str, pattern: str) -> Optional[str]:
    """Find token matching ``pattern`` closest to the `` anchor `` token."""
    if anchor not in tokens:
        return None
    idx = tokens.index(anchor)
    rx = re.compile(pattern)
    best = None
    for j, t in enumerate(tokens):
        if rx.search(t):
            if best is None or abs(j - idx) < best[0]:
                best = (abs(j - idx), t)
    return best[1] if best else None


def _first_filetime(window: bytes) -> Optional[dt.datetime]:
    """
    Extract the first plausible Windows FILETIME from ``window``.
    :return: Decoded timestamp in UTC (no timezone conversion).
    """
    base = dt.datetime(1601, 1, 1)
    for i in range(0, max(0, len(window) - 8)):
        val = struct.unpack_from("<Q", window, i)[0]
        # translate to datetime, accepts years within an adequate range
        try:
            time_date = base + dt.timedelta(microseconds=val / 10)
        except OverflowError:
            continue
        if 1990 <= time_date.year <= 2100:
            return time_date
    return None


def _apply_tz(t_utc: Optional[dt.datetime], tz: Optional[object]) -> Tuple[Optional[str], Optional[str]]:
    """
    Convert native UTC -> local tz. Returns (iso_local, iso_utc).
    If ``tz`` is ``None`` or conversion is unavailable, ``iso_local`` is ``None``.
    """
    if t_utc is None:
        return None, None
    iso_utc = t_utc.replace(tzinfo=dt.timezone.utc).isoformat(timespec="milliseconds")
    if tz is None:
        return None, iso_utc
    tzinfo = ZoneInfo(tz) if isinstance(tz, str) else tz
    local = t_utc.replace(tzinfo=dt.timezone.utc).astimezone(tzinfo)
    return local.isoformat(timespec="milliseconds"), iso_utc


def _norm(s: str) -> str:
    """Replace control bytes \x00-\x1F with newlines to stabilize regex."""
    return re.sub(r"[\x00-\x1F]+", "\n", s)


def _is_label_like(s: str) -> bool:
    """Heuristics: line looks like another label 'Something.'"""
    return bool(re.match(r"^[A-Za-z][A-Za-z /]*:\s*$", s))


def _cap(chunk: str, label: str, pattern_after: str = r"[^\r\n]+") -> Optional[str]:
    """
    First, try to capture value on the same line (without a newline).
    Then enable jumping to the *next* line - but only if it's not another label.
    """
    # 1) same line (only spaces/tabs, not a new line)
    m = re.search(rf"{re.escape(label)}[ \t]*({pattern_after})", chunk, re.IGNORECASE)
    if m:
        val = m.group(1).strip()
        if val and not _is_label_like(val):
            return val

    # 2) value on the next line (guard: it must not look like a label)
    m2 = re.search(rf"{re.escape(label)}[^\r\n]*\r?\n([^\r\n]+)", chunk, re.IGNORECASE)
    if m2:
        cand = m2.group(1).strip()
        if cand and not _is_label_like(cand):
            return cand

    return None


def _cap_num(chunk: str, label: str) -> Optional[float]:
    """Capture number after `label`."""
    return _to_float(re.search(rf"{re.escape(label)}\D*([0-9.]+)", chunk, re.IGNORECASE))


def _cap_broken_interpolate(chunk: str) -> Optional[str]:
    """
    Finds value of 'InterPol...ate:' even though the label is broken by noise/lines.
    """
    m = re.search(r"InterPol(?:.|\n){0,400}?ate:\s*([^\r\n]+)", chunk, re.IGNORECASE)
    if m:
        val = m.group(1).strip()
        return val or None
    return None


def _empty_to_none(s: Optional[str]) -> Optional[str]:
    return None if s is None or not s.strip() else s


# --- Helpers ---
def _read_bytes(path: Path) -> bytes:
    """
    Load raw bytes from the disk.

    :param path: Path to the file.
    :return: Raw bytes.
    """
    with open(path, "rb") as f:
        return f.read()


# --- Sectioned metadata ---
_SECTION_NAMES = [
    "Software Information",
    "Data Information",
    "Instrument Information",
    "Measurement Properties",
    "Instrument Properties",
    "Attachment Properties",
    "Operation",
    "Sample Preparation Properties"
]

_SCHEMA = {
    "software_information": ["name", "version", "mode"],
    "data_information": ["analyst", "comments", "datetime", "datetime_utc"],
    "instrument_information": ["name", "type", "model_sn"],
    "measurement_properties": [
        "wl_start_nm", "wl_end_nm", "scan_speed", "sampling_interval_nm",
        "auto_sampling_interval", "scan_mode"
    ],
    "instrument_properties": [
        "sr_exchange", "measuring_mode", "slit_width_nm", "light_source_change_nm"
    ],
    "attachment_properties": ["attachment"],
    "operation": ["threshold", "points", "interpolate", "average"],
    "sample_preparation_properties": [
        "weight", "volume", "dilution", "path_length", "additional_information"
    ],
    "stored_data": ["data_block_offset", "data_dtype", "point_count"],
}


def _ensure_schema(meta: Dict[str, Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    """Fills missing keys with None."""
    for section, keys in _SCHEMA.items():
        meta.setdefault(section, {})
        for k in keys:
            meta[section].setdefault(k, None)
    return meta


def _slice_sections(txt: str) -> Mapping[str, str]:
    """
    Return mapping ``section_name -> text chunk`` between headings like
    ``[Measurement Properties]`` and the next heading (or file end).
    """
    heads: List[Tuple[str, int]] = []
    for m in re.finditer(r"\[([A-Za-z ]+)]", txt):
        name = m.group(1).strip()
        if name in _SECTION_NAMES:
            heads.append((name, m.start()))
    heads.sort(key=lambda x: x[1])

    out: Dict[str, str] = {}
    for i, (name, pos) in enumerate(heads):
        end = heads[i + 1][1] if i + 1 < len(heads) else len(txt)
        out[name] = _norm(txt[pos:end])
    return out


def _parse_measurement_props(chunk: str) -> Dict[str, object]:
    """Parse Measurement Properties: range, scan speed/mode, intervals."""
    def get(pat): return re.search(pat, chunk, re.IGNORECASE | re.DOTALL)
    m: Dict[str, object] = {}
    rng = get(r"Wavelength\s*Range\s*\(nm\.\):[^0-9]*([0-9.]+)[^0-9]+([0-9.]+)")
    if rng:
        _put(m, "wl_start_nm", float(rng.group(1)))
        _put(m, "wl_end_nm", float(rng.group(2)))
    _put(m, "scan_speed", _cap(chunk, "Scan Speed:"))
    _put(m, "sampling_interval_nm", _cap_num(chunk, "Sampling Interval:"))
    # Auto Sampling Interval can be number or "Disabled"
    auto = _cap(chunk, "Auto Sampling Interval:")
    if auto is not None:
        auto_num = _to_float(re.search(r"([0-9.]+)", auto))
        _put(m, "auto_sampling_interval", auto_num if auto_num is not None else auto.strip())
    _put(m, "scan_mode", _cap(chunk, "Scan Mode:"))
    return m


def _parse_instrument_props(chunk: str) -> Dict[str, object]:
    """Parse Instrument Properties: measuring mode, slit, SR, light λ."""
    m: Dict[str, object] = {}
    _put(m, "sr_exchange", _cap(chunk, "S/R Exchange:"))
    _put(m, "measuring_mode", _cap(chunk, "Measuring Mode:"))
    _put(m, "slit_width_nm", _cap_num(chunk, "Slit Width:"))
    _put(m, "light_source_change_nm", _cap_num(chunk, "Light Source Change Wavelength:"))
    return m


def _parse_attachment_props(chunk: str) -> Dict[str, object]:
    """Parse Attachment Properties"""
    return {"attachment": _cap(chunk, "Attachment:")}


def _parse_operation_props(chunk: str) -> Dict[str, object]:
    """Parse Operation Properties"""
    out: Dict[str, object] = {}
    _put(out, "threshold", _cap_num(chunk, "Threshold:"))
    _put(out, "points", _to_int(re.search(r"Points:\D*([0-9]+)", chunk, re.IGNORECASE)))
    interp = _cap(chunk, "Interpolate:") or _cap(chunk, "Interpolate:")
    if interp is None:
        interp = _cap_broken_interpolate(chunk)
    _put(out, "interpolate", interp)
    _put(out, "average", _cap(chunk, "Average:"))
    return out


def _parse_sample_prep(chunk: str) -> Dict[str, object]:
    """Parse Sample Preparation Properties"""
    # Values might be blank; keep explicit keys (None) to show presence
    return {
        "weight": _empty_to_none(_cap(chunk, "Weight:", r"[^\r\n]*")),
        "volume": _empty_to_none(_cap(chunk, "Volume:", r"[^\r\n]*")),
        "dilution": _empty_to_none(_cap(chunk, "Dilution:", r"[^\r\n]*")),
        "path_length": _empty_to_none(_cap(chunk, "Path Length:", r"[^\r\n]*")),
        "additional_information": _empty_to_none(_cap(chunk, "Additional Information:", r"[^\r\n]*")),
    }


def _extract_sections(blob: bytes) -> Dict[str, Dict[str, object]]:
    """
    Decode latin-1 text, slice known sections, and parse each subsection.
    Returns a nested dict with keys mirroring the Summary screen.
    """
    txt = blob.decode("latin1", errors="ignore")
    sec = _slice_sections(txt)

    meta: Dict[str, Dict[str, object]] = {
        "software_information": {},
        "data_information": {},
        "instrument_information": {},
        "measurement_properties": {},
        "instrument_properties": {},
        "attachment_properties": {},
        "operation": {},
        "sample_preparation_properties": {},
        "stored_data": {}
    }

    if "Measurement Properties" in sec:
        meta["measurement_properties"] = _parse_measurement_props(sec["Measurement Properties"])
    if "Instrument Properties" in sec:
        meta["instrument_properties"] = _parse_instrument_props(sec["Instrument Properties"])
    if "Attachment Properties" in sec:
        meta["attachment_properties"] = _parse_attachment_props(sec["Attachment Properties"])
    if "Operation" in sec:
        meta["operation"] = _parse_operation_props(sec["Operation"])
    if "Sample Preparation Properties" in sec:
        meta["sample_preparation_properties"] = _parse_sample_prep(sec["Sample Preparation Properties"])

    # Software "Mode" is not always printed; default to Normal Mode if missing
    # (Measuring Mode is parsed above)
    if "Software Information" in sec:
        # try to read explicit "Mode:" only within this section
        mode = _cap(sec["Software Information"], "Mode:")
        meta["software_information"]["mode"] = mode or "Normal Mode"

    return meta


# --- Mining the ASCII cluster (names, VP, dt) ---
def _mine_ascii_cluster(blob: bytes, tz: Optional[object]) -> Dict[str, Dict[str, object]]:
    """
    Extracts detailed ASCII-based cluster information from the provided binary blob. The function aims to identify
    and parse metadata such as software information, instrument details, data information, and related properties.
    This is achieved by analyzing specific ASCII patterns and clusters within the binary data, using regular
    expressions and pre-defined token recognition methods.

    :param blob: The binary data to be analyzed. Expected to contain ASCII patterns or clusters relevant for metadata.
    :param tz: Optional timezone object to apply timezone adjustments for date-time metadata; defaults to None.
    :return: A dictionary containing parsed metadata organized into different categories, such as software information,
             data information, instrument details, and measurement properties.
    """
    out: Dict[str, Dict[str, object]] = {
        "software_information": {},
        "data_information": {},
        "instrument_information": {},
        "measurement_properties": {},
        "instrument_properties": {},
        "attachment_properties": {},
        "operation": {},
        "sample_preparation_properties": {},
        "stored_data": {}
    }

    # Analyst + comments (robust signature)
    m = re.search(rb"\x02([ -~]{1,12})\x0b([ -~]{1,128})", blob)  # analyst / comments
    win_start, win_end = (0, 0)
    if m:
        out['data_information']['analyst'] = m.group(1).decode("ascii", "ignore").strip()
        out['data_information']['comments'] = m.group(2).decode("ascii", "ignore").strip()
        center = m.start()
        win_start, win_end = max(0, center - 256), min(len(blob), center + 256)

    # Collect ASCII tokens in the window (fallback: whole file if not found)
    tokens = _ascii_runs(blob[win_start:win_end]) if m else _ascii_runs(blob)

    # Software
    if "UVProbe" in tokens:
        out['software_information']['name'] = "UVProbe"
        # the version is usually a short float-like token near UVProbe
        ver = _nearest(tokens, "UVProbe", r"^\d+\.\d+$")
        out['software_information']['version'] = ver if ver else None

    # Instrument
    out["instrument_information"]["model_sn"] = _first(tokens, r"^A\d{6,}$")
    out["instrument_information"]["type"] = _first(tokens, r"UV-\d+\s+Series")
    out["instrument_information"]["name"] = _first(tokens, r"UV-\d{3,4}")

    # FILETIME near the cluster → UTC and optional tz presentation
    if m:
        t_utc = _first_filetime(blob[win_start:win_end])
        local_iso, utc_iso = _apply_tz(t_utc, tz)
        if local_iso:
            out["data_information"]["datetime"] = local_iso
            out["data_information"]["datetime_utc"] = utc_iso
        elif utc_iso:
            out["data_information"]["datetime"] = utc_iso  # "fallback: show UTC
            out["data_information"]["datetime_utc"] = utc_iso

    return out


# --- Y-block scan ---
def _find_y_values(
        blob: bytes,
        *,
        n: int,
        bounds: Tuple[float, float] = (-10.0, 10.0)
) -> Tuple[np.ndarray, int, str]:
    """
    Locate the contiguous Y-values block (absorbance).

    The search scans the raw bytes for the *smoothest* contiguous window
    of length ``n`` that decodes to finite values within ``bounds``.
    It tries ``float64`` first and falls back to ``float32``.

    Note
    ----
    The \"smoothest\" window is chosen by minimizing the mean-squared second
    difference (a roughness metric) among plausible candidates.

    :param blob: Full file content.
    :param n: Expected number of points (derived from wavelength range and step).
    :param bounds: Acceptable min/max for absorbance values. Defaults to ``(-10, 10)``.
    :return: Tuple ``(y, offset, dtype_str)`` where ``y`` is ``float64`` array,
             ``offset`` is the byte offset of the block in the file,
             and ``dtype_str`` is ``"float64"`` or ``"float32"``.
    :raises ValueError: If no plausible numeric block is found.
    """
    L = len(blob)
    lo, hi = bounds
    best = None  # (roughness, start, array, dtype_name)

    for dtype, dname, step in (("<f8", "float64", 8), ("<f4", "float32", 4)):
        # Byte-wise scan is fine here; SPC files are small (~tens of kB)
        for start in range(0, L-n * step + 1):
            chunk = blob[start:start + n * step]
            arr = np.frombuffer(chunk, dtype=dtype, count=n)
            if not np.isfinite(arr).all():
                continue
            if arr.min() < lo or arr.max() > hi:
                continue
            if np.std(arr) < 1e-6:  # avoid constant garbage
                continue
            r = _roughness(arr)
            if best is None or r < best[0]:
                best = (r, start, arr.astype(np.float64), dname)
        if best is not None:
            return best[2], int(best[1]), str(best[3])

    raise ValueError("Could not locate Y data block.")


# --- Public API ---
def load_uvvis_spc(path: Path, *, tz: Optional[object] = "Europe/Prague") -> pd.DataFrame:
    """
    Read a Shimadzu UVProbe ``.spc`` file and return a tidy DataFrame.

    :param path: Filesystem path to the SPC file.
    :param tz: If provided (e.g., ``Europe/Prague``), converts the interval FILETIME
               (treated as UTC) to this zone and stores both ``datetime`` (local) and
               ``datetime_utc`` in :attr:`DataFrame.attrs['data_information']`.
               If ``None`` (default), the timestamp is kept in UTC.
    :return:
        Columns: ``wavelength_nm`` (float), ``absorbance`` (float)
        All metadata is placed into **nested** groups within
        :attr:`DataFrame.attrs`::

            software_information, data_information, instrument_information,
            measurement_properties, instrument_properties,
            attachment_properties, operation, sample_preparation_properties,
            stored_data

    :raises FileNotFoundError: If the file does not exist.
    :raises ValueError: If required metadata is missing or the Y-values block cannot be found.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: '{p}'.")

    blob = _read_bytes(p)

    # 1) Precise section parsing
    meta = _extract_sections(blob)

    # 2) Enrich from the compact ASCII cluster (names/versions/analyst/comments/time)
    mined = _mine_ascii_cluster(blob, tz=tz)
    for key in mined:
        meta[key].update({kk: vv for kk, vv in mined[key].items() if vv is not None})

    # Ensure software mode present (fallback)
    meta["software_information"].setdefault("mode", "Normal Mode")

    # Build X from Measurement Properties
    mp = meta["measurement_properties"]
    wl0 = float(mp.get("wl_start_nm") or 0.0)
    wl1 = float(mp.get("wl_end_nm") or 0.0)
    step = float(mp.get("sampling_interval_nm") or 1.0)
    n = int(round((wl1 - wl0) / step)) + 1
    if n <= 1:
        raise ValueError("Invalid wavelength range or sampling step.")

    # 3) Data block
    y, y_offset, y_dtype = _find_y_values(blob, n=n)
    x = np.round(np.linspace(wl0, wl1, n), 3)[::-1]  # y-values are measured in reverse order

    df = pd.DataFrame({"wavelength_nm": x, "absorbance": y})

    # 4) Store metadata (plus data block info)
    meta['stored_data'].update({
        "data_block_offset": int(y_offset),
        "data_dtype": y_dtype,
        "point_count": int(n)
    })
    meta = _ensure_schema(meta)
    df.attrs.update(meta)
    return df
