# src/sciwork/imports/__init__.py

from __future__ import annotations

import platform
from .lazyproxy import LazyModule, lazy_module

_MAGIC_HINT = (
	"pip install python-magic-bin"  # Windows
	if platform.system() == "Windows"
	else "pip install python-magic  # plus OS libmagic (e.g. apt install libmagic1)"
)

# Convenience lazy proxies for common imports
np = numpy = lazy_module("numpy", install="pip install numpy", reason="numerical arrays")
pd = pandas = lazy_module("pandas", install="pip install pandas", reason="data analysis and dataframes")
sp = scipy = lazy_module("scipy", install="pip install scipy", reason="scientific computing")
PIL = lazy_module("PIL", install="pip install Pillow", reason="image processing")

ZIPFILE = zipfile = lazy_module("zipfile", install="pip install zipfile", reason="ZIP archives")
pyzipper = lazy_module("pyzipper", install="pip install pyzipper", reason="AES-256 encryption for ZIP archives")
TARFILE = tarfile = lazy_module("tarfile", install="pip install tarfile", reason="TAR archives")
RARFILE = rarfile = lazy_module("rarfile", install="pip install rarfile", reason="RAR archive")

MAGIC = magic = lazy_module("magic", install=_MAGIC_HINT, reason="file type identification")
charset_normalizer = lazy_module("charset_normalizer", install="pip install charset-normalizer", reason="normalize character encodings")
chardet = lazy_module("chardet", install="pip install chardet", reason="detect character encodings")

send2trash = Send2Trash = lazy_module("send2trash", install="pip install Send2Trash", reason="send files to trash")

openpyxl = lazy_module("openpyxl", install="pip install openpyxl", reason="read/write Excel files")
ET = et = lazy_module("xml.etree.ElementTree", install="pip install lxml", reason="read/write XML files")
sif_parser = sif = SIF = lazy_module("sif_parser", install="pip install sif_parser, xarray", reason="read/write SIF files (+ xarray dependency)")

__all__ = [
	"LazyModule", "lazy_module",
	# data
	"np", "numpy", "pd", "pandas", "sp", "scipy",
	# image
	"PIL",
	# ZIP archives
	"ZIPFILE", "zipfile", "pyzipper",
	# TAR archives
	"TARFILE", "tarfile",
	# RAR archives
	"RARFILE", "rarfile",
	# encoding
	"MAGIC", "magic", "charset_normalizer", "chardet",
	# deletion
	"send2trash", "Send2Trash",
	# data
	"openpyxl", "ET", "et", "sif_parser", "sif", "SIF"
]
