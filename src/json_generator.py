import json
from src.tools import output_mp4_name

def generate_json(tracks, output_path):
	data = [
		{
			"year": track.year,
			"title": track.title,
			"artist": track.artist,
			"md5sum": track.md5sum,
			"url": track.url,
			"filename": output_mp4_name(track.md5sum)
		}
		for track in tracks
	]
	with open(output_path, "w", encoding="utf-8") as f:
		json.dump(data, f, indent=4, ensure_ascii=False)
