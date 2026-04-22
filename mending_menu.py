#!/usr/bin/python3
"""
╔══════════════════════════════════════════╗
║     MENDING.AI TRADING BOT V3 — MENU     ║
╚══════════════════════════════════════════╝
"""
import json, os, sys, time
from datetime import datetime

DB_FILE  = '/root/mending_db.json'
LOG_FILE = '/root/mending_log.txt'

STRATEGIES = {
    "1": "Liquidity Hunter",
    "2": "Trend Follower",
    "3": "Smart Money (SMC)",
    "4": "Scalping RSI",
    "5": "Grid Trading",
}

PLATFORMS = {
    "1": "binance",
    "2": "bybit",
    "3": "okx",
    "4": "bitget",
}

PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]

C = {
    "G": "\033[92m", "R": "\033[91m", "Y": "\033[93m",
    "C": "\033[96m", "B": "\033[94m", "W": "\033[97m",
    "D": "\033[2m",  "K": "\033[1m",  "X": "\033[0m",
}

def c(text, col): return f"{C.get(col,'')}{text}{C['X']}"
def clear():       os.system('cls' if os.name == 'nt' else 'clear')
def pause():       input(c("\n  ↵  Tekan Enter...", "D"))
def div():         print(c("  " + "─" * 46, "D"))

def confirm(msg):
    return input(c(f"\n  {msg} (y/n): ", "Y")).strip().lower() == 'y'

def spin(msg, secs=1.2):
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    end = time.time() + secs
    i = 0
    while time.time() < end:
        print(c(f"\r  {frames[i%len(frames)]} {msg}...", "C"), end="", flush=True)
        time.sleep(0.1); i += 1
    print(c(f"\r  ✔ {msg} OK.          ", "G"))
    time.sleep(0.3)

def header(sub=""):
    ts = datetime.now().strftime("%d %b %Y  %H:%M:%S")
    print(c("╔══════════════════════════════════════════════╗", "C"))
    if sub:
        print(c(f"║  MENDING.AI BOT V3  ·  {sub:<22}║", "C"))
    else:
        print(c("║     MENDING.AI  TRADING  BOT  V3             ║", "C"))
    print(c("╚══════════════════════════════════════════════╝", "C"))
    print(c(f"  {ts}", "D")); print()

def load_db():
    if not os.path.exists(DB_FILE): return {}
    with open(DB_FILE) as f: return json.load(f)

def save_db(data):
    with open(DB_FILE, 'w') as f: json.dump(data, f, indent=4)

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, 'a') as f: f.write(f"[{ts}] {msg}\n")

def badge(status):
    return c("● RUN ", "G") if status == "RUNNING" else c("○ STOP", "R")

def default_user(name):
    return {
        "name": name, "status": "STOPPED",
        "platform": "binance", "api_key": "", "secret_key": "",
        "strategy": "Smart Money (SMC)", "pair": "BTC/USDT",
        "leverage": "20", "risk_pct": "1.0", "capital": "100",
        "pnl_total": 0.0, "trades_total": 0, "win": 0, "loss": 0,
        "cooldown_sec": "60",
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "last_run": "-",
    }

# ═══════════════════════════════════════════
#  MAIN MENU
# ═══════════════════════════════════════════
def main():
    while True:
        clear(); db = load_db()
        header()

        if db:
            print(c("  #   NAMA            STATUS   PLATFORM  PAIR        STRATEGI", "K"))
            div()
            for i, (name, u) in enumerate(db.items(), 1):
                pnl  = u.get('pnl_total', 0.0)
                pc   = "G" if pnl >= 0 else "R"
                ps   = f"+{pnl:.2f}" if pnl >= 0 else f"{pnl:.2f}"
                win  = u.get('win', 0); loss = u.get('loss', 0)
                wr   = f"{win/(win+loss)*100:.0f}%" if (win+loss) > 0 else "─"
                print(f"  [{i}] {name:<15} {badge(u.get('status','STOPPED'))}  "
                      f"{u.get('platform','─'):<8}  {u.get('pair','─'):<10}  "
                      f"{u.get('strategy','─')}")
                print(c(f"       PNL: {ps} USDT  |  WR: {wr}  |  Strat: {u.get('strategy','─')}", "D"))
        else:
            print(c("  Belum ada user. Tambah dengan [A].", "D"))

        div()
        print(c("\n  [A] Tambah User    [E] Edit User    [L] Log", "W"))
        print(c("  [R] Reset DB       [0] Keluar\n",            "W"))
        ch = input(c("  //_ Pilihan: ", "Y")).strip().upper()

        if   ch == 'A': menu_add(db)
        elif ch == 'E': menu_select(db)
        elif ch == 'L': menu_log()
        elif ch == 'R': menu_reset(db)
        elif ch == '0':
            clear()
            print(c("\n  Bot tetap jalan di engine. Sampai jumpa!\n", "C"))
            sys.exit(0)
        elif ch.isdigit():
            idx = int(ch) - 1
            keys = list(db.keys())
            if 0 <= idx < len(keys):
                menu_user(db, keys[idx])

