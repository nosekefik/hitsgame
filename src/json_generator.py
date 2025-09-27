import json
from src.cards_generator import Track

def generate_json(tracks, output_path):
	data = [
		{
			"year": track.year,
			"title": track.title,
			"artist": track.artist,
			"md5sum": track.md5sum,
			"url": track.url,
			"filename": track.out_fname()
		}
		for track in tracks
	]
	with open(output_path, "w", encoding="utf-8") as f:
		json.dump(data, f, indent=4, ensure_ascii=False)
