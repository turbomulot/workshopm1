"""Schémas du dossier et des slides (matplotlib), en thème clair et sombre.

    .venv\\Scripts\\python livrables\\src\\diagrammes.py

Sortie : livrables/src/build/<nom>_light.png et <nom>_dark.png
Les valeurs (IP, ports, topics, broches) reprennent le dépôt : firmware branche
c_plus_plus, backend/, webcam-detection/, security/ (branche cyber).
"""
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

BUILD = Path(__file__).resolve().parent / "build"
plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans"]
plt.rcParams["svg.fonttype"] = "none"


@dataclass
class Theme:
    name: str
    bg: str
    panel: str
    panel2: str
    border: str
    text: str
    muted: str
    cyan: str
    amber: str
    red: str
    green: str
    violet: str
    wire5v: str
    wire3v3: str
    gnd: str


LIGHT = Theme("light", "#FFFFFF", "#F3F6FA", "#E8EEF6", "#B8C4D6", "#142033", "#56657C",
              "#0B7A99", "#B86200", "#C42B45", "#178A5B", "#6B3FC4", "#D7263D", "#E08A00", "#2B2B2B")
DARK = Theme("dark", "#0A1020", "#111B30", "#16233D", "#2C3E62", "#E7EEF7", "#93A4C0",
             "#22D3EE", "#F5A524", "#FF5D73", "#34D399", "#A78BFA", "#FF5D73", "#F5A524", "#C9D4E5")


def canvas(w, h, T, scale=0.1):
    fig = plt.figure(figsize=(w * scale, h * scale), facecolor=T.bg)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    ax.set_facecolor(T.bg)
    return fig, ax


def save(fig, nom, T, dpi=220):
    BUILD.mkdir(exist_ok=True)
    fig.savefig(BUILD / f"{nom}_{T.name}.png", dpi=dpi, facecolor=T.bg)
    plt.close(fig)


def box(ax, T, x, y, w, h, title=None, lines=(), accent=None, fc=None, fs=7.2, tfs=8.2,
        dashed=False, radius=0.9, lw=1.0, mono=False, center=False, title_color=None):
    accent = accent or T.cyan
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radius}",
                                fc=fc or T.panel, ec=accent if not dashed else T.border, lw=lw,
                                ls=(0, (4, 3)) if dashed else "-", zorder=2))
    ty = y + h - 1.0
    tx = x + w / 2 if center else x + 1.0
    ha = "center" if center else "left"
    if title:
        ax.text(tx, ty, title, color=title_color or (accent if not dashed else T.muted), fontsize=tfs,
                fontweight="bold", va="top", ha=ha, zorder=5)
        ty -= tfs * 0.21
    for line in lines:
        ax.text(tx, ty, line, color=T.text, fontsize=fs, va="top", ha=ha, zorder=5,
                family="Consolas" if mono else None)
        ty -= fs * 0.2


def arrow(ax, T, pts, color=None, both=False, lw=1.3, ls="-", z=3):
    color = color or T.muted
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=color, lw=lw, ls=ls, zorder=z, solid_capstyle="round")
    props = dict(arrowstyle="-|>", color=color, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=9)
    ax.annotate("", xy=pts[-1], xytext=pts[-2], arrowprops=props, zorder=z)
    if both:
        ax.annotate("", xy=pts[0], xytext=pts[1], arrowprops=dict(props), zorder=z)


def badge(ax, T, x, y, n, color=None):
    ax.add_patch(Circle((x, y), 1.05, fc=color or T.amber, ec=T.bg, lw=1.0, zorder=6))
    ax.text(x, y - 0.05, str(n), color=T.bg, fontsize=6.6, fontweight="bold", ha="center", va="center", zorder=7)


def label(ax, T, x, y, text, color=None, fs=6.6, ha="center", va="bottom", bold=False, bgc=None):
    ax.text(x, y, text, color=color or T.muted, fontsize=fs, ha=ha, va=va, zorder=6,
            fontweight="bold" if bold else None,
            bbox=dict(fc=bgc, ec="none", pad=0.6) if bgc else None)


