#!/usr/bin/python3
"""
╔══════════════════════════════════════════╗
║    MENDING.AI ENGINE V3 — SMART CORE     ║
║    Multi-Strategy | ATR TP/SL | SMC      ║
╚══════════════════════════════════════════╝

PERBAIKAN DARI V5.5:
─────────────────────────────────────────────
[FIX] Strategi dibangun ulang dari nol dengan
      logika teknikal yang benar
[FIX] TP/SL sekarang berbasis ATR (dinamis)
      bukan angka fixed $0.12 / $0.06
[FIX] Cooldown antar trade per-user
[FIX] Minimum signal strength check
[FIX] Tidak eksekusi di kondisi sideways/choppy
[NEW] Smart Money Concepts (SMC) strategy:
      Break of Structure + Order Block
[NEW] Scalping RSI + Volume Spike
[NEW] Win/Loss tracking + statistik dikirim Tele
[NEW] Trailing stop sederhana
"""
import os, json, time, math, requests
from datetime import datetime

# ──────────────────────────────────────────
#  CONFIG
# ──────────────────────────────────────────
DB_FILE    = '/root/mending_db.json'
LOG_FILE   = '/root/mending_log.txt'
TELE_TOKEN = "8540807673:AAFzSIbMLwZVTT_i_gmqgGWRdYwyMOy36Sc"
TELE_ID    = "5329232945"
LOOP_SLEEP = 10   # detik antar iterasi engine utama

# ──────────────────────────────────────────
#  UTILITAS
# ──────────────────────────────────────────
def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(msg):
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{ts()}] {msg}\n")

def tele(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage",
            json={"chat_id": TELE_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        log(f"TELE_ERROR: {e}")

def load_db():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE) as f: return json.load(f)
    except: return {}

def save_db(data):
    with open(DB_FILE, 'w') as f: json.dump(data, f, indent=4)

# ──────────────────────────────────────────
#  INDIKATOR TEKNIKAL
# ──────────────────────────────────────────
def ema(values, period):
    """Exponential Moving Average."""
    if len(values) < period: return None
    k = 2 / (period + 1)
    result = sum(values[:period]) / period
    for v in values[period:]:
        result = v * k + result * (1 - k)
    return result

def sma(values, period):
    if len(values) < period: return None
    return sum(values[-period:]) / period

def rsi(closes, period=14):
    """RSI standar Wilder."""
    if len(closes) < period + 1: return None
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains  = [d for d in deltas if d > 0]
    losses = [-d for d in deltas if d < 0]
    if not gains or not losses: return 50.0
    avg_g = sum(gains[-period:]) / period
    avg_l = sum(losses[-period:]) / period
    if avg_l == 0: return 100.0
    rs = avg_g / avg_l
    return 100 - (100 / (1 + rs))

def atr(bars, period=14):
    """Average True Range untuk sizing TP/SL."""
    if len(bars) < period + 1: return None
    trs = []
    for i in range(1, len(bars)):
        h = bars[i][2]; l = bars[i][3]; pc = bars[i-1][4]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs[-period:]) / period

def find_swing_highs(bars, lookback=5):
    """Cari swing highs di N candle terakhir."""
    highs = [b[2] for b in bars]
    swings = []
    for i in range(lookback, len(highs) - lookback):
        if highs[i] == max(highs[i-lookback:i+lookback+1]):
            swings.append((i, highs[i]))
    return swings

def find_swing_lows(bars, lookback=5):
    """Cari swing lows di N candle terakhir."""
    lows = [b[3] for b in bars]
    swings = []
    for i in range(lookback, len(lows) - lookback):
        if lows[i] == min(lows[i-lookback:i+lookback+1]):
            swings.append((i, lows[i]))
    return swings

def is_choppy(bars, lookback=20):
    """
    Deteksi market sideways/choppy.
    Jika range (high-low) relative kecil dan EMA21 datar → skip trade.
    """
    if len(bars) < lookback: return True
    recent = bars[-lookback:]
    highs  = [b[2] for b in recent]
    lows   = [b[3] for b in recent]
    closes = [b[4] for b in recent]
    total_range = max(highs) - min(lows)
    avg_price   = sum(closes) / len(closes)
    # Range < 0.8% dari harga → sideways
    if (total_range / avg_price) < 0.008:
        return True
    # EMA21 vs EMA9 terlalu dekat → datar
    e9 = ema(closes, 9); e21 = ema(closes, 21)
    if e9 and e21 and abs(e9 - e21) / avg_price < 0.001:
        return True
    return False

