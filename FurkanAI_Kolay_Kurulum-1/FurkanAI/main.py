import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont
import os, sys, platform, subprocess, webbrowser, json, threading, urllib.request, urllib.parse
import random, ast, operator, re, time, math
from datetime import datetime

try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)   # net, keskin yazılar
except Exception:
    pass

# ----------------------------------------------------------------- ayarlar
APP_DIR = os.path.join(os.path.expanduser("~"), "FurkanAI")
os.makedirs(APP_DIR, exist_ok=True)
NOTES_FILE = os.path.join(APP_DIR, "notlar.txt")
CFG_FILE = os.path.join(APP_DIR, "ayarlar.json")
DEFAULT_CFG = {"name": "Berat Furkan", "city": "Afyonkarahisar", "lat": 38.7567, "lon": 30.5433,
               "speak": True, "lm_url": "http://localhost:1234"}

def load_cfg():
    cfg = dict(DEFAULT_CFG)
    try:
        with open(CFG_FILE, encoding="utf-8") as f: cfg.update(json.load(f))
    except Exception:
        pass
    return cfg

def save_cfg(cfg):
    try:
        with open(CFG_FILE, "w", encoding="utf-8") as f: json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)

# ------------------------------------------------------------------ renkler
BG, SIDE, CARD, CARD2, BORDER = "#0a0f1c", "#070b14", "#111827", "#172033", "#1f2a44"
ACCENT, ACCENT2, TEXT, MUTED = "#3b82f6", "#22d3ee", "#e8eefc", "#8a99b8"
GREEN, AMBER, RED = "#34d399", "#fbbf24", "#f87171"
USER_BUBBLE, AI_BUBBLE, NAV_ACTIVE = "#2563eb", "#131d33", "#14284d"
FONT = "Segoe UI" if sys.platform.startswith("win") else "DejaVu Sans"
S = 1.0
def px(n): return int(n * S)

GUN = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
AY = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

def tr_lower(s):
    return s.replace("İ", "i").replace("I", "ı").lower()
_ASCII = str.maketrans("ığüşöç", "iguso" + "c")
def norm(s): return tr_lower(s).translate(_ASCII)

def run_cmd(args, timeout=10):
    """Konsol penceresi açmadan komut çalıştırır (--noconsole EXE'de gerekli)."""
    flags = 0x08000000 if sys.platform.startswith("win") else 0
    return subprocess.check_output(args, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                                   text=True, timeout=timeout, creationflags=flags).strip()

def http_json(url, data=None, timeout=8):
    headers = {"User-Agent": "FurkanAI/2.0"}
    if data is not None: headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

# ------------------------------------------------------------- güvenli hesap
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.Mod: operator.mod, ast.USub: operator.neg, ast.UAdd: operator.pos}
def safe_eval(node):
    if isinstance(node, ast.Expression): return safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)): return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        a, b = safe_eval(node.left), safe_eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(b) > 100: raise ValueError
        return _OPS[type(node.op)](a, b)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS: return _OPS[type(node.op)](safe_eval(node.operand))
    raise ValueError

# --------------------------------------------------------- uygulama / site listesi
SITES = {"google": "https://www.google.com", "youtube": "https://www.youtube.com", "gmail": "https://mail.google.com",
         "harita": "https://www.google.com/maps", "haritalar": "https://www.google.com/maps",
         "vikipedi": "https://tr.wikipedia.org", "instagram": "https://www.instagram.com",
         "netflix": "https://www.netflix.com", "claude": "https://claude.ai", "chatgpt": "https://chatgpt.com",
         "twitch": "https://www.twitch.tv", "discord": "https://discord.com/app", "github": "https://github.com"}
APPS = {"not defteri": "notepad", "hesap makinesi": "calc", "paint": "mspaint", "chrome": "chrome",
        "edge": "msedge", "dosya gezgini": "explorer", "dosyalar": "explorer", "spotify": "spotify:",
        "whatsapp": "whatsapp:", "ayarlar": "ms-settings:", "gorev yoneticisi": "taskmgr",
        "komut istemi": "cmd", "powershell": "powershell", "denetim masasi": "control",
        "steam": "steam:", "cizim": "mspaint"}
OPEN_WORDS = {"ac", "acsana", "acar", "acarmisin", "acabilir", "acarmisin", "baslat", "calistir", "git", "goster"}
STOP = {"google", "youtube", "da", "de", "ara", "arat", "arama", "yap", "lutfen", "bana", "icin", "bir", "bul", "hava",
        "durumu", "durum", "nasil", "ne", "bugun", "su", "an", "kac", "derece", "mi", "var", "sicaklik", "yagmur"}