# ---------------------------------------------------------------------------
def architecture(T):
    fig, ax = canvas(80, 64, T)
    # Boîtier
    box(ax, T, 1.5, 24, 19.5, 18, "Boîtier SENTINEL-X", [
        "ESP8266 NodeMCU v2 (Lolin)", "DHT22 · MQ-2 · PIR HC-SR501", "OLED 0,96\" I2C (SSD1306)",
        "Buzzer · LED rouge · LED verte", "Firmware C++ / PlatformIO", "IP réservée 10.10.11.10"], accent=T.amber)
    box(ax, T, 1.5, 9, 19.5, 11, "Poste superviseur / jury", [
        "Navigateur (dashboard React)", "HTTPS + identifiant", "DHCP 10.10.11.100-150"], accent=T.violet)
    # PC serveur
    box(ax, T, 25, 6.5, 53.5, 50, "PC Serveur Local — PC portable apprenant (option B)", [],
        accent=T.cyan, fc=T.bg, lw=1.6, tfs=8.8)
    label(ax, T, 26, 52.4, "10.10.11.1 · Intel Core Ultra 7 155U · 16 Go · webcam USB branchée en direct",
          ha="left", va="top", fs=6.6)
    box(ax, T, 27, 42, 24, 8, "wlan0 · point d'accès Wi-Fi", ["hostapd WPA2 · dnsmasq DHCP/DNS", "chrony NTP · ap_isolate"],
        accent=T.green)
    box(ax, T, 53, 42, 23.5, 8, "Pare-feu UFW (deny par défaut)", ["entrants : 443, 8883 (+22 limit)", "routage refusé (pas de NAT)"],
        accent=T.red)
    box(ax, T, 27, 8.5, 31.5, 31.5, "Docker Compose · réseau interne", [], dashed=True, fc=T.bg)
    box(ax, T, 29, 27, 12, 10, "Mosquitto 2", ["MQTTS :8883", "TLS 1.2 · ACL", "anonymes refusés"])
    box(ax, T, 45, 27, 12, 10, "API Node.js 20", ["Express + socket.io", "127.0.0.1:3000", "user node, ro"])
    box(ax, T, 29, 11, 12, 12, "Caddy (HTTPS)", [":443 · certificat web", "dashboard statique", "/api · /socket.io", "/vision → :5001"])
    box(ax, T, 45, 11, 12, 12, "PostgreSQL 16", ["api_measurements", "api_alerts", "non publié"])
    box(ax, T, 60.5, 8.5, 16, 31.5, "Processus hôte (Python)", [], dashed=True, fc=T.bg)
    box(ax, T, 62, 32, 13, 6, "Webcam USB", ["UVC · 1280×720 MJPG"], accent=T.amber)
    box(ax, T, 62, 21, 13, 9, "Vision YOLOv8n", ["Flask 127.0.0.1:5001", "640×480 · conf 0,5"], accent=T.violet)
    box(ax, T, 62, 10.5, 13, 9, "IA prédictive", ["Isolation Forest", "scikit-learn"], accent=T.violet)

    arrow(ax, T, [(21, 33), (29, 33)], T.amber, lw=1.6); badge(ax, T, 24.5, 34.8, 1)
    arrow(ax, T, [(41, 33), (45, 33)], T.cyan, both=True); badge(ax, T, 43, 35.3, 2)
    arrow(ax, T, [(51, 27), (51, 23)], T.cyan, both=True); badge(ax, T, 53, 25, 3)
    arrow(ax, T, [(21, 15), (29, 15)], T.violet, both=True, lw=1.6); badge(ax, T, 24.5, 16.8, 4)
    arrow(ax, T, [(41, 19), (43, 19), (43, 29.5), (45, 29.5)], T.violet); badge(ax, T, 43, 24.5, 5)
    arrow(ax, T, [(62, 25), (59.5, 25), (59.5, 31), (57, 31)], T.violet); badge(ax, T, 59.5, 27.5, 6)
    arrow(ax, T, [(57, 15), (62, 15)], T.violet); badge(ax, T, 59.5, 17, 7)
    arrow(ax, T, [(68.5, 32), (68.5, 30)], T.amber); badge(ax, T, 71, 31, 8)

    legend = [
        (1, "ESP8266 → broker : MQTTS 8883 (sentinel/sensors, alerts) ; ← sentinel/cmd"),
        (2, "Broker ↔ API : MQTTS, compte « api », CA du groupe"),
        (3, "API ↔ PostgreSQL : SQL paramétré, réseau Docker uniquement"),
        (4, "Navigateur ↔ Caddy : HTTPS 443 (dashboard, REST, socket.io)"),
        (5, "Caddy → API : reverse proxy vers 127.0.0.1:3000"),
        (6, "Vision → API : POST /api/v1/alerts (source « vision »)"),
        (7, "PostgreSQL → IA prédictive : dump / CSV → scores d'anomalie"),
        (8, "Webcam USB → vision : capture directe sur le PC serveur"),
    ]
    for i, (n, t) in enumerate(legend):
        cx = 3 if i < 4 else 42
        cy = 5.2 - (i % 4) * 1.5
        badge(ax, T, cx, cy, n)
        ax.text(cx + 1.7, cy, t, color=T.text, fontsize=6.3, va="center")
    save(fig, "architecture", T)


