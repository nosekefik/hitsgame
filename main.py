import os
import time
from collections import Counter
from src.config import Config
from src.cards_generator import Track, Table
from src.json_generator import generate_json
from src.html_generator import generate_html, load_texts

# Main orchestration

def main():
    config = Config.load("config.toml")
    os.makedirs(config.out_dir, exist_ok=True)
    os.makedirs("build", exist_ok=True)
    track_dir = "tracks"

    table = Table.new()
    tables = []
    tracks = []
    year_counts = Counter()
    decade_counts = Counter()

    # Process all FLAC files in track_dir
    for fname in os.listdir(track_dir):
        if not fname.endswith(".flac"):
            continue
        fname_full = os.path.join(track_dir, fname)
        track = Track.load(config, fname_full)
        track.encode_to_out(config)
        tracks.append(track)

    # Sort tracks and group into tables (pages)
    tracks.sort()
    for track in tracks:
        table.append(track)
        year_counts[track.year] += 1
        decade_counts[10 * (track.year // 10)] += 1
        if table.is_full():
            tables.append(table)
            table = Table.new()
    if not table.is_empty():
        tables.append(table)

    print("YEAR STATISTICS")
    for year, count in sorted(year_counts.items()):
        print(f"{year}: {count:2} {'#' * count}")
    print("\nDECADE STATISTICS")
    for decade, count in sorted(decade_counts.items()):
        print(f"{decade}s: {count:2} {'#' * count}")
    print("\nTOTAL")
    print(f"{sum(decade_counts.values())} tracks")

    pdf_inputs = []
    pdf_outputs = []
    # Generate SVG and PDF for each page side
    for i, table in enumerate(tables):
        p = i + 1
        title_svg = f"build/{p}a.svg"
        qr_svg = f"build/{p}b.svg"
        title_pdf = f"build/{p}a.pdf"
        qr_pdf = f"build/{p}b.pdf"
        pdf_inputs.extend([title_svg, qr_svg])
        pdf_outputs.extend([title_pdf, qr_pdf])
        with open(title_svg, "w", encoding="utf-8") as f:
            f.write(table.render_svg(config, "title", f"{p}a"))
        with open(qr_svg, "w", encoding="utf-8") as f:
            f.write(table.render_svg(config, "qr", f"{p}b"))
    # Convert SVGs to PDFs using Inkscape
    for svg_file, pdf_file in zip(pdf_inputs, pdf_outputs):
        print(f"Converting {svg_file} to {pdf_file} using Inkscape...")
        import subprocess
        subprocess.check_call([
            "inkscape", svg_file, "--export-type=pdf",
            f"--export-filename={pdf_file}", "--export-background=white"
        ])
        for _ in range(20):
            if os.path.isfile(pdf_file):
                break
            time.sleep(0.1)
        if not os.path.isfile(pdf_file):
            print(f"ERROR: PDF was not generated: {pdf_file}")
            exit(1)
    print("Waiting 15 seconds to ensure all PDFs are ready before merging...")
    time.sleep(15)
    print("Merging PDFs into build/cards.pdf...")
    from PyPDF2 import PdfMerger
    merger = PdfMerger()
    for pdf_file in pdf_outputs:
        merger.append(pdf_file)
    merger.write("build/cards.pdf")
    merger.close()
    print("Done! Output is build/cards.pdf.")
    # Generate JSON file
    json_output_path = os.path.join(config.out_dir, "index.json")
    generate_json(tracks, json_output_path)
    print(f"JSON index generated at {json_output_path}")
    # Load texts from translations
    texts = load_texts(config)
    # Generate HTML file
    html_output_path = os.path.join(config.out_dir, "index.html")
    generate_html(config, texts, html_output_path)
    print(f"HTML index generated at {html_output_path}")

if __name__ == "__main__":
    main()