# ═══════════════════════════════════════════
#  TAMBAH USER
# ═══════════════════════════════════════════
def menu_add(db):
    clear(); header("TAMBAH USER")
    name = input(c("  Nama User   : ", "Y")).strip()
    if not name or name in db:
        print(c("  ✖ Nama kosong atau sudah ada.", "R")); pause(); return

    print(c("\n  Platform:", "C"))
    for k, v in PLATFORMS.items(): print(c(f"    [{k}] {v}", "W"))
    pk = input(c("  Pilih platform: ", "Y")).strip()
    platform = PLATFORMS.get(pk, "binance")

    print(c(f"\n  ⚠  Masukkan API Key {platform.upper()}", "Y"))
    api_key    = input(c("  API Key    : ", "Y")).strip()
    secret_key = input(c("  Secret Key : ", "Y")).strip()

    u = default_user(name)
    u['platform']   = platform
    u['api_key']    = api_key
    u['secret_key'] = secret_key
    db[name] = u
    save_db(db)
    spin(f"Membuat akun '{name}'")
    log(f"USER_ADD: {name} platform={platform}")
    print(c(f"  ✔ User '{name}' berhasil ditambahkan!", "G"))
    pause()

# ═══════════════════════════════════════════
#  PILIH USER DARI DAFTAR
# ═══════════════════════════════════════════
def menu_select(db):
    clear(); header("PILIH USER")
    if not db: print(c("  Belum ada user.", "D")); pause(); return
    for i, name in enumerate(db.keys(), 1):
        print(c(f"  [{i}] {name}", "W"))
    ch = input(c("\n  Nomor: ", "Y")).strip()
    if ch.isdigit():
        idx = int(ch) - 1
        keys = list(db.keys())
        if 0 <= idx < len(keys):
            menu_user(db, keys[idx])

# ═══════════════════════════════════════════
#  DETAIL USER
# ═══════════════════════════════════════════
def menu_user(db, name):
    while True:
        clear(); u = db[name]
        header(f"USER: {name.upper()}")

        win  = u.get('win', 0); loss = u.get('loss', 0)
        wr   = f"{win/(win+loss)*100:.1f}%" if (win+loss) > 0 else "─"
        pnl  = u.get('pnl_total', 0.0)
        pc   = "G" if pnl >= 0 else "R"

        print(c(f"  Status   : ", "D") + badge(u.get('status','STOPPED')))
        print(c(f"  Platform : {u.get('platform','─').upper()}", "W"))
        print(c(f"  Pair     : {u.get('pair','─')}", "W"))
        print(c(f"  Leverage : {u.get('leverage','─')}x", "W"))
        print(c(f"  Strategi : {u.get('strategy','─')}", "W"))
        print(c(f"  Risk/Trade: {u.get('risk_pct','1.0')}%  |  Kapital: ${u.get('capital','100')}", "W"))
        print(c(f"  Cooldown : {u.get('cooldown_sec','60')}s antar trade", "W"))
        div()
        ps = f"+{pnl:.2f}" if pnl >= 0 else f"{pnl:.2f}"
        print(c(f"  Total PNL: ", "D") + c(f"{ps} USDT", pc))
        print(c(f"  Win/Loss : {win}W / {loss}L  (WR: {wr})", "W"))
        print(c(f"  Trades   : {u.get('trades_total',0)}", "W"))
        print(c(f"  Last Run : {u.get('last_run','-')}", "D"))
        div()

        print(c("\n  [1] Start / Stop Engine", "W"))
        print(c("  [2] Ganti Strategi", "W"))
        print(c("  [3] Ganti Pair", "W"))
        print(c("  [4] Leverage & Risk Management", "W"))
        print(c("  [5] Update API Key", "W"))
        print(c("  [6] Reset Statistik PNL", "W"))
        print(c("  [D] Hapus User", "R"))
        print(c("  [0] Kembali\n", "W"))

        ch = input(c("  //_ : ", "Y")).strip().upper()
        if   ch == '1': act_startstop(db, name)
        elif ch == '2': act_strategy(db, name)
        elif ch == '3': act_pair(db, name)
        elif ch == '4': act_risk(db, name)
        elif ch == '5': act_apikey(db, name)
        elif ch == '6': act_reset_stat(db, name)
        elif ch == 'D':
            if confirm(f"Hapus user '{name}'?"):
                del db[name]; save_db(db)
                log(f"USER_DEL: {name}")
                print(c("  ✔ Dihapus.", "G")); pause(); return
        elif ch == '0': return