def reseau(T):
    fig, ax = canvas(80, 50, T)
    box(ax, T, 1.5, 3, 20, 44, "Hors périmètre (non routé)", [], dashed=True, fc=T.bg)
    box(ax, T, 3, 31, 17, 11, "Réseau campus EPSI", ["Wi-Fi / Ethernet école", "Internet (mises à jour)", "eth0 / wlan1 en DHCP"],
        accent=T.muted)
    box(ax, T, 3, 15, 17, 12, "Autres tables", ["10.10.<n>.0/24 par groupe", "AP propres à chaque groupe", "aucun flux autorisé", "vers notre table"],
        accent=T.muted)
    box(ax, T, 3, 5, 17, 7, "Isolation", ["ip_forward = 0", "ufw default deny routed"], accent=T.red)

    box(ax, T, 27, 9, 24, 32, "PC serveur · 10.10.11.1/24", [
        "wlan0 = point d'accès de table", "hostapd : SSID SENTINELX-G11", "WPA2-PSK (CCMP), canal fixe",
        "ap_isolate = 1 (clients isolés)", "dnsmasq : DHCP + DNS local", "chrony : NTP pour l'ESP8266",
        "UFW : 443, 8883, 67, 53, 123", "(+22 limit, clés uniquement)", "", "Docker : ports publiés", "sur 10.10.11.1 uniquement"],
        accent=T.cyan, fs=7.0)
    box(ax, T, 56, 3, 22.5, 44, "Réseau de table 10.10.11.0/24", [], dashed=True, fc=T.bg)
    label(ax, T, 57.2, 43.6, "masque 255.255.255.0 · 254 hôtes · broadcast .255", ha="left", va="top", fs=6.2)
    box(ax, T, 58, 31, 19, 9.5, "Boîtier ESP8266", ["10.10.11.10 (réservation MAC)", "client MQTTS → .1:8883", "NTP → .1:123"], accent=T.amber)
    box(ax, T, 58, 18.5, 19, 9.5, "Poste superviseur", ["DHCP .100 → .150", "HTTPS → .1:443"], accent=T.violet)
    box(ax, T, 58, 6, 19, 9.5, "Poste de contrôle", ["DHCP .100 → .150", "vérification défensive", "(audit de notre table)"], accent=T.green)

    arrow(ax, T, [(58, 35.5), (51, 35.5)], T.amber, lw=1.6); label(ax, T, 54.5, 36.0, "8883/tcp", T.amber, bold=True)
    arrow(ax, T, [(58, 23), (51, 23)], T.violet, lw=1.6); label(ax, T, 54.5, 23.5, "443/tcp", T.violet, bold=True)
    arrow(ax, T, [(58, 11), (51, 11)], T.green, lw=1.2, ls=(0, (3, 2))); label(ax, T, 54.5, 11.5, "contrôle", T.green)
    # lien campus coupé
    ax.plot([20, 27], [36, 36], color=T.muted, lw=1.2, ls=(0, (3, 2)), zorder=3)
    ax.plot([20, 27], [20, 20], color=T.muted, lw=1.2, ls=(0, (3, 2)), zorder=3)
    for yy in (36, 20):
        ax.plot([22.6, 24.4], [yy - 1.1, yy + 1.1], color=T.red, lw=2, zorder=4)
        ax.plot([22.6, 24.4], [yy + 1.1, yy - 1.1], color=T.red, lw=2, zorder=4)
    label(ax, T, 23.5, 37.4, "pas de routage", T.red, fs=6.0)
    label(ax, T, 23.5, 21.4, "pas de pont", T.red, fs=6.0)
    save(fig, "reseau", T)


