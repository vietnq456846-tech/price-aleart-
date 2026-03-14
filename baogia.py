import streamlit as st
import pandas as pd
from binance.client import Client
import time
import warnings
import streamlit.components.v1 as components
import concurrent.futures
import plotly.express as px
import requests

warnings.filterwarnings("ignore")

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="BINANCE SPOT TRACKER V4.2", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS UI PRO (CYBERPUNK GLOW) ---
st.markdown("""
<style>
    /* Nền tổng thể */
    .stApp { background-color: #06090e; }
    
    /* Thiết kế Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 45px; background-color: #161b22; border-radius: 8px 8px 0px 0px;
        padding: 10px 20px; color: #848e9c; font-weight: 600; border: 1px solid rgba(255,255,255,0.05); border-bottom: none;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(180deg, rgba(243, 186, 47, 0.15) 0%, rgba(22, 27, 34, 1) 100%);
        color: #F3BA2F !important; font-weight: 800; border-top: 2px solid #F3BA2F;
        box-shadow: 0px -5px 15px rgba(243, 186, 47, 0.2);
    }
    
    /* Bảng Data Bo góc */
    [data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3); }
    
    /* Main Title Neon Glow */
    .main-title {
        text-align: center; font-family: 'Arial Black', sans-serif; font-size: 42px;
        background: -webkit-linear-gradient(90deg, #F3BA2F, #f5d47a, #F3BA2F); -webkit-background-clip: text;
        -webkit-text-fill-color: transparent; text-shadow: 0px 0px 20px rgba(243, 186, 47, 0.4); margin-bottom: 5px;
    }
    
    /* Bảng bối cảnh BTC */
    .btc-dashboard {
        background: rgba(22, 27, 34, 0.8); backdrop-filter: blur(10px); border-radius: 10px; padding: 15px 20px; 
        margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.4);
    }
</style>
""", unsafe_allow_html=True)

CATEGORIES = {
    "🔥 Layer 1 / Layer 2": ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT', 'AVAXUSDT', 'MATICUSDT', 'DOTUSDT', 'LINKUSDT', 'NEARUSDT', 'APTUSDT', 'SUIUSDT', 'ARBUSDT', 'OPUSDT'],
    "🐶 Meme Coins": ['DOGEUSDT', 'SHIBUSDT', 'PEPEUSDT', 'FLOKIUSDT', 'BONKUSDT', 'WIFUSDT', 'MEMEUSDT', 'BOMEUSDT', 'TURBOUSDT', 'NEIROUSDT'],
    "🤖 AI & Big Data": ['FETUSDT', 'AGIXUSDT', 'OCEANUSDT', 'RNDRUSDT', 'WLDUSDT', 'TAOUSDT', 'ARKMUSDT', 'IQUSDT', 'PHBUSDT'],
    "🎮 GameFi & Metaverse": ['SANDUSDT', 'MANAUSDT', 'GALAUSDT', 'AXSUSDT', 'ILVUSDT', 'PIXELUSDT', 'PORTALUSDT', 'YGGUSDT'],
    "🏢 RWA (Real World Assets)": ['ONDOUSDT', 'PENDLEUSDT', 'MKRUSDT', 'SNXUSDT', 'POLYXUSDT', 'TRUUSDT', 'OMUSDT'],
    "⚽ Fan Tokens": ['SANTOSUSDT', 'LAZIOUSDT', 'PORTOUSDT', 'ALPINEUSDT', 'PSGUSDT', 'BARUSDT', 'CITYUSDT']
}

def play_sound():
    components.html("""<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mpeg"></audio>""", height=0)

def inject_js():
    components.html("""
        <script>
        window.parent.notifyMe = function(symbol, percent, tf, unit) {
            if (Notification.permission === "granted") {
                new Notification("🚀 BƠM TIỀN: " + symbol, {
                    body: "Tăng " + percent + "% trong " + tf + " " + unit,
                    icon: "https://cryptologos.cc/logos/binance-coin-bnb-logo.png"
                });
            }
        }
        </script>
    """, height=0)

inject_js()

def format_volume(vol):
    if vol >= 1_000_000_000: return f"${vol/1_000_000_000:.2f}B"
    elif vol >= 1_000_000: return f"${vol/1_000_000:.2f}M"
    elif vol >= 1_000: return f"${vol/1_000:.1f}K"
    return f"${vol:,.0f}".replace(',', '.')

@st.cache_resource
def get_client(): return Client()
client = get_client()