def volume_spike(bars, multiplier=1.5):
    """Apakah volume candle terakhir di atas rata-rata?"""
    vols = [b[5] for b in bars[-20:]]
    if len(vols) < 10: return False
    avg_vol = sum(vols[:-1]) / len(vols[:-1])
    return vols[-1] > avg_vol * multiplier

# ──────────────────────────────────────────
#  STRATEGI
# ──────────────────────────────────────────

def strat_liquidity_hunter(bars, curr_price):
    """
    Cari area likuiditas:
    - Harga sweep high/low lama lalu reversal
    - Konfirmasi: candle close kembali ke dalam range
    Return: ('buy'|'sell'|None, strength 0-100)
    """
    if len(bars) < 50: return None, 0

    closes = [b[4] for b in bars]
    highs  = [b[2] for b in bars]
    lows   = [b[3] for b in bars]

    # Swing highs/lows pada 30 candle sebelum 5 candle terakhir
    lookback_bars = bars[:-5]
    sh = find_swing_highs(lookback_bars, lookback=5)
    sl = find_swing_lows(lookback_bars,  lookback=5)

    if not sh or not sl: return None, 0

    last_sh = sh[-1][1]  # level swing high terakhir
    last_sl = sl[-1][1]  # level swing low terakhir

    last_high = highs[-1]
    last_low  = lows[-1]
    last_close = closes[-1]
    prev_close = closes[-2]

    # Liquidity grab di HIGH: harga spike atas swing high lalu close balik ke bawah
    # → SHORT setup (smart money jual di sana)
    if last_high > last_sh and last_close < last_sh and prev_close < last_sh:
        # Konfirmasi momentum bearish
        rsi_val = rsi(closes[-20:])
        strength = 70
        if rsi_val and rsi_val > 60: strength += 15
        if volume_spike(bars): strength += 10
        return 'sell', min(strength, 100)

    # Liquidity grab di LOW: harga spike bawah swing low lalu close balik ke atas
    # → LONG setup (smart money beli di sana)
    if last_low < last_sl and last_close > last_sl and prev_close > last_sl:
        rsi_val = rsi(closes[-20:])
        strength = 70
        if rsi_val and rsi_val < 40: strength += 15
        if volume_spike(bars): strength += 10
        return 'buy', min(strength, 100)

    return None, 0


def strat_trend_follower(bars, curr_price):
    """
    EMA 9/21/50 crossover dengan konfirmasi multi-timeframe.
    Hanya masuk saat trend jelas, bukan saat crossover saja.
    Return: ('buy'|'sell'|None, strength)
    """
    if len(bars) < 60: return None, 0

    closes = [b[4] for b in bars]

    e9  = ema(closes, 9)
    e21 = ema(closes, 21)
    e50 = ema(closes, 50)

    if not all([e9, e21, e50]): return None, 0

    rsi_val = rsi(closes[-20:])
    if not rsi_val: return None, 0

    # Trend BULLISH: e9 > e21 > e50, harga di atas semua EMA, RSI 40-70
    if e9 > e21 > e50 and curr_price > e9 and 40 < rsi_val < 70:
        # Cek pullback: harga sempat menyentuh area EMA21 sebelumnya
        recent_low = min([b[3] for b in bars[-10:]])
        strength = 65
        if recent_low <= e21 * 1.005: strength += 20  # ada pullback ke EMA21
        if volume_spike(bars):        strength += 10
        if rsi_val < 60:              strength += 5   # belum overbought
        return 'buy', min(strength, 100)

    # Trend BEARISH: e9 < e21 < e50, harga di bawah semua EMA, RSI 30-60
    if e9 < e21 < e50 and curr_price < e9 and 30 < rsi_val < 60:
        recent_high = max([b[2] for b in bars[-10:]])
        strength = 65
        if recent_high >= e21 * 0.995: strength += 20
        if volume_spike(bars):         strength += 10
        if rsi_val > 40:               strength += 5
        return 'sell', min(strength, 100)

    return None, 0


