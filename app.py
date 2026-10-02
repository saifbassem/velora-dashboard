import os, re, calendar, base64, html, hmac, time
from pathlib import Path
from datetime import datetime, timezone
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
@keyframes slideR{from{opacity:0;transform:translateX(40px)}to{opacity:1;transform:translateX(0)}}
@keyframes pop{0%{opacity:0;transform:scale(.4)}70%{transform:scale(1.12)}100%{opacity:1;transform:scale(1)}}
@keyframes shine{from{background-position:220% 0}to{background-position:-120% 0}}
@keyframes glow{0%,100%{filter:drop-shadow(0 0 6px rgba(200,210,225,.25))}50%{filter:drop-shadow(0 0 20px rgba(225,235,250,.6))}}
@keyframes floaty{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}
@keyframes lineMove{from{background-position:0 0}to{background-position:300% 0}}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(255,193,7,.5)}100%{box-shadow:0 0 0 12px rgba(255,193,7,0)}}

.block-container{animation:fadeUp .6s cubic-bezier(.2,.8,.2,1) backwards;}

/* theme toggle */
.st-key-theme_btn button{font-size:.8rem;padding:2px 10px;min-height:2rem;}

/* header with logo */
.vsw-header{display:flex;align-items:center;gap:22px;margin:4px 0 10px;animation:fadeUp .7s backwards;}
.logo-wrap{position:relative;width:150px;animation:floaty 5s ease-in-out infinite;}
.logo-wrap img{width:100%;display:block;animation:glow 4s ease-in-out infinite;}
.logo-shine{position:absolute;inset:0;
  -webkit-mask:var(--logo) center/contain no-repeat;mask:var(--logo) center/contain no-repeat;
  background:linear-gradient(110deg,transparent 40%,rgba(255,255,255,.95) 50%,transparent 60%);
  background-size:250% 100%;animation:shine 3.2s ease-in-out infinite;}
.vsw-title{font-size:2rem;font-weight:800;letter-spacing:.18em;
  background:linear-gradient(180deg,var(--title-a),var(--title-b));-webkit-background-clip:text;background-clip:text;color:transparent;}
.vsw-title small{display:block;font-size:.75rem;font-weight:500;letter-spacing:.3em;color:var(--silver-d);
  -webkit-text-fill-color:var(--silver-d);margin-top:2px;}
.vsw-line{height:2px;border-radius:2px;margin:6px 0 22px;
  background:linear-gradient(90deg,transparent,var(--line-a),var(--line-b),transparent,var(--line-a));background-size:300% 100%;
  animation:lineMove 6s linear infinite;}

/* generic buttons */
.stButton>button{border-radius:12px;border:1px solid var(--bd);background:var(--card);color:var(--text);
  transition:transform .25s cubic-bezier(.2,.8,.2,1),box-shadow .25s,border-color .25s;}
.stButton>button:hover{transform:translateY(-2px);border-color:var(--bd-h);box-shadow:0 8px 20px var(--sh);}
.stButton>button:active{transform:scale(.97);}

/* order cards */
.st-key-grid .stButton>button{height:auto;padding:18px 10px;position:relative;overflow:hidden;
  animation:fadeUp .55s cubic-bezier(.2,.8,.2,1) backwards;}
.st-key-grid .stButton>button:hover{transform:translateY(-7px) scale(1.03);
  box-shadow:0 16px 32px var(--sh2),0 0 24px var(--glow);}
.st-key-grid .stButton>button p{margin:0;line-height:1.4;}
.st-key-grid .stButton>button p:first-child{font-size:1.25rem;font-weight:700;letter-spacing:.05em;}
.st-key-grid .stButton>button p:last-child:not(:first-child){font-size:.8rem;color:var(--silver-d);}
.st-key-grid .stButton>button::after{content:"";position:absolute;top:0;left:-120%;width:60%;height:100%;
  background:linear-gradient(110deg,transparent,var(--sweep),transparent);transition:left .6s;}