@st.cache_data(ttl=3600)
def get_spot_symbols():
    try:
        info = client.get_exchange_info()
        return sorted([s['symbol'] for s in info['symbols'] if s['status'] == 'TRADING' and ('SPOT' in s.get('permissions', []) or s.get('isSpotTradingAllowed', False))])
    except: return []

all_spot_coins = get_spot_symbols()

@st.cache_data(ttl=15)
def get_btc_context():
    try:
        k_15m = client.get_klines(symbol='BTCUSDT', interval='15m', limit=100)
        k_5m = client.get_klines(symbol='BTCUSDT', interval='5m', limit=100)

        def calc_rsi(klines):
            closes = [float(k[4]) for k in klines]
            delta = pd.Series(closes).diff()
            gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
            loss = -delta.clip(upper=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))

        rsi_15m, rsi_5m = calc_rsi(k_15m).iloc[-1], calc_rsi(k_5m).iloc[-1]
        change_15m = ((float(k_15m[-1][4]) - float(k_15m[-1][1])) / float(k_15m[-1][1])) * 100
        change_5m = ((float(k_5m[-1][4]) - float(k_5m[-1][1])) / float(k_5m[-1][1])) * 100

        return {
            "price": float(k_5m[-1][4]), "rsi_5m": round(rsi_5m, 1), "rsi_15m": round(rsi_15m, 1),
            "change_5m": round(change_5m, 2), "change_15m": round(change_15m, 2)
        }
    except: return None

def fetch_single_coin(symbol, interval, limit_candle, vol_dict, ticker_dict):
    try:
        fetch_limit = max(limit_candle * 2, 100)
        klines = client.get_klines(symbol=symbol, interval=interval, limit=fetch_limit)
        
        if len(klines) >= limit_candle * 2:
            target_klines = klines[-limit_candle:]
            prev_klines = klines[-(limit_candle*2):-limit_candle]
            
            p_old = float(target_klines[0][1]) 
            p_now = float(target_klines[-1][4]) 
            
            vol_in_tf = sum(float(k[7]) for k in target_klines) 
            prev_vol_in_tf = sum(float(k[7]) for k in prev_klines)
            vol_spike = (vol_in_tf / prev_vol_in_tf * 100) if prev_vol_in_tf > 0 else 100.0
            
            buy_vol_in_tf = sum(float(k[10]) for k in target_klines)
            sell_vol_in_tf = vol_in_tf - buy_vol_in_tf
            buy_ratio = (buy_vol_in_tf / vol_in_tf * 100) if vol_in_tf > 0 else 50.0
            tb_ts_ratio = buy_vol_in_tf / sell_vol_in_tf if sell_vol_in_tf > 0 else (9.99 if buy_vol_in_tf > 0 else 1.0)
            
            cum_tp_vol, cum_vol = 0, 0
            for k in target_klines:
                tp = (float(k[2]) + float(k[3]) + float(k[4])) / 3
                cum_tp_vol += tp * float(k[5])
                cum_vol += float(k[5])
            vwap = cum_tp_vol / cum_vol if cum_vol > 0 else p_now
            vwap_dist = ((p_now - vwap) / vwap) * 100
            
            closes = [float(k[4]) for k in klines]
            delta = pd.Series(closes).diff()
            gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
            loss = -delta.clip(upper=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
            
            high_24h = ticker_dict.get(symbol, {}).get('high', p_now)
            drop_from_high = ((p_now - high_24h) / high_24h * 100) if high_24h > 0 else 0.0
            
            if p_old > 0:
                change = ((p_now - p_old) / p_old) * 100
                return {
                    'Symbol': symbol, 'Giá ($)': p_now, 'Biến động (%)': round(change, 2),
                    'Đột biến Vol (%)': round(vol_spike, 0), 'Độ lệch VWAP (%)': round(vwap_dist, 2),
                    'Tỷ lệ Mua/Bán': round(tb_ts_ratio, 2), 'Lực Mua (%)': round(buy_ratio, 1), 
                    'RSI (14)': round(current_rsi, 1), 'Cách Đỉnh 24h (%)': round(drop_from_high, 2),
                    'vol_tf': vol_in_tf, 'Volume 24h ($)': vol_dict.get(symbol, 0)
                }
    except: pass
    return None

def get_scan_data_fast(val, unit, vol_limit, selected_categories, pinned):
    if not all_spot_coins: return pd.DataFrame(), ""
    if unit == "Phút": interval, limit_candle, unit_char = '1m', val, 'm'
    elif unit == "Giờ": interval, limit_candle, unit_char = '1m', val * 60, 'h'
    else: interval, limit_candle, unit_char = '1h', val * 24, 'd'
        
    if limit_candle > 1000: interval = '1h' if unit == 'Giờ' else '1d'; limit_candle = val
    vol_col_name = f'Volume {val}{unit_char} ($)'

    try:
        tickers = client.get_ticker()
        vol_dict = {t['symbol']: float(t['quoteVolume']) for t in tickers if t['symbol'].endswith('USDT') and t['symbol'] in all_spot_coins}
        ticker_dict = {t['symbol']: {'high': float(t['highPrice'])} for t in tickers if t['symbol'].endswith('USDT')}
        
        sorted_coins_by_vol = sorted(vol_dict.items(), key=lambda x: x[1], reverse=True)
        
        target_symbols = []
        if selected_categories:
            allowed_symbols = set()
            for cat in selected_categories: allowed_symbols.update(CATEGORIES[cat])
            target_symbols = [s for s, v in sorted_coins_by_vol if s in allowed_symbols or s in pinned]
        else:
            filtered = [s for s, v in sorted_coins_by_vol if v >= vol_limit or s in pinned]
            target_symbols = filtered[:120] # Đảm bảo an toàn IP
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
            futures = {executor.submit(fetch_single_coin, sym, interval, limit_candle, vol_dict, ticker_dict): sym for sym in target_symbols}
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res:
                    res[vol_col_name] = res.pop('vol_tf')
                    results.append(res)
        return pd.DataFrame(results), vol_col_name
    except: return pd.DataFrame(), ""

def call_openai_api(api_key, prompt):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {"model": "gpt-4o-mini", "messages": [{"role": "system", "content": "Bạn là chuyên gia trade Spot. Trả lời ngắn gọn, đánh giá rủi ro rõ ràng."}, {"role": "user", "content": prompt}]}
    try:
        res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=15)
        if res.status_code == 200: return res.json()['choices'][0]['message']['content']
        return f"Lỗi OpenAI ({res.status_code})"
    except Exception as e: return f"Lỗi OpenAI: {str(e)}"

