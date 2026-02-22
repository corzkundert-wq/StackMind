import os
import uuid

DECKS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "static", "decks")
os.makedirs(DECKS_DIR, exist_ok=True)


def render_deck_html(slides: list, title: str = "StackMind Deck", theme: str = "dark") -> str:
    slide_html_parts = []
    for i, s in enumerate(slides):
        slide_num = s.get("slide_number", i + 1)
        stitle = s.get("title", f"Slide {slide_num}")
        body = s.get("body", "")
        bullets = s.get("bullets", [])
        speaker_notes = s.get("speaker_notes", "")

        bullets_html = ""
        if bullets:
            items = "".join(f"<li>{b}</li>" for b in bullets)
            bullets_html = f"<ul class='slide-bullets'>{items}</ul>"

        notes_html = ""
        if speaker_notes:
            notes_html = f"<div class='speaker-notes'><strong>Notes:</strong> {speaker_notes}</div>"

        slide_html_parts.append(f"""
        <div class="slide" id="slide-{slide_num}">
            <div class="slide-number">{slide_num}</div>
            <h2 class="slide-title">{stitle}</h2>
            <div class="slide-body">{body}</div>
            {bullets_html}
            {notes_html}
        </div>
        """)

    slides_joined = "\n".join(slide_html_parts)
    total = len(slides)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: #0a0a0a;
    color: #e8e8e8;
    overflow: hidden;
    height: 100vh;
}}
.deck-container {{
    width: 100vw;
    height: 100vh;
    position: relative;
}}
.slide {{
    display: none;
    width: 100%;
    height: 100vh;
    padding: 60px 80px;
    position: absolute;
    top: 0;
    left: 0;
    background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
    animation: fadeIn 0.4s ease;
}}
.slide.active {{ display: flex; flex-direction: column; justify-content: center; }}
@keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
.slide-number {{
    position: absolute;
    top: 30px;
    right: 40px;
    font-size: 14px;
    color: rgba(255,255,255,0.3);
    font-weight: 300;
}}
.slide-title {{
    font-size: 42px;
    font-weight: 700;
    margin-bottom: 30px;
    background: linear-gradient(90deg, #667eea, #764ba2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.2;
}}
.slide-body {{
    font-size: 22px;
    line-height: 1.7;
    color: #c0c0c0;
    margin-bottom: 30px;
    max-width: 900px;
}}
.slide-bullets {{
    list-style: none;
    padding: 0;
    margin-bottom: 30px;
}}
.slide-bullets li {{
    font-size: 20px;
    line-height: 1.6;
    color: #d0d0d0;
    padding: 8px 0 8px 30px;
    position: relative;
}}
.slide-bullets li::before {{
    content: '';
    position: absolute;
    left: 0;
    top: 16px;
    width: 12px;
    height: 12px;
    background: linear-gradient(135deg, #667eea, #764ba2);
    border-radius: 3px;
}}
.speaker-notes {{
    position: absolute;
    bottom: 30px;
    left: 80px;
    right: 80px;
    font-size: 13px;
    color: rgba(255,255,255,0.25);
    border-top: 1px solid rgba(255,255,255,0.1);
    padding-top: 12px;
}}
.controls {{
    position: fixed;
    bottom: 30px;
    right: 40px;
    display: flex;
    gap: 10px;
    z-index: 100;
}}
.controls button {{
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.2);
    color: #fff;
    padding: 10px 20px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    transition: background 0.2s;
}}
.controls button:hover {{ background: rgba(255,255,255,0.2); }}
.progress {{
    position: fixed;
    bottom: 0;
    left: 0;
    height: 3px;
    background: linear-gradient(90deg, #667eea, #764ba2);
    transition: width 0.3s ease;
    z-index: 100;
}}
.slide-counter {{
    position: fixed;
    bottom: 35px;
    left: 40px;
    font-size: 14px;
    color: rgba(255,255,255,0.4);
    z-index: 100;
}}
.title-slide .slide-title {{
    font-size: 56px;
    text-align: center;
}}
.title-slide .slide-body {{
    text-align: center;
    margin: 0 auto;
}}
</style>
</head>
<body>
<div class="deck-container">
{slides_joined}
</div>
<div class="progress" id="progress"></div>
<div class="slide-counter" id="counter">1 / {total}</div>
<div class="controls">
    <button onclick="prevSlide()">Prev</button>
    <button onclick="nextSlide()">Next</button>
</div>
<script>
let current = 0;
const total = {total};
const slides = document.querySelectorAll('.slide');
if (slides.length > 0) slides[0].classList.add('active');
if (slides.length > 0 && slides[0]) slides[0].classList.add('title-slide');
function showSlide(n) {{
    slides.forEach(s => s.classList.remove('active'));
    slides[n].classList.add('active');
    document.getElementById('counter').textContent = (n+1) + ' / ' + total;
    document.getElementById('progress').style.width = ((n+1)/total*100) + '%';
}}
function nextSlide() {{ if (current < total-1) {{ current++; showSlide(current); }} }}
function prevSlide() {{ if (current > 0) {{ current--; showSlide(current); }} }}
document.addEventListener('keydown', e => {{
    if (e.key === 'ArrowRight' || e.key === ' ') nextSlide();
    if (e.key === 'ArrowLeft') prevSlide();
}});
showSlide(0);
</script>
</body>
</html>"""

    filename = f"deck_{uuid.uuid4().hex[:8]}.html"
    filepath = os.path.join(DECKS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filename