.st-key-grid .stButton>button:hover::after{left:140%;}
.st-key-grid [data-testid="stColumn"]:nth-child(2) .stButton>button{animation-delay:.07s}
.st-key-grid [data-testid="stColumn"]:nth-child(3) .stButton>button{animation-delay:.14s}
.st-key-grid [data-testid="stColumn"]:nth-child(4) .stButton>button{animation-delay:.21s}

/* inputs */
.stTextInput [data-baseweb="input"]{background:var(--card);border:1px solid var(--bd);border-radius:12px;}
.stTextInput input{background:transparent;color:var(--text);transition:border-color .3s,box-shadow .3s;}
.stTextInput [data-baseweb="input"]:focus-within{border-color:var(--silver);box-shadow:0 0 0 3px var(--ring);}

/* detail page */
.st-key-detail [data-testid="stColumn"]:nth-child(1){animation:slideL .7s cubic-bezier(.2,.8,.2,1) backwards;}
.st-key-detail [data-testid="stColumn"]:nth-child(2){animation:slideR .7s cubic-bezier(.2,.8,.2,1) .1s backwards;}
.panel{background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:18px 20px;margin-bottom:16px;
  backdrop-filter:blur(6px);transition:transform .3s,box-shadow .3s,border-color .3s;}
.panel:hover{transform:translateY(-3px);border-color:var(--bd-h2);box-shadow:0 12px 28px var(--sh);}
.panel h4{margin:0 0 10px;font-size:.8rem;letter-spacing:.25em;text-transform:uppercase;color:var(--silver-d);}
.badge{display:inline-block;padding:5px 14px;border-radius:999px;font-size:.78rem;font-weight:700;letter-spacing:.08em;
  border:1px solid var(--bd);margin:0 8px 8px 0;animation:pop .6s backwards;}
.badge.ok{color:var(--ok);border-color:var(--ok-bd);background:var(--ok-bg);}
.badge.wait{color:var(--wait);border-color:var(--wait-bd);background:var(--wait-bg);animation:pop .6s backwards,pulse 1.8s infinite;}
.badge.bad{color:var(--bad);border-color:var(--bad-bd);background:var(--bad-bg);}
.badge.neutral{color:var(--silver);}
.item{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 4px;
  border-bottom:1px solid var(--bd);animation:fadeUp .5s backwards;transition:background .25s,padding-left .25s;}
.item:hover{background:var(--rowh);padding-left:12px;border-radius:8px;}
.item .t{font-weight:600}.item .s{font-size:.78rem;color:var(--silver-d)}
.item .q{font-weight:700;white-space:nowrap}
.tot{display:flex;justify-content:space-between;padding:6px 4px;color:var(--silver);}
.tot.big{font-size:1.25rem;font-weight:800;color:var(--strong);border-top:1px solid var(--bd);margin-top:6px;padding-top:12px;}
.avatar{width:64px;height:64px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:1.5rem;font-weight:800;color:var(--av-text);margin-bottom:12px;animation:pop .7s backwards;
  background:var(--av-grad);box-shadow:0 0 22px var(--glow);}
.confirm{margin:2px 0 14px;color:var(--silver);animation:fadeUp .6s backwards;}
.confirm b{color:var(--strong);letter-spacing:.06em;}
[data-testid="stForm"]{border:1px solid var(--bd);border-radius:16px;background:var(--card);margin-bottom:16px;}
.kv{margin:4px 0;color:var(--silver)}.kv b{color:var(--strong)}
.addr{color:var(--silver);line-height:1.6}

.track-link{display:inline-block;margin:6px 0 2px;padding:8px 16px;border-radius:10px;font-weight:700;letter-spacing:.05em;
  color:var(--btn-text)!important;text-decoration:none!important;background:var(--btn-grad);
  transition:transform .25s,box-shadow .25s;}
