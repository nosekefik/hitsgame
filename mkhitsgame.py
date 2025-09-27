#!/usr/bin/env python3

# Hitsgame -- Build cards for a music game
# Copyright 2023 Ruud van Asseldonk

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

from __future__ import annotations

import html
import json
import os
import os.path
import subprocess
import sys
import tomllib
import time

import qrcode  # type: ignore

from typing import Dict, Iterable, List, Literal, NamedTuple, Tuple
from collections import Counter

from qrcode.image.svg import SvgPathImage  # type: ignore


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


class Track(NamedTuple):
    year: int
    fname: str
    title: str
    artist: str
    md5sum: str
    url: str

    @staticmethod
    def load(config: Config, fname: str) -> Track:
        """
        Create a track from an input filename.
        """
        md5sum, tags = metaflac_get_tags(fname)
        title = tags.get("TITLE")
        artist = tags.get("ARTIST")
        date = tags.get("ORIGINALDATE", tags.get("DATE"))
        if title is None:
            print(f"{fname}: No TITLE tag present.")
            sys.exit(1)
        if artist is None:
            print(f"{fname}: No ARTIST tag present.")
            sys.exit(1)
        if date is None:
            print(f"{fname}: No ORIGINALDATE or DATE tag present.")
            sys.exit(1)

        url = config.url_prefix + md5sum + ".mp4"
        year = int(date[0:4])

        return Track(year, fname, title, artist, md5sum, url)

    def out_fname(self) -> str:
        """
        Returns the output mp4 filename based on the md5sum.
        """
        return self.md5sum + ".mp4"

    def encode_to_out(self) -> None:
        """
        Encode the input flac file to an mp4 file in the output directory,
        under an unpredictable (but reproducible) name based on the audio
        md5sum. The resulting file has all metadata removed on purpose.
        """
        out_dir = os.path.join("out", "songs")  # Updated output directory
        os.makedirs(out_dir, exist_ok=True)
        out_fname = os.path.join(out_dir, self.out_fname())
        if os.path.isfile(out_fname):
            return
        # fmt:off
        subprocess.check_call([
            "ffmpeg",
            "-i", self.fname,
            # Copy the audio stream, and no other stream (no cover art).
            "-map", "0:a",
            # By default ffmpeg copies metadata from the input file (file 0).
            # Disable this by copying from the non-existing file -1 instead.
            "-map_metadata", "-1",
            # Really disable metadata writing, including the encoder tag.
            "-write_xing", "0",
            "-id3v2_version", "0",
            # Downmix stereo to mono (audio channels = 1). When we play the
            # game we listen on a phone speaker or bluetooth speaker anyway.
            "-ac", "1",
            # Encode as AAC at 192kbps.
            "-b:a", "192k",
            "-c:a", "aac",
            out_fname,
        ])
        # fmt:on

    def qr_svg(self) -> Tuple[str, int]:
        """
        Render a QR code for the URL as SVG path, return also the side length
        (in SVG units, which by convention we map to mm).
        """
        from qrcode.compat.etree import ET  # type: ignore

        # A box size of 10 means that every "pixel" in the code is 1mm, but we
        # don't know how many pixels wide and tall the code is, so return that
        # too, the "pixel size". Note, it is independent of the specified box
        # size, we always have to divide by 10.
        qr = qrcode.make(self.url, image_factory=SvgPathImage, box_size=8)
        return ET.tostring(qr.path).decode("ascii"), qr.pixel_size / 10


class Config(NamedTuple):
    url_prefix: str
    font: str
    grid: bool
    crop_marks: bool
    language: str
    title: str  # Added title attribute

    @staticmethod
    def load(fname: str) -> Config:
        with open(fname, "rb") as f:
            toml = tomllib.load(f)
            return Config(**toml)


