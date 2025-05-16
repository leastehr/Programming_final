import random, textwrap, io, requests, base64, platform
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# Page setup
st.set_page_config(page_title="Meme Generator", layout="wide")

# --- Detect system font path safely ---
def get_default_font_path():
    system = platform.system()
    if system == "Darwin":
        return "/System/Library/Fonts/Supplemental/Arial.ttf"
    elif system == "Windows":
        return "C:\\Windows\\Fonts\\Arial.ttf"
    else:
        return "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

FONT_PATH = get_default_font_path()
POSITION_OPTIONS = ["Top", "Centre", "Bottom", "Custom"]

# Custom CSS
st.markdown("""
<style>
html, body { margin: 0; padding: 0; background: #ffffff; overflow-x: hidden; }
section[data-testid="stSidebar"] {
  background-color: #2c3e50;
  height: 100vh;
  padding: 0 1rem 1rem;
  overflow: auto;
  box-sizing: border-box;
}
.scaled-img-container img {
  height: auto;
  max-height: 60vh;
  width: auto;
  max-width: 100%;
  object-fit: contain;
  border-radius: 8px;
}
.scaled-img-container img {
  max-height: 50vh;
  object-fit: contain;
  border-radius: 8px;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label {
  color: #ffffff;
  font-family: "Segoe UI", sans-serif;
}
section[data-testid="stSidebar"] button:not(:disabled) {
  background: #ff4c4c;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  padding: 0.5rem 1rem;
  font-size: 1rem;
  font-weight: 600;
}
/* Slider min, max and tooltip text styling */
div[data-baseweb="slider"] > div > div:first-child,
div[data-baseweb="slider"] > div > div:last-child {
    color: #ff4c4c !important;
    font-weight: 600;
}
div[data-baseweb="slider"] [role="tooltip"] {
    color: #ff4c4c !important;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# Session defaults
st.session_state.setdefault("skips", 0)
st.session_state.setdefault("template_data", None)

# Template fetch
@st.cache_data
def get_templates():
    res = requests.get("https://api.imgflip.com/get_memes").json()
    return res.get("data", {}).get("memes", [])

templates = get_templates()

# Sidebar
with st.sidebar:
    st.markdown("<h1 class='sidebar-title'>Meme Generator</h1>", unsafe_allow_html=True)
    
    with st.expander("ℹ️ How to use", expanded=False):
        st.markdown("""
        <div style="color: white;">
            1. Choose a template or keep pressing Select template up to five times.<br>
            2. Add your captions below and pick a position for each.<br>
            3. Tweak font size or auto-fit as you wish.<br>
            4. Download your meme.
        </div>
        """, unsafe_allow_html=True)

    btn_disabled = not templates
    if st.button("Select template 🔄", disabled=btn_disabled) and st.session_state["skips"] < 5:
        st.session_state["template_data"] = random.choice(templates)
        st.session_state["skips"] += 1

        keys_to_clear = [k for k in st.session_state.keys() if k.startswith(("txt", "pos_select", "x", "y", "color"))]
        for k in keys_to_clear:
            del st.session_state[k]

        st.session_state["force_reset"] = True

    st.markdown(f"Skips left: {5 - st.session_state['skips']}")

    num_caps = st.slider("Number of captions", 1, 5, 2)

    caption_boxes = []

    for i in range(num_caps):
        st.markdown(f"### Caption {i+1}")

        # Sicher initialisieren
        if st.session_state.get("force_reset") or f"txt{i}" not in st.session_state:
            st.session_state[f"txt{i}"] = ""
            st.session_state[f"pos_select{i}"] = "Top"
            st.session_state[f"color{i}"] = "#FFFFFF"
            st.session_state[f"x{i}"] = 50
            st.session_state[f"y{i}"] = 50

        txt = st.text_input("Add your text here", key=f"txt{i}")
        selected = st.selectbox("Position", POSITION_OPTIONS, key=f"pos_select{i}")
        color = st.color_picker("Text color", key=f"color{i}")

        if selected == "Top":
            x_pct, y_pct = 50, 10
        elif selected == "Centre":
            x_pct, y_pct = 50, 50
        elif selected == "Bottom":
            x_pct, y_pct = 50, 90
        else:
            colx, coly = st.columns(2)
            x_pct = colx.slider("X %", 0, 100, key=f"x{i}")
            y_pct = coly.slider("Y %", 0, 100, key=f"y{i}")

        caption_boxes.append({"text": txt, "x": x_pct, "y": y_pct, "color": color})

    base_font = st.slider("Base font size", 10, 100, 48)
    auto_fit = st.checkbox("Auto-fit width", value=True)

# Reset-Flag 
st.session_state["force_reset"] = False

# Main content
st.markdown('<div class="meme-title"><strong>Create your meme here</strong></div>', unsafe_allow_html=True)

def draw_caption(im: Image.Image, txt: str, x_pct: int, y_pct: int, base: int, fit: bool, color: str) -> None:
    draw = ImageDraw.Draw(im)
    fs = base
    try:
        f = ImageFont.truetype(FONT_PATH, fs)
    except OSError:
        st.error("⚠️ Font not found. Using default font.")
        f = ImageFont.load_default()
    while fit and fs >= 12:
        try:
            f = ImageFont.truetype(FONT_PATH, fs)
        except OSError:
            f = ImageFont.load_default()
        wrapped = textwrap.fill(txt.upper(), 25)
        w = draw.multiline_textbbox((0, 0), wrapped, font=f, spacing=4)[2]
        if w <= im.width * 0.95:
            break
        fs -= 2
    wrapped = textwrap.fill(txt.upper(), 25)
    w, h = draw.multiline_textbbox((0, 0), wrapped, font=f, spacing=4)[2:]
    x = int(im.width * x_pct / 100) - w // 2
    y = int(im.height * y_pct / 100) - h // 2
    for dx, dy in [(-2, -2), (2, 2), (2, -2), (-2, 2)]:
        draw.multiline_text((x + dx, y + dy), wrapped, font=f, fill="black", spacing=4, align="center")
    draw.multiline_text((x, y), wrapped, font=f, fill=color, spacing=4, align="center")

if st.session_state.get("template_data"):
    meme_url = st.session_state["template_data"]["url"]
    img = Image.open(BytesIO(requests.get(meme_url).content)).convert("RGB")
    for box in caption_boxes:
        if box["text"]:
            draw_caption(img, box["text"], box["x"], box["y"], base_font, auto_fit, box["color"])
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.getvalue()).decode()
    st.markdown(f"""
    <div class="scaled-img-container">
        <img src="data:image/png;base64,{img_base64}" />
    </div>
    """, unsafe_allow_html=True)
    st.download_button("⬇️ Download meme", buf, "meme.png", mime="image/png")
else:
    st.info("Click Select template in the sidebar to start.")