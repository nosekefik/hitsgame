import subprocess
import sys
from typing import Dict, Tuple

def metaflac_get_tags(fname: str) -> Tuple[str, Dict[str, str]]:
	"""
	Return the metadata tags (Vorbis comments) from the file. If a tag is
	repeated, only the last value is kept. Returns the audio data md5sum as
	well.
	"""
	out = subprocess.check_output(
		["metaflac", "--show-md5sum", "--export-tags-to=-", fname],
		encoding="utf-8",
	)
	lines = out.splitlines()
	md5sum = lines[0]
	if md5sum == "00000000000000000000000000000000":
		print(f"{fname} has no embedded md5sum, re-encode with -f8")
		sys.exit(1)
	tags = [line.split("=", maxsplit=1) for line in lines[1:]]
	tags = [t for t in tags if len(t) == 2]
	return md5sum, {k.upper(): v for k, v in tags}
