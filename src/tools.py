import os
import subprocess
from typing import Dict, Tuple		
import hashlib
import soundfile as sf

def process_tracks(track_dir: str, config, force: bool = False) -> list:
	from src.models.track import Track
	"""
	Process all FLAC files in track_dir, create Track objects, encode audio, sort and return the tracks list.
	"""
	tracks = []
	for fname in os.listdir(track_dir):
		if not fname.endswith(".flac"):
			continue
		fname_full = os.path.join(track_dir, fname)
		# Extract cover and encode audio BEFORE loading Track so cover_url can be properly set
		md5sum, _ = metaflac_get_tags(fname_full)
		ensure_encoded_audio(fname_full, md5sum, config.out_dir, force=force)
		extract_cover_art(fname_full, md5sum, config.out_dir, force=force)
		# Now load the Track with cover already extracted
		track = Track.load(config, fname_full)
		tracks.append(track)
	tracks.sort()
	return tracks

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
		print(f"{fname} has no embedded md5sum, calculating from audio data...")
		with sf.SoundFile(fname) as f:
			pcm = f.read(dtype='int16')
			md5sum = hashlib.md5(pcm.tobytes()).hexdigest()
	tags = [line.split("=", maxsplit=1) for line in lines[1:]]
	tags = [t for t in tags if len(t) == 2]
	return md5sum, {k.upper(): v for k, v in tags}


def output_ogg_name(md5sum: str) -> str:
	"""Return canonical output file name for an OGG file given its md5sum."""
	return md5sum + ".ogg"


def extract_cover_art(input_path: str, md5sum: str, out_dir: str, force: bool = False) -> bool:
	"""
	Extract cover art from FLAC file and save to <out_dir>/covers/<md5sum>.jpg.
	Returns True if cover was extracted, False otherwise.
	"""
	covers_dir = os.path.join(out_dir, "covers")
	os.makedirs(covers_dir, exist_ok=True)
	out_path = os.path.join(covers_dir, f"{md5sum}.jpg")
	
	if not force and os.path.isfile(out_path):
		return True
	
	try:
		# Use ffmpeg to extract cover art
		subprocess.check_call(
			["ffmpeg", "-y", "-i", input_path, "-an", "-vcodec", "copy", out_path],
			stdout=subprocess.DEVNULL,
			stderr=subprocess.DEVNULL
		)
		return True
	except subprocess.CalledProcessError:
		print(f"Warning: Could not extract cover from {input_path}")
		return False


def encode_flac_to_ogg(input_path: str, out_dir: str, out_name: str, force: bool = False) -> str:
	"""
	Encode a FLAC (or any audio supported by ffmpeg) file to mono OGG Vorbis with
	fixed parameters and place the result under `<out_dir>/songs/<out_name>`.

	Returns the absolute path to the output file. If the output already exists,
	no work is performed unless force is True.
	"""
	songs_dir = os.path.join(out_dir, "songs")
	os.makedirs(songs_dir, exist_ok=True)
	out_path = os.path.join(songs_dir, out_name)
	if not force and os.path.isfile(out_path):
		return out_path
	# Use ffmpeg to convert to mono OGG Vorbis quality 5, stripping metadata
	subprocess.check_call([
		"ffmpeg", "-y", "-i", input_path,
		"-map", "0:a",
		"-map_metadata", "-1",
		"-c:a", "libvorbis",
		"-q:a", "5",
		"-ac", "1", "-ar", "44100",
		out_path
	])
	return out_path


def ensure_encoded_audio(input_path: str, md5sum: str, out_dir: str, force: bool = False) -> str:
	"""
	Ensure the audio file identified by md5sum has been encoded and stored under
	`out_dir/songs/<md5>.ogg`. Returns the absolute OGG output path.
	"""
	out_name_ogg = output_ogg_name(md5sum)
	return encode_flac_to_ogg(input_path, out_dir, out_name_ogg, force=force)
