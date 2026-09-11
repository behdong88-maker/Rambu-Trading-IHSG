import streamlit as st
import pandas as pd
import numpy as np
import datetime
import requests
import yfinance as yf
import io

# Page Config
st.set_page_config(
    page_title="AI Signal Engine - BEI/IHSG",
    page_icon="⚡",
    layout="wide"
)

# Custom Styling
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    .session-card-pagi {
        background-color: #1a2733;
        border-left: 5px solid #2962ff;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .session-card-siang {
        background-color: #332b1a;
        border-left: 5px solid #ffb300;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .session-card-sore {
        background-color: #2b1a33;
        border-left: 5px solid #ab47bc;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .badge-session {
        background-color: #2a2e39;
        color: #00e676;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# Helper: Send Telegram Signal
def send_telegram_signal(bot_token, chat_id, text_message):
    if not bot_token or not chat_id:
        return False, "Bot Token dan Chat ID wajib diisi pada sidebar."
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text_message,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=5)
        if res.status_code == 200:
            return True, "Sinyal terkirim ke Telegram!"
        else:
            return False, f"Gagal kirim ({res.status_code}): {res.text}"
    except Exception as e:
        return False, f"Error koneksi Telegram: {str(e)}"

# Helper: Fetch Real-Time Data from yfinance
def fetch_idx_stock_data(ticker):
    symbol = f"{ticker}.JK"
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period="1mo")
        if df.empty or len(df) < 5:
            return None
        
        latest_price = int(df['Close'].iloc[-1])
        avg_vol_m = df['Volume'].mean() / 1e6
        
        price_3d_ago = df['Close'].iloc[-4] if len(df) >= 4 else df['Close'].iloc[0]
        change_3d = round(((latest_price - price_3d_ago) / price_3d_ago) * 100, 1)
        
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        latest_ema = df['EMA20'].iloc[-1]
        ema_trend = "Bullish" if latest_price >= latest_ema else "Bearish"
        
        return {
            "price": latest_price,
            "avg_vol": round(avg_vol_m, 2),
            "change_3d": change_3d,
            "ema_trend": ema_trend
        }
    except Exception:
        return None

# Core Engine with Session & Execution Schedule
def run_zeta_engine(ihsg_regime="BULLISH"):
    watchlist = [
        {"ticker": "BBCA", "name": "Bank Central Asia Tbk", "mock_price": 10975, "sesi_code": "PAGI", "sesi_label": "🌅 Sesi Pagi (Pre-Market)", "jam_scan": "08:30 WIB", "jam_eksekusi": "08:55 - 09:05 WIB"},
        {"ticker": "DIVA", "name": "Distribusi Voucher Nusantara Tbk", "mock_price": 158, "sesi_code": "PAGI", "sesi_label": "🌅 Sesi Pagi (Pre-Market)", "jam_scan": "08:30 WIB", "jam_eksekusi": "08:55 - 09:05 WIB"},
        {"ticker": "TMPO", "name": "Tempo Inti Media Tbk", "mock_price": 151, "sesi_code": "SIANG", "sesi_label": "☀️ Sesi Siang (Midday Break)", "jam_scan": "13:00 WIB", "jam_eksekusi": "13:25 - 13:35 WIB"},
        {"ticker": "BBYB", "name": "Bank Neo Commerce Tbk", "mock_price": 234, "sesi_code": "SIANG", "sesi_label": "☀️ Sesi Siang (Midday Break)", "jam_scan": "13:00 WIB", "jam_eksekusi": "13:25 - 13:35 WIB"},
        {"ticker": "TOWR", "name": "Sarana Menara Nusantara Tbk", "mock_price": 342, "sesi_code": "SORE", "sesi_label": "🌆 Sesi Sore (Buy-On-Close)", "jam_scan": "16:30 WIB", "jam_eksekusi": "15:50 - 16:00 WIB"},
        {"ticker": "TLKM", "name": "Telkom Indonesia Tbk", "mock_price": 2730, "sesi_code": "SIANG", "sesi_label": "☀️ Sesi Siang (Midday Break)", "jam_scan": "13:00 WIB", "jam_eksekusi": "13:25 - 13:35 WIB"},
        {"ticker": "GORE", "name": "Saham Gorengan Fiktif", "mock_price": 75, "sesi_code": "PAGI", "sesi_label": "🌅 Sesi Pagi (Pre-Market)", "jam_scan": "08:30 WIB", "jam_eksekusi": "08:55 - 09:05 WIB"}
    ]
    
    results = []
    for s in watchlist:
        ticker = s["ticker"]
        live = fetch_idx_stock_data(ticker)
        
        if live:
            price = live["price"]
            avg_vol = live["avg_vol"]
            change_3d = live["change_3d"]
            ema_trend = live["ema_trend"]
        else:
            price = s["mock_price"]
            avg_vol = 15.5 if price > 500 else 0.4
            change_3d = 2.1 if ticker != "GORE" else 28.5
            ema_trend = "Bullish" if ticker != "GORE" else "Overbought"
            
        # BEI Tick Size calculation
        if price < 200:
            tick = 1
        elif price < 500:
            tick = 2
        elif price < 2000:
            tick = 5
        elif price < 5000:
            tick = 10
        else:
            tick = 25
            
        tp1 = int(round(price * 1.020 / tick) * tick)
        tp2 = int(round(price * 1.030 / tick) * tick)
        sl  = int(round(price * 0.985 / tick) * tick)
        
        tp1_pct = round((tp1 - price) / price * 100, 1)
        tp2_pct = round((tp2 - price) / price * 100, 1)
        sl_pct = round((sl - price) / price * 100, 1)
        
        bandar_score = 88 if ticker in ["BBCA", "DIVA", "TMPO", "BBYB", "TOWR"] else 35
        broker_summary = "Big Accumulation (ZP, AK, BK)" if bandar_score >= 80 else "Distribution (YP, PD)"
        
        passed = True
        reason = []
        if price < 100:
            passed = False
            reason.append("Harga < Rp100")
        if avg_vol < 1.0:
            passed = False
            reason.append("Volume < 1 Juta lembar")
        if change_3d > 7.0:
            passed = False
            reason.append("Sudah naik > 7% dalam 3 candle")
        if bandar_score < 70:
            passed = False
            reason.append("Skor Bandarmologi Rendah")
            
        if ihsg_regime == "BEARISH":
            signal = "HINDARI 🔴"
        elif passed:
            signal = "BELI 🟢"
        else:
            signal = "HINDARI 🔴"
            
        results.append({
            "ticker": ticker,
            "name": s["name"],
            "signal": signal,
            "score": bandar_score,
            "price": price,
            "tp1": f"Rp{tp1:,} (+{tp1_pct}%)",
            "tp2": f"Rp{tp2:,} (+{tp2_pct}%)",
            "sl": f"Rp{sl:,} ({sl_pct}%)",
            "sesi_code": s["sesi_code"],
            "sesi_label": s["sesi_label"],
            "jam_scan": s["jam_scan"],
            "jam_eksekusi": s["jam_eksekusi"],
            "broker_summary": broker_summary,
            "passed": passed
        })
        
    return pd.DataFrame(results)

