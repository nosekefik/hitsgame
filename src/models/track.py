import sys
from typing import NamedTuple, Tuple
from src.tools import metaflac_get_tags
from src.models.config import Config
import qrcode
from qrcode.image.svg import SvgPathImage
from qrcode.compat.etree import ET

class Track(NamedTuple):
    def qr_svg(self) -> Tuple[str, int]:
        qr = qrcode.make(self.url, image_factory=SvgPathImage, box_size=8)
        return ET.tostring(qr.path).decode("ascii"), qr.pixel_size / 10
    year: int
    fname: str
    title: str
    artist: str
    md5sum: str
    url: str

    @staticmethod
    def load(config: Config, fname: str) -> "Track":
        md5sum, tags = metaflac_get_tags(fname)
        title = tags.get("TITLE")
        artist = tags.get("MAINARTIST", tags.get("ARTIST"))
        date = tags.get("ORIGINALDATE", tags.get("DATE"))
        if title is None:
            print(f"{fname}: No TITLE tag found.")
            sys.exit(1)
        if artist is None:
            print(f"{fname}: No ARTIST tag found.")
            sys.exit(1)
        if date is None:
            print(f"{fname}: No ORIGINALDATE or DATE tag found.")
            sys.exit(1)
        url = config.url_prefix + md5sum + ".mp4"
        year = int(date[0:4])
        return Track(year, fname, title, artist, md5sum, url)