def cablage(T):
    fig, ax = canvas(80, 66, T)
    bx, by, bw, bh = 31, 12, 17, 44
    ax.add_patch(FancyBboxPatch((bx, by), bw, bh, boxstyle="round,pad=0,rounding_size=1.2",
                                fc="#1D3B6E" if T.name == "light" else "#14305C", ec=T.cyan, lw=1.4, zorder=2))
    ax.add_patch(Rectangle((bx + 4.5, by + bh - 7), 8, 6, fc="#C9CED6", ec="#7D8796", lw=0.8, zorder=3))
    ax.text(bx + 8.5, by + bh - 4, "ESP-12E", fontsize=6.2, ha="center", va="center", color="#1B2433", zorder=4)
    ax.text(bx + bw / 2, by + 20, "NodeMCU v2\n(Lolin v3)", fontsize=7.4, ha="center", va="center",
            color="#E7EEF7", fontweight="bold", zorder=4)
    ax.add_patch(Rectangle((bx + 6, by - 0.6), 5, 2.4, fc="#9AA3AF", ec="#5F6B7A", zorder=3))
    ax.text(bx + 8.5, by + 2.8, "micro-USB 5 V", fontsize=5.6, ha="center", color="#C9D4E5", zorder=4)
    left = ["A0", "G", "VU", "SD3", "SD2", "SD1", "CMD", "SD0", "CLK", "GND", "3V3", "EN", "RST", "GND", "VIN"]
    right = ["D0", "D1", "D2", "D3", "D4", "3V3", "GND", "D5", "D6", "D7", "D8", "RX", "TX", "GND", "3V3"]
    used_l = {0, 1, 2, 9, 10}
    used_r = {1, 2, 3, 4, 7, 8, 10}
    yL, yR = {}, {}
    for i, (l, r) in enumerate(zip(left, right)):
        y = by + bh - 9.5 - i * 2.35
        for name, x, ha, side, used in ((l, bx, "left", "L", used_l), (r, bx + bw, "right", "R", used_r)):
            on = i in used
            ax.add_patch(Circle((x, y), 0.45, fc=T.amber if on else "#8892A0", ec="none", zorder=4))
            ax.text(x + (0.9 if side == "L" else -0.9), y, name, fontsize=5.6, ha=ha, va="center",
                    color="#FFFFFF" if on else "#AEB8C6", zorder=4, fontweight="bold" if on else None)
        yL.setdefault(l, y)
        yR.setdefault(r, y)
        yL[f"{l}#{i}"] = y
        yR[f"{r}#{i}"] = y
    GNDC = "#555E6B"

    def net(x, y, txt, color, side="right"):
        w = 0.75 * len(txt) + 1.2
        x0 = x if side == "right" else x - w
        ax.add_patch(FancyBboxPatch((x0, y - 0.75), w, 1.5, boxstyle="round,pad=0,rounding_size=0.4",
                                    fc=color, ec="none", zorder=5))
        ax.text(x0 + w / 2, y, txt, fontsize=5.4, ha="center", va="center", color="#FFFFFF", fontweight="bold", zorder=6)

    def comp(x, y, w, h, title, pins, accent, side):
        box(ax, T, x, y, w, h, title, [], accent=accent, tfs=7.2)
        pos = {}
        for k, p in enumerate(pins):
            py = y + h - 3.2 - k * 1.9
            px = x + w if side == "right" else x
            ax.add_patch(Circle((px, py), 0.35, fc=accent, ec="none", zorder=4))
            ax.text(px + (-0.8 if side == "right" else 0.8), py, p, fontsize=5.6, va="center",
                    ha="right" if side == "right" else "left", color=T.text, zorder=5)
            pos[p] = py
        return pos

    def resistor(x, y, txt, vertical=False):
        if vertical:
            ax.add_patch(Rectangle((x - 0.55, y - 1.4), 1.1, 2.8, fc=T.bg, ec=T.text, lw=0.9, zorder=5))
            ax.text(x + 0.9, y, txt, fontsize=5.4, va="center", color=T.text, zorder=6)
        else:
            ax.add_patch(Rectangle((x - 1.4, y - 0.55), 2.8, 1.1, fc=T.bg, ec=T.text, lw=0.9, zorder=5))
            ax.text(x, y + 0.9, txt, fontsize=5.4, ha="center", color=T.text, zorder=6)

    W = dict(lw=1.15, zorder=3, solid_capstyle="round")

    def wire(pts, color):
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=color, **W)

    # --- Gauche : MQ-2 et pont diviseur (AO 0-5 V -> A0 0-3,3 V)
    mq = comp(2, 46.9, 12, 12, "MQ-2 (gaz)", ["VCC", "GND", "DO", "AO"], T.red, "right")
    net(14.8, mq["VCC"], "5V (VU)", T.wire5v)
    net(14.8, mq["GND"], "GND", GNDC)
    ax.text(15.0, mq["DO"], "non câblé", fontsize=5.2, va="center", color=T.muted)
    ya = mq["AO"]
    wire([(14, ya), (17.1, ya)], T.red)
    resistor(18.5, ya, "R1 10 kΩ")
    wire([(19.9, ya), (24, ya), (24, yL["A0"]), (bx, yL["A0"])], T.red)
    ax.add_patch(Circle((24, ya), 0.4, fc=T.red, zorder=5))
    wire([(24, ya), (24, ya + 1.0)], T.red)
    resistor(24, ya + 2.4, "R2 20 kΩ", vertical=True)
    wire([(24, ya + 3.8), (24, ya + 4.6)], T.red)
    net(22.3, ya + 5.4, "GND", GNDC)
    label(ax, T, 2, 39.4, "Pont diviseur : 5 V × 20/(10+20) = 3,3 V max", T.text, fs=5.8, ha="left", va="top")
    label(ax, T, 2, 37.7, "sur A0 (ADC NodeMCU 0-3,3 V → 0-1023)", T.muted, fs=5.6, ha="left", va="top")
    for key, txt, col in (("VU", "5V USB", T.wire5v), ("G", "GND", GNDC), ("3V3", "3V3", T.wire3v3), ("GND#13", "GND", GNDC)):
        wire([(bx - 3.2, yL[key]), (bx, yL[key])], col)
        net(bx - 3.2, yL[key], txt, col, side="left")
    box(ax, T, 2, 4, 21, 17, "Alimentation", [
        "USB 5 V (≥ 1 A) → VU / VIN", "Régulateur 3,3 V intégré", "MQ-2 : chauffe ≈ 150 mA en 5 V",
        "PIR : 5 V (sortie 3,3 V TTL)", "DHT22, OLED : 3,3 V", "Masse commune à tous les modules"],
        accent=T.wire5v, fs=6.0, tfs=7.2)

    # --- Droite : un trajet en L par signal, sans croisement
    xr = bx + bw
    oled = comp(66, 55, 12.5, 10, "OLED SSD1306", ["SCL", "SDA", "VCC", "GND"], T.cyan, "left")
    wire([(xr, yR["D1"]), (57, yR["D1"]), (57, oled["SCL"]), (66, oled["SCL"])], T.cyan)
    wire([(xr, yR["D2"]), (59, yR["D2"]), (59, oled["SDA"]), (66, oled["SDA"])], T.green)
    net(65.7, oled["VCC"], "3V3", T.wire3v3, side="left")
    net(65.7, oled["GND"], "GND", GNDC, side="left")
    label(ax, T, 72.2, 54.4, "I2C adresse 0x3C", T.muted, fs=5.6, va="top")

    bz = comp(66, 33.5, 12.5, 8, "Buzzer piézo", ["− (NPN)", "+"], T.amber, "left")
    yb = bz["− (NPN)"]
    wire([(xr, yR["D3"]), (55, yR["D3"]), (55, yb), (58.1, yb)], T.amber)
    resistor(59.5, yb, "1 kΩ")
    wire([(60.9, yb), (62, yb)], T.amber)
    ax.add_patch(Circle((63.2, yb), 1.2, fc=T.bg, ec=T.text, lw=0.9, zorder=5))
    ax.text(63.2, yb, "NPN", fontsize=4.6, ha="center", va="center", color=T.text, zorder=6)
    wire([(64.4, yb), (66, yb)], T.amber)
    label(ax, T, 61.6, yb - 1.5, "2N2222, E → GND", T.muted, fs=5.0, va="top")
    net(78.0, bz["+"], "5V", T.wire5v, side="left")

    lr = comp(66, 25, 12.5, 6.5, "LED rouge", ["A", "K"], T.red, "left")
    wire([(xr, yR["D4"]), (57, yR["D4"]), (57, lr["A"]), (59.1, lr["A"])], T.red)
    resistor(60.5, lr["A"], "220 Ω")
    wire([(61.9, lr["A"]), (66, lr["A"])], T.red)
    net(78.0, lr["K"], "GND", GNDC, side="left")

    pir = comp(66, 16, 12.5, 8, "PIR HC-SR501", ["OUT", "VCC", "GND"], T.violet, "left")
    wire([(xr, yR["D5"]), (55, yR["D5"]), (55, pir["OUT"]), (66, pir["OUT"])], T.violet)
    net(78.0, pir["VCC"], "5V", T.wire5v, side="left")
    net(78.0, pir["GND"], "GND", GNDC, side="left")

    dht = comp(66, 7, 12.5, 8, "DHT22", ["DATA", "VCC", "GND"], T.green, "left")
    wire([(xr, yR["D6"]), (53, yR["D6"]), (53, dht["DATA"]), (66, dht["DATA"])], T.green)
    net(78.0, dht["VCC"], "3V3", T.wire3v3, side="left")
    net(78.0, dht["GND"], "GND", GNDC, side="left")
    ax.add_patch(Circle((60.5, dht["DATA"]), 0.4, fc=T.green, zorder=5))
    wire([(60.5, dht["DATA"]), (60.5, dht["DATA"] + 1.2)], T.green)
    resistor(60.5, dht["DATA"] + 2.6, "10 kΩ", vertical=True)
    net(59.0, dht["DATA"] + 4.9, "3V3", T.wire3v3)

    lv = comp(66, 0.6, 12.5, 6, "LED verte", ["A", "K"], T.green, "left")
    wire([(xr, yR["D8"]), (51, yR["D8"]), (51, lv["A"]), (59.1, lv["A"])], T.green)
    resistor(60.5, lv["A"], "220 Ω")
    wire([(61.9, lv["A"]), (66, lv["A"])], T.green)
    net(78.0, lv["K"], "GND", GNDC, side="left")
    save(fig, "cablage", T)