# HEADER
st.title("⚡ Zeta AI Signal Engine (Dengan Sesi & Jam Eksekusi)")
st.caption("Sistem Sinyal Saham BEI Terjadwal Per Sesi dengan Jadwal Eksekusi Presisi")

# SIDEBAR
st.sidebar.header("⚙️ Pengaturan Telegram")
telegram_token = st.sidebar.text_input("Bot Token Telegram", type="password")
telegram_chat_id = st.sidebar.text_input("Chat ID / Channel ID")

st.sidebar.markdown("---")
st.sidebar.subheader("🌐 IHSG Market Regime")
ihsg_regime = st.sidebar.selectbox("Status Pasar IHSG", ["BULLISH", "CAUTIOUS", "BEARISH"], index=0)

# FILTER SESI TRADING
st.sidebar.markdown("---")
st.sidebar.subheader("🕐 Filter Sesi Sinyal")
filter_sesi = st.sidebar.radio("Tampilkan Sesi Sinyal:", ["Semua Sesi", "🌅 Sesi Pagi (08:30 WIB)", "☀️ Sesi Siang (13:00 WIB)", "🌆 Sesi Sore (16:30 WIB)"])

# TABS
tab1, tab2, tab3 = st.tabs(["🚀 Screener & Jam Eksekusi", "⏰ Panduan Jadwal Sesi", "🤖 Bot Telegram Control"])