def find_lm_studio():
    for base in (os.environ.get("LOCALAPPDATA", ""), os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")):
        for sub in (r"Programs\LM Studio\LM Studio.exe", r"LM Studio\LM Studio.exe"):
            p = os.path.join(base, sub)
            if base and os.path.exists(p): return p
    return None

# ================================================================ ARAYÜZ PARÇALARI
def rrect(cv, x1, y1, x2, y2, r, **kw):
    r = max(1, min(r, (x2 - x1) // 2, (y2 - y1) // 2))
    p = [x1+r, y1, x1+r, y1, x2-r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y1+r, x2, y2-r, x2, y2-r, x2, y2,
         x2-r, y2, x2-r, y2, x1+r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y2-r, x1, y1+r, x1, y1+r, x1, y1]
    return cv.create_polygon(p, smooth=True, **kw)

class Card(tk.Frame):
    """Yuvarlak köşeli kart. İçine .body üzerinden widget eklenir."""
    def __init__(self, parent, bg=CARD, border=BORDER, radius=14, pad=14):
        super().__init__(parent, bg=parent.cget("bg"))
        self._bg, self._border, self._r = bg, border, px(radius)
        self.cv = tk.Canvas(self, bg=parent.cget("bg"), highlightthickness=0, bd=0)
        self.cv.place(x=0, y=0, relwidth=1, relheight=1)
        self.body = tk.Frame(self, bg=bg)
        self.body.pack(fill="both", expand=True, padx=px(pad), pady=px(pad))
        self.bind("<Configure>", self._draw)
    def _draw(self, e):
        self.cv.delete("all")
        if e.width > 4 and e.height > 4:
            rrect(self.cv, 1, 1, e.width - 1, e.height - 1, self._r, fill=self._bg, outline=self._border)

class Btn(tk.Canvas):
    """Yuvarlak, üstüne gelince renk değiştiren düğme."""
    def __init__(self, parent, text, command=None, bg=CARD2, hover=ACCENT, fg=TEXT, size=10, bold=False,
                 padx=16, pady=9, radius=10, anchor="center", measure=None, border=None):
        self.font = tkfont.Font(family=FONT, size=size, weight="bold" if bold else "normal")
        tw = max(self.font.measure(t) for t in ([text] + (measure or [])))
        super().__init__(parent, width=tw + 2 * px(padx), height=self.font.metrics("linespace") + 2 * px(pady),
                         bg=parent.cget("bg"), highlightthickness=0, bd=0, cursor="hand2")
        self.text, self.command, self.fg, self.radius, self.anchor = text, command, fg, px(radius), anchor
        self.base, self.hov, self.cur, self.padx, self.border = bg, hover, bg, px(padx), border
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", lambda e: self._set_cur(self.hov))
        self.bind("<Leave>", lambda e: self._set_cur(self.base))
        self.bind("<ButtonRelease-1>", self._click)
    def _set_cur(self, c): self.cur = c; self._draw()
    def _click(self, e):
        if self.command and 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height(): self.command()
    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 8: w, h = int(float(self["width"])), int(float(self["height"]))
        rrect(self, 1, 1, w - 1, h - 1, self.radius, fill=self.cur, outline=self.border or self.cur)
        if self.anchor == "w": self.create_text(self.padx, h / 2, text=self.text, fill=self.fg, font=self.font, anchor="w")
        else: self.create_text(w / 2, h / 2, text=self.text, fill=self.fg, font=self.font)
    def style(self, text=None, bg=None, hover=None, fg=None):
        if text is not None: self.text = text
        if bg is not None: self.base = bg; self.cur = bg
        if hover is not None: self.hov = hover
        if fg is not None: self.fg = fg
        self._draw()

class Switch(tk.Canvas):
    def __init__(self, parent, value, command):
        super().__init__(parent, width=px(46), height=px(24), bg=parent.cget("bg"), highlightthickness=0, cursor="hand2")
        self.value, self.command = value, command
        self.bind("<Button-1>", self._toggle); self._draw()
    def _toggle(self, _=None): self.value = not self.value; self._draw(); self.command(self.value)
    def set(self, v): self.value = bool(v); self._draw()
    def _draw(self):
        self.delete("all"); w, h = px(46), px(24)
        rrect(self, 1, 1, w - 1, h - 1, h // 2, fill=ACCENT if self.value else "#334155", outline="")
        x = w - h + px(3) if self.value else px(3)
        self.create_oval(x, px(3), x + h - px(6), h - px(3), fill="white", outline="")

class Bar(tk.Canvas):
    def __init__(self, parent):
        super().__init__(parent, height=px(8), bg=parent.cget("bg"), highlightthickness=0)
        self.pct, self.color = 0, ACCENT
        self.bind("<Configure>", lambda e: self._draw())
    def set(self, pct, color=None):
        self.pct = max(0, min(100, pct)); self.color = color or (GREEN if pct < 60 else AMBER if pct < 85 else RED); self._draw()
    def _draw(self):
        self.delete("all"); w, h = self.winfo_width(), self.winfo_height()
        if w < 6: return
        rrect(self, 0, 0, w, h, h // 2, fill="#1e293b", outline="")
        if self.pct > 0: rrect(self, 0, 0, max(h, int(w * self.pct / 100)), h, h // 2, fill=self.color, outline="")

def blend(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]; b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * max(0, min(1, t))) for i in range(3))

class VoiceOverlay(tk.Canvas):
    """Sesli komutta ekranın ortasında hareket eden yuvarlak."""
    def __init__(self, parent, on_stop):
        super().__init__(parent, bg=BG, highlightthickness=0)
        self.state, self.text, self.t, self.running = "listening", "", 0, False
        self.btn = Btn(self, "■  Durdur", on_stop, bg="#3b1d28", hover=RED, size=11, bold=True, padx=24, pady=11, radius=22)
        self.btn_win = self.create_window(0, 0, window=self.btn)
        self.bind("<Configure>", lambda e: self._layout())
    def _layout(self):
        w, h = self.winfo_width(), self.winfo_height()
        self.cx, self.cy = w / 2, h / 2 - px(40)
        self.coords(self.btn_win, self.cx, self.cy + px(205))
    def start(self):
        self.state, self.text = "listening", ""
        self.place(x=0, y=0, relwidth=1, relheight=1); tk.Misc.lift(self); self.update_idletasks(); self._layout()
        if not self.running: self.running = True; self._tick()
    def stop(self): self.running = False; self.place_forget()
    def set_state(self, state, text=""): self.state, self.text = state, text
    def _tick(self):
        if not self.running: return
        self.t += 1; t = self.t; self.delete("fx")
        col = {"listening": ACCENT2, "thinking": AMBER, "heard": GREEN}[self.state]
        R, cx, cy = px(64), self.cx, self.cy
        if self.state == "listening":
            for i in range(3):                      # dışarı yayılan halkalar
                p = ((t / 50.0) + i / 3.0) % 1.0; r = R + p * px(100)
                self.create_oval(cx - r, cy - r, cx + r, cy + r, outline=blend(col, BG, p ** 0.6), width=px(3), tags="fx")
        amp = 0.055 if self.state == "listening" else 0.03
        sp = 1.0 if self.state == "listening" else 0.5
        pts = []
        for k in range(72):                         # yaşayan, dalgalanan yuvarlak
            th = 2 * 3.14159265 * k / 72
            m = 1 + amp * math.sin(3 * th + t * 0.13 * sp) + amp * 0.7 * math.sin(5 * th - t * 0.17 * sp)
            m += 0.03 * math.sin(t * 0.09)
            r = R * m
            pts += [cx + r * math.cos(th), cy + r * math.sin(th)]
        self.create_polygon(pts, smooth=True, fill=blend(col, BG, 0.55), outline=col, width=px(3), tags="fx")
        if self.state == "thinking":
            self.create_arc(cx - R - px(16), cy - R - px(16), cx + R + px(16), cy + R + px(16), start=-t * 9, extent=110,
                            style="arc", outline=AMBER, width=px(5), tags="fx")
        self.create_text(cx, cy, text="🎙" if self.state != "heard" else "✓", fill="white", font=(FONT, 34, "bold"), tags="fx")
        title, sub = {"listening": ("Dinliyorum...", "Şimdi konuş. İptal etmek için Durdur'a bas."),
                      "thinking": ("Anlıyorum...", "Sesin metne çevriliyor."),
                      "heard": ("Anlaşıldı", "“" + self.text + "”")}[self.state]
        self.create_text(cx, cy + px(125), text=title, fill=TEXT, font=(FONT, 18, "bold"), tags="fx")
        self.create_text(cx, cy + px(158), text=sub, fill=MUTED, font=(FONT, 11), width=px(520), tags="fx")
        self.after(33, self._tick)

class ChatView(tk.Frame):
    """Kaydırılabilir sohbet balonları."""
    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        self.cv = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.sb = ttk.Scrollbar(self, orient="vertical", command=self.cv.yview)
        self.inner = tk.Frame(self.cv, bg=BG)
        self.win = self.cv.create_window((0, 0), window=self.inner, anchor="nw")
        self.cv.configure(yscrollcommand=self.sb.set)
        self.sb.pack(side="right", fill="y"); self.cv.pack(side="left", fill="both", expand=True)
        self.inner.bind("<Configure>", lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        self.cv.bind("<Configure>", self._resize)
        self.wrap = px(520); self.labels = []; self.typing = None

    def _resize(self, e):
        self.cv.itemconfig(self.win, width=e.width)
        self.wrap = max(px(240), int(e.width * 0.62))
        for l in self.labels:
            try: l.config(wraplength=self.wrap)
            except Exception: pass

    def to_bottom(self): self.after(40, lambda: self.cv.yview_moveto(1.0))

    def add(self, who, text, actions=None):
        self.remove_typing()
        row = tk.Frame(self.inner, bg=BG); row.pack(fill="x", padx=px(12), pady=(px(7), 0))
        stamp = datetime.now().strftime("%H:%M")
        if who == "user":
            card = Card(row, bg=USER_BUBBLE, border=USER_BUBBLE, radius=16, pad=11); card.pack(side="right")
            fg, tfg = "white", "#bfdbfe"
        else:
            av = tk.Canvas(row, width=px(34), height=px(34), bg=BG, highlightthickness=0); av.pack(side="left", anchor="n", padx=(0, px(8)))
            av.create_oval(1, 1, px(34) - 1, px(34) - 1, fill=ACCENT, outline=""); av.create_text(px(17), px(17), text="F", fill="white", font=(FONT, 11, "bold"))
            card = Card(row, bg=AI_BUBBLE, border=BORDER, radius=16, pad=11); card.pack(side="left")
            fg, tfg = TEXT, MUTED
        lbl = tk.Label(card.body, text=text, bg=card.body.cget("bg"), fg=fg, font=(FONT, 10), justify="left", anchor="w", wraplength=self.wrap)
        lbl.pack(anchor="w"); self.labels.append(lbl)
        if actions:
            bar = tk.Frame(card.body, bg=card.body.cget("bg")); bar.pack(anchor="w", pady=(px(8), 0))
            for t, fn in actions: Btn(bar, t, fn, bg=CARD2, size=9, padx=12, pady=6, radius=8).pack(side="left", padx=(0, px(6)))
        tk.Label(card.body, text=stamp, bg=card.body.cget("bg"), fg=tfg, font=(FONT, 8)).pack(anchor="e", pady=(px(4), 0))
        self.to_bottom()

    def show_typing(self):
        self.remove_typing()
        row = tk.Frame(self.inner, bg=BG); row.pack(fill="x", padx=px(12), pady=(px(7), 0))
        card = Card(row, bg=AI_BUBBLE, border=BORDER, radius=16, pad=10); card.pack(side="left", padx=(px(42), 0))
        lbl = tk.Label(card.body, text="●", bg=AI_BUBBLE, fg=ACCENT2, font=(FONT, 10)); lbl.pack()
        self.typing = row
        def tick(n=0):
            if self.typing is row and row.winfo_exists():
                lbl.config(text=["●", "● ●", "● ● ●"][n % 3]); self.after(380, tick, n + 1)
        tick(); self.to_bottom()

    def remove_typing(self):
        if self.typing is not None:
            try: self.typing.destroy()
            except Exception: pass
            self.typing = None

    def clear(self):
        for w in self.inner.winfo_children(): w.destroy()
        self.labels.clear(); self.typing = None

# ================================================================ ANA UYGULAMA
class FurkanAI:
    def __init__(self, root):
        global S
        self.root = root
        try: S = max(1.0, root.winfo_fpixels("1i") / 96.0)
        except Exception: S = 1.0
        self.cfg = load_cfg()
        self.page = "home"; self.voice_busy = False; self._voice_id = 0; self.ai_gen = 0; self._engine = None; self.history = []; self.lm_model = None
        self.last_system = {}; self.weather_text = ""; self._speaking = threading.Lock()
        root.title("FurkanAI"); root.configure(bg=BG)
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        w, h = min(px(1480), sw - px(80)), min(px(900), sh - px(110))
        root.geometry(f"{w}x{h}+{(sw - w) // 2}+{max(0, (sh - h) // 3)}"); root.minsize(px(1080), px(680))
        try: root.iconbitmap(resource_path("icon.ico"))
        except Exception: pass
        self._style(); self._build()
        root.bind_all("<MouseWheel>", self._wheel)
        self.show_page("home")
        self.refresh_system(); self.load_weather(); self.check_lm(); self.tick_clock(); self.refresh_notes()
        self.chat.add("ai", "Merhaba! Ben FurkanAI 👋\nYazarak ya da 🎙 Sesli Komut ile konuşarak bana komut verebilirsin. Neler yapabildiğimi görmek için “yardım” yaz.")
        root.after(400, self.focus_input)

    # ---------------------------------------------------------------- stil
    def _style(self):
        st = ttk.Style()
        try: st.theme_use("clam")
        except Exception: pass
        st.configure("Vertical.TScrollbar", background=CARD2, troughcolor=BG, bordercolor=BG, arrowcolor=MUTED,
                     lightcolor=CARD2, darkcolor=CARD2, gripcount=0, relief="flat", arrowsize=px(12))
        st.map("Vertical.TScrollbar", background=[("active", ACCENT)])

    def lab(self, parent, text, size=10, color=TEXT, bold=False, **kw):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color, font=(FONT, size, "bold" if bold else "normal"),
                        anchor="w", justify="left", **kw)

    # ------------------------------------------------------------ arayüz kurulumu
    def _build(self):
        outer = tk.Frame(self.root, bg=BG); outer.pack(fill="both", expand=True)
        self._build_side(outer); self._build_right(outer)
        main = tk.Frame(outer, bg=BG); main.pack(side="left", fill="both", expand=True)
        top = tk.Frame(main, bg=BG); top.pack(fill="x", padx=px(26), pady=(px(16), 0))
        self.lab(top, "Her zaman yanında, her konuda yardımcı.", 10, MUTED).pack(side="left")
        self.clock = self.lab(top, "", 10, MUTED); self.clock.pack(side="right")
        self.area = tk.Frame(main, bg=BG); self.area.pack(fill="both", expand=True, padx=px(26), pady=px(14))
        self.overlay = VoiceOverlay(self.area, self.stop_all)
        self.root.bind("<Escape>", lambda e: self.stop_all())
        self.pages = {"chat": self._page_chat(), "browser": self._page_browser(),
                      "system": self._page_system(), "settings": self._page_settings()}

    def _build_side(self, outer):
        side = tk.Frame(outer, bg=SIDE, width=px(215)); side.pack(side="left", fill="y"); side.pack_propagate(False)
        logo = tk.Frame(side, bg=SIDE); logo.pack(anchor="w", padx=px(18), pady=(px(22), px(26)))
        c = tk.Canvas(logo, width=px(38), height=px(38), bg=SIDE, highlightthickness=0); c.pack(side="left")
        rrect(c, 1, 1, px(38) - 1, px(38) - 1, px(11), fill=ACCENT, outline="")
        c.create_text(px(19), px(19), text="F", fill="white", font=(FONT, 15, "bold"))
        self.lab(logo, "FurkanAI", 17, ACCENT2, True).pack(side="left", padx=(px(10), 0))
        self.lab(side, "MENÜ", 8, MUTED, True).pack(anchor="w", padx=px(20), pady=(0, px(6)))
        self.nav = {}
        for key, txt in [("home", "⌂   Ana Sayfa"), ("chat", "✉   Sohbet"), ("browser", "◎   Tarayıcı"),
                         ("system", "▣   Sistem"), ("settings", "⚙   Ayarlar")]:
            b = Btn(side, txt, lambda k=key: self.show_page(k), bg=SIDE, hover=CARD2, size=10, padx=16, pady=11, radius=10, anchor="w")
            b.pack(fill="x", padx=px(12), pady=px(2)); self.nav[key] = b
        tk.Frame(side, bg=SIDE).pack(fill="both", expand=True)
        card = Card(side, bg="#0c1424", border=BORDER, radius=12, pad=10); card.pack(fill="x", padx=px(12), pady=px(10))
        top = tk.Frame(card.body, bg="#0c1424"); top.pack(fill="x")
        self.dot = tk.Canvas(top, width=px(10), height=px(10), bg="#0c1424", highlightthickness=0); self.dot.pack(side="left")
        self.dot_id = self.dot.create_oval(1, 1, px(10) - 1, px(10) - 1, fill=AMBER, outline="")
        self.status_t = self.lab(top, "AI DURUMU", 9, AMBER, True); self.status_t.pack(side="left", padx=(px(6), 0))
        self.status_s = self.lab(card.body, "Kontrol ediliyor...", 9, MUTED, wraplength=px(160)); self.status_s.pack(anchor="w", pady=(px(4), 0))
        self.side_name = self.lab(side, self.cfg["name"], 11, TEXT, True); self.side_name.pack(anchor="w", padx=px(20), pady=(px(6), 0))
        self.lab(side, "Windows asistanı", 9, MUTED).pack(anchor="w", padx=px(20), pady=(0, px(18)))

    def _page_chat(self):
        f = tk.Frame(self.area, bg=BG)
        self.greet = tk.Frame(f, bg=BG)
        self.greet_h = self.lab(self.greet, "", 25, TEXT, True); self.greet_h.pack(anchor="w")
        self.lab(self.greet, "Bugün sana nasıl yardımcı olabilirim?", 19, ACCENT2, True).pack(anchor="w", pady=(0, px(4)))
        self.lab(self.greet, "Soru sor, komut ver, bilgi iste... Ben buradayım.", 10, MUTED).pack(anchor="w", pady=(0, px(12)))
        chips = tk.Frame(self.greet, bg=BG); chips.pack(anchor="w", pady=(0, px(10)))
        for t in ["🔎 Google'ı aç", "▣ Sistem bilgilerim", "🌤 Hava durumu", "♪ Spotify aç", "🕒 Saat kaç?", "😄 Fıkra anlat"]:
            Btn(chips, t, lambda t=t: self.submit(t.split(" ", 1)[1]), bg=CARD, hover=ACCENT, size=10, padx=14, pady=8, radius=18, border=BORDER).pack(side="left", padx=(0, px(8)))
        inp = Card(f, bg=CARD, border="#26417a", radius=16, pad=7); inp.pack(side="bottom", fill="x", pady=(px(12), 0))
        self.entry = tk.Entry(inp.body, bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat", font=(FONT, 11), bd=0, highlightthickness=0)
        self.entry.pack(side="left", fill="x", expand=True, padx=(px(10), px(6)), ipady=px(8))
        self.entry.insert(0, "Mesajını yaz... (ör. Google aç)"); self.entry.config(fg=MUTED)
        self.entry.bind("<FocusIn>", self.clear_placeholder); self.entry.bind("<Return>", lambda e: self.send_message())
        self.voice_btn = Btn(inp.body, "🎙 Sesli Komut", self.voice_command, bg="#14376a", hover="#1d4ed8", measure=["● Dinliyorum..."])
        self.voice_btn.pack(side="right", padx=(px(6), 0))
        Btn(inp.body, "Gönder ➤", self.send_message, bg=ACCENT, hover="#2563eb", bold=True).pack(side="right", padx=(0, px(6)))
        Btn(inp.body, "■ Durdur", self.stop_all, bg="#3b1d28", hover=RED).pack(side="right", padx=(0, px(6)))
        self.spk_btn = Btn(inp.body, "🔊 Ses açık", lambda: self.set_speak(not self.cfg["speak"]), bg=CARD2, hover=ACCENT, measure=["🔇 Ses kapalı"])
        self.spk_btn.pack(side="right", padx=(0, px(6)))
        self.spk_btn.style(text="🔊 Ses açık" if self.cfg["speak"] else "🔇 Ses kapalı")
        self.chat = ChatView(f); self.chat.pack(fill="both", expand=True)
        return f

    def _page_browser(self):
        f = tk.Frame(self.area, bg=BG)
        self.lab(f, "Tarayıcı", 22, TEXT, True).pack(anchor="w")
        self.lab(f, "Sık kullanılan sitelere tek tıkla git.", 10, MUTED).pack(anchor="w", pady=(0, px(16)))
        grid = tk.Frame(f, bg=BG); grid.pack(fill="x")
        items = [("🔎 Google", "google"), ("▶ YouTube", "youtube"), ("✉ Gmail", "gmail"), ("🗺 Haritalar", "harita"),
                 ("📖 Vikipedi", "vikipedi"), ("🤖 Claude", "claude"), ("💬 ChatGPT", "chatgpt"), ("📷 Instagram", "instagram"),
                 ("🎬 Netflix", "netflix"), ("🎮 Twitch", "twitch"), ("🗨 Discord", "discord"), ("💻 GitHub", "github")]
        for i, (t, k) in enumerate(items):
            Btn(grid, t, lambda k=k: webbrowser.open(SITES[k]), bg=CARD, hover=ACCENT, size=11, padx=20, pady=18, radius=14,
                border=BORDER).grid(row=i // 4, column=i % 4, sticky="ew", padx=px(6), pady=px(6))
        for c in range(4): grid.grid_columnconfigure(c, weight=1)
        return f

    def _page_system(self):
        f = tk.Frame(self.area, bg=BG)
        self.lab(f, "Sistem", 22, TEXT, True).pack(anchor="w")
        self.lab(f, "Bilgisayarının canlı durumu (2 saniyede bir yenilenir).", 10, MUTED).pack(anchor="w", pady=(0, px(14)))
        grid = tk.Frame(f, bg=BG); grid.pack(fill="x")
        self.live = {}
        for i, (k, t) in enumerate([("cpu", "İşlemci kullanımı"), ("ram", "Bellek (RAM)"), ("disk", "Depolama"), ("bat", "Pil")]):
            card = Card(grid, radius=14, pad=16); card.grid(row=i // 2, column=i % 2, sticky="nsew", padx=px(6), pady=px(6))
            self.lab(card.body, t, 10, MUTED).pack(anchor="w")
            v = self.lab(card.body, "—", 22, TEXT, True); v.pack(anchor="w", pady=(px(2), px(8)))
            bar = Bar(card.body); bar.pack(fill="x")
            d = self.lab(card.body, "", 9, MUTED); d.pack(anchor="w", pady=(px(6), 0))
            self.live[k] = (v, bar, d)
        for c in range(2): grid.grid_columnconfigure(c, weight=1, uniform="a")
        info = Card(f, radius=14, pad=16); info.pack(fill="x", padx=px(6), pady=px(6))
        self.big_info = self.lab(info.body, "Bilgi alınıyor...", 10, TEXT, wraplength=px(900)); self.big_info.pack(anchor="w")
        return f

    def _page_settings(self):
        f = tk.Frame(self.area, bg=BG)
        self.lab(f, "Ayarlar", 22, TEXT, True).pack(anchor="w")
        self.lab(f, "Değişiklikler otomatik olarak bilgisayarına kaydedilir.", 10, MUTED).pack(anchor="w", pady=(0, px(14)))
        card = Card(f, radius=14, pad=18); card.pack(fill="x", padx=px(6))
        def row(title, sub):
            r = tk.Frame(card.body, bg=CARD); r.pack(fill="x", pady=px(8))
            left = tk.Frame(r, bg=CARD); left.pack(side="left", fill="x", expand=True)
            self.lab(left, title, 11, TEXT, True).pack(anchor="w"); self.lab(left, sub, 9, MUTED).pack(anchor="w")
            return r
        def entry(parent, val, w=26):
            e = tk.Entry(parent, bg=CARD2, fg=TEXT, insertbackground=TEXT, relief="flat", font=(FONT, 10), width=w, highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT)
            e.insert(0, val); e.pack(side="right", ipady=px(7), padx=(px(8), 0)); return e
        r = row("Adın", "Karşılama mesajında kullanılır."); self.set_name = entry(r, self.cfg["name"])
        r = row("Şehir", "Hava durumu bu şehir için gösterilir."); self.set_city = entry(r, self.cfg["city"])
        r = row("LM Studio adresi", "Yerel yapay zekâ sunucusu (varsayılan: http://localhost:1234)."); self.set_lm = entry(r, self.cfg["lm_url"], 30)
        r = row("Sesli yanıt", "FurkanAI cevaplarını sesli okusun."); self.sw = Switch(r, self.cfg["speak"], self.toggle_speak); self.sw.pack(side="right")
        bar = tk.Frame(card.body, bg=CARD); bar.pack(fill="x", pady=(px(10), 0))
        Btn(bar, "Kaydet", self.save_settings, bg=ACCENT, hover="#2563eb", bold=True).pack(side="right")
        self.set_msg = self.lab(bar, "", 9, GREEN); self.set_msg.pack(side="right", padx=px(12))
        about = Card(f, radius=14, pad=16); about.pack(fill="x", padx=px(6), pady=px(12))
        self.lab(about.body, "Hakkında", 11, TEXT, True).pack(anchor="w")
        self.lab(about.body, f"FurkanAI 2.0 · Notların: {NOTES_FILE}\nSesli komutta konuşman tanıma için Google servisine gönderilir; mikrofon ve internet gerekir.",
                 9, MUTED, wraplength=px(900)).pack(anchor="w", pady=(px(4), 0))
        return f

    def _build_right(self, outer):
        right = tk.Frame(outer, bg=SIDE, width=px(310)); right.pack(side="right", fill="y"); right.pack_propagate(False)
        pad = dict(fill="x", padx=px(14))
        self.lab(right, "▣  Sistem Bilgileri", 12, TEXT, True).pack(anchor="w", padx=px(16), pady=(px(20), px(8)))
        card = Card(right, bg=CARD, radius=12, pad=12); card.pack(**pad)
        self.sys_labels = {}
        for k, t in [("os", "İşletim sistemi"), ("cpu", "İşlemci"), ("ram", "RAM"), ("gpu", "Ekran kartı"), ("disk", "Depolama")]:
            self.lab(card.body, t, 8, MUTED).pack(anchor="w", pady=(px(4), 0))
            v = self.lab(card.body, "...", 9, TEXT, True, wraplength=px(250)); v.pack(anchor="w"); self.sys_labels[k] = v
        self.lab(right, "🌤  Hava Durumu", 12, TEXT, True).pack(anchor="w", padx=px(16), pady=(px(16), px(8)))
        w = Card(right, bg=CARD, radius=12, pad=12); w.pack(**pad)
        self.w_city = self.lab(w.body, self.cfg["city"], 9, MUTED); self.w_city.pack(anchor="w")
        self.w_temp = self.lab(w.body, "--°", 26, TEXT, True); self.w_temp.pack(anchor="w")
        self.w_desc = self.lab(w.body, "Yükleniyor...", 10, ACCENT2, True, wraplength=px(250)); self.w_desc.pack(anchor="w")
        self.w_more = self.lab(w.body, "", 9, MUTED, wraplength=px(250)); self.w_more.pack(anchor="w", pady=(px(4), px(6)))
        Btn(w.body, "↻ Yenile", self.load_weather, size=9, padx=12, pady=6, radius=8).pack(anchor="e")
        self.lab(right, "⚡  Hızlı İşlemler", 12, TEXT, True).pack(anchor="w", padx=px(16), pady=(px(16), px(8)))
        g = tk.Frame(right, bg=SIDE); g.pack(**pad)
        acts = [("Google'da ara", self.search_google), ("Dosyalarım", self.open_home_folder), ("Not yaz", self.focus_note),
                ("Ekran alıntısı", self.screenshot), ("Hesap mak.", lambda: self.launch("calc")), ("LM Studio", self.open_lm)]
        for i, (t, fn) in enumerate(acts):
            Btn(g, t, fn, bg=CARD, hover=ACCENT, size=9, padx=8, pady=8, radius=9, border=BORDER).grid(row=i // 2, column=i % 2, sticky="ew", padx=px(3), pady=px(3))
        g.grid_columnconfigure(0, weight=1, uniform="q"); g.grid_columnconfigure(1, weight=1, uniform="q")
        self.lab(right, "📝  Notlarım", 12, TEXT, True).pack(anchor="w", padx=px(16), pady=(px(16), px(8)))
        n = Card(right, bg=CARD, radius=12, pad=10); n.pack(**pad)
        self.note_entry = tk.Entry(n.body, bg=CARD2, fg=TEXT, insertbackground=TEXT, relief="flat", font=(FONT, 10), highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT)
        self.note_entry.pack(fill="x", ipady=px(7)); self.note_entry.bind("<Return>", lambda e: self.save_note())
        self.notes_list = self.lab(n.body, "", 8, MUTED, wraplength=px(250)); self.notes_list.pack(anchor="w", pady=(px(6), px(4)))
        Btn(n.body, "Notu kaydet", self.save_note, bg=ACCENT, hover="#2563eb", size=9, padx=12, pady=6, radius=8).pack(anchor="e")

    # ---------------------------------------------------------------- sayfalar
    def show_page(self, key):
        self.page = key
        for k, b in self.nav.items():
            on = (k == key)
            b.style(bg=NAV_ACTIVE if on else SIDE, hover=NAV_ACTIVE if on else CARD2, fg=ACCENT2 if on else TEXT)
        for p in self.pages.values(): p.pack_forget()
        target = "chat" if key == "home" else key
        self.pages[target].pack(fill="both", expand=True)
        if target == "chat":
            if key == "home":
                hr = datetime.now().hour
                g = "Günaydın" if 5 <= hr < 12 else "İyi günler" if hr < 18 else "İyi akşamlar" if hr < 23 else "İyi geceler"
                self.greet_h.config(text=f"{g} {self.cfg['name']},")
                self.greet.pack(side="top", fill="x", before=self.chat)
            else: self.greet.pack_forget()
            self.focus_input()
        if key == "system": self.tick_system()

    def tick_clock(self):
        n = datetime.now()
        self.clock.config(text=f"{GUN[n.weekday()]}, {n.day} {AY[n.month - 1]} {n.year}  ·  {n:%H:%M}")
        self.root.after(20000, self.tick_clock)

    def _wheel(self, e):
        w = self.root.winfo_containing(e.x_root, e.y_root)
        while w is not None:
            if w is self.chat: self.chat.cv.yview_scroll(int(-e.delta / 120) * 2, "units"); return
            w = getattr(w, "master", None)

    # ------------------------------------------------------------------- giriş
    def clear_placeholder(self, _=None):
        if self.entry.get().startswith("Mesajını yaz..."): self.entry.delete(0, "end")
        self.entry.config(fg=TEXT)
    def focus_input(self):
        if self.page in ("home", "chat"): self.entry.focus_set(); self.clear_placeholder()
    def send_message(self):
        m = self.entry.get().strip()
        if not m or m.startswith("Mesajını yaz..."): return
        self.entry.delete(0, "end"); self.submit(m)

    def submit(self, msg):
        if self.page not in ("home", "chat"): self.show_page("chat")
        self.chat.add("user", msg)
        res = self.local_command(msg)
        if res is ASYNC: return
        if res is not None: self.reply(*res); return
        self.chat.show_typing(); self.ai_gen += 1
        threading.Thread(target=self._ai_worker, args=(msg, self.ai_gen), daemon=True).start()

    def reply(self, text, actions=None):
        self.chat.add("ai", text, actions)
        if self.cfg["speak"]: threading.Thread(target=self.speak, args=(text,), daemon=True).start()
    def reply_async(self, text, actions=None): self.root.after(0, lambda: self.reply(text, actions))

    def _ai_worker(self, msg, gen):
        ans = self.ask_local_ai(msg)
        if gen != self.ai_gen: return
        if ans: self.root.after(0, lambda: self.reply(ans))
        else:
            acts = [("Google'da ara", lambda: webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(msg))),
                    ("Neler yapabilirsin?", lambda: self.submit("yardım"))]
            self.root.after(0, lambda: self.reply("Bunu tam anlayamadım. İstersen Google'da arayabilirim ya da “yardım” yazıp "
                                                  "yapabildiklerime bakabilirsin. LM Studio'yu açıp yerel sunucuyu başlatırsan serbest sohbet de edebilirim.", acts))

    # -------------------------------------------------------------- komutlar
    def local_command(self, msg):
        low = tr_lower(msg).strip()
        orig = re.findall(r"\w+", low); toks = [t.translate(_ASCII) for t in orig]; ts = set(toks); n = " ".join(toks)

        if ts & {"merhaba", "selam", "gunaydin", "hey", "slm", "naber"} and len(toks) <= 3:
            return (random.choice(["Merhaba! 😊 Ne yapmak istersin?", "Selam! Seni dinliyorum.", "Hey! Nasıl yardımcı olabilirim?"]), None)
        if "yardim" in ts or "ne yapabilirsin" in n:
            return ("Şunları yapabilirim:\n• Aç: “Google aç”, “YouTube aç”, “Spotify aç”, “Not defteri aç”, “LM Studio aç”\n"
                    "• Ara: “Google'da Minecraft ara”, “YouTube'da müzik ara”\n• “Sistem bilgilerimi göster”, “Pil durumu”\n"
                    "• “Hava durumu” veya “İstanbul hava durumu”\n• “Not al: yarın market”, “Notlarımı göster”\n"
                    "• “Saat kaç?”, “Bugün günlerden ne?”, “125*4 hesapla”\n• “Ekran görüntüsü al”, “Sesi kapat”, “Sohbeti temizle”, “Fıkra anlat”", None)
        if ts & {"dur", "durdur", "sus", "sustur", "iptal"} and len(toks) <= 2:
            self.stop_all(); self.chat.add("ai", "Durdurdum. ⏹"); return ASYNC
        if ts & {"tesekkurler", "tesekkur", "eyvallah"} or "sag ol" in n: return ("Rica ederim! 😊", None)
        if "kimsin" in ts or "adin ne" in n or "ismin ne" in n:
            return (f"Ben FurkanAI, {self.cfg['name']} için yapılmış Windows masaüstü asistanıyım.", None)
        if ts & {"saka", "fikra", "espri"}:
            return (random.choice(["Bilgisayar neden doktora gitmiş? Çünkü virüs kapmış! 🦠", "Programcı neden gözlük takar? C# göremediği için! 👓",
                                   "Wi-Fi ile aşk arasındaki fark ne? İkisinde de sinyal kaybolunca sinir olursun. 📶",
                                   "İki bit karşılaşmış: “Naber?” “1 sıfır.” 😄"]), None)
        if ts & {"temizle", "sil"} and ("sohbet" in ts or "ekran" in ts or toks == ["temizle"]):
            self.chat.clear(); return ("Sohbet temizlendi. ✨", None)
        if "sesi" in ts and ts & {"kapat", "kapa"} or "sessiz" in ts: self.set_speak(False); return ("Sesli yanıt kapatıldı. 🔇", None)
        if "sesi" in ts and "ac" in ts or "sesli" in ts and "yanit" in ts: self.set_speak(True); return ("Sesli yanıt açıldı. 🔊", None)
        if "ekran" in ts and ts & {"goruntusu", "alintisi", "resmi"}: self.screenshot(); return ("Ekran alıntısı aracını açtım (Win + Shift + S ile de açabilirsin).", None)

        # not işlemleri
        m = re.match(r"^\s*not\s*(al)?\s*[:\-]?\s*(.*)$", low)
        if m and (toks[0] == "not") and m.group(2).strip():
            note = msg.split(":", 1)[1].strip() if ":" in msg else re.sub(r"(?i)^\s*not\s*al\s*", "", msg).strip()
            if note: self.write_note(note); return ("Notunu kaydettim: " + note, None)
        if toks[:1] == ["not"] and len(toks) <= 2: self.focus_note(); return ("Sağdaki Notlarım alanına notunu yazıp Enter'a basabilirsin.", None)
        if ts & {"notlarim", "notlarimi", "notlari"}: return (self.read_notes(), None)

        # hesap
        if ts & {"hesapla", "kac", "eder"} or re.search(r"\d\s*[-+*/x×÷^]\s*\d", low):
            expr = low
            for a, b in [("artı", "+"), ("eksi", "-"), ("çarpı", "*"), ("bölü", "/"), ("x", "*"), ("×", "*"), ("÷", "/"), ("^", "**"), (",", ".")]:
                expr = expr.replace(a, b)
            expr = re.sub(r"[^0-9+\-*/(). %]", "", expr).strip()
            if re.search(r"\d", expr) and re.search(r"[+\-*/]", expr.lstrip("-+")):
                try:
                    r = safe_eval(ast.parse(expr, mode="eval"))
                    return (f"{expr} = {round(r, 6):g}", None)
                except Exception: pass

        if ts & {"saat", "tarih"} or ("gun" in ts or "gunlerden" in ts):
            nw = datetime.now()
            return (f"Şu an saat {nw:%H:%M}. Bugün {nw.day} {AY[nw.month - 1]} {nw.year}, {GUN[nw.weekday()]}.", None)
        if ts & {"pil", "batarya", "sarj"}:
            try:
                import psutil; b = psutil.sensors_battery()
                if b: return (f"Pil %{b.percent:.0f} — " + ("şarj oluyor ⚡" if b.power_plugged else "pille çalışıyor 🔋"), None)
            except Exception: pass
            return ("Pil bilgisine ulaşamadım.", None)
        if ts & {"sistem", "ram", "islemci", "bellek", "depolama", "disk"} or ("bilgisayar" in ts and "bilgi" in " ".join(toks)):
            self.refresh_system(); return (self.system_summary(), None)
        if ts & {"hava", "sicaklik", "yagmur"} or ("kac" in ts and "derece" in ts):
            city = " ".join(o for o, t in zip(orig, toks) if t not in STOP and t not in OPEN_WORDS)
            if city: threading.Thread(target=self._weather_for, args=(city,), daemon=True).start(); return ASYNC
            self.load_weather(); return (self.weather_text or "Hava durumunu alıyorum, sağ panelde görünecek.", None)

        # arama
        if ts & {"ara", "arat", "arama"} and not (ts & OPEN_WORDS):
            q = " ".join(o for o, t in zip(orig, toks) if t not in STOP)
            eng = "youtube" if "youtube" in ts else "google"
            if not q: return ("Neyi aramamı istersin? Örn: “Google'da Minecraft ara”", None)
            url = ("https://www.youtube.com/results?search_query=" if eng == "youtube" else "https://www.google.com/search?q=") + urllib.parse.quote(q)
            webbrowser.open(url); return (f"{'YouTube' if eng == 'youtube' else 'Google'}'da “{q}” için arama yaptım.", None)

        # aç / başlat
        if ts & OPEN_WORDS:
            if "lm" in ts and "studio" in ts: return self.open_lm(True)
            for name, target in APPS.items():
                if name in n or (name.split()[0] in ts and len(name.split()) == 1):
                    return (self.launch(target, name), None)
            for name, url in SITES.items():
                if name in ts: webbrowser.open(url); return (f"{name.capitalize()} sitesini tarayıcıda açtım.", None)
        return None

    def launch(self, target, name=None):
        try:
            if sys.platform.startswith("win"): os.startfile(target)
            else: subprocess.Popen(["xdg-open", target], stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"{(name or target).title()} açılıyor... 🚀"
        except Exception:
            return f"{(name or target).title()} uygulamasını açamadım. Bilgisayarında kurulu olmayabilir."

    def open_lm(self, as_reply=False):
        p = find_lm_studio()
        txt = None
        if p:
            try:
                os.startfile(p) if sys.platform.startswith("win") else subprocess.Popen([p])
                txt = "LM Studio açılıyor... Model yüklenince “Local Server” sekmesinden sunucuyu başlat. 🚀"
            except Exception: pass
        if txt is None: txt = "LM Studio'yu bulamadım. Kurulu değilse lmstudio.ai adresinden indirebilirsin."
        if as_reply: return (txt, None if p else [("lmstudio.ai'yi aç", lambda: webbrowser.open("https://lmstudio.ai"))])
        self.chat.add("ai", txt)

    def open_google(self): webbrowser.open("https://www.google.com")
    def search_google(self):
        self.show_page("chat"); self.entry.delete(0, "end"); self.entry.insert(0, "Google'da "); self.entry.config(fg=TEXT); self.entry.focus_set(); self.entry.icursor("end")
    def open_home_folder(self):
        try:
            p = os.path.expanduser("~")
            if sys.platform.startswith("win"): os.startfile(p)
            else: subprocess.Popen(["xdg-open", p])
        except Exception as e: messagebox.showerror("Klasör açılamadı", str(e))
    def screenshot(self):
        try:
            if sys.platform.startswith("win"): os.startfile("ms-screenclip:")
            else: messagebox.showinfo("Ekran alıntısı", "Windows'ta Win + Shift + S tuşlarına bas.")
        except Exception: messagebox.showinfo("Ekran alıntısı", "Windows'ta Win + Shift + S tuşlarına bas.")

    # ------------------------------------------------------------------- ses
    def voice_command(self):
        if self.voice_busy: self.stop_all(); return        # tekrar basınca durdurur
        self.stop_speaking()
        self.voice_busy = True; self._voice_id += 1; vid = self._voice_id
        self.voice_btn.style(text="● Dinliyorum...", bg=RED, hover=RED)
        self.overlay.start()
        threading.Thread(target=self._listen, args=(vid,), daemon=True).start()
    def _listen(self, vid):
        try:
            import speech_recognition as sr
            rec = sr.Recognizer()
            with sr.Microphone() as src:
                rec.adjust_for_ambient_noise(src, duration=0.5)
                audio = rec.listen(src, timeout=6, phrase_time_limit=10)
            if vid != self._voice_id: return
            self.root.after(0, lambda: self.overlay.set_state("thinking") if vid == self._voice_id else None)
            heard = rec.recognize_google(audio, language="tr-TR")
            self.root.after(0, lambda: self._voice_done(vid, heard))
        except ImportError:
            self.root.after(0, lambda: self._voice_done(vid, None, "Ses tanıma paketi (SpeechRecognition/PyAudio) kurulu değil. KUR.bat dosyasını tekrar çalıştırırsan kurmayı dener."))
        except Exception:
            self.root.after(0, lambda: self._voice_done(vid, None, "Seni duyamadım ya da ses tanıma servisine ulaşılamadı. Mikrofon iznini ve interneti kontrol et."))
    def _voice_done(self, vid, heard, err=None):
        if vid != self._voice_id: return
        self.voice_busy = False; self.voice_btn.style(text="🎙 Sesli Komut", bg="#14376a", hover="#1d4ed8")
        if heard:
            self.overlay.set_state("heard", heard)
            self.root.after(900, lambda: (self.overlay.stop(), self.submit(heard)) if vid == self._voice_id else None)
        else:
            self.overlay.stop()
            if err: self.chat.add("ai", err)
    def stop_all(self):
        """Konuşmayı, dinlemeyi ve bekleyen yapay zekâ cevabını durdurur."""
        self.stop_speaking(); self._voice_id += 1; self.ai_gen += 1
        if self.voice_busy:
            self.voice_busy = False; self.voice_btn.style(text="🎙 Sesli Komut", bg="#14376a", hover="#1d4ed8")
        self.overlay.stop(); self.chat.remove_typing()
    def stop_speaking(self):
        try:
            if self._engine is not None: self._engine.stop()
        except Exception: pass
    def speak(self, text):
        if not self._speaking.acquire(blocking=False): return
        try:
            import pyttsx3
            e = pyttsx3.init(); self._engine = e; e.setProperty("rate", 175)
            for v in e.getProperty("voices"):
                s = (v.name + " " + v.id).lower()
                if "turk" in s or "türk" in s or "tr-tr" in s: e.setProperty("voice", v.id); break
            clean = re.sub(r"[^\w\s.,!?:;%()'’\-+*/=°]", " ", text)
            e.say(clean[:600]); e.runAndWait(); e.stop()
        except Exception: pass
        finally: self._engine = None; self._speaking.release()
    def set_speak(self, v):
        self.cfg["speak"] = bool(v); save_cfg(self.cfg)
        if not v: self.stop_speaking()
        try: self.spk_btn.style(text="🔊 Ses açık" if v else "🔇 Ses kapalı"); self.sw.set(v)
        except Exception: pass
    def toggle_speak(self, v): self.set_speak(v)

    # ----------------------------------------------------------------- sistem
    def refresh_system(self):
        def work():
            info = {"os": f"{platform.system()} {platform.release()}", "cpu": platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "Bilinmiyor"), "gpu": "Bilgi alınamadı"}
            if sys.platform.startswith("win"):
                try:
                    out = run_cmd(["powershell", "-NoProfile", "-Command",
                                   "(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name); "
                                   "((Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name) -join ' + ')"], 15).splitlines()
                    if out and out[0].strip(): info["cpu"] = out[0].strip()
                    if len(out) > 1 and out[1].strip(): info["gpu"] = out[1].strip()[:90]
                except Exception: pass
            try:
                import psutil
                ram = psutil.virtual_memory(); d = psutil.disk_usage(os.path.expanduser("~"))
                info["ram"] = f"{ram.total / 1024**3:.1f} GB (boşta {ram.available / 1024**3:.1f} GB)"
                info["disk"] = f"{d.total / 1024**3:.0f} GB (boş {d.free / 1024**3:.0f} GB)"
            except Exception: info["ram"] = "Bilgi alınamadı"; info["disk"] = "Bilgi alınamadı"
            self.root.after(0, lambda: self._apply_system(info))
        threading.Thread(target=work, daemon=True).start()
    def _apply_system(self, info):
        self.last_system = info
        for k, v in info.items():
            if k in self.sys_labels: self.sys_labels[k].config(text=v)
        self.big_info.config(text="\n".join([f"İşletim sistemi:  {info.get('os','')}", f"İşlemci:  {info.get('cpu','')}",
                                             f"Ekran kartı:  {info.get('gpu','')}", f"RAM:  {info.get('ram','')}", f"Depolama:  {info.get('disk','')}"]))
    def tick_system(self):
        if self.page != "system": return
        try:
            import psutil
            c = psutil.cpu_percent(interval=None); r = psutil.virtual_memory(); d = psutil.disk_usage(os.path.expanduser("~")); b = psutil.sensors_battery()
            self.live["cpu"][0].config(text=f"%{c:.0f}"); self.live["cpu"][1].set(c); self.live["cpu"][2].config(text=f"{psutil.cpu_count()} mantıksal çekirdek")
            self.live["ram"][0].config(text=f"%{r.percent:.0f}"); self.live["ram"][1].set(r.percent); self.live["ram"][2].config(text=f"{(r.total - r.available) / 1024**3:.1f} / {r.total / 1024**3:.1f} GB kullanımda")
            self.live["disk"][0].config(text=f"%{d.percent:.0f}"); self.live["disk"][1].set(d.percent); self.live["disk"][2].config(text=f"{d.free / 1024**3:.0f} GB boş / {d.total / 1024**3:.0f} GB")
            if b: self.live["bat"][0].config(text=f"%{b.percent:.0f}"); self.live["bat"][1].set(b.percent, GREEN if b.percent > 30 else RED); self.live["bat"][2].config(text="Şarj oluyor ⚡" if b.power_plugged else "Pille çalışıyor")
            else: self.live["bat"][0].config(text="—"); self.live["bat"][2].config(text="Pil bulunamadı (masaüstü bilgisayar)")
        except Exception:
            for k in self.live: self.live[k][2].config(text="Canlı bilgi için psutil gerekli")
        self.root.after(2000, self.tick_system)
    def system_summary(self):
        i = self.last_system
        return "\n".join(["Bilgisayarının bilgileri:", f"• İşletim sistemi: {i.get('os','...')}", f"• İşlemci: {i.get('cpu','...')}",
                          f"• RAM: {i.get('ram','...')}", f"• Ekran kartı: {i.get('gpu','...')}", f"• Depolama: {i.get('disk','...')}"])

    # ------------------------------------------------------------ hava durumu
    WCODE = {0: ("Açık", "☀"), 1: ("Çoğunlukla açık", "🌤"), 2: ("Parçalı bulutlu", "⛅"), 3: ("Kapalı", "☁"), 45: ("Sisli", "🌫"), 48: ("Sisli", "🌫"),
             51: ("Hafif çisenti", "🌦"), 53: ("Çisenti", "🌦"), 55: ("Yoğun çisenti", "🌧"), 61: ("Hafif yağmur", "🌧"), 63: ("Yağmurlu", "🌧"),
             65: ("Kuvvetli yağmur", "🌧"), 71: ("Hafif kar", "🌨"), 73: ("Karlı", "❄"), 75: ("Yoğun kar", "❄"), 80: ("Hafif sağanak", "🌦"),
             81: ("Sağanak", "🌧"), 82: ("Şiddetli sağanak", "⛈"), 95: ("Gök gürültülü fırtına", "⛈"), 96: ("Dolu", "⛈"), 99: ("Şiddetli dolu", "⛈")}
    def fetch_weather(self, lat, lon):
        d = http_json(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=1")
        c, day = d["current"], d["daily"]; desc, ico = self.WCODE.get(c["weather_code"], ("Değişken", "🌡"))
        return {"t": f"{c['temperature_2m']:.0f}°", "desc": f"{ico} {desc}",
                "more": f"Hissedilen {c['apparent_temperature']:.0f}°C · Bugün {day['temperature_2m_max'][0]:.0f}° / {day['temperature_2m_min'][0]:.0f}°\nNem %{c['relative_humidity_2m']} · Rüzgâr {c['wind_speed_10m']} km/sa",
                "text": f"{c['temperature_2m']:.0f}°C, {desc}. Hissedilen {c['apparent_temperature']:.0f}°C. Bugün en yüksek {day['temperature_2m_max'][0]:.0f}°, en düşük {day['temperature_2m_min'][0]:.0f}°C."}
    def geocode(self, city):
        r = http_json("https://geocoding-api.open-meteo.com/v1/search?count=1&language=tr&name=" + urllib.parse.quote(city))
        x = r["results"][0]; return x["latitude"], x["longitude"], x["name"]
    def load_weather(self):
        self.w_desc.config(text="Yükleniyor...")
        def work():
            try:
                w = self.fetch_weather(self.cfg["lat"], self.cfg["lon"]); self.weather_text = f"{self.cfg['city']}: " + w["text"]
                self.root.after(0, lambda: (self.w_city.config(text=self.cfg["city"]), self.w_temp.config(text=w["t"]), self.w_desc.config(text=w["desc"]), self.w_more.config(text=w["more"])))
            except Exception:
                self.root.after(0, lambda: (self.w_temp.config(text="--°"), self.w_desc.config(text="Hava durumu alınamadı"), self.w_more.config(text="İnternet bağlantını kontrol et.")))
        threading.Thread(target=work, daemon=True).start()
    def _weather_for(self, city):
        try:
            lat, lon, name = self.geocode(city); w = self.fetch_weather(lat, lon)
            self.reply_async(f"{name} için hava durumu:\n{w['t']}C · {w['desc']}\n{w['more']}")
        except Exception: self.reply_async(f"“{city}” için hava durumunu alamadım. Şehir adını ya da internet bağlantını kontrol eder misin?")

    # -------------------------------------------------------------- notlar
    def write_note(self, note):
        with open(NOTES_FILE, "a", encoding="utf-8") as f: f.write(f"[{datetime.now():%d.%m.%Y %H:%M}] {note}\n")
        self.refresh_notes()
    def read_notes(self):
        try:
            with open(NOTES_FILE, encoding="utf-8") as f: lines = [l.strip() for l in f if l.strip()]
            return "Son notların:\n" + "\n".join("• " + l for l in lines[-8:]) if lines else "Henüz kayıtlı notun yok."
        except Exception: return "Henüz kayıtlı notun yok."
    def refresh_notes(self):
        try:
            with open(NOTES_FILE, encoding="utf-8") as f: lines = [l.strip() for l in f if l.strip()]
            self.notes_list.config(text="\n".join(lines[-3:]) if lines else "Henüz not yok.")
        except Exception: self.notes_list.config(text="Henüz not yok.")
    def save_note(self):
        note = self.note_entry.get().strip()
        if not note: messagebox.showinfo("Notlarım", "Önce bir not yaz."); return
        self.write_note(note); self.note_entry.delete(0, "end"); self.chat.add("ai", "Notunu kaydettim: " + note)
    def focus_note(self): self.note_entry.focus_set()

    # ---------------------------------------------------------------- ayarlar
    def save_settings(self):
        self.cfg["name"] = self.set_name.get().strip() or "Kullanıcı"; self.cfg["lm_url"] = self.set_lm.get().strip().rstrip("/") or DEFAULT_CFG["lm_url"]
        self.side_name.config(text=self.cfg["name"]); city = self.set_city.get().strip()
        def work():
            msg = "Kaydedildi ✓"
            if city and city != self.cfg["city"]:
                try:
                    lat, lon, name = self.geocode(city); self.cfg.update(city=name, lat=lat, lon=lon); self.root.after(0, self.load_weather)
                except Exception: msg = "Kaydedildi, ama şehir bulunamadı."
            save_cfg(self.cfg); self.root.after(0, lambda: (self.set_msg.config(text=msg), self.check_lm()))
            self.root.after(3000, lambda: self.set_msg.config(text=""))
        threading.Thread(target=work, daemon=True).start()

    # --------------------------------------------------------------- LM Studio
    def check_lm(self):
        def work():
            try:
                d = http_json(self.cfg["lm_url"] + "/v1/models", timeout=2); ids = [m["id"] for m in d.get("data", [])]
                self.lm_model = ids[0] if ids else None; self.root.after(0, lambda: self._status(True, self.lm_model or "model yüklü değil"))
            except Exception: self.lm_model = None; self.root.after(0, lambda: self._status(False))
        threading.Thread(target=work, daemon=True).start(); self.root.after(15000, self.check_lm)
    def _status(self, ok, model=""):
        c = GREEN if ok else AMBER
        self.dot.itemconfig(self.dot_id, fill=c); self.status_t.config(text="AI BAĞLI" if ok else "KOMUT MODU", fg=c)
        self.status_s.config(text=("Yerel yapay zekâ: " + model[:28]) if ok else "Komutlara hazır · LM Studio kapalı")
    def ask_local_ai(self, prompt):
        try:
            self.history.append({"role": "user", "content": prompt}); self.history = self.history[-10:]
            msgs = [{"role": "system", "content": "Sen FurkanAI adlı, Türkçe konuşan Windows masaüstü asistanısın. Kısa, samimi ve yardımcı cevap ver."}] + self.history
            d = http_json(self.cfg["lm_url"] + "/v1/chat/completions", json.dumps({"model": self.lm_model or "local-model", "messages": msgs, "temperature": 0.7}).encode(), timeout=60)
            ans = d["choices"][0]["message"]["content"].strip(); self.history.append({"role": "assistant", "content": ans}); return ans
        except Exception:
            if self.history and self.history[-1]["role"] == "user": self.history.pop()
            return None

ASYNC = object()

if __name__ == "__main__":
    root = tk.Tk(); app = FurkanAI(root); root.mainloop()