def flux(T):
    fig, ax = canvas(80, 46, T)
    cols = [(1, 11, "ESP8266", T.amber), (23, 33, "Mosquitto", T.cyan), (45, 56, "API Node.js", T.cyan),
            (68, 79, "Dashboard", T.violet)]
    for x0, x1, t, c in cols:
        box(ax, T, x0, 9.5, x1 - x0, 34, t, [], accent=c, center=True)
    box(ax, T, 45, 1.0, 11, 6.2, "PostgreSQL", ["api_* (2 tables)"], accent=T.cyan, center=True)
    box(ax, T, 68, 1.0, 11, 6.2, "Vision YOLO", ["Flask :5001"], accent=T.violet, center=True)
    arrow(ax, T, [(50.5, 9.5), (50.5, 7.2)], T.cyan, both=True)
    rows = [
        (37, [(11, 23, "sentinel/sensors", "JSON toutes les 2 s", T.amber),
              (33, 45, "abonnement sentinel/#", "QoS 1", T.cyan),
              (56, 68, "socket.io « sensors »", "temps réel", T.violet)]),
        (30, [(11, 23, "sentinel/alerts", "gas / motion", T.amber),
              (33, 45, "handleAlert()", "type + level", T.cyan),
              (56, 68, "socket.io « alert »", "liste d'alertes", T.violet)]),
        (23, [(68, 56, "GET /api/v1/history", "/status · /alerts", T.violet)]),
        (16, [(68, 56, "POST /api/v1/commands", "{buzzer, led}", T.red),
              (45, 33, "publish sentinel/cmd", "QoS 1", T.red),
              (23, 11, "receptionCommande()", "buzzer · LED R/V", T.red)]),
    ]
    for y, segs in rows:
        for x0, x1, t1, t2, c in segs:
            arrow(ax, T, [(x0, y), (x1, y)], c, lw=1.4)
            label(ax, T, (x0 + x1) / 2, y + 0.5, t1, T.text, fs=6.1, bold=True)
            label(ax, T, (x0 + x1) / 2, y - 0.5, t2, T.muted, fs=5.8, va="top")
    arrow(ax, T, [(68, 4.1), (56, 4.1)], T.violet, lw=1.4)
    label(ax, T, 62, 4.6, "POST /api/v1/alerts", T.text, fs=6.1, bold=True)
    label(ax, T, 62, 3.6, "source « vision »", T.muted, fs=5.8, va="top")
    label(ax, T, 6, 7.6, "OLED local", T.muted, fs=6.0, va="top")
    label(ax, T, 6, 6.3, "Gaz · Hum · Tmp · Mvt", T.muted, fs=5.8, va="top")
    save(fig, "flux", T)


