import os, base64, html, hmac, time
from pathlib import Path
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

# ---------- Style + animations ----------
CSS = """
<style>
:root{--silver:#c9ced6;--silver-d:#8b929c;--bg:#0a0b0d;--card:rgba(255,255,255,.04);--bd:rgba(201,206,214,.16);}
html,body,.stApp{background:var(--bg);color:#e8eaee;}
[data-testid="stHeader"]{background:transparent;}
[data-testid="stMain"]{position:relative;z-index:1;}

/* drifting metallic glow in the background */
.stApp::before{content:"";position:fixed;inset:-20%;z-index:0;pointer-events:none;
  background:radial-gradient(40% 40% at 20% 25%,rgba(150,165,190,.16),transparent 70%),
             radial-gradient(35% 35% at 80% 70%,rgba(190,200,215,.12),transparent 70%);
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

/* header with logo */
.vsw-header{display:flex;align-items:center;gap:22px;margin:4px 0 10px;animation:fadeUp .7s backwards;}
.logo-wrap{position:relative;width:150px;animation:floaty 5s ease-in-out infinite;}
.logo-wrap img{width:100%;display:block;animation:glow 4s ease-in-out infinite;}
.logo-shine{position:absolute;inset:0;
  -webkit-mask:var(--logo) center/contain no-repeat;mask:var(--logo) center/contain no-repeat;
  background:linear-gradient(110deg,transparent 40%,rgba(255,255,255,.95) 50%,transparent 60%);
  background-size:250% 100%;animation:shine 3.2s ease-in-out infinite;}
.vsw-title{font-size:2rem;font-weight:800;letter-spacing:.18em;
  background:linear-gradient(180deg,#fff,#8b929c);-webkit-background-clip:text;background-clip:text;color:transparent;}
.vsw-title small{display:block;font-size:.75rem;font-weight:500;letter-spacing:.3em;color:var(--silver-d);
  -webkit-text-fill-color:var(--silver-d);margin-top:2px;}
.vsw-line{height:2px;border-radius:2px;margin:6px 0 22px;
  background:linear-gradient(90deg,transparent,#e8eaee,#6e7580,transparent,#e8eaee);background-size:300% 100%;
  animation:lineMove 6s linear infinite;}

/* generic buttons */
.stButton>button{border-radius:12px;border:1px solid var(--bd);background:var(--card);color:#e8eaee;
  transition:transform .25s cubic-bezier(.2,.8,.2,1),box-shadow .25s,border-color .25s;}
.stButton>button:hover{transform:translateY(-2px);border-color:rgba(230,235,245,.6);box-shadow:0 8px 20px rgba(0,0,0,.4);}
.stButton>button:active{transform:scale(.97);}

/* order cards */
.st-key-grid .stButton>button{height:auto;padding:18px 10px;position:relative;overflow:hidden;
  animation:fadeUp .55s cubic-bezier(.2,.8,.2,1) backwards;}
.st-key-grid .stButton>button:hover{transform:translateY(-7px) scale(1.03);
  box-shadow:0 16px 32px rgba(0,0,0,.55),0 0 24px rgba(200,210,225,.2);}
.st-key-grid .stButton>button p{margin:0;line-height:1.4;}
.st-key-grid .stButton>button p:first-child{font-size:1.25rem;font-weight:700;letter-spacing:.05em;}
.st-key-grid .stButton>button p:last-child:not(:first-child){font-size:.8rem;color:var(--silver-d);}
.st-key-grid .stButton>button::after{content:"";position:absolute;top:0;left:-120%;width:60%;height:100%;
  background:linear-gradient(110deg,transparent,rgba(255,255,255,.18),transparent);transition:left .6s;}
.st-key-grid .stButton>button:hover::after{left:140%;}
.st-key-grid [data-testid="stColumn"]:nth-child(2) .stButton>button{animation-delay:.07s}
.st-key-grid [data-testid="stColumn"]:nth-child(3) .stButton>button{animation-delay:.14s}
.st-key-grid [data-testid="stColumn"]:nth-child(4) .stButton>button{animation-delay:.21s}

/* inputs */
.stTextInput input{background:var(--card);border:1px solid var(--bd);border-radius:12px;transition:border-color .3s,box-shadow .3s;}
.stTextInput input:focus{border-color:var(--silver);box-shadow:0 0 0 3px rgba(201,206,214,.18);}

/* detail page */
.st-key-detail [data-testid="stColumn"]:nth-child(1){animation:slideL .7s cubic-bezier(.2,.8,.2,1) backwards;}
.st-key-detail [data-testid="stColumn"]:nth-child(2){animation:slideR .7s cubic-bezier(.2,.8,.2,1) .1s backwards;}
.panel{background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:18px 20px;margin-bottom:16px;
  backdrop-filter:blur(6px);transition:transform .3s,box-shadow .3s,border-color .3s;}
.panel:hover{transform:translateY(-3px);border-color:rgba(230,235,245,.35);box-shadow:0 12px 28px rgba(0,0,0,.4);}
.panel h4{margin:0 0 10px;font-size:.8rem;letter-spacing:.25em;text-transform:uppercase;color:var(--silver-d);}
.badge{display:inline-block;padding:5px 14px;border-radius:999px;font-size:.78rem;font-weight:700;letter-spacing:.08em;
  border:1px solid var(--bd);margin:0 8px 8px 0;animation:pop .6s backwards;}
.badge.ok{color:#5be39a;border-color:#2c8a5a;background:rgba(60,200,120,.1);}
.badge.wait{color:#ffc107;border-color:#8a6d10;background:rgba(255,193,7,.1);animation:pop .6s backwards,pulse 1.8s infinite;}
.badge.bad{color:#ff6b6b;border-color:#8a2c2c;background:rgba(255,80,80,.1);}
.badge.neutral{color:var(--silver);}
.item{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 4px;
  border-bottom:1px solid var(--bd);animation:fadeUp .5s backwards;transition:background .25s,padding-left .25s;}
.item:hover{background:rgba(255,255,255,.05);padding-left:12px;border-radius:8px;}
.item .t{font-weight:600}.item .s{font-size:.78rem;color:var(--silver-d)}
.item .q{font-weight:700;white-space:nowrap}
.tot{display:flex;justify-content:space-between;padding:6px 4px;color:var(--silver);}
.tot.big{font-size:1.25rem;font-weight:800;color:#fff;border-top:1px solid var(--bd);margin-top:6px;padding-top:12px;}
.avatar{width:64px;height:64px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:1.5rem;font-weight:800;color:#0a0b0d;margin-bottom:12px;animation:pop .7s backwards;
  background:linear-gradient(135deg,#fff,#8b929c 60%,#d8dde5);box-shadow:0 0 22px rgba(200,210,225,.35);}
.kv{margin:4px 0;color:var(--silver)}.kv b{color:#fff}
.addr{color:var(--silver);line-height:1.6}

.track-link{display:inline-block;margin:6px 0 2px;padding:8px 16px;border-radius:10px;font-weight:700;letter-spacing:.05em;
  color:#0a0b0d!important;text-decoration:none!important;background:linear-gradient(135deg,#fff,#aab0ba);
  transition:transform .25s,box-shadow .25s;}
.track-link:hover{transform:translateY(-3px);box-shadow:0 8px 22px rgba(200,210,225,.35);}
.ship{padding:10px 0;border-bottom:1px solid var(--bd);animation:fadeUp .5s backwards;}
.ship:last-child{border-bottom:none}

@media (prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def header(subtitle="Velora Sportswear"):
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
query($cursor: String) {
  orders(first: 100, after: $cursor, sortKey: CREATED_AT, reverse: true) {
    pageInfo { hasNextPage endCursor }
    nodes { id name createdAt }
  }
}
"""