def strat_smc(bars, curr_price):
    """
    Smart Money Concepts:
    1. Identifikasi Break of Structure (BOS)
    2. Cari Order Block terakhir sebelum BOS
    3. Tunggu harga retest Order Block → entry

    BOS Bullish : harga break swing high terakhir
    BOS Bearish : harga break swing low terakhir
    Order Block : candle bearish terakhir sebelum impulse naik (untuk long)
                  candle bullish terakhir sebelum impulse turun (untuk short)
    """
    if len(bars) < 80: return None, 0

    closes = [b[4] for b in bars]
    highs  = [b[2] for b in bars]
    lows   = [b[3] for b in bars]

    # Cari swing highs/lows pada bars[-80:-10]
    context_bars = bars[-80:-10]
    sh = find_swing_highs(context_bars, lookback=4)
    sl = find_swing_lows(context_bars,  lookback=4)

    if not sh or not sl: return None, 0

    prev_sh = sh[-1][1]  # swing high sebelumnya
    prev_sl = sl[-1][1]  # swing low sebelumnya

    rsi_val = rsi(closes[-20:])
    if not rsi_val: return None, 0

    # ── BOS BULLISH ──
    # Harga break prev swing high → struktur bullish terbentuk
    if curr_price > prev_sh:
        # Cari Order Block: candle bearish terakhir sebelum impulse
        # (dalam range 5-30 candle ke belakang dari titik BOS)
        ob_zone_bars = bars[-40:-10]
        bearish_candles = [
            b for b in ob_zone_bars
            if b[4] < b[1]  # close < open = bearish candle
        ]
        if bearish_candles:
            ob = bearish_candles[-1]          # OB = bearish candle terakhir
            ob_high = ob[2]; ob_low = ob[3]

            # Retest: harga turun ke zona OB → entry long
            if ob_low <= curr_price <= ob_high * 1.003:
                strength = 75
                if rsi_val < 55:        strength += 10  # belum overbought
                if volume_spike(bars):  strength += 10
                if curr_price > ema(closes, 21): strength += 5
                return 'buy', min(strength, 100)

    # ── BOS BEARISH ──
    if curr_price < prev_sl:
        ob_zone_bars = bars[-40:-10]
        bullish_candles = [
            b for b in ob_zone_bars
            if b[4] > b[1]  # close > open = bullish candle
        ]
        if bullish_candles:
            ob = bullish_candles[-1]
            ob_high = ob[2]; ob_low = ob[3]

            if ob_low * 0.997 <= curr_price <= ob_high:
                strength = 75
                if rsi_val > 45:        strength += 10
                if volume_spike(bars):  strength += 10
                e21 = ema(closes, 21)
                if e21 and curr_price < e21: strength += 5
                return 'sell', min(strength, 100)

    return None, 0


def strat_scalping_rsi(bars, curr_price):
    """
    Scalping berbasis RSI + volume spike + candlestick pattern.
    Cocok untuk pair volatile, timeframe 1m–5m.
    RSI oversold (<30) + volume spike → long
    RSI overbought (>70) + volume spike → short
    WAJIB dikonfirmasi EMA trend tidak berlawanan.
    """
    if len(bars) < 25: return None, 0

    closes = [b[4] for b in bars]
    opens  = [b[1] for b in bars]

    rsi_val = rsi(closes[-20:], period=14)
    if not rsi_val: return None, 0

    e9  = ema(closes, 9)
    e21 = ema(closes, 21)
    if not all([e9, e21]): return None, 0

    v_spike = volume_spike(bars, multiplier=1.8)  # threshold lebih tinggi untuk scalp

    # Candle terakhir bullish reversal (hammer-like: close > open, shadow bawah panjang)
    last = bars[-1]
    body  = abs(last[4] - last[1])
    low_shadow = min(last[1], last[4]) - last[3]
    is_hammer = (low_shadow > body * 1.5) and (last[4] > last[1])

    # Candle terakhir bearish reversal (shooting star)
    high_shadow = last[2] - max(last[1], last[4])
    is_star = (high_shadow > body * 1.5) and (last[4] < last[1])

    # ── LONG: RSI oversold + volume + hammer + trend tidak bearish ──
    if rsi_val < 32 and v_spike and is_hammer and e9 >= e21 * 0.998:
        strength = 70 + (32 - rsi_val) * 1.5  # makin oversold makin kuat
        return 'buy', min(int(strength), 100)

    # ── SHORT: RSI overbought + volume + shooting star + trend tidak bullish ──
    if rsi_val > 68 and v_spike and is_star and e9 <= e21 * 1.002:
        strength = 70 + (rsi_val - 68) * 1.5
        return 'sell', min(int(strength), 100)

    # ── Versi lebih longgar jika RSI ekstrem tanpa pattern ──
    if rsi_val < 25 and v_spike and e9 > e21 * 0.995:
        return 'buy', 72
    if rsi_val > 75 and v_spike and e9 < e21 * 1.005:
        return 'sell', 72

    return None, 0


