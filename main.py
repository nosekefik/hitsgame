import os
import sys
import argparse
import shutil
import subprocess
from collections import Counter
from src.models.config import Config
from src.json_generator import generate_json
from src.html_generator import generate_html, load_texts

# Main orchestration

def main():
    parser = argparse.ArgumentParser(description="Generate hits game")
    parser.add_argument("--force", action="store_true", help="Force regeneration of all MP3 and cover files")
    parser.add_argument("--spotify", type=str, metavar="URL", help="Download a Spotify playlist using votify to the tracks folder")
    args = parser.parse_args()
    
    try:
        config = Config.load("config.toml")
    except FileNotFoundError:
        print("\033[91mError: 'config.toml' file not found.\033[0m")
        print("Please copy 'config.toml.example' to 'config.toml' and edit it with your configuration.")
        print("\nExample:")
        print("  cp config.toml.example config.toml")
        sys.exit(1)
    os.makedirs(config.out_dir, exist_ok=True)
    os.makedirs("build", exist_ok=True)
    track_dir = "tracks"
    os.makedirs(track_dir, exist_ok=True)

    # Download from Spotify if URL is provided
    if args.spotify:
        print(f"Downloading from Spotify: {args.spotify}")
        try:
            # We use --album-folder-template "" etc to avoid subfolders if possible, or we just flatten later
            subprocess.check_call([
                "uv", "run", "votify", 
                "--output", track_dir, 
                "--album-folder-template", "",
                "--compilation-folder-template", "",
                "--podcast-folder-template", "",
                "--no-album-folder-template", "",
                args.spotify
            ])
        except subprocess.CalledProcessError as e:
            print(f"\033[91mError downloading from Spotify: {e}\033[0m")
            sys.exit(1)
        
        print("Converting downloaded tracks to FLAC and flattening directory structure...")
        for root_dir, dirs, files in os.walk(track_dir, topdown=False):
            for fname in files:
                input_path = os.path.join(root_dir, fname)
                # If it's already a FLAC file, just move it to the root track_dir if it's inside a subfolder
                if fname.lower().endswith(".flac"):
                    if root_dir != track_dir:
                        dest_path = os.path.join(track_dir, fname)
                        shutil.move(input_path, dest_path)
                    continue
                
                # Convert other audio formats (ogg, m4a, mp3, etc.) to FLAC
                if fname.lower().endswith((".ogg", ".m4a", ".mp3", ".wav", ".opus", ".aac")):
                    flac_fname = os.path.splitext(fname)[0] + ".flac"
                    flac_path = os.path.join(track_dir, flac_fname)
                    print(f"Converting {fname} to FLAC...")
                    try:
                        subprocess.check_call([
                            "ffmpeg", "-y", "-i", input_path, 
                            "-c:a", "flac", flac_path
                        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        os.remove(input_path)
                    except subprocess.CalledProcessError:
                        print(f"Warning: Failed to convert {fname} to FLAC.")
            
            # Remove empty subdirectories
            if root_dir != track_dir and not os.listdir(root_dir):
                os.rmdir(root_dir)

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
