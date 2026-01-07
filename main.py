import os
import argparse
import shutil
from collections import Counter
from src.models.config import Config
from src.json_generator import generate_json
from src.html_generator import generate_html, load_texts

# Main orchestration

def main():
    parser = argparse.ArgumentParser(description="Generate hits game")
    parser.add_argument("--force", action="store_true", help="Force regeneration of all MP3 and cover files")
    args = parser.parse_args()
    
    config = Config.load("config.toml")
    os.makedirs(config.out_dir, exist_ok=True)
    os.makedirs("build", exist_ok=True)
    track_dir = "tracks"
    
    # If --force, delete all generated MP3 and cover files
    if args.force:
        songs_dir = os.path.join(config.out_dir, "songs")
        covers_dir = os.path.join(config.out_dir, "covers")
        if os.path.exists(songs_dir):
            print(f"Deleting all files in {songs_dir}...")
            shutil.rmtree(songs_dir)
        if os.path.exists(covers_dir):
            print(f"Deleting all files in {covers_dir}...")
            shutil.rmtree(covers_dir)

    from src.tools import process_tracks
    tracks = process_tracks(track_dir, config, force=args.force)
    # Build tables from tracks
    from src.cards_generator import Table
    table = Table.new()
    tables = []
    year_counts = Counter()
    decade_counts = Counter()
    for track in tracks:
        table.append(track)
        year_counts[track.year] += 1
        decade_counts[10 * (track.year // 10)] += 1
        if table.is_full():
            tables.append(table)
            table = Table.new()
    if not table.is_empty():
        tables.append(table)

    # Generate JSON file
    json_output_path = os.path.join(config.out_dir, "index.json")
    generate_json(tracks, json_output_path)
    print(f"JSON index generated at {json_output_path}")

    # Load texts from translations
    texts = load_texts(config)
    generate_html(config.out_dir, config, texts)
    print(f"Website generated in {config.out_dir}")

    from src.cards_generator import generate_cards
    try:
        generate_cards(tables, config)
    except Exception as e:
        print(f"Warning: Cards generation failed: {e}")
    print(f"\nYEAR STATISTICS")
    for year, count in sorted(year_counts.items()):
        print(f"{year}: {count:2} {'#' * count}")
    print(f"\nDECADE STATISTICS")
    for decade, count in sorted(decade_counts.items()):
        print(f"{decade}s: {count:2} {'#' * count}")
    print(f"\nTOTAL: {sum(decade_counts.values())} tracks")


if __name__ == "__main__":
    main()
