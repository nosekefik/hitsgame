import os
from collections import Counter
from src.models.config import Config
from src.json_generator import generate_json
from src.html_generator import generate_html, load_texts

# Main orchestration

def main():
    config = Config.load("config.toml")
    os.makedirs(config.out_dir, exist_ok=True)
    os.makedirs("build", exist_ok=True)
    track_dir = "tracks"

    from src.tools import process_tracks
    tracks = process_tracks(track_dir, config)
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

    from src.cards_generator import generate_cards
    generate_cards(tables, config)
    # Generate JSON file
    json_output_path = os.path.join(config.out_dir, "index.json")
    generate_json(tracks, json_output_path)
    print(f"JSON index generated at {json_output_path}")
    # Load texts from translations
    texts = load_texts(config)
    generate_html(config.out_dir, config, texts)
    print(f"Website generated in {config.out_dir}")
    print(f"")
    print(f"YEAR STATISTICS")
    for year, count in sorted(year_counts.items()):
        print(f"{year}: {count:2} {'#' * count}")
    print(f"DECADE STATISTICS")
    for decade, count in sorted(decade_counts.items()):
        print(f"{decade}s: {count:2} {'#' * count}")
    print(f"TOTAL: {sum(decade_counts.values())} tracks")


if __name__ == "__main__":
    main()
