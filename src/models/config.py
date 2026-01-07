import tomllib
from typing import NamedTuple

class Config(NamedTuple):
    url_prefix: str
    font: str
    grid: bool
    crop_marks: bool
    language: str
    title: str
    out_dir: str = "out"
    mp3_bitrate: str = "190k"

    @staticmethod
    def load(fname: str) -> "Config":
        with open(fname, "rb") as f:
            toml = tomllib.load(f)
            return Config(**toml)
