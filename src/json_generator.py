import json
from src.tools import output_mp3_name

def generate_json(tracks, output_path):
	# Get url_prefix from config through first track
	url_prefix = tracks[0].url.rsplit('/', 1)[0] + '/' if tracks else ""
	
	data = [
		{
			"year": track.year,
			"title": track.title,
			"artist": track.artist,
			"album": track.album,
			"url": track.url,
			"url_mp3": f"{url_prefix}songs/{track.md5sum}.mp3",
			"cover": track.cover_url
		}
		for track in tracks
	]
	with open(output_path, "w", encoding="utf-8") as f:
		json.dump(data, f, indent=4, ensure_ascii=False)