def bdd(T):
    fig, ax = canvas(80, 30, T)

    def table(x, y, w, title, cols, accent):
        h = 2.6 + 1.55 * len(cols)
        box(ax, T, x, y - h, w, h, title, [], accent=accent, tfs=7.4)
        for k, (n, t, key) in enumerate(cols):
            yy = y - 3.4 - k * 1.55
            ax.text(x + 1, yy, n, fontsize=6.2, va="center", color=accent if key else T.text,
                    fontweight="bold" if key else None, family="Consolas")
            ax.text(x + w - 1, yy, t, fontsize=5.8, va="center", ha="right", color=T.muted, family="Consolas")
        return y - h

    box(ax, T, 1, 1, 37, 28, "PostgreSQL 16 (conteneur db)", [], dashed=True, fc=T.bg)
    table(2.5, 25.5, 16, "api_measurements", [("id", "BIGSERIAL PK", 1), ("ts", "TIMESTAMPTZ", 0), ("temp", "DOUBLE", 0),
                                              ("hum", "DOUBLE", 0), ("gas", "INTEGER", 0), ("pir", "SMALLINT", 0)], T.cyan)
    table(20.5, 25.5, 16, "api_alerts", [("id", "BIGSERIAL PK", 1), ("ts", "TIMESTAMPTZ", 0), ("source", "TEXT", 0),
                                        ("type", "TEXT", 0), ("level", "TEXT", 0), ("value", "JSONB", 0)], T.amber)
    label(ax, T, 2.5, 13.2, "Index : ts DESC sur les deux tables", T.muted, fs=6.0, ha="left", va="top")
    label(ax, T, 2.5, 11.4, "source ∈ {esp8266, vision} · level ∈ {info, warn, critical}", T.muted, fs=6.0, ha="left", va="top")
    label(ax, T, 2.5, 9.6, "Accès : compte sentinel, mot de passe en secret Docker", T.muted, fs=6.0, ha="left", va="top")
    label(ax, T, 2.5, 7.8, "Exports : pg_dump → backend/dumps/ → IA prédictive", T.muted, fs=6.0, ha="left", va="top")

    box(ax, T, 41, 1, 38, 28, "SQLite vision (.data/badges.sqlite3)", [], dashed=True, fc=T.bg)
    table(42.5, 25.5, 17, "employees", [("id", "TEXT PK", 1), ("first_name", "TEXT", 0), ("last_name", "TEXT", 0),
                                       ("photo", "TEXT", 0), ("active", "INTEGER", 0), ("badge_token", "TEXT UQ", 0),
                                       ("created_at", "TEXT", 0)], T.violet)
    table(61, 25.5, 16.5, "events", [("id", "INTEGER PK", 1), ("timestamp", "TEXT", 0), ("employee_id", "TEXT", 0),
                                     ("result", "TEXT", 0), ("source", "TEXT", 0)], T.violet)
    table(61, 14.6, 16.5, "face_embeddings", [("id", "INTEGER PK", 1), ("employee_id", "FK", 0), ("model", "TEXT", 0),
                                              ("embedding", "BLOB", 0)], T.violet)
    arrow(ax, T, [(59.5, 23), (61, 23)], T.violet)
    arrow(ax, T, [(59.5, 13.5), (61, 13.5)], T.violet)
    save(fig, "bdd", T)


