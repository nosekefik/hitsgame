import os
import json

def generate_html(config, texts, output_path):
    title = getattr(config, "title", texts.get("title", "Hits!"))
    emoji = getattr(config, "emoji", "🎸")
    html_content = f"""<!DOCTYPE html>
<html lang=\"{config.language}\">
<head>
    <meta charset=\"UTF-8\">
    <title>{title}</title>
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
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

def load_texts(config):
    lang_file = os.path.join("translations", f"{config.language}.json")
    default_file = os.path.join("translations", "en.json")
    if os.path.isfile(lang_file):
        with open(lang_file, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        print(f"Warning: Translation file for '{config.language}' not found. Falling back to English.")
        with open(default_file, "r", encoding="utf-8") as f:
            return json.load(f)