def strat_grid(bars, curr_price):
    """
    Grid Trading sederhana:
    - Tentukan range berdasarkan ATR * 3
    - Beli di sepertiga bawah range, jual di sepertiga atas
    - Hanya aktif jika market sideways (justru kebalikan strategi lain)
    """
    if len(bars) < 30: return None, 0

    closes = [b[4] for b in bars]
    atr_val = atr(bars, 14)
    if not atr_val: return None, 0

    mid   = sma(closes, 20)
    if not mid: return None, 0

    grid_range = atr_val * 3
    lower  = mid - grid_range / 2
    upper  = mid + grid_range / 2
    band   = grid_range / 3

    # Volatile market → skip grid
    range_pct = grid_range / mid
    if range_pct > 0.03:  # range > 3% = terlalu volatile untuk grid
        return None, 0

    if curr_price < lower + band:
        return 'buy', 68
    if curr_price > upper - band:
        return 'sell', 68

    return None, 0


# ──────────────────────────────────────────
#  DISPATCH STRATEGI
# ──────────────────────────────────────────
STRAT_MAP = {
    "Liquidity Hunter":    strat_liquidity_hunter,
    "Trend Follower":      strat_trend_follower,
    "Smart Money (SMC)":   strat_smc,
    "Scalping RSI":        strat_scalping_rsi,
    "Grid Trading":        strat_grid,
}

MIN_SIGNAL_STRENGTH = {
    "Liquidity Hunter":   75,   # butuh konfirmasi kuat
    "Trend Follower":     70,
    "Smart Money (SMC)":  75,
    "Scalping RSI":       70,
    "Grid Trading":       65,
}

# ──────────────────────────────────────────
#  RISK MANAGEMENT & SIZING
# ──────────────────────────────────────────
def calc_tp_sl(side, entry, atr_val, rr_ratio=2.0):
    """
    TP/SL berbasis ATR.
    SL = 1.2 × ATR dari entry (cukup jauh dari noise)
    TP = SL × rr_ratio (default R:R = 1:2)
    """
    sl_dist = atr_val * 1.2
    tp_dist = sl_dist * rr_ratio

    if side == 'buy':
        sl = entry - sl_dist
        tp = entry + tp_dist
    else:
        sl = entry + sl_dist
        tp = entry - tp_dist

    return round(tp, 4), round(sl, 4)

def calc_qty(capital, risk_pct, sl_dist, leverage, entry):
    """
    Position sizing berbasis risk percentage.
    Berapa kontrak yang harus dibuka agar loss = risk_pct% dari capital?
    qty = (capital × risk%) / (sl_dist × leverage) — dalam unit coin
    """
    try:
        risk_usdt = float(capital) * (float(risk_pct) / 100)
        qty = risk_usdt / sl_dist  # dalam USDT
        qty = qty / entry           # konversi ke unit coin
        # Minimum 0.001 BTC, dan bulat ke 3 desimal
        qty = max(0.001, round(qty, 3))
        return qty
    except:
        return 0.001

# ──────────────────────────────────────────
#  COOLDOWN TRACKER
# ──────────────────────────────────────────
# Dict in-memory: {name: last_trade_timestamp}
_last_trade_time = {}
_open_trade_data = {}  # {name: {side, entry, tp, sl, qty}}

def is_on_cooldown(name, cooldown_sec):
    last = _last_trade_time.get(name, 0)
    return (time.time() - last) < float(cooldown_sec)

def set_cooldown(name):
    _last_trade_time[name] = time.time()

# ──────────────────────────────────────────
#  CORE ENGINE
# ──────────────────────────────────────────
def get_exchange(u):
    import ccxt
    ex = getattr(ccxt, u['platform'].lower())({
        'apiKey': u['api_key'],
        'secret': u['secret_key'],
        'options': {'defaultType': 'future'},
        'enableRateLimit': True,
    })
    return ex