def pki(T):
    fig, ax = canvas(80, 30, T)
    box(ax, T, 1, 10, 19, 13, "CA du groupe", ["« SentinelX G11 CA »", "ECDSA P-256 · 90 jours", "ca.key → clé USB", "(supprimée du PC)"], accent=T.amber)
    box(ax, T, 29, 18, 21, 10, "broker.crt / .key", ["30 jours · serverAuth", "SAN : IP 10.10.11.1,", "mosquitto, localhost"], accent=T.cyan)
    box(ax, T, 29, 3, 21, 10, "web.crt / .key", ["30 jours · serverAuth", "SAN : IP 10.10.11.1,", "localhost"], accent=T.cyan)
    box(ax, T, 59, 21, 20, 7.5, "Mosquitto :8883", ["TLS 1.2 minimum"], accent=T.cyan)
    box(ax, T, 59, 3, 20, 7.5, "Caddy :443", ["HTTPS dashboard / API"], accent=T.cyan)
    box(ax, T, 59, 12, 20, 7.5, "Clients (ca.crt)", ["ESP8266 BearSSL · API", "navigateur superviseur"], accent=T.green)
    arrow(ax, T, [(20, 19), (24, 19), (24, 23), (29, 23)], T.amber)
    arrow(ax, T, [(20, 14), (24, 14), (24, 8), (29, 8)], T.amber)
    label(ax, T, 24.5, 24.0, "signe", T.amber, fs=6.0)
    arrow(ax, T, [(50, 24.7), (59, 24.7)], T.cyan)
    arrow(ax, T, [(50, 6.7), (59, 6.7)], T.cyan)
    arrow(ax, T, [(20, 11.3), (26, 11.3), (26, 15.7), (59, 15.7)], T.green, ls=(0, (3, 2)))
    label(ax, T, 54.5, 16.2, "ca.crt distribuée", T.green, fs=6.0)
    label(ax, T, 54.5, 14.6, "(clé USB, jamais Git)", T.muted, fs=5.6, va="top")
    save(fig, "pki", T)