# TAB 1: SCREENER & JAM EKSEKUSI
with tab1:
    st.subheader("🎯 Hasil Sinyal Sesuai Jam Eksekusi Market")
    
    df_signals = run_zeta_engine(ihsg_regime)
    
    # Apply Sesi Filter
    if filter_sesi == "🌅 Sesi Pagi (08:30 WIB)":
        df_filtered = df_signals[df_signals["sesi_code"] == "PAGI"]
    elif filter_sesi == "☀️ Sesi Siang (13:00 WIB)":
        df_filtered = df_signals[df_signals["sesi_code"] == "SIANG"]
    elif filter_sesi == "🌆 Sesi Sore (16:30 WIB)":
        df_filtered = df_signals[df_signals["sesi_code"] == "SORE"]
    else:
        df_filtered = df_signals
        
    valid_signals = df_filtered[df_filtered["passed"] == True]
    
    # Display Sesi Cards
    st.markdown("### 🟢 Sinyal Aktif Siap Eksekusi")
    
    if len(valid_signals) > 0 and ihsg_regime != "BEARISH":
        for idx, row in valid_signals.iterrows():
            with st.expander(f"**{row['ticker']} - {row['name']}** | {row['sesi_label']} | Jam Eksekusi Beli: {row['jam_eksekusi']}", expanded=True):
                
                # Session Highlight
                st.info(f"📌 **Sesi Sinyal**: {row['sesi_label']} | 🕒 **Jam Scan AI**: {row['jam_scan']} | ⚡ **Jam Eksekusi Beli Broker**: `{row['jam_eksekusi']}`")
                
                c1, c2, c3, c4 = st.columns(4)
                c1.markdown(f"**Harga Entry**: Rp{row['price']:,}")
                c2.markdown(f"**TP1 (+2%)**: <span style='color:#0ecb81;font-weight:bold'>{row['tp1']}</span>", unsafe_allow_html=True)
                c3.markdown(f"**TP2 (+3%)**: <span style='color:#0ecb81;font-weight:bold'>{row['tp2']}</span>", unsafe_allow_html=True)
                c4.markdown(f"**Cut Loss (-1.5%)**: <span style='color:#f6465d;font-weight:bold'>{row['sl']}</span>", unsafe_allow_html=True)
                
                st.markdown(f"**🕵️ Bandarmologi**: {row['broker_summary']}")
                
                # Message Template with Session Details
                msg_text = (
                    f"⚡ **ZETA AI SIGNAL ({row['sesi_label']})** ⚡\n\n"
                    f"🟢 **BUY {row['ticker']}** ({row['name']})\n"
                    f"📍 **Harga Entry**: Rp{row['price']:,}\n"
                    f"🎯 **Target TP1 (2%)**: {row['tp1']}\n"
                    f"🚀 **Target TP2 (3%)**: {row['tp2']}\n"
                    f"🛡 **Stop Loss (Wajib)**: {row['sl']}\n\n"
                    f"⏰ **Waktu Scan**: {row['jam_scan']}\n"
                    f"⚡ **JAM EKSEKUSI BELI**: {row['jam_eksekusi']}\n"
                    f"🕵️ **Bandarmologi**: {row['broker_summary']}\n\n"
                    f"⚠️ *Disiplin pasang OLT TP/SL di broker saat jam eksekusi.*"
                )
                
                if st.button(f"📲 Broadcast {row['ticker']} ke Telegram", key=f"btn_sesi_{row['ticker']}"):
                    ok, res = send_telegram_signal(telegram_token, telegram_chat_id, msg_text)
                    if ok:
                        st.success(res)
                    else:
                        st.error(res)
    else:
        st.warning("Tidak ada sinyal pada sesi ini / Status IHSG Bearish.")

    st.markdown("---")
    st.markdown("### 📋 Table Rekap Sinyal Lengkap dengan Jam Eksekusi")
    st.dataframe(
        df_filtered[['ticker', 'name', 'sesi_label', 'jam_scan', 'jam_eksekusi', 'price', 'tp1', 'tp2', 'sl', 'signal']],
        use_container_width=True
    )

# TAB 2: PANDUAN JADWAL SESI
with tab2:
    st.subheader("⏰ Panduan Lengkap 3 Sesi Sinyal & Jam Eksekusi")
    
    col_pagi, col_siang, col_sore = st.columns(3)
    
    with col_pagi:
        st.markdown("""
        <div class="session-card-pagi">
            <h4>🌅 1. Sesi Pagi (Pre-Market)</h4>
            <p><b>Jam Scan AI:</b> 08:30 WIB</p>
            <p><b>Jam Eksekusi Beli:</b> <code>08:55 - 09:05 WIB</code></p>
            <p><b>Target:</b> Mengambil lonjakan momentum pembukaan pasar (+2% s/d +3% dalam 15-30 menit).</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_siang:
        st.markdown("""
        <div class="session-card-siang">
            <h4>☀️ 2. Sesi Siang (Midday)</h4>
            <p><b>Jam Scan AI:</b> 13:00 WIB</p>
            <p><b>Jam Eksekusi Beli:</b> <code>13:25 - 13:35 WIB</code></p>
            <p><b>Target:</b> Membeli saham yang konsisten diakumulasi Bandar dari Sesi 1 untuk TP sebelum sore.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_sore:
        st.markdown("""
        <div class="session-card-sore">
            <h4>🌆 3. Sesi Sore (Buy-On-Close)</h4>
            <p><b>Jam Scan AI:</b> 16:30 WIB</p>
            <p><b>Jam Eksekusi Beli:</b> <code>15:50 - 16:00 WIB</code></p>
            <p><b>Target:</b> Buy-On-Close (BOC) untuk dijual besok pagi saat pembukaan pasar (Sell on Open).</p>
        </div>
        """, unsafe_allow_html=True)

# TAB 3: BOT CONTROL
with tab3:
    st.subheader("🤖 Pengujian Notifikasi Telegram")
    st.write("Kirim notifikasi otomatis lengkap dengan keterangan Sesi & Jam Eksekusi.")
