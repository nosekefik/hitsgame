import os
import json
from jinja2 import Environment, FileSystemLoader, select_autoescape


def generate_html(out_dir, config, texts):
    """Render the entire website in out_dir using Jinja2 templates."""
    title = getattr(config, "title", "Hits!")
    emoji = getattr(config, "emoji", "🎸")
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html", "xml", "jinja"]),
    )
    template = env.get_template("index.html.jinja")
    rendered = template.render(
        config=config,
        title=title,
        emoji=emoji,
        texts=texts,
    )
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(rendered)
    # Generate CSS
    try:
        css_tmpl = env.get_template("main.css.jinja")
        css_rendered = css_tmpl.render()
        with open(os.path.join(out_dir, "main.css"), "w", encoding="utf-8") as f_css:
            f_css.write(css_rendered)
    except Exception as e:
        print(f"Warning: could not render main.css: {e}")
    # Generate JS
    try:
        js_tmpl = env.get_template("index.js.jinja")
        js_rendered = js_tmpl.render(
            config=config,
            title=title,
            emoji=emoji,
            texts=texts,
        )
        with open(os.path.join(out_dir, "index.js"), "w", encoding="utf-8") as f_js:
            f_js.write(js_rendered)
    except Exception as e:
        print(f"Warning: could not render index.js: {e}")


def load_texts(config):
    lang_file = os.path.join("translations", f"{config.language}.json")
    default_file = os.path.join("translations", "en.json")
    if os.path.isfile(lang_file):
        with open(lang_file, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        print(
            f"Warning: Translation file for '{config.language}' not found. Falling back to English."
        )
        with open(default_file, "r", encoding="utf-8") as f:
            return json.load(f)