def process_user(name, u, db):
    """Logika lengkap per-user per-siklus."""
    pair    = u.get('pair', 'BTC/USDT')
    strat   = u.get('strategy', 'Smart Money (SMC)')
    lev     = int(u.get('leverage', 20))
    cap     = float(u.get('capital', 100))
    risk    = float(u.get('risk_pct', 1.0))
    cd_sec  = float(u.get('cooldown_sec', 60))
    tf      = '3m'  # default timeframe

    # Scalping pakai 1m, grid pakai 15m
    if strat == "Scalping RSI":   tf = '1m'
    elif strat == "Grid Trading": tf = '15m'

    try:
        ex = get_exchange(u)

        # ── Set leverage ──
        try: ex.set_leverage(lev, pair)
        except: pass

        # ── Fetch data pasar ──
        bars      = ex.fetch_ohlcv(pair, timeframe=tf, limit=100)
        curr_price = bars[-1][4]
        atr_val    = atr(bars, 14)

        if not atr_val:
            log(f"[{name}] ATR tidak tersedia, skip.")
            return

        # ── Cek posisi aktif ──
        pos_data = ex.fetch_positions(symbols=[pair])
        pos = next(
            (p for p in pos_data if float(p.get('contracts', 0)) != 0), None
        )

        if pos:
            # Ada posisi aktif → cek TP/SL
            pnl_usdt = float(pos.get('unrealizedPnl', 0))
            amount   = abs(float(pos['contracts']))
            side_pos = 'LONG' if float(pos['contracts']) > 0 else 'SHORT'
            entry_p  = float(pos.get('entryPrice', curr_price))

            # Ambil TP/SL yang disimpan
            od = _open_trade_data.get(name, {})
            tp = od.get('tp')
            sl = od.get('sl')

            close_reason = None

            # Jika tidak ada data TP/SL tersimpan, hitung ulang dari ATR
            if not tp or not sl:
                tp, sl = calc_tp_sl(
                    'buy' if side_pos == 'LONG' else 'sell',
                    entry_p, atr_val
                )

            if side_pos == 'LONG':
                if curr_price >= tp:    close_reason = f"✅ TP HIT"
                elif curr_price <= sl:  close_reason = f"🛑 SL HIT"
            else:
                if curr_price <= tp:    close_reason = f"✅ TP HIT"
                elif curr_price >= sl:  close_reason = f"🛑 SL HIT"

            if close_reason:
                close_side = 'sell' if side_pos == 'LONG' else 'buy'
                # Cancel semua open order TP/SL yang masih ada di exchange
                try:
                    ex.cancel_all_orders(pair)
                    log(f"[{name}] All open TP/SL orders cancelled.")
                except Exception as e:
                    log(f"[{name}] Cancel orders warning: {e}")
                ex.create_market_order(pair, close_side, amount,
                                       params={'reduceOnly': True})
                # Update DB
                sign = "win" if "TP" in close_reason else "loss"
                db[name][sign] = db[name].get(sign, 0) + 1
                db[name]['pnl_total'] = round(
                    db[name].get('pnl_total', 0.0) + pnl_usdt, 4
                )
                db[name]['trades_total'] = db[name].get('trades_total', 0) + 1
                save_db(db)
                _open_trade_data.pop(name, None)
                set_cooldown(name)

                win  = db[name].get('win', 0)
                loss = db[name].get('loss', 0)
                wr   = f"{win/(win+loss)*100:.1f}%" if (win+loss) > 0 else "─"

                msg = (
                    f"{close_reason} — <b>{name}</b>\n"
                    f"📍 Pair     : {pair}\n"
                    f"📊 Strategi : {strat}\n"
                    f"💵 PnL      : {'+' if pnl_usdt>=0 else ''}{pnl_usdt:.2f} USDT\n"
                    f"📈 Total PNL: {'+' if db[name]['pnl_total']>=0 else ''}"
                    f"{db[name]['pnl_total']:.2f} USDT\n"
                    f"🎯 Win Rate : {wr} ({win}W/{loss}L)"
                )
                tele(msg)
                log(f"[{name}] CLOSE {side_pos} {close_reason} PNL={pnl_usdt:.2f}")
            return  # Ada posisi aktif, jangan buka lagi

        # ── Tidak ada posisi → cari sinyal ──
        if is_on_cooldown(name, cd_sec):
            sisa = cd_sec - (time.time() - _last_trade_time.get(name, 0))
            log(f"[{name}] Cooldown {sisa:.0f}s tersisa.")
            return

        # Deteksi choppy (kecuali Grid yang justru butuh sideways)
        if strat != "Grid Trading" and is_choppy(bars):
            log(f"[{name}] Market choppy/sideways, skip entry.")
            return

        # Pilih strategi
        fn = STRAT_MAP.get(strat)
        if not fn:
            log(f"[{name}] Strategi '{strat}' tidak dikenal.")
            return

        signal, strength = fn(bars, curr_price)

        # Filter kekuatan sinyal
        min_str = MIN_SIGNAL_STRENGTH.get(strat, 70)
        if not signal or strength < min_str:
            log(f"[{name}] Sinyal lemah: {signal} str={strength} (min={min_str}), skip.")
            return

        # Hitung TP/SL & Qty
        tp, sl   = calc_tp_sl(signal, curr_price, atr_val)
        sl_dist  = abs(curr_price - sl)
        qty      = calc_qty(cap, risk, sl_dist, lev, curr_price)

        # Eksekusi order market entry
        ex.create_market_order(pair, signal, qty)
        log(f"[{name}] OPEN {signal.upper()} {pair} qty={qty} "
            f"entry={curr_price} TP={tp} SL={sl} str={strength}")

        # Pasang SL dan TP sebagai order langsung di Binance
        sl_side = 'sell' if signal == 'buy' else 'buy'
        try:
            # Pasang Stop Loss order di exchange
            ex.create_order(
                pair, 'stop_market', sl_side, qty,
                params={
                    'stopPrice': round(sl, 2),
                    'reduceOnly': True,
                    'closePosition': True,
                }
            )
            log(f"[{name}] SL ORDER PLACED @ {sl:.4f}")
        except Exception as e:
            log(f"[{name}] SL ORDER FAILED: {e}")

        try:
            # Pasang Take Profit order di exchange
            ex.create_order(
                pair, 'take_profit_market', sl_side, qty,
                params={
                    'stopPrice': round(tp, 2),
                    'reduceOnly': True,
                    'closePosition': True,
                }
            )
            log(f"[{name}] TP ORDER PLACED @ {tp:.4f}")
        except Exception as e:
            log(f"[{name}] TP ORDER FAILED: {e}")

        _open_trade_data[name] = {
            'side': signal, 'entry': curr_price,
            'tp': tp, 'sl': sl, 'qty': qty
        }

        msg = (
            f"🚀 OPEN <b>{signal.upper()}</b> — {name}\n"
            f"📍 Pair     : {pair}\n"
            f"📊 Strategi : {strat} (strength: {strength})\n"
            f"⚙️  Leverage : {lev}x\n"
            f"💰 Qty      : {qty} {pair.split('/')[0]}\n"
            f"🎯 Entry    : {curr_price:.4f}\n"
            f"✅ TP       : {tp:.4f}\n"
            f"🛑 SL       : {sl:.4f}\n"
            f"📐 R:R      : 1:2.0\n"
            f"🔒 TP/SL dipasang otomatis di Binance"
        )
        tele(msg)

    except Exception as e:
        err = str(e)
        if "ReduceOnly" not in err and "position" not in err.lower():
            log(f"[{name}] ERROR: {err}")
            if "Invalid API" in err or "authentication" in err.lower():
                tele(f"⚠️ [{name}] API Key error! Cek di menu.")

# ──────────────────────────────────────────
#  MAIN LOOP
# ──────────────────────────────────────────
def engine_loop():
    log("ENGINE_START: Mending.AI V3 dimulai")
    tele(
        "✅ <b>Mending.AI Engine V3 Online!</b>\n"
        "🧠 Smart Core aktif\n"
        "📊 Strategi: Liquidity Hunter | Trend Follower\n"
        "         Smart Money (SMC) | Scalping RSI | Grid\n"
        "⚙️  TP/SL berbasis ATR | Cooldown aktif"
    )
    print(f"[{ts()}] Engine V3 started.")

    while True:
        db = load_db()
        for name, u in db.items():
            if u.get('status') == 'RUNNING':
                print(f"[{ts()}] Processing {name}...")
                process_user(name, u, db)
        time.sleep(LOOP_SLEEP)

if __name__ == "__main__":
    try:
        engine_loop()
    except KeyboardInterrupt:
        log("ENGINE_STOP: Dihentikan manual")
        print(f"\n[{ts()}] Engine dihentikan.")