def pipeline(T, nom, etapes, accent_last=None, h=17):
    fig, ax = canvas(80, h, T)
    n = len(etapes)
    gap = 1.6
    w = (78 - gap * (n - 1)) / n
    for i, (titre, lignes, c) in enumerate(etapes):
        x = 1 + i * (w + gap)
        box(ax, T, x, 1.2, w, h - 2.4, titre, lignes, accent=c, fs=6.1, tfs=7.0)
        if i < n - 1:
            arrow(ax, T, [(x + w, h / 2), (x + w + gap, h / 2)], T.muted, lw=1.2)
    save(fig, nom, T)


def vision(T):
    pipeline(T, "vision", [
        ("Webcam USB", ["1280×720 MJPG", "fil de capture", "tampon 1 image"], T.amber),
        ("Pré-traitement", ["cv2.resize", "→ 640×480", "QR sur 1280×720"], T.cyan),
        ("YOLOv8n", ["classe 0 (personne)", "conf ≥ 0,5", "4 threads CPU"], T.violet),
        ("Décision", ["présence / zone libre", "rappel toutes 5 s", "anti-spam"], T.violet),
        ("Exposition", ["/video MJPEG", "/status · /logs", "127.0.0.1:5001"], T.cyan),
        ("Backend", ["POST /api/v1/alerts", "source « vision »", "→ socket.io"], T.green),
    ])


def prédictif(T):
    pipeline(T, "predictif", [
        ("Mesures", ["api_measurements", "1 mesure / 2 s", "pg_dump"], T.amber),
        ("Extraction", ["extraire_dump.py", "COPY → CSV", "sans PostgreSQL"], T.cyan),
        ("Sessions", ["coupure > 10 s", "= nouvelle session", "interpolation"], T.cyan),
        ("10 variables", ["valeur, vitesse/s", "agitation 10 s", "PIR fréquence 30 s"], T.violet),
        ("Modèle", ["StandardScaler", "IsolationForest", "200 arbres · 5 %"], T.violet),
        ("Sortie", ["score + anomalie", "périodes groupées", "modele.joblib"], T.green),
    ])


def sensibilite(T):
    m = json.loads((BUILD / "ia_metrics.json").read_text(encoding="utf-8"))["injection"]["sensibilite"]
    fig, ax = plt.subplots(figsize=(7.6, 3.2), facecolor=T.bg)
    ax.set_facecolor(T.bg)
    import numpy as np
    x = np.arange(len(m))
    series = [("Seuil statique (temp > 40 ou gaz > 400)", "statique", T.muted),
              ("Isolation Forest (version équipe)", "v1", T.cyan),
              ("Isolation Forest + tendances 60 s", "v2", T.violet)]
    for k, (lab, key, c) in enumerate(series):
        vals = [e[key] for e in m]
        bars = ax.bar(x + (k - 1) * 0.26, vals, 0.24, color=c, label=lab)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.08, str(v), ha="center", va="bottom", fontsize=8, color=T.text)
    ax.set_xticks(x, [f"×{e['facteur']}\n+{str(e['delta_temp']).replace('.', ',')} °C · +{e['delta_gas']} gaz"
                      for e in m], fontsize=8, color=T.text)
    ax.set_ylim(0, 7.2)
    ax.set_ylabel("dérives détectées / 6", color=T.text, fontsize=8.5)
    ax.tick_params(colors=T.text, labelsize=8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(T.border)
    ax.grid(axis="y", color=T.border, lw=0.5, alpha=0.6)
    ax.set_axisbelow(True)
    ax.legend(fontsize=7.5, frameon=False, labelcolor=T.text, loc="upper left")
    fig.tight_layout()
    fig.savefig(BUILD / f"sensibilite_{T.name}.png", dpi=220, facecolor=T.bg)
    plt.close(fig)


def main():
    for T in (LIGHT, DARK):
        architecture(T)
        reseau(T)
        cablage(T)
        flux(T)
        bdd(T)
        pki(T)
        vision(T)
        prédictif(T)
        sensibilite(T)
    print("Schémas écrits dans", BUILD)


if __name__ == "__main__":
    main()
