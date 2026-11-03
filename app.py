import os, re, calendar, base64, html, hmac, time
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def cfg(name, default=None):
    """Read a setting from environment/.env (local) or st.secrets (Streamlit Cloud)."""
    val = os.getenv(name)
    if val:
        return val
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


SHOP = cfg("SHOP")
API_VERSION = "2026-07"
PAGE_SIZE = 24

LOGO_PATH = Path(__file__).parent / "logo.png"
LOGO_B64 = base64.b64encode(LOGO_PATH.read_bytes()).decode() if LOGO_PATH.exists() else ""

st.set_page_config(
    page_title="VSW Orders",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None,
    layout="wide",
)

# ---------- Themes (dark / light) ----------
THEMES = {
    "dark": {
        "bg": "#0a0b0d", "text": "#e8eaee", "strong": "#ffffff",
        "silver": "#c9ced6", "silver-d": "#8b929c",
        "card": "rgba(255,255,255,.04)", "bd": "rgba(201,206,214,.16)",
        "bd-h": "rgba(230,235,245,.6)", "bd-h2": "rgba(230,235,245,.35)",
        "sh": "rgba(0,0,0,.4)", "sh2": "rgba(0,0,0,.55)", "glow": "rgba(200,210,225,.2)",
        "ring": "rgba(201,206,214,.18)", "rowh": "rgba(255,255,255,.05)", "sweep": "rgba(255,255,255,.18)",
        "blob1": "rgba(150,165,190,.16)", "blob2": "rgba(190,200,215,.12)",
        "title-a": "#ffffff", "title-b": "#8b929c", "line-a": "#e8eaee", "line-b": "#6e7580",
        "ok": "#5be39a", "ok-bg": "rgba(60,200,120,.1)", "ok-bd": "#2c8a5a",
        "wait": "#ffc107", "wait-bg": "rgba(255,193,7,.1)", "wait-bd": "#8a6d10",
        "bad": "#ff6b6b", "bad-bg": "rgba(255,80,80,.1)", "bad-bd": "#8a2c2c",
        "av-grad": "linear-gradient(135deg,#fff,#8b929c 60%,#d8dde5)", "av-text": "#0a0b0d",
        "btn-grad": "linear-gradient(135deg,#fff,#aab0ba)", "btn-text": "#0a0b0d",
    },
    "light": {
        "bg": "#f3f4f6", "text": "#14161a", "strong": "#0a0b0d",
        "silver": "#3c424c", "silver-d": "#6b7280",
        "card": "rgba(255,255,255,.8)", "bd": "rgba(20,22,26,.14)",
        "bd-h": "rgba(20,22,26,.45)", "bd-h2": "rgba(20,22,26,.3)",
        "sh": "rgba(30,40,60,.12)", "sh2": "rgba(30,40,60,.2)", "glow": "rgba(90,105,130,.18)",
        "ring": "rgba(20,22,26,.12)", "rowh": "rgba(20,22,26,.05)", "sweep": "rgba(20,40,80,.1)",
        "blob1": "rgba(120,135,160,.2)", "blob2": "rgba(150,165,190,.16)",
        "title-a": "#14161a", "title-b": "#5b6270", "line-a": "#14161a", "line-b": "#9aa0aa",
        "ok": "#12804a", "ok-bg": "rgba(18,128,74,.1)", "ok-bd": "#7fcf9f",
        "wait": "#9a6b00", "wait-bg": "rgba(255,193,7,.2)", "wait-bd": "#d9b24a",
        "bad": "#c0392b", "bad-bg": "rgba(192,57,43,.1)", "bad-bd": "#e0a29b",
        "av-grad": "linear-gradient(135deg,#4a5160,#1a1d22 60%,#5b6270)", "av-text": "#ffffff",
        "btn-grad": "linear-gradient(135deg,#1a1d22,#4a5160)", "btn-text": "#ffffff",
    },
}

if "theme" not in st.session_state:
    q = st.query_params.get("theme", "dark")
    st.session_state["theme"] = q if q in THEMES else "dark"

# ---------- Style + animations ----------
BASE_CSS = """
<style>
html,body,.stApp{background:var(--bg);color:var(--text);}

/* hide Streamlit / GitHub branding */
#MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"],
[data-testid="stAppDeployButton"],.stAppDeployButton,[class*="viewerBadge"],[class*="_profileContainer"],
a[href*="streamlit.io"],a[href*="github.com"]{display:none!important;visibility:hidden!important;}
[data-testid="stHeader"]{display:none;}
.block-container{padding-top:1.5rem;}
[data-testid="stMain"]{position:relative;z-index:1;}

/* drifting metallic glow in the background */
.stApp::before{content:"";position:fixed;inset:-20%;z-index:0;pointer-events:none;
  background:radial-gradient(40% 40% at 20% 25%,var(--blob1),transparent 70%),
             radial-gradient(35% 35% at 80% 70%,var(--blob2),transparent 70%);
  animation:drift 22s ease-in-out infinite alternate;}

@keyframes drift{from{transform:translate(0,0) scale(1)}to{transform:translate(4%,-3%) scale(1.12)}}
@keyframes fadeUp{from{opacity:0;transform:translateY(22px)}to{opacity:1;transform:translateY(0)}}
@keyframes slideL{from{opacity:0;transform:translateX(-40px)}to{opacity:1;transform:translateX(0)}}
