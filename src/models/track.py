import sys
import os
from typing import NamedTuple, Tuple, Optional
from src.tools import metaflac_get_tags
from src.models.config import Config
import qrcode
from qrcode.image.svg import SvgPathImage
from qrcode.compat.etree import ET

class Track(NamedTuple):
    year: int
    fname: str
    title: str
    artist: str
    album: str
    md5sum: str
    url: str
    cover_url: Optional[str]

    def qr_svg(self) -> Tuple[str, int]:
        qr = qrcode.make(self.url, image_factory=SvgPathImage, box_size=8)
        return ET.tostring(qr.path).decode("ascii"), qr.pixel_size / 10

    @staticmethod
    def load(config: Config, fname: str) -> "Track":
        md5sum, tags = metaflac_get_tags(fname)
        title = tags.get("TITLE")
        artist = tags.get("MAINARTIST", tags.get("ARTIST"))
        album = tags.get("ALBUM", "")
        date = tags.get("ORIGINALDATE", tags.get("DATE"))
        if title is None:
            print(f"{fname}: No TITLE tag found.")
            sys.exit(1)
        if artist is None:
            print(f"{fname}: No MAINARTIST or ARTIST tag found.")
            sys.exit(1)
        if date is None:
            print(f"{fname}: No ORIGINALDATE or DATE tag found.")
            sys.exit(1)
        url = config.url_prefix + md5sum + ".ogg"
        
        # Check if cover exists
        cover_path = os.path.join(config.out_dir, "covers", md5sum + ".jpg")
        cover_url = config.url_prefix + "covers/" + md5sum + ".jpg" if os.path.isfile(cover_path) else None
        
        year = int(date[0:4])
        return Track(year, fname, title, artist, album, md5sum, url, cover_url)
