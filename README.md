# Hitsgame

## Table of Contents
1. [Overview](#overview)
2. [Requirements](#requirements)
3. [Preparation](#preparation)
4. [Configuration](#configuration)
5. [Deployment](#deployment)
6. [How to Play](#how-to-play)
7. [License](#license)

## Overview

This is a customized version based on the original [Hitsgame by ruuda](https://github.com/ruuda/hitsgame).

Build your own version of the game [Hitster][hitster]. The resulting cards contain a QR code that points to an audio file on a webserver, no Spotify is needed to play. The program generates a PDF with cards like this:

![Two sides of an example output page](example.png)

## Requirements

- **Music files:** FLAC files with proper tags (`TITLE`, `ARTIST`, `ALBUM`, and `ORIGINALDATE` or `DATE`). Cover art embedded in the FLAC file is optional but recommended.
- **Hardware:** Printer, paper cutter or scissors, A4 paper (180 g/m²), tokens (from Hitster or alternatives like poker chips)
- **Software:**
  - Python ≥ 3.11 (`pip install -r requirements.txt`)
  - flac (for `metaflac`)
  - ffmpeg (for audio encoding and cover extraction)
  - inkscape (for PDF generation)

Note: `flac`, `ffmpeg`, and `inkscape` must be in your system's PATH.

## Preparation

1. Create a directory named `tracks` and add the music files you want to include.
2. Create a file named `config.toml` next to the `tracks` directory, and add the configuration as shown in the [Configuration](#configuration) section.
3. Run `main.py`. It will print statistics about the track distribution over years and decades, so you can tweak the track selection to balance out the game.
4. After running the script, you will find a new directory: `out` (or the directory specified in `out_dir`). This directory contains:
   - The tracks, compressed and anonymized in MP3 format at the configured bitrate (default 190kbps), inside a `songs` subdirectory. These files have no metadata and the filenames are long enough to be virtually unguessable.
   - The cover art extracted from the FLAC files, inside a `covers` subdirectory (as `.jpg` files).
   - The PDF file with the cards (`cards.pdf`).
   - The web player files (`index.html`, `index.json`, and related assets).
5. Upload the contents of your `out` to your webserver.
6. Print `cards.pdf` and cut out the cards.


## Configuration

The `config.toml` file follows this format:

```toml
# The url prefix that your webserver will serve the track files from.
url_prefix = "http://example.com/"

# Font to use on the cards.
font = "Arial"

# Draw grid: enable for scissors, disable for paper cutter.
grid = true

# Whether to include crop marks at the sides of the page. If you are cutting with a paper cutter, you should enable this to know where to cut.
crop_marks = false

# Default language (optional, defaults to 'en').
language = "en"

# Game title (optional, defaults to 'Hits!').
title = "Hits Custom Version!"

# Default emoji (optional, defaults to '🎸').
emoji = "🎸"

# Output directory (optional, defaults to 'out').
out_dir = "custom_out"

# MP3 encoding bitrate (optional, defaults to '190k').
# Any ffmpeg-valid value is accepted, e.g. '128k', '192k', '256k'.
mp3_bitrate = "190k"
```



## Deployment

Upload the contents of the `out` directory to your web server (e.g., Nginx) to serve the game files. Example Nginx configuration:

```nginx
server {
   listen 80;
   server_name example.com/;

   root /var/www/html;

   location /songs/ {
      try_files $uri =404;
   }

   location /covers/ {
      try_files $uri =404;
   }

   location ~* \.(html|css|js|pdf|json)$ {
      try_files $uri =404;
   }

   location / {
      try_files /index.html =404;
   }
}
```

This configuration ensures that the `songs` directory serves the audio files (MP3 format), the `covers` directory serves the cover art images, and the root serves the web player files.


## How to Play

Refer to [the original game rules][howplay] for how to play the game itself. You do not need to connect Spotify. Scanning a QR code will open the track in your browser. Most browsers will auto-play the track.


## License

Hitsgame is free software. It is licensed under the [GNU General Public License][gplv3], version 3.

[gplv3]:   https://www.gnu.org/licenses/gpl-3.0.html
[hitster]: https://boardgamegeek.com/boardgame/318243/hitster
[howplay]: https://hitstergame.com/en-us/how-to-play-premium/