def call_gemini_api(api_key, prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"
    data = {"contents": [{"parts":[{"text": "Chuyên gia Trade Spot: " + prompt}]}]}
    try:
        res = requests.post(url, json=data, timeout=15)
        if res.status_code == 200: return res.json()['candidates'][0]['content']['parts'][0]['text']
        return f"Lỗi Gemini ({res.status_code})"
    except Exception as e: return f"Lỗi kết nối Gemini: {str(e)}"

# --- SIDEBAR UI ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/1/12/Binance_logo.svg", width=180)
st.sidebar.markdown("### ⚙️ BỘ LỌC CỐT LÕI")

selected_cats = st.sidebar.multiselect("🌊 Lọc Sóng Ngành (Trends):", options=list(CATEGORIES.keys()), help="Bỏ trống để quét Top toàn thị trường.")
pinned_coins = st.sidebar.multiselect("📌 Ghim Coin theo dõi:", options=all_spot_coins, default=[])

st.sidebar.markdown("---")
col_tf1, col_tf2 = st.sidebar.columns(2)
with col_tf1: tf_value = st.number_input("Thời gian", value=5, min_value=1, max_value=1000)
with col_tf2: tf_unit = st.selectbox("Đơn vị", ["Phút", "Giờ", "Ngày"], index=0)

min_vol_24h = st.sidebar.number_input("Volume tối thiểu ($)", value=1000000, step=500000, disabled=bool(selected_cats))
threshold = st.sidebar.slider("Ngưỡng báo động (%)", 0.1, 20.0, 1.5, step=0.1)

st.sidebar.markdown("---")
st.sidebar.markdown("### 👁️ HIỂN THỊ CHỈ BÁO")
all_indicators = ["Biến động (%)", "Đột biến Vol (%)", "Độ lệch VWAP (%)", "Tỷ lệ Mua/Bán", "Lực Mua (%)", "RSI (14)", "Cách Đỉnh 24h (%)"]
default_indicators = ["Biến động (%)", "Đột biến Vol (%)", "Độ lệch VWAP (%)", "Tỷ lệ Mua/Bán", "RSI (14)"]
selected_indicators = st.sidebar.multiselect("Chọn các chỉ số muốn xem:", options=all_indicators, default=default_indicators)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🧠 CẤU HÌNH AI")
ai_provider = st.sidebar.selectbox("Lõi Phân Tích:", ["Google Gemini", "OpenAI (ChatGPT)"])
ai_api_key = st.sidebar.text_input("🔑 Nhập API Key:", type="password")

st.sidebar.markdown("---")
refresh_val = st.sidebar.slider("Tốc độ Auto-Refresh (giây)", 5, 300, 5) 
auto_refresh = st.sidebar.toggle("⚡ BẬT AUTO SCAN", value=True)

if st.sidebar.button("🔔 KIỂM TRA ÂM THANH", use_container_width=True):
    components.html("<script>Notification.requestPermission();</script>")
    play_sound()

# ----------------- TÍNH NĂNG MỚI: BẢNG CHỮ LED -----------------
st.sidebar.markdown("---")
st.sidebar.markdown("### 📢 BẢNG LED NHẮC NHỞ")
show_led = st.sidebar.toggle("💡 Bật LED dưới đáy màn hình", value=True)
led_text = st.sidebar.text_input("Nội dung chạy:", value="⚠️ KỶ LUẬT THÉP: Vốn $35. Chỉ báo MUA khi ĐỒNG THUẬN (🔥 Vol Nổ + 🐳 Cá Mập Mua + VWAP DƯƠNG). Lãi 7% chốt, Lỗ 4% cắt!! ⚠️")


# --- MAIN DASHBOARD ---
st.markdown("<h1 class='main-title'>⚡ BINANCE SPOT TRACKER</h1>", unsafe_allow_html=True)

# Hiển thị BTC Context
btc_ctx = get_btc_context()
if btc_ctx:
    btc_color = "#00e676" if btc_ctx['change_15m'] >= 0 else "#ff3366"
    btc_border = "1px solid #00e676" if btc_ctx['change_15m'] >= 0 else "1px solid #ff3366"
    btc_shadow = "0px 0px 15px rgba(0, 230, 118, 0.2)" if btc_ctx['change_15m'] >= 0 else "0px 0px 15px rgba(255, 51, 102, 0.2)"
    
    warn_text = "⚖️ **ỔN ĐỊNH:** BTC đi ngang, cơ hội cho dòng tiền chạy qua Altcoin."
    if btc_ctx['change_15m'] < -0.5 or btc_ctx['rsi_15m'] < 30:
        warn_text = "⚠️ **CẢNH BÁO:** BTC đang xả mạnh! Cực kỳ cẩn thận khi bắt đáy Altcoin lúc này."
    elif btc_ctx['change_15m'] > 0.5 or btc_ctx['rsi_15m'] > 70:
        warn_text = "🚀 **TÍN HIỆU TỐT:** BTC đang hút dòng tiền, thị trường hưng phấn!"

    st.markdown(f"""
    <div class="btc-dashboard" style="border: {btc_border}; border-left: 5px solid {btc_color}; box-shadow: {btc_shadow};">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div><span style="font-size: 24px; font-weight: 900; color: {btc_color}; text-shadow: 0 0 10px {btc_color};">₿ BTC/USDT: ${btc_ctx['price']:,.2f}</span></div>
            <div style="font-size: 15px; color: #EAECEF;"><b>5m:</b> {btc_ctx['change_5m']}% (RSI: {btc_ctx['rsi_5m']}) | <b>15m:</b> {btc_ctx['change_15m']}% (RSI: {btc_ctx['rsi_15m']})</div>
        </div>
        <div style="margin-top: 8px; color: #EAECEF; font-size: 14px;">{warn_text}</div>
    </div>
    """, unsafe_allow_html=True)

if 'notified' not in st.session_state: st.session_state.notified = {}

df, dynamic_vol_col = get_scan_data_fast(tf_value, tf_unit, min_vol_24h, selected_cats, pinned_coins)

if not df.empty and dynamic_vol_col:
    df['is_pinned'] = df['Symbol'].isin(pinned_coins)
    df['Ghim'] = df['is_pinned'].apply(lambda x: '⭐' if x else '')
    
    # HỆ THỐNG PHÁT TÍN HIỆU THÔNG MINH
    def generate_signals(row):
        sigs = []
        if row.get('Biến động (%)', 0) >= threshold: sigs.append("🚀")
        if row.get('Đột biến Vol (%)', 0) >= 300: sigs.append("🔥")
        if row.get('Tỷ lệ Mua/Bán', 1) >= 1.5: sigs.append("🐳")
        if row.get('RSI (14)', 50) >= 70: sigs.append("⚠️")
        elif row.get('RSI (14)', 50) <= 30: sigs.append("🟢")
        return " | ".join(sigs) if sigs else "➖"
        
    df['Tín Hiệu'] = df.apply(generate_signals, axis=1)
    
    df = df.sort_values(by=['is_pinned', 'Biến động (%)'], ascending=[False, False])
    df = df.reset_index(drop=True) 
    
    df['Vào Sàn'] = df['Symbol'].apply(lambda x: f"https://www.binance.com/vi/trade/{x.replace('USDT', '_USDT')}?type=spot")
    gainers = df[df['Biến động (%)'] >= threshold]
    
    tab_bubbles, tab_data = st.tabs(["🫧 BẢN ĐỒ DÒNG TIỀN (HEATMAP)", "📊 RADAR CÁ MẬP"])
    
    with tab_bubbles:
        heatmap_options = selected_indicators + [f"Volume {tf_value} {tf_unit}"] if selected_indicators else [f"Volume {tf_value} {tf_unit}"]
        bubble_display = st.radio("📍 Tùy chỉnh thông số hiển thị:", heatmap_options, horizontal=True)
        
        if bubble_display == "Biến động (%)": df['Bubble_Text'] = df.apply(lambda x: f"<b>{x['Symbol'].replace('USDT', '')}</b><br>{'+' if x['Biến động (%)'] > 0 else ''}{x['Biến động (%)']}%", axis=1)
        elif bubble_display == "Đột biến Vol (%)": df['Bubble_Text'] = df.apply(lambda x: f"<b>{x['Symbol'].replace('USDT', '')}</b><br>Vol: {x['Đột biến Vol (%)']:.0f}%", axis=1)
        elif bubble_display == "Độ lệch VWAP (%)": df['Bubble_Text'] = df.apply(lambda x: f"<b>{x['Symbol'].replace('USDT', '')}</b><br>VWAP: {x['Độ lệch VWAP (%)']}%", axis=1)
        elif bubble_display == "Tỷ lệ Mua/Bán": df['Bubble_Text'] = df.apply(lambda x: f"<b>{x['Symbol'].replace('USDT', '')}</b><br>M/B: {x['Tỷ lệ Mua/Bán']}", axis=1)
        elif bubble_display == "RSI (14)": df['Bubble_Text'] = df.apply(lambda x: f"<b>{x['Symbol'].replace('USDT', '')}</b><br>RSI: {x['RSI (14)']}", axis=1)
        else: df['Bubble_Text'] = df.apply(lambda x: f"<b>{x['Symbol'].replace('USDT', '')}</b><br>{format_volume(x[dynamic_vol_col])}", axis=1)
        
        fig = px.treemap(
            df, path=[px.Constant("Thị Trường"), 'Bubble_Text'], values=dynamic_vol_col if not selected_cats else 'Volume 24h ($)', 
            color='Biến động (%)', color_continuous_scale=['#ff4d4d', '#161b22', '#00e676'], color_continuous_midpoint=0,
            custom_data=['Symbol', 'Giá ($)', 'Biến động (%)', 'Đột biến Vol (%)', 'Độ lệch VWAP (%)', 'Tỷ lệ Mua/Bán', 'RSI (14)']
        )
        fig.update_traces(
            textinfo="label", textfont=dict(size=19, color="white", family="Arial Black"),
            hovertemplate="<br>".join(["<b style='font-size: 16px;'>%{customdata[0]}</b>", "Giá: $%{customdata[1]:.6f} (%{customdata[2]}%)", "VWAP Lệch: %{customdata[4]}%", "Đột biến Vol: %{customdata[3]}%", "Tỷ lệ Mua/Bán: %{customdata[5]} | RSI: %{customdata[6]}"]),
            marker=dict(line=dict(width=2, color="#06090e")), root_color="#06090e"
        )
        fig.update_layout(margin=dict(t=10, l=0, r=0, b=0), height=600, paper_bgcolor="#06090e", plot_bgcolor="#06090e")
        st.plotly_chart(fig, use_container_width=True)

    with tab_data:
        m1, m2, m3 = st.columns(3)
        m1.info(f"🔎 Tổng TOP mã đang quét: **{len(df)}**")
        m2.success(f"🔥 Đạt ngưỡng bơm: **{len(gainers)}**")
        if auto_refresh: m3.warning(f"⚡ Đang Auto-Scan 5s")
        else: m3.error("🔴 Đang Dừng Quét")

        base_cols = ['Ghim', 'Tín Hiệu', 'Symbol', 'Giá ($)']
        end_cols = [dynamic_vol_col, 'Vào Sàn']
        valid_indicators = [i for i in selected_indicators if i not in base_cols and i not in end_cols]
        
        final_cols = base_cols + valid_indicators + end_cols
        unique_cols = list(dict.fromkeys(final_cols))
        display_df = df[unique_cols].copy()

        # --- TÍNH NĂNG MỚI: HÀM TÔ MÀU HIGHLIGHT ---
        def highlight_pump(row):
            # Điều kiện: Nếu Biến động (%) lớn hơn hoặc bằng Ngưỡng báo động (threshold)
            if row['Biến động (%)'] >= threshold:
                # Dùng rgba với độ trong suốt 15% để highlight êm mắt, in đậm chữ
                return ['background-color: rgba(0, 230, 118, 0.15); font-weight: bold; color: #00e676;'] * len(row)
            # Nếu có sóng rớt mạnh (Giảm quá threshold) thì highlight đỏ mờ cảnh báo
            elif row['Biến động (%)'] <= -threshold:
                return ['background-color: rgba(255, 51, 102, 0.15);'] * len(row)
            return [''] * len(row)

        # Áp dụng hàm tô màu vào DataFrame
        styled_df = display_df.style.apply(highlight_pump, axis=1)

        col_settings = {
            "Vào Sàn": st.column_config.LinkColumn("🛒 Spot", display_text="👉 Múc Ngay"),
            "Giá ($)": st.column_config.NumberColumn("Giá ($)", format="$ %.6f"),
            "Biến động (%)": st.column_config.NumberColumn("Biến động (%)", format="%.2f %%"),
            "Đột biến Vol (%)": st.column_config.NumberColumn("Đột biến Vol (%)", format="%.0f %%"),
            "Độ lệch VWAP (%)": st.column_config.NumberColumn("Độ lệch VWAP (%)", format="%.2f %%"),
            "Tỷ lệ Mua/Bán": st.column_config.NumberColumn("Tỷ lệ Mua/Bán", format="%.2f"),
            "Cách Đỉnh 24h (%)": st.column_config.NumberColumn("Cách Đỉnh 24h (%)", format="%.2f %%"),
            "Lực Mua (%)": st.column_config.NumberColumn("Lực Mua (%)", format="%.1f %%"),
            "RSI (14)": st.column_config.NumberColumn("RSI (14)", format="%.1f"),
            dynamic_vol_col: st.column_config.NumberColumn(dynamic_vol_col, format="$ %d")
        }

        # Hiển thị bảng đã được tô màu (truyền styled_df thay vì display_df)
        st.dataframe(
            styled_df,
            column_config=col_settings,
            use_container_width=True, 
            height=350,
            hide_index=True 
        )

    # --- KHU VỰC CHART LUÔN HIỂN THỊ Ở DƯỚI ---
    st.markdown("<br><hr style='border:1px dashed rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    st.markdown(f"### 📈 BIỂU ĐỒ & AI THẨM ĐỊNH TỰ DO")
    
    col_search, col_ai_btn = st.columns([3, 1])
    
    with col_search:
        default_index = all_spot_coins.index("BTCUSDT") if "BTCUSDT" in all_spot_coins else 0
        search_symbol = st.selectbox("🔍 Gõ tên hoặc chọn Coin để soi Chart & Phân tích:", options=all_spot_coins, index=default_index)
        
    tv_widget = f"""
    <div class="tradingview-widget-container" style="height:100%;width:100%; border-radius:12px; overflow:hidden; border: 1px solid rgba(0, 230, 118, 0.2); box-shadow: 0 0 20px rgba(0, 230, 118, 0.05);">
      <div id="tradingview_chart" style="height:550px;width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
      "autosize": true, "symbol": "BINANCE:{search_symbol}", "interval": "15",
      "timezone": "Asia/Ho_Chi_Minh", "theme": "dark", "style": "1", "locale": "vi",
      "enable_publishing": false, "allow_symbol_change": true, "backgroundColor": "#0b0e14", "gridColor": "rgba(255, 255, 255, 0.03)",
      "hide_top_toolbar": false, "hide_legend": false, "save_image": false, "container_id": "tradingview_chart"
    }});
      </script>
    </div>
    """
    components.html(tv_widget, height=550)
    
    with col_ai_btn:
        st.write("") 
        trigger_ai = st.button("🧠 AI TƯ VẤN KÈO NÀY", type="primary", use_container_width=True)

    if trigger_ai:
        coin_in_df = df[df['Symbol'] == search_symbol]
        
        if not coin_in_df.empty:
            coin_data = coin_in_df.iloc[0]
            ai_prompt = f"Phân tích Spot mã {search_symbol}: Giá ${coin_data['Giá ($)']}, RSI {coin_data.get('RSI (14)', 'N/A')}, Tỷ lệ Mua/Bán (Taker) {coin_data.get('Tỷ lệ Mua/Bán', 'N/A')}, Độ lệch VWAP {coin_data.get('Độ lệch VWAP (%)', 'N/A')}%, Vol Đột biến {coin_data.get('Đột biến Vol (%)', 'N/A')}%. KẾT LUẬN: MUA hay QUAN SÁT."
            
            if ai_api_key == "":
                st.success(f"🤖 **AI Nội Bộ Nhận Định ({search_symbol}):**")
                rsi, vol_spike, vwap_dist, buy_sell_ratio = coin_data.get('RSI (14)', 50), coin_data.get('Đột biến Vol (%)', 0), coin_data.get('Độ lệch VWAP (%)', 0), coin_data.get('Tỷ lệ Mua/Bán', 1)
                
                advice = "✅ **Vol / Lực mua:** Đột biến mạnh, phe Mua làm chủ.\n" if vol_spike > 200 and buy_sell_ratio >= 1.2 else "⚖️ **Dòng tiền:** Đang giằng co, chưa có dấu hiệu tay to gom hàng.\n"
                
                if vwap_dist > 0: advice += f"✅ **Xu hướng:** Giá đang nằm TRÊN VWAP (+{vwap_dist}%), lực tăng được ủng hộ.\n"
                else: advice += f"⚠️ **Xu hướng:** Giá nằm DƯỚI VWAP ({vwap_dist}%), lực bán đè nén.\n"
                
                if rsi > 70: advice += "⚠️ **Cảnh báo:** RSI Quá Mua, coi chừng đu đỉnh!\n"
                
                if rsi < 65 and vol_spike > 150 and buy_sell_ratio > 1.1 and vwap_dist > 0:
                    advice += "\n👉 **KẾT LUẬN: ĐIỂM VÀO ĐẸP.** Giá vượt VWAP + Vol nổ, đánh Breakout chuẩn bài."
                else:
                    advice += "\n👉 **KẾT LUẬN: RỦI RO CAO. QUAN SÁT!** Vị thế chưa đủ an toàn."
                st.markdown(advice)
        else:
            ai_prompt = f"Đánh giá xu hướng ngắn hạn của mã {search_symbol} trên Binance. Lời khuyên MUA hay ĐỨNG NGOÀI?"
            if ai_api_key == "":
                st.success(f"🤖 **AI Nội Bộ Nhận Định ({search_symbol}):**")
                st.markdown(f"Mã **{search_symbol}** hiện không có Vol đột biến hoặc bị bộ lọc an toàn IP loại trừ. \n👉 **Khuyến nghị:** QUAN SÁT.")

        if ai_api_key != "":
            with st.spinner("Cố vấn AI đang phân tích rủi ro..."):
                if "Gemini" in ai_provider: ai_response = call_gemini_api(ai_api_key, ai_prompt)
                else: ai_response = call_openai_api(ai_api_key, ai_prompt)
                st.success(f"🤖 **AI Chuyên Gia ({search_symbol}):**")
                st.markdown(ai_response)

    curr_ts = time.time()
    for _, row in gainers.iterrows():
        s = row['Symbol']
        if s not in st.session_state.notified or (curr_ts - st.session_state.notified[s] > 120):
            components.html(f"<script>window.parent.notifyMe('{s}', '{row['Biến động (%)']}', '{tf_value}', '{tf_unit}')</script>", height=0)
            play_sound() 
            st.session_state.notified[s] = curr_ts

# ----------------- INJECT JAVASCRIPT CHO BẢNG LED & AUTO REFRESH -----------------
# Chúng ta dùng chung 1 block script để quản lý Timer và thanh LED, tránh xung đột DOM
led_flag = 'true' if show_led else 'false'
safe_led_text = led_text.replace('"', '\\"').replace("'", "\\'")

js_code = f"""
<script>
    // --- XỬ LÝ BẢNG LED ---
    let showLed = {led_flag};
    let ledContainer = window.parent.document.getElementById("custom-cyber-led");
    
    if (showLed) {{
        if (!ledContainer) {{
            // Tạo thanh LED nếu chưa có
            ledContainer = window.parent.document.createElement("div");
            ledContainer.id = "custom-cyber-led";
            ledContainer.style.position = "fixed";
            ledContainer.style.bottom = "0";
            ledContainer.style.left = "0";
            ledContainer.style.width = "100%";
            ledContainer.style.backgroundColor = "#000000";
            ledContainer.style.borderTop = "2px solid #00e676";
            ledContainer.style.boxShadow = "0px -5px 25px rgba(0, 230, 118, 0.3)";
            ledContainer.style.zIndex = "999999";
            ledContainer.style.overflow = "hidden";
            ledContainer.style.whiteSpace = "nowrap";
            ledContainer.style.padding = "8px 0";
            
            let textElem = window.parent.document.createElement("div");
            textElem.id = "custom-led-text";
            textElem.style.display = "inline-block";
            textElem.style.color = "#00e676";
            textElem.style.fontFamily = "'Courier New', Courier, monospace";
            textElem.style.fontSize = "22px";
            textElem.style.fontWeight = "900";
            textElem.style.textShadow = "0 0 5px #00e676, 0 0 10px #00e676, 0 0 20px #00e676";
            
            // Tạo animation CSS
            let style = window.parent.document.createElement('style');
            style.innerHTML = '@keyframes cyberScroll {{ 0% {{ transform: translateX(100vw); }} 100% {{ transform: translateX(-100%); }} }}';
            window.parent.document.head.appendChild(style);
            
            textElem.style.animation = "cyberScroll 20s linear infinite";
            
            ledContainer.appendChild(textElem);
            window.parent.document.body.appendChild(ledContainer);
            
            // Đẩy layout chính lên một chút để không bị thanh LED che mất nút bấm
            let mainBlock = window.parent.document.querySelector('.main .block-container');
            if(mainBlock) mainBlock.style.paddingBottom = "80px";
        }}
        // Chỉ cập nhật nội dung chữ (Không làm reset lại animation lúc đang scroll)
        window.parent.document.getElementById("custom-led-text").innerText = "{safe_led_text}";
    }} else {{
        if (ledContainer) {{
            // Tắt LED thì gỡ bỏ element
            ledContainer.remove();
            let mainBlock = window.parent.document.querySelector('.main .block-container');
            if(mainBlock) mainBlock.style.paddingBottom = "2rem";
        }}
    }}

    // --- XỬ LÝ AUTO REFRESH TIMER ---
    let autoRefresh = {'true' if auto_refresh else 'false'};
    let timerDisplay = window.parent.document.getElementById("auto-timer-display");
    
    if (autoRefresh) {{
        if (!timerDisplay) {{
            timerDisplay = window.parent.document.createElement("div");
            timerDisplay.id = "auto-timer-display";
            timerDisplay.style.padding = "10px"; timerDisplay.style.marginTop = "10px";
            timerDisplay.style.borderRadius = "8px"; timerDisplay.style.backgroundColor = "rgba(243, 186, 47, 0.15)";
            timerDisplay.style.color = "#F3BA2F"; timerDisplay.style.fontWeight = "bold";
            timerDisplay.style.textAlign = "center";
            let targetDiv = window.parent.document.querySelector('[data-testid="stSidebar"] > div:first-child');
            if(targetDiv) targetDiv.appendChild(timerDisplay);
        }}
        timerDisplay.style.display = 'block';
        let timeLeft = {refresh_val};
        
        // Gỡ bỏ Interval cũ (nếu có) để tránh loạn nhịp
        if (window.parent.countdownInterval) clearInterval(window.parent.countdownInterval);
        
        window.parent.countdownInterval = setInterval(function() {{
            if(timeLeft <= 0) {{ 
                clearInterval(window.parent.countdownInterval); 
                timerDisplay.innerHTML = "🔄 Đang tải dữ liệu Mật..."; 
            }} else {{ 
                timerDisplay.innerHTML = "⏳ Quét lại sau: " + timeLeft + "s"; 
            }}
            timeLeft -= 1;
        }}, 1000);
    }} else {{
        if (timerDisplay) timerDisplay.style.display = 'none';
        if (window.parent.countdownInterval) clearInterval(window.parent.countdownInterval);
    }}
</script>
"""
components.html(js_code, height=0)

if auto_refresh:
    time.sleep(refresh_val)
    st.rerun()
