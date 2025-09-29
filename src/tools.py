def process_tracks(track_dir: str, config) -> list:
	from src.models.track import Track
	"""
	Process all FLAC files in track_dir, create Track objects, encode audio, sort and return the tracks list.
	"""
	tracks = []
	for fname in os.listdir(track_dir):
		if not fname.endswith(".flac"):
			continue
		fname_full = os.path.join(track_dir, fname)
		track = Track.load(config, fname_full)
		ensure_encoded_audio(track.fname, track.md5sum, config.out_dir)
		tracks.append(track)
	tracks.sort()
	return tracks
import os
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
		print(f"{fname} has no embedded md5sum, please re-encode with -f8")
		sys.exit(1)
	tags = [line.split("=", maxsplit=1) for line in lines[1:]]
	tags = [t for t in tags if len(t) == 2]
	return md5sum, {k.upper(): v for k, v in tags}


def encode_flac_to_aac_mp4(input_path: str, out_dir: str, out_name: str) -> str:
	"""
	Encode a FLAC (or any audio supported by ffmpeg) file to mono AAC-in-MP4 with
	fixed parameters and place the result under `<out_dir>/songs/<out_name>`.

	Returns the absolute path to the output file. If the output already exists,
	no work is performed.
	"""
	songs_dir = os.path.join(out_dir, "songs")
	os.makedirs(songs_dir, exist_ok=True)
	out_path = os.path.join(songs_dir, out_name)
	if os.path.isfile(out_path):
		return out_path
	# Use ffmpeg to convert to mono AAC 128k inside MP4 container, stripping metadata
	subprocess.check_call([
        "ffmpeg", "-i", input_path, 
        "-map", "0:a",
		"-map_metadata", "-1",
        "-movflags", "faststart",
        "-c:a", "aac",
		"-b:a", "128k",
        "-profile:a", "aac_low",    
        "-ac", "1", "-ar", "44100",
        out_path
    ])

	return out_path


def output_mp4_name(md5sum: str) -> str:
	"""Return canonical output file name for a song given its md5sum."""
	return md5sum + ".mp4"


def ensure_encoded_audio(input_path: str, md5sum: str, out_dir: str) -> str:
	"""
	Ensure the audio file identified by md5sum has been encoded and stored under
	`out_dir/songs/<md5>.mp4`. Returns the absolute output path.
	"""
	out_name = output_mp4_name(md5sum)
	return encode_flac_to_aac_mp4(input_path, out_dir, out_name)