def line_break_text(s: str) -> List[str]:
    """
    Line break the artist and title so they (hopefully) fit on a card. This
    is a hack based on string lengths, but it's good enough for most cases.
    """
    if len(s) < 24:
        return [s]

    words = s.split(" ")
    char_count = sum(len(word) for word in words)

    # The starting situation is everything on the first line. We'll try
    # out every possible line break and pick the one with the most even
    # distribution (by characters in the string, not true text width).
    top, bot = " ".join(words), ""
    diff = char_count

    # Try line-breaking between every word.
    for i in range(1, len(words) - 1):
        w1, w2 = words[:i], words[i:]
        t, b = " ".join(w1), " ".join(w2)
        d = abs(len(t) - len(b))
        if d < diff:
            top, bot, diff = t, b, d
    return [top, bot]

def render_text_svg(x_mm: float, y_mm: float, s: str, class_: str) -> Iterable[str]:
    """
    Render the artist or title, broken across lines if needed.
    """
    lines = line_break_text(s)
    line_height_mm = 6
    h_mm = line_height_mm * len(lines)
    for i, line in enumerate(lines):
        dy_mm = line_height_mm * (1 + i) - h_mm / 2
        yield (
            f'<text x="{x_mm}" y="{y_mm + dy_mm}" text-anchor="middle" '
            f'class="{class_}">{html.escape(line)}</text>'
        )


class Table(NamedTuple):
    """
    A table of cards laid out on two-sided paper.
    """

    cells: List[Track]

    # Hitster cards are 65mm wide, so on a 210mm wide A4 paper, we can fit
    # 3 columns and still have 7mm margin on both sides. That may be a bit
    # tight but either way, let's do 3 columns.
    width: int = 3

    # In the 297mm A4 paper, if we put 4 rows of 65mm that leaves 37mm of
    # margin, about 20mm top and bottom.
    height: int = 4

    @staticmethod
    def new() -> Table:
        return Table(cells=[])

    def append(self, track: Track) -> None:
        self.cells.append(track)

    def is_empty(self) -> bool:
        return len(self.cells) == 0

    def is_full(self) -> bool:
        return len(self.cells) >= self.width * self.height

    def render_svg(
        self, config: Config, mode: Literal["qr"] | Literal["title"], page_footer: str
    ) -> str:
        """
        Render the front of the page as svg. The units are in millimeters.
        Adds a white background and optional grid (with no black fill).
        """
        # Size of the page and cards
        w_mm = 210
        h_mm = 297
        # Size of the cards / table cells. In the Hitster game I have, the
        # cards have a side length of 65mm. But then fitting the table on A4
        # paper, it is possible, but the margins get very small to the point
        # where the crop marks may fall into the non-printable region. So make
        # the cards slightly smaller so they are safe to print.
        side_mm = 62
        tw_mm = side_mm * self.width
        th_mm = side_mm * self.height
        hmargin_mm = (w_mm - tw_mm) / 2
        vmargin_mm = (h_mm - th_mm) / 2
        # Align the table top-left with a fixed margin and leave more space at
        # the bottom, so we can put a page number there.
        vmargin_mm = hmargin_mm

        parts: List[str] = []
        # SVG header and white background
        parts.append(
            '<svg version="1.1" width="210mm" height="297mm" '
            'viewBox="0 0 210 297" '
            'xmlns="http://www.w3.org/2000/svg">'
        )
        parts.append(
            '<rect x="0" y="0" width="210" height="297" fill="white"/>'
        )
        # CSS styles for text and shapes
        parts.append(
            f"""
            <style>
            text {{ font-family: {config.font!r}; }}
            .year {{ font-size: 18px; font-weight: 900; }}
            .title, .artist, .footer {{ font-size: 5.2px; font-weight: 400; }}
            .title {{ font-style: italic; }}
            rect, line {{ stroke: black; stroke-width: 0.2; }}
            </style>
            """
        )
        # Optional grid (no fill)
        if config.grid:
            parts.append(
                f'<rect x="{hmargin_mm}" y="{vmargin_mm}" '
                f'width="{tw_mm}" height="{th_mm}" '
                'fill="none" stroke-linejoin="miter"/>'
            )
        # Column lines and crop marks
        for ix in range(0, self.width + 1):
            x_mm = hmargin_mm + ix * side_mm
            if config.grid and ix > 0 and ix <= self.width:
                parts.append(
                    f'<line x1="{x_mm}" y1="{vmargin_mm}" '
                    f'x2="{x_mm}" y2="{vmargin_mm + th_mm}" />'
                )
            if config.crop_marks:
                parts.append(
                    f'<line x1="{x_mm}" y1="{vmargin_mm - 5}" x2="{x_mm}" y2="{vmargin_mm - 1}" />'
                    f'<line x1="{x_mm}" y1="{vmargin_mm + th_mm + 1}" x2="{x_mm}" y2="{vmargin_mm + th_mm + 5}" />'
                )
        # Row lines and crop marks
        for iy in range(0, self.height + 1):
            y_mm = vmargin_mm + iy * side_mm
            if config.grid and iy > 0 and iy <= self.height:
                parts.append(
                    f'<line x1="{hmargin_mm}" y1="{y_mm}" '
                    f'x2="{hmargin_mm + tw_mm}" y2="{y_mm}" />'
                )
            if config.crop_marks:
                parts.append(
                    f'<line x1="{hmargin_mm - 5}" y1="{y_mm}" x2="{hmargin_mm - 1}" y2="{y_mm}" />'
                    f'<line x1="{hmargin_mm + tw_mm + 1}" y1="{y_mm}" x2="{hmargin_mm + tw_mm + 5}" y2="{y_mm}" />'
                )
        # Cards: QR or title/artist/year
        for i, track in enumerate(self.cells):
            if mode == "qr":
                # Centered and mirrored QR for double-sided printing
                ix = self.width - 1 - (i % self.width)
                iy = i // self.width
                qr_path, qr_mm = track.qr_svg()
                x_mm = hmargin_mm + ix * side_mm + (side_mm - qr_mm) / 2
                y_mm = vmargin_mm + iy * side_mm + (side_mm - qr_mm) / 2
                parts.append(f'<g transform="translate({x_mm}, {y_mm})">')
                parts.append(qr_path)
                parts.append(f"</g>")

            if mode == "title":
                ix = i % self.width
                iy = i // self.width
                x_mm = hmargin_mm + (ix + 0.5) * side_mm
                y_mm = vmargin_mm + (iy + 0.5) * side_mm
                # Year
                parts.append(
                    f'<text x="{x_mm}" y="{y_mm + 6.5}" text-anchor="middle" '
                    f'class="year">{track.year}</text>'
                )
                # Artist and title
                for part in render_text_svg(x_mm, y_mm - 19, track.artist, "artist"):
                    parts.append(part)
                for part in render_text_svg(x_mm, y_mm + 18, track.title, "title"):
                    parts.append(part)
        # Page footer (page number)
        parts.append(
            f'<text x="{w_mm - hmargin_mm}" y="{h_mm - hmargin_mm}" text-anchor="end" '
            f'class="footer">{html.escape(page_footer)}</text>'
        )
        parts.append("</svg>")
        return "\n".join(parts)