.track-link:hover{transform:translateY(-3px);box-shadow:0 8px 22px var(--sh2);}
.ship{padding:10px 0;border-bottom:1px solid var(--bd);animation:fadeUp .5s backwards;}
.ship:last-child{border-bottom:none}

@media (prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
</style>
"""

# Extra rules that make Streamlit's own dark widgets readable in light mode
LIGHT_EXTRA = """
<style>
.logo-wrap img{animation:glowL 4s ease-in-out infinite;}
@keyframes glowL{0%,100%{filter:brightness(.3) drop-shadow(0 0 3px rgba(20,30,50,.15))}
                 50%{filter:brightness(.3) drop-shadow(0 0 12px rgba(20,30,50,.35))}}
.stApp h1,.stApp h2,.stApp h3,.stApp label,
.stApp [data-testid="stMarkdownContainer"] p,.stApp [data-testid="stWidgetLabel"] p{color:var(--text);}
.stTextInput [data-baseweb="input"]{background:var(--card)!important;border-color:var(--bd)!important;}
.stTextInput input{color:var(--text)!important;-webkit-text-fill-color:var(--text);}
.stTextInput input::placeholder{color:var(--silver-d);}
.stButton>button:disabled{opacity:.45;}
[data-testid="stAlert"]{background:rgba(255,255,255,.85)!important;}
[data-testid="stAlert"] p{color:var(--text);}
</style>
"""


def inject_css():
    name = st.session_state["theme"]
    root = f":root{{color-scheme:{name};" + "".join(f"--{k}:{v};" for k, v in THEMES[name].items()) + "}"
    st.markdown(f"<style>{root}</style>" + BASE_CSS + (LIGHT_EXTRA if name == "light" else ""),
                unsafe_allow_html=True)


inject_css()


def theme_toggle():
    light = st.session_state["theme"] == "light"
    _, right = st.columns([5, 1])
    if right.button("☾ Dark mode" if light else "☀ Light mode", key="theme_btn", width="stretch"):
        st.session_state["theme"] = "dark" if light else "light"
        st.query_params["theme"] = st.session_state["theme"]
        st.rerun()


def header(subtitle="Velora Sportswear"):
    theme_toggle()
    if LOGO_B64:
        uri = f"data:image/png;base64,{LOGO_B64}"
        logo = (f'<div class="logo-wrap" style="--logo:url(\'{uri}\')">'
                f'<img src="{uri}"/><div class="logo-shine"></div></div>')
    else:
        logo = ""
    st.markdown(
        f'<div class="vsw-header">{logo}<div class="vsw-title">ORDERS<small>{html.escape(subtitle)}</small></div></div>'
        '<div class="vsw-line"></div>',
        unsafe_allow_html=True,
    )


# ---------- Shopify helpers ----------
@st.cache_data(ttl=60 * 60 * 12)  # token lasts ~24h
def get_token():
    r = requests.post(
        f"https://{SHOP}/admin/oauth/access_token",
        json={
            "client_id": cfg("CLIENT_ID"),
            "client_secret": cfg("CLIENT_SECRET"),
            "grant_type": "client_credentials",
        },
    )
    r.raise_for_status()
    return r.json()["access_token"]


def gql(query, variables=None):
    r = requests.post(
        f"https://{SHOP}/admin/api/{API_VERSION}/graphql.json",
        headers={"X-Shopify-Access-Token": get_token()},
        json={"query": query, "variables": variables or {}},
    )
    r.raise_for_status()
    return r.json()


LIST_QUERY = """
query($cursor: String, $q: String) {
  shop { ianaTimezone }
  orders(first: 100, after: $cursor, sortKey: CREATED_AT, reverse: true, query: $q) {
    pageInfo { hasNextPage endCursor }
    nodes { id name createdAt }
  }
}
"""

DETAIL_QUERY = """
query($id: ID!) {
  shop { ianaTimezone }
  order(id: $id) {
    name
    confirmationNumber
    createdAt
    displayFinancialStatus
    displayFulfillmentStatus
    note
    tags
    paymentGatewayNames
    discountCodes
    fulfillments(first: 10) {
      status
      createdAt
      trackingInfo { company number url }
    }
    totalDiscountsSet { shopMoney { amount currencyCode } }
    totalTipReceivedSet { shopMoney { amount currencyCode } }
    currentSubtotalPriceSet { shopMoney { amount currencyCode } }
    totalShippingPriceSet { shopMoney { amount currencyCode } }
    totalTaxSet { shopMoney { amount currencyCode } }
    totalPriceSet { shopMoney { amount currencyCode } }
    lineItems(first: 100) {
      nodes {
        title variantTitle sku quantity
        originalUnitPriceSet { shopMoney { amount currencyCode } }
      }
    }
    customer { displayName email phone numberOfOrders }
    email
    phone
    shippingAddress { name address1 address2 city province country zip phone }
    billingAddress { name address1 address2 city province country zip phone }
  }
}
"""


def three_months_ago():
    now = datetime.now(timezone.utc)
    y, m = now.year, now.month - 3
    if m < 1:
        m, y = m + 12, y - 1
    return datetime(y, m, min(now.day, calendar.monthrange(y, m)[1]), tzinfo=timezone.utc)


@st.cache_data(ttl=60, show_spinner="Loading orders from Shopify...")
def fetch_order_list(since_date):
    """Every order created from `since_date` (YYYY-MM-DD) until now, newest first."""
    rows, cursor, tz = [], None, None
    for _ in range(100):  # safety limit: 10,000 orders
        data = gql(LIST_QUERY, {"cursor": cursor, "q": f"created_at:>={since_date}"})
        if "errors" in data:
            st.error(data["errors"])
            break
        tz = tz or ((data["data"].get("shop") or {}).get("ianaTimezone"))
        orders = data["data"]["orders"]
        for o in orders["nodes"]:
            rows.append({"Order": o["name"], "Date": fmt_dt(o["createdAt"], tz), "id": o["id"]})
        if not orders["pageInfo"]["hasNextPage"]:
            break
        cursor = orders["pageInfo"]["endCursor"]
    return pd.DataFrame(rows)


@st.cache_data(ttl=600)
def fetch_scopes():
    try:
        d = gql("{ currentAppInstallation { accessScopes { handle } } }")
        return {x["handle"] for x in d["data"]["currentAppInstallation"]["accessScopes"]}
    except Exception:
        return None


def fetch_order(order_id):
    """Always live (no cache), so anything changed or removed in Shopify disappears here too."""
    return gql(DETAIL_QUERY, {"id": order_id})


# ---------- Render helpers ----------
def fmt_dt(iso, tz_name):
    """Format like Shopify admin: 'Sep 30, 2026 at 3:42 pm' in the store's own timezone."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        try:
            dt = dt.astimezone(ZoneInfo(tz_name))
        except Exception:
            pass  # fall back to UTC if the timezone is unavailable
        hour = dt.hour % 12 or 12
        return f"{dt.strftime('%b')} {dt.day}, {dt.year} at {hour}:{dt.minute:02d} {'am' if dt.hour < 12 else 'pm'}"
    except Exception:
        return str(iso)[:16].replace("T", " ")


def amt(node):
    return float(node["shopMoney"]["amount"]) if node else 0.0


def esc(x):
    return html.escape(str(x)) if x not in (None, "") else "-"


def money(node):
    if not node:
        return "-"
    m = node["shopMoney"]
    return f'{float(m["amount"]):,.2f} {m["currencyCode"]}'


def badge(label):
    label = label or "-"
    l = label.upper()
    if any(k in l for k in ("PAID", "FULFILLED")) and "UN" not in l and "PARTIAL" not in l:
        cls = "ok"
    elif any(k in l for k in ("PENDING", "UNFULFILLED", "PARTIAL", "AUTHORIZED")):
        cls = "wait"
    elif any(k in l for k in ("REFUND", "VOID", "CANCEL")):
        cls = "bad"
    else:
        cls = "neutral"
    return f'<span class="badge {cls}">{esc(label)}</span>'


def address_html(title, a):
    if not a:
        body = '<span style="color:var(--silver-d)">Not available</span>'
    else:
        parts = [a.get("name"), a.get("address1"), a.get("address2"),
                 " ".join(filter(None, [a.get("zip"), a.get("city")])),
                 a.get("province"), a.get("country"), a.get("phone")]
        body = "<br>".join(html.escape(p) for p in parts if p)
    return f'<div class="panel"><h4>{title}</h4><div class="addr">{body}</div></div>'


TAGS_ADD = """
mutation($id: ID!, $tags: [String!]!) {
  tagsAdd(id: $id, tags: $tags) {
    node { id }
    userErrors { field message }
  }
}
"""

TAGS_REMOVE = """
mutation($id: ID!, $tags: [String!]!) {
  tagsRemove(id: $id, tags: $tags) {
    node { id }
    userErrors { field message }
  }
}
"""

ORDER_UPDATE = """
mutation($input: OrderInput!) {
  orderUpdate(input: $input) {
    order { id email }
    userErrors { field message }
  }
}
"""


def run_mutation(query, variables):
    """Send a write request to Shopify. Returns (ok, error_message)."""
    msg = ""
    for attempt in range(2):
        try:
            data = gql(query, variables)
        except requests.RequestException as e:
            return False, f"Network error: {e}"
        msg = ""
        if data.get("errors"):
            msg = "; ".join(str(e.get("message", e)) for e in data["errors"])
        else:
            root = next(iter((data.get("data") or {}).values()), None) or {}
            msg = "; ".join(u.get("message", "") for u in (root.get("userErrors") or []))
        if not msg:
            return True, ""
        denied = any(k in msg.lower() for k in ("access", "scope", "permission", "denied"))
        if denied and attempt == 0:
            get_token.clear()  # the saved token may be from before you added write_orders; get a fresh one
            continue
        break
    if any(k in msg.lower() for k in ("access", "scope", "permission", "denied")):
        msg += " (Your app needs the write_orders scope: release a new app version with it, then update the install.)"
    return False, msg


def looks_like_email(x):
    return re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", x or "") is not None


# ---------- Page 2: order details ----------
def order_page(order_id):
    header("Order details")
    b1, b2, _ = st.columns([1.4, 1.1, 6])
    if b1.button("← Back to orders"):
        st.session_state.pop("selected", None)
        st.rerun()
    if b2.button("↻ Refresh"):
        st.rerun()

    flash = st.session_state.pop("flash", None)
    if flash:
        st.success(flash)
    order_body(order_id)


@st.fragment(run_every=30)  # re-reads Shopify every 30 seconds
def order_body(order_id):
    data = fetch_order(order_id)
    order = (data.get("data") or {}).get("order")

    if data.get("errors"):
        st.warning(
            "Some fields were blocked by Shopify (usually customer data needs "
            "'protected customer data access' approval in the Dev Dashboard)."
        )
        with st.expander("Error details"):
            st.json(data["errors"])
    if not order:
        st.error("Order not found.")
        return

    tz = ((data.get("data") or {}).get("shop") or {}).get("ianaTimezone")
    cur = order["totalPriceSet"]["shopMoney"]["currencyCode"]

    # Tips are hidden: removed from the product list, item count and totals
    def is_tip(i):
        return (i["title"] or "").strip().lower() in ("tip", "tips", "gratuity")

    all_items = order["lineItems"]["nodes"]
    shown_items = [i for i in all_items if not is_tip(i)]
    tip_line_total = sum(amt(i["originalUnitPriceSet"]) * i["quantity"] for i in all_items if is_tip(i))
    tip_total = amt(order.get("totalTipReceivedSet")) + tip_line_total
    subtotal_val = amt(order["currentSubtotalPriceSet"]) - tip_line_total
    total_val = amt(order["totalPriceSet"]) - tip_total

    with st.container(key="detail"):
        left, right = st.columns(2)

        with left:
            st.markdown(
                f'<h2 style="margin:0">Order {esc(order["name"])}</h2>'
                f'<div style="color:var(--silver-d);margin-bottom:12px">{fmt_dt(order["createdAt"], tz)}</div>'
                f'{badge(order["displayFinancialStatus"])}{badge(order["displayFulfillmentStatus"])}',
                unsafe_allow_html=True,
            )

            total_items = sum(i["quantity"] for i in shown_items)
            chips = f'<span class="badge neutral">TOTAL ITEMS: {total_items}</span>'
            for code in order.get("discountCodes") or []:
                chips += f'<span class="badge ok">DISCOUNT CODE: {esc(code)}</span>'
            st.markdown(chips, unsafe_allow_html=True)
            if order.get("confirmationNumber"):
                st.markdown(
                    f'<div class="confirm">Confirmation <b>#{esc(order["confirmationNumber"])}</b> '
                    'was generated for this order.</div>',
                    unsafe_allow_html=True,
                )

            items = ""
            for n, i in enumerate(shown_items):
                sub = " · ".join(filter(None, [i["variantTitle"], f'SKU {i["sku"]}' if i["sku"] else ""]))
                items += (
                    f'<div class="item" style="animation-delay:{0.15 + n * 0.08:.2f}s">'
                    f'<div><div class="t">{esc(i["title"])}</div><div class="s">{esc(sub) if sub else ""}</div></div>'
                    f'<div class="q">{i["quantity"]} × {money(i["originalUnitPriceSet"])}</div></div>'
                )
            st.markdown(f'<div class="panel"><h4>Products ({total_items} items)</h4>{items}</div>', unsafe_allow_html=True)

            disc = order.get("totalDiscountsSet")
            disc_row = ""
            if disc and float(disc["shopMoney"]["amount"]) > 0:
                codes = ", ".join(order.get("discountCodes") or [])
                label = f"Discount ({esc(codes)})" if codes else "Discount"
                disc_row = (f'<div class="tot" style="color:var(--ok)"><span>{label}</span>'
                            f'<span>-{money(disc)}</span></div>')
            totals = (
                f'<div class="tot"><span>Subtotal</span><span>{subtotal_val:,.2f} {cur}</span></div>'
                f'{disc_row}'
                f'<div class="tot"><span>Shipping</span><span>{money(order["totalShippingPriceSet"])}</span></div>'
                f'<div class="tot"><span>Tax</span><span>{money(order["totalTaxSet"])}</span></div>'
                f'<div class="tot big"><span>Total</span><span>{total_val:,.2f} {cur}</span></div>'
            )
            extra = ""
            if order["paymentGatewayNames"]:
                extra += f'<div class="kv">Payment method: <b>{esc(", ".join(order["paymentGatewayNames"]))}</b></div>'
            if order["tags"]:
                extra += f'<div class="kv">Tags: <b>{esc(", ".join(order["tags"]))}</b></div>'
            if order["note"]:
                extra += f'<div class="kv">Note: <b>{esc(order["note"])}</b></div>'
            st.markdown(f'<div class="panel"><h4>Summary</h4>{totals}{extra}</div>', unsafe_allow_html=True)

            with st.form("tag_form"):
                st.markdown("**Tags** — add or remove, separated by commas")
                new_tags = st.text_input("Tags", value=", ".join(order["tags"]),
                                         key="tag_input|" + order_id + "|" + "|".join(order["tags"]),
                                         placeholder="e.g. vip, gift", label_visibility="collapsed")
                if st.form_submit_button("Save tags to Shopify"):
                    wanted = []
                    for t in new_tags.split(","):
                        t = t.strip()
                        if t and t.lower() not in [w.lower() for w in wanted]:
                            wanted.append(t)
                    have = {t.lower() for t in order["tags"]}
                    keep = {w.lower() for w in wanted}
                    to_add = [t for t in wanted if t.lower() not in have]
                    to_remove = [t for t in order["tags"] if t.lower() not in keep]
                    if not to_add and not to_remove:
                        st.info("No changes to save.")
                    else:
                        ok, err = True, ""
                        if to_add:
                            ok, err = run_mutation(TAGS_ADD, {"id": order_id, "tags": to_add})
                        if ok and to_remove:
                            ok, err = run_mutation(TAGS_REMOVE, {"id": order_id, "tags": to_remove})
                        if ok:
                            st.session_state["flash"] = "Tags updated in Shopify."
                            st.rerun()
                        else:
                            st.error(f"Shopify did not accept the tags: {err}")

            ship_html = ""
            for n, f in enumerate(order.get("fulfillments") or []):
                ship_html += f'<div class="ship" style="animation-delay:{n * 0.1:.1f}s">{badge(f["status"])}'
                trackings = f.get("trackingInfo") or []
                if not trackings:
                    ship_html += '<div style="color:var(--silver-d)">No tracking code added yet.</div>'
                for t in trackings:
                    company = esc(t.get("company")) if t.get("company") else "Carrier"
                    number = t.get("number")
                    url = t.get("url") or ""
                    ship_html += f'<div class="kv">Carrier: <b>{company}</b></div>'
                    if number and url.startswith(("http://", "https://")):
                        ship_html += (f'<a class="track-link" href="{html.escape(url, quote=True)}" '
                                      f'target="_blank" rel="noopener noreferrer">Track: {esc(number)} ↗</a>')
                    elif number:
                        ship_html += f'<div class="kv">Tracking number: <b>{esc(number)}</b></div>'
                ship_html += "</div>"
            if not ship_html:
                ship_html = '<div style="color:var(--silver-d)">Not fulfilled yet. Tracking will appear here once it ships.</div>'
            st.markdown(f'<div class="panel"><h4>Shipping &amp; tracking</h4>{ship_html}</div>', unsafe_allow_html=True)

        with right:
            c = order.get("customer")
            if c:
                name = c["displayName"] or "Customer"
                initials = "".join(w[0] for w in name.split()[:2]).upper() or "?"
                body = (
                    f'<div class="avatar">{esc(initials)}</div>'
                    f'<div class="kv">Name: <b>{esc(name)}</b></div>'
                    f'<div class="kv">Email: <b>{esc(c["email"] or order.get("email"))}</b></div>'
                    f'<div class="kv">Phone: <b>{esc(c["phone"] or order.get("phone"))}</b></div>'
                    f'<div class="kv">Total orders: <b>{c["numberOfOrders"]}</b></div>'
                )
            else:
                body = (
                    f'<div class="avatar">?</div>'
                    f'<div class="kv">Email: <b>{esc(order.get("email"))}</b></div>'
                    f'<div class="kv">Phone: <b>{esc(order.get("phone"))}</b></div>'
                    '<div style="color:var(--silver-d);font-size:.8rem">No customer record '
                    '(guest checkout or access not approved).</div>'
                )
            st.markdown(f'<div class="panel"><h4>Customer</h4>{body}</div>', unsafe_allow_html=True)

            current_email = order.get("email") or (c and c.get("email")) or ""
            if not current_email and data.get("errors"):
                st.info("The email could not be checked because Shopify blocked customer data, "
                        "so editing is hidden to avoid overwriting an existing email.")
            else:
                with st.form("email_form"):
                    st.markdown("**Customer email**" if current_email else "**No customer email on this order.** Add one:")
                    new_email = st.text_input("Email", value=current_email,
                                              key="email_input|" + order_id + "|" + current_email,
                                              placeholder="name@example.com", label_visibility="collapsed")
                    if st.form_submit_button("Save email to Shopify"):
                        new_email = new_email.strip()
                        if new_email == current_email:
                            st.info("No changes to save.")
                        elif not looks_like_email(new_email):
                            st.warning("Please enter a valid email address.")
                        else:
                            ok, err = run_mutation(ORDER_UPDATE, {"input": {"id": order_id, "email": new_email}})
                            if ok:
                                st.session_state["flash"] = f"Email updated in Shopify: {new_email}"
                                st.rerun()
                            else:
                                st.error(f"Shopify did not accept the email: {err}")
            st.markdown(address_html("Shipping address", order.get("shippingAddress")), unsafe_allow_html=True)
            st.markdown(address_html("Billing address", order.get("billingAddress")), unsafe_allow_html=True)


# ---------- Page 1: order list ----------
def list_page():
    header()
    since = three_months_ago()
    df = fetch_order_list(since.strftime("%Y-%m-%d"))

    info_col, refresh_col = st.columns([5, 1])
    info_col.caption(f"All orders from {since.strftime('%b')} {since.day}, {since.year} until now · {len(df)} orders")
    if refresh_col.button("↻ Refresh", key="refresh_list", width="stretch"):
        fetch_order_list.clear()
        st.rerun()

    scopes = fetch_scopes()
    if scopes is not None and "read_all_orders" not in scopes:
        st.info("Shopify only shares the last 60 days with this app. To see the full 3 months, "
                "request the read_all_orders scope from Shopify and add it to the app.")

    if df.empty:
        st.info("No orders found.")
        return

    st.text_input("Search order number", placeholder="e.g. 1001", key="search",
                  on_change=lambda: st.session_state.update(page=0))
    q = st.session_state.get("search", "")
    if q:
        df = df[df["Order"].str.contains(q, case=False)]

    pages = max(1, -(-len(df) // PAGE_SIZE))
    page = min(st.session_state.get("page", 0), pages - 1)
    chunk = df.iloc[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    with st.container(key="grid"):
        for start in range(0, len(chunk), 4):
            cols = st.columns(4)
            for col, row in zip(cols, chunk.iloc[start:start + 4].itertuples()):
                if col.button(f"{row.Order}\n\n{row.Date}", key=f"o_{row.id}", width="stretch"):
                    st.session_state["selected"] = row.id
                    st.rerun()

    p1, p2, p3 = st.columns([1, 2, 1])
    if p1.button("← Prev", disabled=page == 0):
        st.session_state["page"] = page - 1
        st.rerun()
    p2.markdown(f'<div style="text-align:center;color:var(--silver-d);padding-top:6px">Page {page + 1} / {pages} · {len(df)} orders</div>',
                unsafe_allow_html=True)
    if p3.button("Next →", disabled=page >= pages - 1):
        st.session_state["page"] = page + 1
        st.rerun()


# ---------- Login (protects customer data when the app is online) ----------
def login_gate():
    password = cfg("APP_PASSWORD")
    if not password:
        header("Locked")
        st.error("APP_PASSWORD is not set. Add it to your .env file (local) or to the app Secrets (online).")
        st.stop()
    if st.session_state.get("auth"):
        return
    header("Sign in")
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        pw = st.text_input("Password", type="password", key="pw")
        if st.button("Sign in", width="stretch"):
            if hmac.compare_digest(pw.encode(), str(password).encode()):
                st.session_state["auth"] = True
                st.rerun()
            else:
                time.sleep(1)  # slows down password guessing
                st.error("Wrong password.")
    st.stop()


# ---------- Router ----------
login_gate()
if "selected" in st.session_state:
    order_page(st.session_state["selected"])
else:
    list_page()