# ═══════════════════════════════════════════
#  ACTIONS
# ═══════════════════════════════════════════
def act_startstop(db, name):
    u = db[name]
    is_run = u.get('status') == 'RUNNING'

    if not is_run:
        # Validasi API key
        if not u.get('api_key') or not u.get('secret_key'):
            print(c("\n  ✖ API Key belum diisi! Isi dulu via menu [5].", "R"))
            pause(); return

        clear(); header(f"START ENGINE: {name}")
        print(c("  Pilih Strategi:\n", "C"))
        for k, v in STRATEGIES.items():
            desc = {
                "1": "Cari likuiditas di high/low area",
                "2": "EMA cross + trend filter multi-TF",
                "3": "Break of Structure + Order Block (SMC)",
                "4": "RSI divergence + volume spike",
                "5": "Grid order di range volatilitas",
            }.get(k, "")
            print(c(f"    [{k}] {v}", "W") + c(f"  — {desc}", "D"))

        s = input(c("\n  Pilih (1-5): ", "Y")).strip()
        if s not in STRATEGIES:
            print(c("  ✖ Tidak valid.", "R")); pause(); return
        u['strategy'] = STRATEGIES[s]

    if not confirm(f"{'STOP' if is_run else 'START'} engine '{name}'?"):
        return

    u['status']   = 'STOPPED' if is_run else 'RUNNING'
    u['last_run'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_db(db)
    log(f"ENGINE_{'STOP' if is_run else 'START'}: {name} strat={u['strategy']} lev={u['leverage']}x")

    spin(f"{'Menghentikan' if is_run else 'Menjalankan'} engine")
    st = c("STOPPED", "R") if is_run else c("RUNNING", "G")
    print(c(f"\n  ✔ Engine '{name}' sekarang: ", "W") + st)
    pause()

def act_strategy(db, name):
    clear(); header("GANTI STRATEGI")
    for k, v in STRATEGIES.items(): print(c(f"  [{k}] {v}", "W"))
    s = input(c("\n  Pilih (1-5): ", "Y")).strip()
    if s not in STRATEGIES: print(c("  ✖", "R")); pause(); return
    db[name]['strategy'] = STRATEGIES[s]; save_db(db)
    log(f"STRAT_CHANGE: {name} -> {STRATEGIES[s]}")
    print(c(f"  ✔ Strategi: {STRATEGIES[s]}", "G")); pause()

def act_pair(db, name):
    clear(); header("GANTI PAIR")
    for i, p in enumerate(PAIRS, 1): print(c(f"  [{i}] {p}", "W"))
    print(c("  [M] Manual", "D"))
    ch = input(c("\n  Pilih: ", "Y")).strip().upper()
    if ch == 'M':
        pair = input(c("  Pair (cth: ARB/USDT): ", "Y")).strip().upper()
    elif ch.isdigit() and 1 <= int(ch) <= len(PAIRS):
        pair = PAIRS[int(ch) - 1]
    else: print(c("  ✖", "R")); pause(); return
    db[name]['pair'] = pair; save_db(db)
    log(f"PAIR_CHANGE: {name} -> {pair}")
    print(c(f"  ✔ Pair: {pair}", "G")); pause()

def act_risk(db, name):
    clear(); header("LEVERAGE & RISK MANAGEMENT")
    u = db[name]
    print(c("  ── LEVERAGE ──", "C"))
    print(c("  ⚠  Leverage tinggi = risiko likuidasi tinggi", "Y"))
    print(c("  Rekomendasi: 5x–20x untuk safety\n", "D"))
    lev = input(c(f"  Leverage [{u.get('leverage','20')}x] → : ", "Y")).strip()

    print(c("\n  ── RISK PER TRADE ──", "C"))
    print(c("  Persentase kapital yang di-risk per trade", "D"))
    print(c("  Rekomendasi: 0.5%–2% (profesional pakai 1%)\n", "D"))
    risk = input(c(f"  Risk % [{u.get('risk_pct','1.0')}%] → : ", "Y")).strip()

    print(c("\n  ── KAPITAL ──", "C"))
    cap = input(c(f"  Kapital USDT [{u.get('capital','100')}] → $: ", "Y")).strip()

    print(c("\n  ── COOLDOWN ANTAR TRADE ──", "C"))
    print(c("  Minimum jeda setelah close trade (detik)", "D"))
    cd = input(c(f"  Cooldown [{u.get('cooldown_sec','60')}s] → : ", "Y")).strip()

    try:
        if lev:
            lv = int(lev)
            if lv > 50:
                print(c(f"\n  ⚠  Leverage {lv}x sangat berisiko! ", "R"))
                if not confirm("Tetap lanjut?"): return
            u['leverage'] = str(lv)
        if risk:  u['risk_pct']    = risk
        if cap:   u['capital']     = cap
        if cd:    u['cooldown_sec']= cd
        save_db(db)
        log(f"RISK_UPDATE: {name} lev={u['leverage']} risk={u['risk_pct']}% cap={u['capital']}")
        print(c("\n  ✔ Pengaturan disimpan!", "G"))
    except ValueError:
        print(c("  ✖ Input tidak valid.", "R"))
    pause()

def act_apikey(db, name):
    clear(); header("UPDATE API KEY")
    u = db[name]
    print(c(f"  Platform : {u.get('platform','─').upper()}", "W"))
    print(c("  (Kosongkan untuk tidak mengubah)\n", "D"))
    ak = input(c("  API Key baru    : ", "Y")).strip()
    sk = input(c("  Secret Key baru : ", "Y")).strip()
    if ak: u['api_key']    = ak
    if sk: u['secret_key'] = sk
    save_db(db)
    log(f"APIKEY_UPDATE: {name}")
    print(c("  ✔ API Key diperbarui.", "G")); pause()

def act_reset_stat(db, name):
    if confirm(f"Reset semua statistik PNL '{name}'?"):
        db[name].update({"pnl_total": 0.0, "trades_total": 0, "win": 0, "loss": 0})
        save_db(db)
        log(f"STAT_RESET: {name}")
        print(c("  ✔ Statistik direset.", "G"))
    pause()

# ═══════════════════════════════════════════
#  LOG VIEWER
# ═══════════════════════════════════════════
def menu_log():
    clear(); header("LOG AKTIVITAS")
    if not os.path.exists(LOG_FILE):
        print(c("  Belum ada log.", "D")); pause(); return
    with open(LOG_FILE) as f: lines = f.readlines()
    for ln in lines[-40:]: print(c(f"  {ln.rstrip()}", "D"))
    print(c(f"\n  ({len(lines)} entri total)", "D"))
    pause()

# ═══════════════════════════════════════════
#  RESET
# ═══════════════════════════════════════════
def menu_reset(db):
    clear(); header("RESET DATABASE")
    print(c("  ⚠  SEMUA data user akan dihapus permanent!", "R"))
    if confirm("Yakin reset total?"):
        save_db({})
        if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
        spin("Reset database"); log("DB_RESET")
        print(c("  ✔ Database direset.", "G"))
    else: print(c("  Batal.", "D"))
    pause()

# ═══════════════════════════════════════════
#  ENTRY
# ═══════════════════════════════════════════
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear()
        print(c("\n  Keluar. Engine tetap jalan.\n", "Y"))
        sys.exit(0)
