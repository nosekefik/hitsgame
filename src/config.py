import tomllib
from typing import NamedTuple

class Config(NamedTuple):
	url_prefix: str
	font: str
	grid: bool
	crop_marks: bool
	language: str
	title: str
	emoji: str = "🎸"
	out_dir: str = "out"

	@staticmethod
	def load(fname: str) -> "Config":
		with open(fname, "rb") as f:
			toml = tomllib.load(f)
			# Filter keys to avoid errors from extra fields in the TOML file
			valid_keys = {k: v for k, v in toml.items() if k in Config._fields}
			return Config(**valid_keys)
