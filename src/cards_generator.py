import os
import time
import html
import subprocess
import shutil
from typing import List, Iterable, Literal, NamedTuple
from PyPDF2 import PdfMerger
from src.models.track import Track
from src.models.config import Config

def generate_cards(tables, config):
	temp_dir = "temp"
	out_dir = config.out_dir if hasattr(config, 'out_dir') else "out"
	os.makedirs(temp_dir, exist_ok=True)
	os.makedirs(out_dir, exist_ok=True)
	pdf_inputs = []
	pdf_outputs = []
	# Generate SVG and PDF for each page side
	for i, table in enumerate(tables):
		p = i + 1
		title_svg = os.path.join(temp_dir, f"{p}a.svg")
		qr_svg = os.path.join(temp_dir, f"{p}b.svg")
		title_pdf = os.path.join(temp_dir, f"{p}a.pdf")
		qr_pdf = os.path.join(temp_dir, f"{p}b.pdf")
		pdf_inputs.extend([title_svg, qr_svg])
		pdf_outputs.extend([title_pdf, qr_pdf])
		with open(title_svg, "w", encoding="utf-8") as f:
			f.write(table.render_svg(config, "title", f"{p}a"))
		with open(qr_svg, "w", encoding="utf-8") as f:
			f.write(table.render_svg(config, "qr", f"{p}b"))
	# Convert SVGs to PDFs using Inkscape
	for svg_file, pdf_file in zip(pdf_inputs, pdf_outputs):
		print(f"Converting {svg_file} to {pdf_file} using Inkscape...")
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
	final_pdf = os.path.join(out_dir, "cards.pdf")
	print(f"Merging PDFs into {final_pdf}...")
	merger = PdfMerger()
	for pdf_file in pdf_outputs:
		merger.append(pdf_file)
	merger.write(final_pdf)
	merger.close()
	print(f"Done! Output is {final_pdf}.")
	# Remove temporary SVG and PDF files and temp dir
	try:
		shutil.rmtree(temp_dir)
	except Exception as e:
		print(f"Warning: could not remove temp dir {temp_dir}: {e}")

def line_break_text(s: str) -> List[str]:
	if len(s) < 24:
		return [s]
	words = s.split(" ")
	char_count = sum(len(word) for word in words)
	top, bot = " ".join(words), ""
	diff = char_count
	for i in range(1, len(words) - 1):
		w1, w2 = words[:i], words[i:]
		t, b = " ".join(w1), " ".join(w2)
		d = abs(len(t) - len(b))
		if d < diff:
			top, bot, diff = t, b, d
	return [top, bot]

def render_text_svg(x_mm: float, y_mm: float, s: str, class_: str) -> Iterable[str]:
	lines = line_break_text(s)
	line_height_mm = 6
	h_mm = line_height_mm * len(lines)
	for i, line in enumerate(lines):
		dy_mm = line_height_mm * (1 + i) - h_mm / 2
		yield (
			f'<text x="{x_mm}" y="{y_mm + dy_mm}" text-anchor="middle" class="{class_}">{html.escape(line)}</text>'
		)

class Table(NamedTuple):
	cells: List[Track]
	width: int = 3
	height: int = 4
	@staticmethod
	def new() -> "Table":
		return Table(cells=[])
	def append(self, track: Track) -> None:
		self.cells.append(track)
	def is_empty(self) -> bool:
		return len(self.cells) == 0
	def is_full(self) -> bool:
		return len(self.cells) >= self.width * self.height
	def render_svg(self, config: Config, mode: Literal["qr"] | Literal["title"], page_footer: str) -> str:
		# ...existing code for SVG rendering...
		w_mm = 210
		h_mm = 297
		side_mm = 62
		tw_mm = side_mm * self.width
		th_mm = side_mm * self.height
		hmargin_mm = (w_mm - tw_mm) / 2
		vmargin_mm = (h_mm - th_mm) / 2
		vmargin_mm = hmargin_mm
		parts: List[str] = []
		parts.append('<svg version="1.1" width="210mm" height="297mm" viewBox="0 0 210 297" xmlns="http://www.w3.org/2000/svg">')
		parts.append('<rect x="0" y="0" width="210" height="297" fill="white"/>')
		parts.append(f"""
			<style>
			text {{ font-family: {config.font!r}; }}
			.year {{ font-size: 18px; font-weight: 900; }}
			.title, .artist, .footer {{ font-size: 5.2px; font-weight: 400; }}
			.title {{ font-style: italic; }}
			rect, line {{ stroke: black; stroke-width: 0.2; }}
			</style>
			""")
		if config.grid:
			parts.append(f'<rect x="{hmargin_mm}" y="{vmargin_mm}" width="{tw_mm}" height="{th_mm}" fill="none" stroke-linejoin="miter"/>')
		for ix in range(0, self.width + 1):
			x_mm = hmargin_mm + ix * side_mm
			if config.grid and ix > 0 and ix <= self.width:
				parts.append(f'<line x1="{x_mm}" y1="{vmargin_mm}" x2="{x_mm}" y2="{vmargin_mm + th_mm}" />')
			if config.crop_marks:
				parts.append(f'<line x1="{x_mm}" y1="{vmargin_mm - 5}" x2="{x_mm}" y2="{vmargin_mm - 1}" />'
							 f'<line x1="{x_mm}" y1="{vmargin_mm + th_mm + 1}" x2="{x_mm}" y2="{vmargin_mm + th_mm + 5}" />')
		for iy in range(0, self.height + 1):
			y_mm = vmargin_mm + iy * side_mm
			if config.grid and iy > 0 and iy <= self.height:
				parts.append(f'<line x1="{hmargin_mm}" y1="{y_mm}" x2="{hmargin_mm + tw_mm}" y2="{y_mm}" />')
			if config.crop_marks:
				parts.append(f'<line x1="{hmargin_mm - 5}" y1="{y_mm}" x2="{hmargin_mm - 1}" y2="{y_mm}" />'
							 f'<line x1="{hmargin_mm + tw_mm + 1}" y1="{y_mm}" x2="{hmargin_mm + tw_mm + 5}" y2="{y_mm}" />')
		for i, track in enumerate(self.cells):
			if mode == "qr":
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
				parts.append(f'<text x="{x_mm}" y="{y_mm + 6.5}" text-anchor="middle" class="year">{track.year}</text>')
				for part in render_text_svg(x_mm, y_mm - 19, track.artist, "artist"):
					parts.append(part)
				for part in render_text_svg(x_mm, y_mm + 18, track.title, "title"):
					parts.append(part)
		parts.append(f'<text x="{w_mm - hmargin_mm}" y="{h_mm - hmargin_mm}" text-anchor="end" class="footer">{html.escape(page_footer)}</text>')
		parts.append("</svg>")
		return "\n".join(parts)
