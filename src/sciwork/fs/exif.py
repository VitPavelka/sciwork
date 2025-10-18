# src/sciwork/fs/exif.py

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from ..logutil import get_logger

LOG = get_logger(__name__)


# --- Numeric helpers ---
def _ratio_to_float(value: Any) -> Optional[float]:
	"""
	Convert common EXIF rational/tuple representations to ``float``.

	Accepts:
		* Pillow's rational objects (float-castable),
		* ``(numerator, denominator)`` tuples,
		* plain ``int``/``float``.

	:param value: EXIF value to convert.
	:return: Float value or ``None`` if conversion fails.
	"""
	try:
		return float(value)
	except Exception:
		pass

	try:
		if isinstance(value, (tuple, list)) and len(value) == 2:
			num, den = value
			den = float(den)
			if den == 0.0:
				return None
			return float(num) / den
	except Exception:
		return None

	try:
		return float(value)
	except Exception:
		return None


def _dms_to_deg(dms: Any, ref: Any) -> Optional[float]:
	"""
	Convert EXIF DMS (degrees, minutes, seconds) + hemisphere ref to decimal degrees.

	:param dms: Typically, a 3-tuple of rationals (deg, min, sec).
	:param ref: Hemisphere reference (``'N'``, ``'S'``, ``'E'``, ``'W'``).
	:return: Signed decimal degrees or ``None`` if parsing fails.
	"""
	try:
		if not isinstance(dms, (tuple, list)) or len(dms) != 3:
			return None
		d = _ratio_to_float(dms[0])
		m = _ratio_to_float(dms[1])
		s = _ratio_to_float(dms[2])
		if d is None or m is None or s is None:
			return None
		sign = -1.0 if str(ref).upper() in ("S", "W") else 1.0
		return sign * (d + m / 60.0 + s / 3600.0)
	except Exception:
		return None


# --- Tag decoding ---
def _decode_exif_maps(exif_obj: Any, ExifTags: Any) -> Tuple[Dict[str, Any], Dict[str, Any]]:
	"""
	Convert EXIF numeric tag keys to human-readable names and extract GPS sub-IFD.

	Works with the moder Pillow ``Image.getexif()`` object and tolerates odd shapes.

	:param exif_obj: Mapping-like EXIF data (as returned by Pillow) - may be ``None``.
	:param ExifTags: Pillow's :mod:`PIL.ExifTags` module.
	:return: ``(flat_tags, gps_map)``, where keys are strings.
	"""
	tags = getattr(ExifTags, "TAGS", {})
	gpstags = getattr(ExifTags, "GPSTAGS", {})

	flat: Dict[str, Any] = {}
	gps_map: Dict[str, Any] = {}

	if not exif_obj:
		return flat, gps_map

	# 1) Flatten main EXIF tags
	try:
		items = exif_obj.items()
	except Exception:
		items = []

	gps_raw = None
	for k, v in items:
		name = tags.get(k, str(k))
		if name == "GPSInfo":
			gps_raw = v  # often a dict with numeric GPS tags
		else:
			flat[name] = v

	# 2) Decode GPS sub-IFD
	if isinstance(gps_raw, dict):
		for gk, gv in gps_raw.items():
			gps_map[gpstags.get(gk, str(gk))] = gv

	# Some Pillow builds expose get_ifd(); try it as a bonus path
	get_ifd = getattr(exif_obj, "get_ifd", None)
	if callable(get_ifd):
		try:
			gps_ifd = get_ifd(0x8825)  # GPS IFD
			if isinstance(gps_ifd, dict):
				for gk, gv in gps_ifd.items():
					gps_map[gpstags.get(gk, str(gk))] = gv
		except Exception:
			pass

	return flat, gps_map


def _decode_xp_bytes(v: Any) -> Optional[str]:
	"""
	XPTitle/XPComment/XPKeywords in UTF-16-LE -> clean text.

	:param v: Raw field value.
	:return: Decoded string or ``None``.
	"""
	if isinstance(v, (bytes, bytearray)):
		try:
			s = bytes(v).decode("utf-16-le", errors="ignore").rstrip("\x00")
			return s or None
		except Exception:
			return None
	return None


def _gps_to_latlon_from_maps(
		gps_map: Dict[str, Any]
) -> Tuple[Optional[float], Optional[float]]:
	"""
	Extract ``(lat, lon)`` from a decoded GPS tag map.

	:param gps_map: Map with keys like ``GPSLatitude``, ``GPSLatitudeRef``,
					``GPSLongitude``, ``GPSLongitudeRef``.
	:return: ``(lat, lon)`` floats or ``(None, None)`` if not available.
	"""
	try:
		lat = _dms_to_deg(gps_map.get("GPSLatitude"), gps_map.get("GPSLatitudeRef"))
		lon = _dms_to_deg(gps_map.get("GPSLongitude"), gps_map.get("GPSLongitudeRef"))
		return lat, lon
	except Exception:
		return None, None