def generate_json(tracks: List[Track], output_path: str) -> None:
    """
    Generate a JSON file containing track information.
    """
    data = [
        {
            "year": track.year,
            "title": track.title,
            "artist": track.artist,
            "md5sum": track.md5sum,
            "url": track.url,
            "filename": track.out_fname()  # Added filename field
        }
        for track in tracks
    ]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def generate_html(config: Config, texts: dict, output_path: str) -> None:
    """
    Generate an HTML file using the provided configuration and texts.
    """
    title = getattr(config, "title", texts.get("title", "Hits!"))
    emoji = getattr(config, "emoji", "🎸")

    html_content = f"""<!DOCTYPE html>
<html lang="{config.language}">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{
      background: linear-gradient(135deg, #1a1a1a 0%, #5d0000 100%);
      margin: 0;
      padding: 0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: 'Montserrat', 'Verdana', sans-serif;
    }}
    .container {{
      width: 100vw;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }}
    .big-btn {{
      display: flex;
      align-items: center;
      justify-content: center;
      background: #b60000;
      color: #fff;
      font-size: 2.2em;
      font-weight: 700;
      border: none;
      border-radius: 50px;
      padding: 38px 60px;
      box-shadow: 0 2px 28px #000c, 0 0px 0px #fff6 inset;
      cursor: pointer;
      transition: background 0.2s, color 0.2s, box-shadow 0.2s, transform 0.18s;
      outline: none;
      letter-spacing: 1px;
      margin-bottom: 20px;
      user-select: none;
      touch-action: manipulation;
      position: relative;
      text-shadow: 0 2px 7px #0008;
      overflow: hidden;
    }}
    .big-btn:active {{
      background: #5d0000;
      color: #eee;
      box-shadow: 0 2px 16px #b60000;
      transform: scale(0.98);
    }}
    .icon {{
      margin-right: 20px;
      font-size: 2em;
      vertical-align: middle;
      filter: drop-shadow(0 2px 5px #0007);
      transition: transform 0.5s cubic-bezier(.68,-0.55,.27,1.55), color .4s;
    }}
    .big-btn.playing .icon {{
      transform: rotate(-30deg) scale(1.15);
      color: #ffd700;
      animation: swing 1.1s infinite cubic-bezier(.68,-0.55,.27,1.55) alternate;
    }}
    .big-btn.paused .icon {{
      transform: none;
      color: #fff;
      animation: none;
    }}
    .big-btn.playing {{
      animation: pulse-btn 1s infinite alternate;
      background: #d40000;
      color: #fff;
      box-shadow: 0 4px 38px #d40000a0;
    }}
    @keyframes pulse-btn {{
      from {{ box-shadow: 0 2px 28px #d40000a0, 0 0px 0px #fff6 inset; }}
      to {{ box-shadow: 0 6px 54px #ff0033a0, 0 0px 0px #fff6 inset; transform: scale(1.05);}}
    }}
    @keyframes swing {{
      0% {{ transform: rotate(-30deg) scale(1.15);}}
      50% {{ transform: rotate(30deg) scale(1.15);}}
      100% {{ transform: rotate(-30deg) scale(1.15);}}
    }}
    @media (max-width: 600px) {{
      .big-btn {{ font-size: 1.3em; padding: 22px 10vw; }}
      .icon {{ font-size: 1.5em; margin-right: 10px; }}
    }}
    h1 {{
      color: #fff;
      font-size: 2em;
      font-weight: 700;
      margin-bottom: 28px;
      text-shadow: 0 2px 7px #0008;
      letter-spacing: 1px;
      user-select: none;
    }}
  </style>
  <link href="https://fonts.googleapis.com/css?family=Montserrat:700&display=swap" rel="stylesheet">
</head>
<body>
  <div class="container">
    <h1>{title}</h1>
    <button class="big-btn paused" id="playBtn">
      <span class="icon" id="emoji">{emoji}</span>
      {texts['button_play']}
    </button>
    <audio id="audioPlayer" src="" preload="auto" style="display:none;"></audio>
  </div>
  <script>
    function getMp4NameFromUrl() {{
      const path = window.location.pathname;
      const mp4Regex = /^\/([a-zA-Z0-9_-]+)\.mp4$/;
      const match = path.match(mp4Regex);
      if (match) {{
        return match[1] + ".mp4";
      }}
      return null;
    }}
    const mp4 = getMp4NameFromUrl();
    const src = mp4 ? `/songs/${{mp4}}` : null;

    const audio = document.getElementById('audioPlayer');
    const playBtn = document.getElementById('playBtn');
    const emoji = document.getElementById('emoji');

    function setBtnState(isPlaying) {{
      if (isPlaying) {{
        playBtn.classList.add('playing');
        playBtn.classList.remove('paused');
        playBtn.innerHTML = `<span class='icon' id='emoji'>{emoji}</span> {texts['button_pause']}`;
      }} else {{
        playBtn.classList.remove('playing');
        playBtn.classList.add('paused');
        playBtn.innerHTML = `<span class='icon' id='emoji'>{emoji}</span> {texts['button_play']}`;
      }}
    }}

    if (!mp4) {{
      playBtn.textContent = "{texts['no_song_detected']}";
      playBtn.disabled = true;
      playBtn.style.background = "#444";
      playBtn.style.color = "#ccc";
      playBtn.style.cursor = "not-allowed";
      if (emoji) emoji.remove();
    }} else {{
      audio.src = src;
      let playing = false;

      playBtn.addEventListener('click', function() {{
        if (audio.paused) {{
          audio.play();
          setBtnState(true);
        }} else {{
          audio.pause();
          setBtnState(false);
        }}
      }});

      document.body.addEventListener('touchstart', function() {{
        if (audio.paused) {{
          audio.play();
          setBtnState(true);
        }}
      }}, {{ once: true }});

      audio.addEventListener('play', function() {{
        setBtnState(true);
      }});
      audio.addEventListener('pause', function() {{
        setBtnState(false);
      }});
      audio.addEventListener('ended', function() {{
        setBtnState(false);
      }});

      // Attempt autoplay
      setTimeout(() => {{
        audio.play().catch(() => {{
          setBtnState(false);
        }});
      }}, 100);
    }}
  </script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

def load_texts(config: Config) -> dict:
    """
    Load the appropriate translation file based on the language in the config.
    Default to English if the specified language file is not found.
    """
    lang_file = os.path.join("translations", f"{config.language}.json")
    default_file = os.path.join("translations", "en.json")

    if os.path.isfile(lang_file):
        with open(lang_file, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        print(f"Warning: Translation file for '{config.language}' not found. Falling back to English.")
        with open(default_file, "r", encoding="utf-8") as f:
            return json.load(f)

def main() -> None:
    # Load config and prepare output folders
    config = Config.load("mkhitsgame.toml")
    os.makedirs("out", exist_ok=True)
    os.makedirs("build", exist_ok=True)
    track_dir = "tracks"

    table = Table.new()
    tables: List[Table] = []
    tracks: List[Track] = []

    year_counts: Counter[int] = Counter()
    decade_counts: Counter[int] = Counter()

    # Process all FLAC files in track_dir
    for fname in os.listdir(track_dir):
        if not fname.endswith(".flac"):
            continue
        fname_full = os.path.join(track_dir, fname)
        track = Track.load(config, fname_full)
        track.encode_to_out()
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

    # Append the final table, which may not be full.
    if not table.is_empty():
        tables.append(table)

    # Print statistics about how many tracks we have per year and per decade,
    # so you can tweak the track selection to make the distribution somewhat
    # more even.
    print("YEAR STATISTICS")
    for year, count in sorted(year_counts.items()):
        print(f"{year}: {count:2} {'#' * count}")

    print("\nDECADE STATISTICS")
    for decade, count in sorted(decade_counts.items()):
        print(f"{decade}s: {count:2} {'#' * count}")

    print("\nTOTAL")
    print(f"{sum(decade_counts.values())} tracks")

    pdf_inputs: List[str] = []
    pdf_outputs: List[str] = []

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

    # Convert SVGs to PDFs using Inkscape,
    # wait until each PDF exists before continuing (max 5 seconds)
    for svg_file, pdf_file in zip(pdf_inputs, pdf_outputs):
        print(f"Converting {svg_file} to {pdf_file} using Inkscape...")
        subprocess.check_call([
            "inkscape",
            svg_file,
            "--export-type=pdf",
            f"--export-filename={pdf_file}",
            "--export-background=white"
        ])
        for _ in range(20):
            if os.path.isfile(pdf_file):
                break
            time.sleep(0.1)
        if not os.path.isfile(pdf_file):
            print(f"ERROR: PDF was not generated: {pdf_file}")
            sys.exit(1)

    # Wait before merging PDFs (20 seconds)
    print("Waiting 15 seconds to ensure all PDFs are ready before merging...")
    time.sleep(15)

    # Merge all PDFs into build/cards.pdf
    print("Merging PDFs into build/cards.pdf...")
    from PyPDF2 import PdfMerger
    merger = PdfMerger()
    for pdf_file in pdf_outputs:
        merger.append(pdf_file)
    merger.write("build/cards.pdf")
    merger.close()
    print("Done! Output is build/cards.pdf.")

    # Generate JSON file
    json_output_path = os.path.join("out", "index.json")
    generate_json(tracks, json_output_path)
    print(f"JSON index generated at {json_output_path}")

    # Load texts from translations/ca.json
    texts = load_texts(config)

    # Generate HTML file
    html_output_path = os.path.join("out", "index.html")
    generate_html(config, texts, html_output_path)
    print(f"HTML index generated at {html_output_path}")

if __name__ == "__main__":
    main()