DETAIL_QUERY = """
query($id: ID!) {
  order(id: $id) {
    name
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


@st.cache_data(ttl=300)
def fetch_order_list(max_pages=5):
    rows, cursor = [], None
    for _ in range(max_pages):
        data = gql(LIST_QUERY, {"cursor": cursor})
        if "errors" in data:
            st.error(data["errors"])
            break
        orders = data["data"]["orders"]
        for o in orders["nodes"]:
            rows.append({"Order": o["name"], "Date": o["createdAt"][:10], "id": o["id"]})
        if not orders["pageInfo"]["hasNextPage"]:
            break
        cursor = orders["pageInfo"]["endCursor"]
    return pd.DataFrame(rows)


@st.cache_data(ttl=120)
def fetch_order(order_id):
    return gql(DETAIL_QUERY, {"id": order_id})


# ---------- Render helpers ----------
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
        body = '<span style="color:#8b929c">Not available</span>'
    else:
        parts = [a.get("name"), a.get("address1"), a.get("address2"),
                 " ".join(filter(None, [a.get("zip"), a.get("city")])),
                 a.get("province"), a.get("country"), a.get("phone")]
        body = "<br>".join(html.escape(p) for p in parts if p)
    return f'<div class="panel"><h4>{title}</h4><div class="addr">{body}</div></div>'


# ---------- Page 2: order details ----------
def order_page(order_id):
    header("Order details")
    if st.button("← Back to orders"):
        st.session_state.pop("selected", None)
        st.rerun()

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

    with st.container(key="detail"):
        left, right = st.columns(2)

        with left:
            st.markdown(
                f'<h2 style="margin:0">Order {esc(order["name"])}</h2>'
                f'<div style="color:#8b929c;margin-bottom:12px">{order["createdAt"][:19].replace("T", " ")}</div>'
                f'{badge(order["displayFinancialStatus"])}{badge(order["displayFulfillmentStatus"])}',
                unsafe_allow_html=True,
            )

            total_items = sum(i["quantity"] for i in order["lineItems"]["nodes"])
            chips = f'<span class="badge neutral">TOTAL ITEMS: {total_items}</span>'
            for code in order.get("discountCodes") or []:
                chips += f'<span class="badge ok">DISCOUNT CODE: {esc(code)}</span>'
            st.markdown(chips, unsafe_allow_html=True)

            items = ""
            for n, i in enumerate(order["lineItems"]["nodes"]):
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
                disc_row = (f'<div class="tot" style="color:#5be39a"><span>{label}</span>'
                            f'<span>-{money(disc)}</span></div>')
            totals = (
                f'<div class="tot"><span>Subtotal</span><span>{money(order["currentSubtotalPriceSet"])}</span></div>'
                f'{disc_row}'
                f'<div class="tot"><span>Shipping</span><span>{money(order["totalShippingPriceSet"])}</span></div>'
                f'<div class="tot"><span>Tax</span><span>{money(order["totalTaxSet"])}</span></div>'
                f'<div class="tot big"><span>Total</span><span>{money(order["totalPriceSet"])}</span></div>'
            )
            extra = ""
            if order["paymentGatewayNames"]:
                extra += f'<div class="kv">Payment method: <b>{esc(", ".join(order["paymentGatewayNames"]))}</b></div>'
            if order["tags"]:
                extra += f'<div class="kv">Tags: <b>{esc(", ".join(order["tags"]))}</b></div>'
            if order["note"]:
                extra += f'<div class="kv">Note: <b>{esc(order["note"])}</b></div>'
            st.markdown(f'<div class="panel"><h4>Summary</h4>{totals}{extra}</div>', unsafe_allow_html=True)

            ship_html = ""
            for n, f in enumerate(order.get("fulfillments") or []):
                ship_html += f'<div class="ship" style="animation-delay:{n * 0.1:.1f}s">{badge(f["status"])}'
                trackings = f.get("trackingInfo") or []
                if not trackings:
                    ship_html += '<div style="color:#8b929c">No tracking code added yet.</div>'
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
                ship_html = '<div style="color:#8b929c">Not fulfilled yet. Tracking will appear here once it ships.</div>'
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
                    '<div style="color:#8b929c;font-size:.8rem">No customer record '
                    '(guest checkout or access not approved).</div>'
                )
            st.markdown(f'<div class="panel"><h4>Customer</h4>{body}</div>', unsafe_allow_html=True)
            st.markdown(address_html("Shipping address", order.get("shippingAddress")), unsafe_allow_html=True)
            st.markdown(address_html("Billing address", order.get("billingAddress")), unsafe_allow_html=True)


# ---------- Page 1: order list ----------
def list_page():
    header()
    df = fetch_order_list()
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
    p2.markdown(f'<div style="text-align:center;color:#8b929c;padding-top:6px">Page {page + 1} / {pages} · {len(df)} orders</div>',
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