def _gps_altitude_m(gps_map: Dict[str, Any]) -> Optional[float]:
	"""
	Altitude in meters, respects ``GPSAltitudeRef`` (0=above sea level, 1=below sea level).

	:param gps_map: GPS tag map.
	:return: Altitude in meters, or None if not available.
	"""
	alt = gps_map.get("GPSAltitude")
	if alt is None:
		return None
	val = _ratio_to_float(alt)
	if val is None:
		return None

	ref = gps_map.get("GPSAltitudeRef", 0)
	if isinstance(ref, (bytes, bytearray)):
		ref_int = ref[0] if len(ref) else 0
	else:
		try:
			ref_int = int(ref)
		except Exception:
			ref_int = 0
	sign = -1.0 if ref_int == 1 else 1.0
	return sign * float(val)


# --- Helpers: reading & composing ---
def _read_exif_object(img: Any) -> Any:
	"""
	Return the Exif object for a Pillow image if available, otherwise ``None``.

	Tries modern ``img.getexif()`` first; falls back to old ``_getexif()`` if present.
	"""
	exif = None
	getexif = getattr(img, "getexif", None)
	if callable(getexif):
		try:
			exif = getexif()
		except Exception:
			exif = None
	if exif is None:
		legacy = getattr(img, "_getexif", None)
		if callable(legacy):
			try:
				exif = legacy()
			except Exception:
				exif = None
	return exif


def _basic_info(tag_map: Dict[str, Any]) -> Dict[str, Any]:
	"""
	Extract a compact subset of common EXIF fields (times, make/model).
	"""
	dto = tag_map.get("DateTimeOriginal") or tag_map.get("DateTimeDigitized")
	dt = tag_map.get("DateTime")
	return {
		"datetime_original": dto or None,
		"datetime": dt or None,
		"camera_make": tag_map.get("Make"),
		"camera_model": tag_map.get("Model")
	}


def _dimensions_block(img: Any) -> Dict[str, Any]:
	"""
	Image dimensions block; returns ``{"dimensions": {"width": int, "height": int}}``
	when available, otherwise empty dict.
	"""
	try:
		w = getattr(img, "width", None)
		h = getattr(img, "height", None)
		if w is not None or h is not None:
			return {"dimensions": {"width": w, "height": h}}
	except Exception:
		pass
	return {}


def _orientation_block(tag_map: Dict[str, Any]) -> Dict[str, Any]:
	"""Return ``{"orientation": int}`` if present in EXIF, else empty dict."""
	if "Orientation" in tag_map:
		return {"orientation": tag_map["Orientation"]}
	return {}


def _dpi_block(tag_map: Dict[str, Any]) -> Dict[str, Any]:
	"""
	Build a DPI block like ``{"dpi": {"x": float|None, "y": float|None, "unit": "inch|cm|none"}}``.
	Returns empty dict if nothing useful is present.
	"""
	try:
		x = tag_map.get("XResolution")
		y = tag_map.get("YResolution")
		unit_code = int(tag_map.get("ResolutionUnit", 2) or 2)
		unit = {1: "none", 2: "inch", 3: "cm"}.get(unit_code, "inch")
		if x is not None or y is not None:
			return {"dpi": {"x": x, "y": y, "unit": unit}}
	except Exception:
		pass
	return {}


def _xp_string_block(tag_map: Dict[str, Any]) -> Dict[str, Any]:
	"""
	Decode Windows XP* EXIF strings (XPComment, XPKeywords) into readable text.
	"""
	out: Dict[str, Any] = {}
	xp_comment = _decode_xp_bytes(tag_map.get("XPComment"))
	xp_keywords = _decode_xp_bytes(tag_map.get("XPKeywords"))
	if xp_comment:
		out["xp_comment"] = xp_comment
	if xp_keywords:
		parts = [p.strip() for p in xp_keywords.replace(",", ";").split(";") if p.strip()]
		out["xp_keywords"] = parts or xp_keywords
	return out


def _gps_block(gps_map: Dict[str, Any]) -> Dict[str, Any]:
	"""
	Compose a GPS block like ``{"gps": {"lat": float, "lon": float, "alt" float?}}``
	or return empty dict if coordinates are unavailable.
	"""
	lat, lon = _gps_to_latlon_from_maps(gps_map)
	if lat is None or lon is None:
		return {}
	gps: Dict[str, Any] = {"lat": lat, "lon": lon}
	alt = _gps_altitude_m(gps_map)
	if alt is not None:
		gps["alt"] = alt
	return {"gps": gps}


def _merge(out: Dict[str, Any], piece: Dict[str, Any]) -> None:
	"""Update ``out`` in-place with ``piece`` if it contains any keys."""
	if piece:
		out.update(piece)


def _has_useful_data(d: Dict[str, Any]) -> bool:
	"""Return True if any value looks meaningful (not None/empty)."""
	return any(v not in (None, {}, [], "") for v in d.values())
