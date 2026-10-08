"""Génère livrables/Workshop2026-M1-GX-Dossier.pdf (rapport d'ingénierie + poster A3).

    .venv\\Scripts\\python livrables\\src\\build_dossier.py

Prérequis : analyse_ia.py puis diagrammes.py (images et chiffres dans build/).
"""
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, NextPageTemplate, PageBreak, PageTemplate, Paragraph,
                                Spacer)
from reportlab.platypus.tableofcontents import TableOfContents

from pdf_kit import (AMBER, CYAN, GREEN, INK, LINE, MUTED, NAVY, RED, S, Heading, P, TocMarker, bullets, callout,
                     code, figure, table, todo)

SRC = Path(__file__).resolve().parent
BUILD = SRC / "build"
OUT = SRC.parent / "Workshop2026-M1-GX-Dossier.pdf"
M = json.loads((BUILD / "ia_metrics.json").read_text(encoding="utf-8"))
GROUPE = "GX"


def img(nom, theme="light"):
    return BUILD / f"{nom}_{theme}.png"


def fr(x, nd=1):
    return f"{x:,.{nd}f}".replace(",", " ").replace(".", ",")


def nb(x):
    return f"{x:,}".replace(",", " ")


# ---------------------------------------------------------------------------
# Gabarit de document
class Dossier(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=20 * mm,
                         bottomMargin=18 * mm, title=f"Workshop2026-M1-{GROUPE} — Dossier technique SENTINEL-X",
                         author=f"Consortium {GROUPE} — EPSI Mastère 1", subject="Mission SENTINEL-X, option B",
                         creator="livrables/src/build_dossier.py")
        w, h = A4
        corps = Frame(self.leftMargin, self.bottomMargin, w - 36 * mm, h - 38 * mm, id="corps")
        plein = Frame(0, 0, w, h, id="plein", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        poster = Frame(0, 0, A3[0], A3[1], id="poster")
        self.addPageTemplates([
            PageTemplate("garde", [plein], onPage=page_garde, pagesize=A4),
            PageTemplate("corps", [corps], onPage=entete, pagesize=A4),
            PageTemplate("poster", [poster], onPage=dessiner_poster, pagesize=A3),
        ])

    def afterFlowable(self, flowable):
        if hasattr(flowable, "toc_level"):
            self.notify("TOCEntry", (flowable.toc_level, flowable.toc_text, self.page))


def page_garde(c, doc):
    w, h = A4
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(0, 0, w, h, stroke=0, fill=1)
    # motif « circuit »
    c.setStrokeColor(colors.HexColor("#1B2A4A"))
    c.setLineWidth(0.8)
    for i in range(14):
        y = h - 70 - i * 22
        x0 = w - 250 + (i % 3) * 18
        c.line(x0, y, w - 40, y)
        c.circle(x0, y, 2.2, stroke=1, fill=0)
    c.setFillColor(colors.HexColor("#22D3EE"))
    c.setFont("Body-Bold", 9.5)
    c.drawString(22 * mm, h - 32 * mm, "AETHERCORP INDUSTRIAL SOLUTIONS  ·  EPSI WORKSHOP NATIONAL BAC+4  ·  2026-27")
    c.setFillColor(colors.white)
    c.setFont("Body-Bold", 50)
    c.drawString(22 * mm, h - 92 * mm, "SENTINEL-X")
    c.setFont("Body", 17)
    c.setFillColor(colors.HexColor("#C9D4E5"))
    c.drawString(22 * mm, h - 104 * mm, "L'avant-poste industriel du futur")
    c.setFillColor(colors.HexColor("#F5A524"))
    c.setFont("Body-Semi", 13)
    c.drawString(22 * mm, h - 122 * mm, "Rapport d'ingénierie technique")
    c.setFillColor(colors.HexColor("#93A4C0"))
    c.setFont("Body", 10.5)
    lignes = ["Schéma réseau · câblage électronique · matrice de sécurité",
              "documentation IA · gabarit d'audit de sécurité · MCO · poster A3"]
    for i, l in enumerate(lignes):
        c.drawString(22 * mm, h - 131 * mm - i * 14, l)
    # cartouche
    y0 = 52 * mm
    c.setStrokeColor(colors.HexColor("#2C3E62"))
    c.setFillColor(colors.HexColor("#111B30"))
    c.roundRect(22 * mm, y0, w - 44 * mm, 66 * mm, 8, stroke=1, fill=1)
    infos = [("Livrable", f"Workshop2026-M1-{GROUPE}-Dossier.pdf"),
             ("Consortium", f"Groupe {GROUPE}  —  numéro à confirmer (kit cyber : g11)"),
             ("Variante", "Option B — topologie Edge-to-Server, PC portable d'un apprenant"),
             ("Membres", "[À COMPLÉTER : prénom NOM — filière, ×4 à 6]"),
             ("Version", "v1.0 — jeudi 8 octobre 2026 (gel du code)"),
             ("Dépôt", "github.com/turbomulot/… — branches nino, backend, c_plus_plus, cyber, IA-*")]
    for i, (k, v) in enumerate(infos):
        yy = y0 + 66 * mm - 14 * mm - i * 9 * mm
        c.setFillColor(colors.HexColor("#22D3EE"))
        c.setFont("Body-Bold", 9)
        c.drawString(28 * mm, yy, k.upper())
        c.setFillColor(colors.HexColor("#F5A524") if "COMPLÉTER" in v else colors.white)
        c.setFont("Body", 10)
        c.drawString(62 * mm, yy, v)
    c.setFillColor(colors.HexColor("#93A4C0"))
    c.setFont("Body-Italic", 9)
    c.drawString(22 * mm, 30 * mm, "« Sentinel-X : la sécurité à la bordure. »")
    c.setFont("Body", 8)
    c.drawString(22 * mm, 22 * mm, "Les encadrés orange [À COMPLÉTER] signalent les informations à renseigner par l'équipe "
                                   "(résultats d'audit, mesures finales, noms).")
    c.restoreState()


def entete(c, doc):
    w, h = A4
    c.saveState()
    c.setFont("Body-Semi", 8)
    c.setFillColor(CYAN)
    c.drawString(18 * mm, h - 12 * mm, "SENTINEL-X")
    c.setFillColor(MUTED)
    c.setFont("Body", 8)
    c.drawString(38 * mm, h - 12 * mm, "Rapport d'ingénierie technique · option B")
    c.drawRightString(w - 18 * mm, h - 12 * mm, f"Workshop2026-M1-{GROUPE}")
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.line(18 * mm, h - 14 * mm, w - 18 * mm, h - 14 * mm)
    c.line(18 * mm, 12 * mm, w - 18 * mm, 12 * mm)
    c.drawString(18 * mm, 8 * mm, "EPSI · Workshop Bac+4 2026-27 · Mission SENTINEL-X")
    c.drawRightString(w - 18 * mm, 8 * mm, f"Page {doc.page}")
    c.restoreState()


# ---------------------------------------------------------------------------
# Poster A3 (annexe)
def dessiner_poster(c, doc):
    from reportlab.lib.utils import ImageReader
    W, H = A3
    m = 34
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    cyan, amber, txt, muted, panel, border = (colors.HexColor(x) for x in
                                              ("#22D3EE", "#F5A524", "#E7EEF7", "#93A4C0", "#111B30", "#2C3E62"))

    def image(nom, x, ytop, w):
        r = ImageReader(str(img(nom, "dark")))
        iw, ih = r.getSize()
        hgt = w * ih / iw
        c.drawImage(r, x, ytop - hgt, w, hgt)
        return hgt

    def titre(x, y, t, col=cyan):
        c.setFillColor(col)
        c.setFont("Body-Bold", 15)
        c.drawString(x, y, t.upper())

    def para(x, ytop, w, html, size=11.5, col="#E7EEF7", leading=None):
        st = ParagraphStyle("p", fontName="Body", fontSize=size, leading=leading or size * 1.38, textColor=colors.HexColor(col))
        p = Paragraph(html, st)
        _, hh = p.wrap(w, 1000)
        p.drawOn(c, x, ytop - hh)
        return hh

    # En-tête
    c.setFillColor(cyan)
    c.setFont("Body-Bold", 11)
    c.drawString(m, H - m - 10, "AETHERCORP INDUSTRIAL SOLUTIONS  ·  MISSION SENTINEL-X  ·  EPSI MASTÈRE 1 — OCTOBRE 2026")
    c.setFillColor(colors.white)
    c.setFont("Body-Bold", 76)
    c.drawString(m - 3, H - m - 92, "SENTINEL-X")
    c.setFont("Body", 19)
    c.setFillColor(txt)
    c.drawString(m, H - m - 122, "Boîtier IoT durci · IA locale temps réel · pile conteneurisée chiffrée de bout en bout")
    chips = [("Option B · PC portable serveur", cyan), (f"Groupe {GROUPE}", amber), ("ESP8266 → MQTTS → Docker", cyan)]
    x = m
    for t, col in chips:
        c.setFont("Body-Bold", 11)
        tw = c.stringWidth(t, "Body-Bold", 11) + 22
        c.setFillColor(panel)
        c.setStrokeColor(col)
        c.roundRect(x, H - m - 160, tw, 24, 12, stroke=1, fill=1)
        c.setFillColor(col)
        c.drawString(x + 11, H - m - 152, t)
        x += tw + 10

    # Ligne 1 : architecture + chiffres clés
    y = H - m - 190
    titre(m, y, "Architecture Edge-to-Server")
    h1 = image("architecture", m, y - 10, 380)
    xk = m + 400
    titre(xk, y, "Chiffres clés", amber)
    inj = M["injection"]["sensibilite"][2]
    kpis = [("2", "ports exposés sur le Wi-Fi de table : 443 (HTTPS) et 8883 (MQTTS)"),
            ("TLS 1.2", "ECDSA P-256 · CA du groupe · comptes MQTT et ACL par topic"),
            (nb(M["mesures"]), f"mesures réelles du boîtier analysées ({M['debut'][:5]} → {M['fin'][:5]})"),
            (f"{inj['v1']}/6 vs {inj['statique']}/6", "dérives lentes détectées : Isolation Forest vs seuil statique")]
    ky = y - 14
    for big, small in kpis:
        c.setFillColor(panel)
        c.setStrokeColor(border)
        c.roundRect(xk, ky - 66, W - m - xk, 62, 8, stroke=1, fill=1)
        c.setFillColor(cyan)
        c.setFont("Body-Bold", 25)
        c.drawString(xk + 14, ky - 34, big)
        para(xk + 14, ky - 39, W - m - xk - 28, small, size=10, col="#93A4C0")
        ky -= 70

    # Ligne 2 : boîtier + réseau
    y = y - 10 - max(h1, 4 * 70) - 22
    titre(m, y, "Le boîtier ESP8266")
    h2 = image("cablage", m, y - 10, 350)
    xr = m + 370
    titre(xr, y, "Réseau de table étanche")
    h3 = image("reseau", xr, y - 10, W - m - xr)

    # Ligne 3 : IA + sécurité
    y = y - 10 - max(h2, h3) - 22
    titre(m, y, "IA prédictive : Isolation Forest")
    dispo = y - 10 - (m + 62)
    image("sensibilite", m, y - 10, min(350, dispo * 7.6 / 3.2))
    titre(xr, y, "Vision : YOLOv8n sur la webcam USB")
    h5 = image("vision", xr, y - 12, W - m - xr)
    yy = y - 12 - h5 - 22
    titre(xr, yy, "Sécurité défensive", amber)
    para(xr, yy - 8, W - m - xr,
         "• MQTTS uniquement, anonymes refusés · UFW refus par défaut<br/>"
         "• SSH par clé · conteneurs non-root, cap_drop ALL<br/>"
         "• Secrets hors Git, clé de la CA hors ligne", size=10.5)

    # Pied
    c.setFillColor(amber)
    c.setFont("Body-Bold", 26)
    c.drawString(m, m + 30, "Sentinel-X : la sécurité à la bordure.")
    c.setFillColor(muted)
    c.setFont("Body", 11)
    c.drawString(m, m + 8, f"Consortium {GROUPE} — [À COMPLÉTER : noms et filières des membres]  ·  Workshop2026-M1-{GROUPE}")
    c.restoreState()


# ---------------------------------------------------------------------------
def contenu():
    st = []
    H1 = lambda t: st.append(Heading(t, 0))
    H2 = lambda t: st.append(Heading(t, 1))
    H3 = lambda t: st.append(P(t, "h3"))
    add = st.extend
    p = lambda t: st.append(P(t))

    # Page de garde puis sommaire
    st.append(NextPageTemplate("corps"))
    st.append(PageBreak())
    st.append(P("Sommaire", "h1"))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("t0", fontName="Body-Bold", fontSize=10.5, leading=15, leftIndent=0, textColor=INK,
                       spaceBefore=4),
        ParagraphStyle("t1", fontName="Body", fontSize=9.2, leading=12.5, leftIndent=14, textColor=MUTED),
    ]
    toc.dotsMinLevel = 0
    st.append(toc)
    st.append(PageBreak())

    # 1 ------------------------------------------------------------------
    H1("1. Synthèse")
    p("SENTINEL-X est un prototype cyber-physique de surveillance d'avant-poste pour les micro-centrales "
      "d'AetherCorp. Un boîtier autonome à base d'ESP8266 mesure température, humidité, gaz combustibles et "
      "présence, affiche son état sur un écran OLED et pilote un buzzer et deux LED. Il transmet ses mesures en "
      "Wi-Fi au <b>PC Serveur Local</b>, ici le <b>PC portable d'un apprenant (option B)</b>, qui héberge la pile "
      "conteneurisée (Mosquitto, API Node.js, PostgreSQL, proxy HTTPS), la vision par ordinateur sur la webcam USB "
      "et la maintenance prédictive.")
    p("Ce dossier décrit le système tel qu'il existe dans le dépôt Git du groupe au 8 octobre 2026 et la "
      "configuration cible durcie préparée par l'équipe CYBER. Chaque fois que l'état réel diffère de la cible, "
      "l'écart est indiqué explicitement.")
    add(table([
        ["Brique", "Technologie (dépôt)", "État au 08/10", "Où"],
        ["Firmware boîtier", "C++ Arduino, PlatformIO (nodemcuv2), PubSubClient, ArduinoJson 6", "Fonctionnel en MQTT clair ; version MQTTS fournie par la cyber", "branche c_plus_plus"],
        ["Backend / API", "Node.js 20, Express 4, socket.io, MQTT.js, pg", "Fonctionnel (REST + temps réel)", "backend/"],
        ["Base de données", "PostgreSQL 16 (Docker) + SQLite (vision)", "Fonctionnelle, dumps du 08/10", "backend/dumps/"],
        ["Dashboard", "React 18 + Vite 5, Recharts, socket.io-client", "Fonctionnel (supervision, commandes, badges)", "frontend/"],
        ["Vision IA", "Python 3.13, OpenCV, Ultralytics YOLOv8n, Flask", "Fonctionnelle ; POST /alerts à brancher", "webcam-detection/"],
        ["IA prédictive", "pandas, scikit-learn IsolationForest", "Entraînée sur données réelles", "branche IA-maintenance-predictive"],
        ["Sécurité", "OpenSSL (PKI ECDSA), Mosquitto TLS + ACL, UFW, sshd, Docker", "Kit fourni et testé ; à déployer sur le serveur", "branche cyber, security/"],
    ], [27, 58, 52, 37], first_bold=True))
    add(callout(
        f"<b>{nb(M['mesures'])}</b> mesures réelles et <b>{nb(M['alertes_en_base'])}</b> alertes enregistrées entre le "
        f"{M['debut']} et le {M['fin']} · <b>8</b> flux réseau documentés, <b>2</b> ports exposés sur le Wi-Fi de table · "
        f"Isolation Forest à <b>10</b> variables cinétiques : <b>{M['injection']['sensibilite'][2]['v1']}/6</b> dérives "
        f"lentes détectées contre <b>{M['injection']['sensibilite'][2]['statique']}/6</b> pour un seuil statique.",
        "Chiffres clés"))
    add(todo("Numéro de groupe définitif (remplacer GX dans les noms de fichiers et g11 dans les topics/comptes si "
             "différent), noms et filières des membres, état réel de la migration MQTTS au moment du dépôt."))

    H2("Conventions du document")
    add(bullets([
        "Le numéro de groupe n'étant pas confirmé, les livrables portent <b>GX</b>. Le plan d'adressage reprend la "
        "valeur <b>11</b> du kit CYBER (<font name='Mono'>security/.env.example</font> : GROUP_NUMBER=11, "
        "SERVER_IP=10.10.11.1).",
        "Les chemins de fichiers sont relatifs à la racine du dépôt. Les branches citées sont celles du dépôt distant.",
        "<b>Prouvé</b> : vérifié et preuve conservée · <b>Fourni</b> : livré dans le dépôt, à vérifier une fois "
        "déployé · <b>Exigence</b> : règle à respecter par une autre filière.",
    ]))

    # 2 ------------------------------------------------------------------
    st.append(PageBreak())
    H1("2. Contexte et exigences")
    p("En 2050, AetherCorp Industrial Solutions déploie des micro-centrales énergétiques dans des zones isolées et "
      "hostiles. Elles subissent trois menaces simultanées : cyberattaques de déstabilisation réseau, intrusions "
      "physiques d'espionnage industriel et risques environnementaux (fuites de gaz, surchauffes). Faute de "
      "personnel sur place, SENTINEL-X doit détecter, alerter et résister seul, avec un Centre de Commandement "
      "Tactique matérialisé par un PC Serveur Local durci.")
    H2("2.1 Traçabilité des exigences")
    add(table([
        ["Exigence du sujet", "Réponse SENTINEL-X", "§"],
        ["ESP8266 unique, firmware C++ (Arduino / PlatformIO)", "NodeMCU v2, projet PlatformIO c++/arduino, lecture cadencée 2 s", "5"],
        ["DHT22, MQ-2, PIR HC-SR501, OLED I2C, buzzer, LED", "Câblage complet, pont diviseur sur A0, transistor buzzer", "4"],
        ["Chiffrement de bout en bout (MQTTS / HTTPS)", "Mosquitto 8883 TLS 1.2, CA ECDSA du groupe ; Caddy 443", "7"],
        ["API REST / WebSocket, POST /api/v1/alerts", "Express + socket.io, 5 routes /api/v1, validation stricte", "6"],
        ["Dashboard temps réel + contrôle des actionneurs", "React : courbes, statut, flux webcam, buzzer et LED", "6"],
        ["Vision : webcam USB sur le serveur, < 100 ms / trame, 640×480", "YOLOv8n, redimensionnement 640×480, fil de capture dédié", "8"],
        ["Prédictif sans « if temp > 40 »", "Isolation Forest sur 10 variables cinétiques", "9"],
        ["Docker-Compose : BDD + API + Mosquitto", "4 services, réseau interne, secrets Docker", "3, 6"],
        ["Point d'accès de table, plan IP, isolation", "10.10.11.0/24, hostapd/dnsmasq, ap_isolate, pas de routage", "3"],
        ["UFW, SSH par clés, Docker non-root", "Scripts security/hardening/, contrôles self-audit.sh", "7"],
        ["Audit de sécurité (journée du jeudi)", "Gabarit d'audit défensif à compléter, recommandations de durcissement", "10"],
        ["MCO : CPU/RAM, volumes de logs MQTT", "Indicateurs, seuils, rotation des logs, runbook", "11"],
    ], [62, 100, 12], first_bold=False))

    H2("2.2 Choix de l'option B")
    p("Le groupe a retenu l'<b>option B</b> : le Raspberry Pi est retiré et le rôle de PC Serveur Local est tenu "
      "par le portable d'un apprenant. Le boîtier ne contient que l'ESP8266 et ses composants.")
    add(table([
        ["Critère", "Option A — Raspberry Pi 5", "Option B — PC portable (retenue)"],
        ["Puissance IA", "CPU ARM 4 cœurs, YOLO lent sans export NCNN", "Intel Core Ultra 7 155U, 16 Go : YOLOv8n en PyTorch CPU"],
        ["Webcam USB", "Sur le Pi, dans le boîtier", "Directement sur le portable, orientable"],
        ["Point d'accès Wi-Fi", "hostapd sur le Pi", "Carte Wi-Fi du portable (hostapd ou point d'accès mobile)"],
        ["Intégration", "Boîtier plus gros, alimentation 5 V / 5 A", "Boîtier compact : ESP8266 + capteurs"],
        ["Risque", "Carte et alimentation à fiabiliser", "Le portable est un poste personnel à durcir et isoler"],
    ], [30, 66, 78], first_bold=True))

    # 3 ------------------------------------------------------------------
    st.append(PageBreak())
    H1("3. Architecture globale et réseau")
    H2("3.1 Vue d'ensemble")
    add(figure(img("architecture"), 172, "Figure 1 — Architecture Edge-to-Server (option B). Les numéros renvoient à la "
                                         "matrice des flux du § 3.4."))
    p("Les services réseau tournent dans Docker Compose sur un réseau interne. Seuls Caddy (443) et Mosquitto "
      "(8883) sont publiés, et uniquement sur l'adresse du Wi-Fi de table. La vision tourne en processus hôte "
      "car elle doit ouvrir la webcam USB : elle écoute sur 127.0.0.1:5001 et n'est accessible du réseau qu'à "
      "travers le proxy HTTPS.")

    st.append(PageBreak())
    H2("3.2 Schéma réseau et plan d'adressage")
    add(figure(img("reseau"), 170, "Figure 2 — Réseau de table étanche 10.10.11.0/24 et isolation du campus."))
    add(table([
        ["Élément", "Adresse / plage", "Masque", "Attribution", "Rôle"],
        ["Réseau de table", "10.10.11.0/24", "255.255.255.0", "—", "Sous-réseau dédié au groupe (11 = n° kit)"],
        ["PC serveur (wlan0)", "10.10.11.1", "/24", "statique", "Point d'accès, passerelle, DNS, NTP, broker, HTTPS"],
        ["Boîtier ESP8266", "10.10.11.10", "/24", "réservation DHCP (MAC)", "Client MQTTS, NTP"],
        ["Postes superviseur / jury", "10.10.11.100 → .150", "/24", "DHCP dnsmasq, bail 12 h", "Navigateur HTTPS"],
        ["Réserve équipements", "10.10.11.2 → .99", "/24", "statique", "Futurs boîtiers, poste d'audit"],
        ["Broadcast", "10.10.11.255", "—", "—", "—"],
        ["Interface campus", "DHCP école", "—", "eth0 / 2e carte", "Mises à jour uniquement, jamais routée"],
        ["Réseau Docker", "bridge interne", "—", "Docker", "db non publiée, API sur 127.0.0.1"],
    ], [33, 33, 22, 34, 52], first_bold=True))
    H3("Point d'accès de table (proposition de configuration)")
    add(code("""# /etc/hostapd/hostapd.conf
interface=wlan0
ssid=SENTINELX-G11
hw_mode=g
channel=6                 # canal fixe, à coordonner entre tables
wpa=2
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
wpa_passphrase=<secret, hors Git>
ap_isolate=1              # les clients ne se voient pas entre eux

# /etc/dnsmasq.d/sentinel.conf
interface=wlan0
dhcp-range=10.10.11.100,10.10.11.150,255.255.255.0,12h
dhcp-host=<MAC de l'ESP8266>,10.10.11.10
dhcp-option=option:ntp-server,10.10.11.1"""))
    H3("Isolation des flux")
    add(bullets([
        "<b>Aucun routage</b> : net.ipv4.ip_forward=0 et <font name='Mono'>ufw default deny routed</font>. Le "
        "serveur ne fait ni NAT ni pont vers le campus : un client de la table n'atteint jamais une autre table.",
        "<b>ap_isolate=1</b> : un poste connecté au Wi-Fi de table ne peut pas parler directement à l'ESP8266 "
        "(bloque l'ARP spoofing client-à-client).",
        "<b>Ports Docker publiés sur 10.10.11.1 uniquement</b> (ex. <font name='Mono'>10.10.11.1:8883:8883</font>) : "
        "un port publié par Docker contourne UFW, d'où cette règle.",
        "<b>Canal Wi-Fi fixe</b> et SSID propre au groupe pour éviter les interférences entre tables.",
    ]))
    add(callout("Le firmware actuel vise <font name='Mono'>192.168.137.1:1883</font>, l'adresse par défaut du "
                "<b>point d'accès mobile Windows</b> du portable (réseau 192.168.137.0/24). C'est la configuration "
                "de développement de mardi-mercredi. La cible du présent dossier est 10.10.11.0/24 avec MQTTS. "
                "Le passage impose de regénérer les certificats si l'IP change (elle figure dans le SAN).",
                "Écart prototype / cible", AMBER, colors.HexColor("#FFF4E0")))
    add(todo("Préciser l'OS réellement utilisé par le PC serveur le jour de la démo (Windows 11 + Docker Desktop "
             "ou Linux Ubuntu/Arch) et la solution de point d'accès retenue (hostapd ou point d'accès mobile). "
             "Les scripts UFW/sshd du dépôt visent Linux ; sous Windows, transposer avec le pare-feu Windows "
             "Defender (règles entrantes 443/8883 sur le profil du point d'accès uniquement)."))

    H2("3.3 Composants logiciels et ports")
    add(table([
        ["Composant", "Image / exécution", "Écoute", "Exposition", "Compte"],
        ["Mosquitto", "eclipse-mosquitto:2", "8883/tcp (TLS)", "10.10.11.1", "uid 1883"],
        ["API", "node:20-alpine (backend/Dockerfile)", "3000/tcp", "127.0.0.1 → Caddy", "node (non-root), read_only"],
        ["PostgreSQL", "postgres:16-alpine", "5432/tcp", "réseau Docker seulement", "postgres (abandon des droits)"],
        ["Caddy", "proxy HTTPS (pile INFRA)", "443/tcp", "10.10.11.1", "non-root, cap NET_BIND_SERVICE"],
        ["Vision", "Python 3.13 hôte (stream_detection.py)", "5001/tcp", "127.0.0.1 → Caddy", "utilisateur courant"],
        ["Dashboard", "build Vite statique servi par Caddy", "via 443", "10.10.11.1", "—"],
    ], [24, 50, 26, 36, 38], first_bold=True))

    H2("3.4 Matrice des flux")
    add(table([
        ["#", "Source → destination", "Port / proto", "Contenu", "Protection"],
        ["1", "ESP8266 → Mosquitto", "8883/tcp MQTTS", "sentinel/sensors, sentinel/alerts ; retour sentinel/cmd", "TLS 1.2, CA du groupe, compte esp-g11, ACL"],
        ["2", "Mosquitto ↔ API", "8883 (Docker)", "abonnement sentinel/#, publication cmd", "TLS, compte api, MQTT_CA_FILE"],
        ["3", "API ↔ PostgreSQL", "5432 (Docker)", "INSERT / SELECT mesures et alertes", "réseau interne, requêtes paramétrées, secret Docker"],
        ["4", "Navigateur ↔ Caddy", "443/tcp HTTPS", "dashboard, /api/*, /socket.io/*, /vision/*", "certificat web, identifiant"],
        ["5", "Caddy → API", "127.0.0.1:3000", "reverse proxy REST + WebSocket", "boucle locale uniquement"],
        ["6", "Vision → API", "127.0.0.1:3000", "POST /api/v1/alerts (source vision)", "boucle locale"],
        ["7", "PostgreSQL → IA prédictive", "fichier", "pg_dump → CSV → modèle", "fichier local, hors Git"],
        ["8", "Webcam → vision", "USB (UVC)", "1280×720 MJPG", "physique, pas de réseau"],
        ["—", "ESP8266 → serveur", "123/udp, 67/udp, 53", "NTP (indispensable au TLS), DHCP, DNS", "Wi-Fi de table uniquement"],
        ["—", "Admin → serveur", "22/tcp (option)", "SSH", "clé ed25519, ufw limit, fail2ban"],
    ], [7, 36, 28, 55, 48]))
    p("Fermés depuis le réseau : 1883 (MQTT clair), 3000 (API), 5001 (vision), 5432 (base), 5173 (serveur de "
      "développement Vite). La vérification de cette surface d'exposition réduite (seuls 443 et 8883 répondent) "
      "est le premier contrôle du gabarit d'audit défensif (§ 10).")

    # 4 ------------------------------------------------------------------
    st.append(PageBreak())
    H1("4. Boîtier et électronique")
    H2("4.1 Schéma de câblage")
    add(figure(img("cablage"), 170, "Figure 3 — Câblage NodeMCU v2 (broches du firmware, branche c_plus_plus)."))
    H2("4.2 Affectation des broches")
    add(table([
        ["Composant", "Broche module", "NodeMCU", "GPIO", "Tension", "Remarque"],
        ["DHT22", "DATA", "D6", "GPIO12", "3,3 V", "Pull-up 10 kΩ vers 3V3 (souvent présent sur module)"],
        ["MQ-2", "AO", "A0", "ADC0", "5 V (chauffe)", "Pont 10 kΩ / 20 kΩ : 0-5 V → 0-3,3 V ; DO non utilisé"],
        ["PIR HC-SR501", "OUT", "D5", "GPIO14", "5 V", "Sortie 3,3 V TTL ; temporisation et sensibilité réglées par potentiomètres"],
        ["OLED SSD1306", "SDA / SCL", "D2 / D1", "GPIO4 / GPIO5", "3,3 V", "I2C par défaut de Wire.begin(), adresse 0x3C, 128×64"],
        ["Buzzer", "− via NPN", "D3", "GPIO0", "5 V", "1 kΩ sur la base d'un 2N2222, émetteur à la masse"],
        ["LED rouge", "anode", "D4", "GPIO2", "3,3 V", "220 Ω en série, cathode à la masse"],
        ["LED verte", "anode", "D8", "GPIO15", "3,3 V", "220 Ω en série, cathode à la masse"],
    ], [24, 21, 21, 24, 20, 64], first_bold=True))
    H2("4.3 Alimentation et budget de courant")
    add(table([
        ["Consommateur", "Typique", "Pointe", "Source"],
        ["ESP8266 (Wi-Fi actif, TLS)", "80 mA", "170 mA (émission)", "régulateur 3,3 V de la carte"],
        ["MQ-2 (élément chauffant)", "150 mA", "180 mA", "VU / VIN 5 V"],
        ["OLED 0,96\"", "10 mA", "20 mA", "3V3"],
        ["DHT22 + PIR", "< 2 mA", "2,5 mA", "3V3 / 5 V"],
        ["LED ×2 (220 Ω)", "2 × 6 mA", "12 mA", "GPIO"],
        ["Buzzer piézo actif", "25 mA", "30 mA", "5 V via NPN"],
        ["<b>Total</b>", "<b>≈ 280 mA</b>", "<b>≈ 415 mA</b>", "<b>USB 5 V ≥ 1 A suffisant</b>"],
    ], [52, 30, 38, 54], first_bold=True))
    H2("4.4 Points de vigilance")
    add(bullets([
        "<b>Broches de démarrage</b> : D3 (GPIO0) et D4 (GPIO2) doivent être à l'état haut au boot, D8 (GPIO15) à "
        "l'état bas. La LED verte sur D8 tire bien vers la masse. En revanche la base du transistor sur D3 et la "
        "LED sur D4 peuvent tirer ces broches vers le bas et empêcher le démarrage (ou forcer le mode flash). "
        "Si le boîtier ne redémarre pas seul, déplacer le buzzer sur D0 (GPIO16) et la LED rouge sur D7 (GPIO13), "
        "deux broches libres, puis mettre à jour les constantes du firmware.",
        "<b>Entrée analogique</b> : sans pont diviseur, la sortie AO du MQ-2 alimenté en 5 V dépasse la plage "
        "0-3,3 V de la NodeMCU. Le pont 10 kΩ / 20 kΩ ramène 5 V à 3,33 V.",
        "<b>MQ-2</b> : préchauffage d'1 à 2 minutes avant des valeurs stables (24 h pour un étalonnage). Les valeurs "
        "transmises sont des lectures ADC brutes 0-1023, pas des ppm : le libellé « ppm » du dashboard "
        "(<font name='Mono'>frontend/src/config.js</font>) est à corriger ou à justifier par un étalonnage.",
        "<b>DHT22</b> : une lecture toutes les 2 s minimum, ce que respecte la cadence du firmware.",
        "<b>PIR</b> : environ 60 s de stabilisation à la mise sous tension ; régler la temporisation au minimum "
        "pour une détection réactive.",
    ]))
    H2("4.5 Fabrication (Fablab)")
    p("Coque conçue sous Fusion 360, imprimée sur Creality K2 Plus : logement de la NodeMCU et de la breadboard, "
      "fenêtre pour l'OLED, ouïes d'aération devant le MQ-2 et le DHT22 (éloignés de la chauffe du MQ-2), dôme "
      "du PIR dégagé, passe-câble USB unique. Façade gravée au laser (Creality Falcon A1) : logo AetherCorp, "
      "consignes de sécurité et numéro de série.")
    add(todo("Photos du boîtier fini, dimensions, matériau (PLA / PETG), numéro de série gravé, temps d'impression."))

    # 5 ------------------------------------------------------------------
    st.append(PageBreak())
    H1("5. Firmware ESP8266")
    p("Le firmware (<font name='Mono'>c++/arduino/src/main.cpp</font>, branche <font name='Mono'>c_plus_plus</font>) "
      "est un projet PlatformIO pour la carte <font name='Mono'>nodemcuv2</font>. Dépendances : Adafruit SSD1306 "
      "2.5, Adafruit GFX 1.11, DHT sensor library 1.4, PubSubClient 2.8, ArduinoJson 6.21.")
    H2("5.1 Cycle de fonctionnement")
    add(bullets([
        "<b>setup()</b> : initialisation I2C et DHT, broches en sortie à l'état bas, écran de démarrage en trois "
        "étapes (Wi-Fi, synchronisation NTP, serveur MQTT) affiché sur l'OLED.",
        "<b>loop()</b> : maintien de la connexion MQTT (reconnexion avec identifiant aléatoire "
        "<font name='Mono'>SentinelNode-xxxx</font>), puis toutes les 2 s : lecture des quatre capteurs, publication "
        "de la mesure, publication d'alertes locales, rafraîchissement de l'OLED (Gaz, Hum, Tmp, Mvt).",
        "<b>receptionCommande()</b> : abonné à <font name='Mono'>sentinel/cmd</font>, applique "
        "<font name='Mono'>{\"buzzer\": bool, \"led\": \"red\"|\"green\"|\"off\"}</font>.",
    ]))
    H2("5.2 Messages publiés")
    add(code("""sentinel/sensors   {"temp": 24.5, "hum": 52.1, "gas": 120, "pir": 0, "ts": 1791280000}
sentinel/alerts    {"type": "gas",    "level": "warn" | "critical", "value": 640}
sentinel/alerts    {"type": "motion", "level": "warn", "value": 1}
sentinel/cmd  <-   {"buzzer": true, "led": "red"}"""))
    p("Les alertes locales du firmware (gaz &gt; 400 avertissement, &gt; 700 critique ; mouvement) sont des "
      "<b>alarmes de repli</b> : elles déclenchent l'affichage et le signal physique même si le serveur est "
      "injoignable. La détection d'anomalies, elle, est confiée au modèle prédictif (§ 9), conformément à "
      "l'interdiction des seuils statiques.")
    H2("5.3 Version sécurisée (cible MQTTS)")
    p("L'équipe CYBER fournit les règles et le code de connexion (<font name='Mono'>security/docs/tls-esp8266.md</font>) :")
    add(table([
        ["Règle", "Mise en œuvre"],
        ["Confiance limitée à la CA du groupe", "BearSSL::X509List + setTrustAnchors(), jamais setInsecure()"],
        ["Heure valide avant le TLS", "configTime(0, 0, SERVER_IP), redémarrage si pas d'heure en 30 s"],
        ["Secrets hors Git", "include/secrets.h (ignoré), seul secrets.example.h est versionné"],
        ["Authentification", "compte esp-g11, mot de passe aléatoire 128 bits"],
        ["Présence fiable", "Last Will : le broker publie « offline » sur status si le boîtier disparaît"],
        ["Anti-rejeu", "champ seq + ts dans chaque mesure"],
        ["Commandes", "liste blanche (BUZZER_ON, LED_RED_ON…), tout le reste ignoré"],
        ["RAM", "probeMaxFragmentLength() puis tampons TLS 1024 octets (≈ 25 Ko économisés)"],
    ], [58, 116], first_bold=True))
    H2("5.4 Revue du code actuel")
    add(table([
        ["#", "Constat (branche c_plus_plus, commit 5738b71)", "Impact", "Correction"],
        ["F1", "SSID et clé Wi-Fi écrits en clair dans main.cpp, donc dans l'historique Git", "Élevé", "Changer la clé du point d'accès, passer par secrets.h"],
        ["F2", "MQTT en clair sur 1883, connexion anonyme", "Élevé", "Version MQTTS du kit cyber (§ 5.3)"],
        ["F3", "Ligne isolée « ) » après la boucle de connexion Wi-Fi", "Compilation", "À vérifier : supprimer la ligne"],
        ["F4", "Alerte motion republiée toutes les 2 s tant que le PIR est haut", "Bruit (433 alertes)", "Publier sur front montant uniquement"],
        ["F5", "NTP sur pool.ntp.org, injoignable sur réseau isolé", "TLS impossible", "NTP = 10.10.11.1 (chrony)"],
        ["F6", "Valeur 0 envoyée si le DHT22 échoue (isnan → 0)", "Fausses mesures", "Envoyer null ; le backend l'accepte"],
    ], [9, 78, 26, 61]))

    # 6 ------------------------------------------------------------------
    st.append(PageBreak())
    H1("6. Architecture logicielle et flux de données")
    add(figure(img("flux"), 168, "Figure 4 — Flux de données : topics MQTT, REST et événements socket.io."))
    H2("6.1 Topics MQTT")
    p("Le backend s'abonne à <font name='Mono'>&lt;MQTT_BASE_TOPIC&gt;/#</font> et accepte deux contrats ; c'est "
      "la fin du topic qui décide du traitement (<font name='Mono'>backend/src/index.js</font>).")
    add(table([
        ["Topic", "Sens", "QoS", "Charge utile", "Traitement"],
        ["sentinel/sensors", "ESP → API", "0", "{temp, hum, gas, pir, ts}", "INSERT api_measurements, socket « sensors »"],
        ["sentinel/alerts", "ESP → API", "0", "{type: gas|motion|temp, level, value}", "INSERT api_alerts, socket « alert »"],
        ["sentinel/cmd", "API → ESP", "1", "{buzzer, led}", "receptionCommande()"],
        ["sentinelx/g11/telemetry", "ESP → API", "1", "{seq, ts, t, h, gas, pir, rssi}", "contrat sécurisé du kit"],
        ["sentinelx/g11/event", "ESP → API", "1", "{type, value, ts}", "pir → motion critical / info"],
        ["sentinelx/g11/status", "ESP → API", "1", "online / offline (Last Will)", "boîtier hors ligne immédiat"],
    ], [36, 20, 10, 50, 58]))
    H2("6.2 API REST (préfixe /api/v1)")
    add(table([
        ["Méthode", "Route", "Rôle", "Validation / réponses"],
        ["POST", "/alerts", "Alerte capteur ou IA, diffusée au dashboard", "source ∈ {esp8266, vision}, type ≤ 50 car., value, timestamp ISO 8601, level optionnel ; 201 / 400"],
        ["GET", "/alerts?limit=20", "Dernières alertes", "limit entier 1-200"],
        ["GET", "/history?sensor=temp&amp;limit=100", "Historique des mesures", "sensor ∈ {temp, hum, gas, pir}, limit 1-1000"],
        ["GET", "/status", "État du boîtier et des actionneurs", "online si message &lt; 15 s"],
        ["POST", "/commands", "Buzzer / LED", "buzzer booléen, led ∈ {red, green, off} ; 503 si broker absent"],
    ], [16, 46, 46, 66]))
    add(code("""POST /api/v1/alerts
{ "source": "vision", "type": "person_detected",
  "value": { "people": 1, "confidence": 0.87 },
  "timestamp": "2026-10-07T09:30:00Z", "level": "warn" }"""))
    p("Corps JSON limité à 10 Ko, erreurs 400 / 413 explicites, requêtes SQL paramétrées. Événements socket.io : "
      "<font name='Mono'>sensors</font>, <font name='Mono'>alert</font>, <font name='Mono'>status</font> (envoyé à "
      "chaque connexion, changement d'état en ligne / hors ligne et après chaque commande).")
    H2("6.3 Modèle de données")
    add(figure(img("bdd"), 168, "Figure 5 — Tables PostgreSQL du backend et base SQLite locale du service vision."))
    H2("6.4 Dashboard")
    p("Application React 18 / Vite 5 (<font name='Mono'>frontend/</font>) : bandeau d'état global, tuiles capteurs "
      "colorées selon des seuils d'affichage, courbes Recharts des 30 derniers points, liste d'alertes, flux "
      "MJPEG de la webcam avec état de détection, panneau de commande buzzer / LED, chronologie de présence, et "
      "page « Employés &amp; badges » (QR, vérification faciale par étapes avec consentement). La couche "
      "<font name='Mono'>useSentinelData</font> combine REST au démarrage et socket.io ensuite, avec un mode "
      "simulé (VITE_USE_MOCK) pour développer sans matériel.")
    add(todo("Capture d'écran du dashboard en fonctionnement réel (courbes animées, alerte, flux webcam)."))

    # 7 ------------------------------------------------------------------
    st.append(PageBreak())
    H1("7. Matrice de sécurité")
    p("Elle reprend et complète <font name='Mono'>security/docs/matrice-securite.md</font>. Chaque ligne relie une "
      "menace à une contre-mesure, à son responsable et à la preuve présentée au jury.")
    H2("7.1 Chiffrement et gestion des certificats")
    add(figure(img("pki"), 160, "Figure 6 — PKI du groupe : une CA ECDSA, deux certificats serveur à IP dans le SAN."))
    add(bullets([
        "<b>ECDSA P-256 plutôt que RSA 2048</b> : poignée de main d'environ 1 s sur l'ESP8266 contre 3 à 5 s, et "
        "beaucoup moins de RAM.",
        "<b>IP dans le SubjectAltName</b> : BearSSL compare l'adresse demandée au certificat ; un faux broker sans "
        "certificat signé par la CA du groupe est refusé.",
        "<b>Durées courtes</b> : CA 90 jours, certificats 30 jours ; régénération par "
        "<font name='Mono'>make-pki.sh --force</font>.",
        "<b>Clé de la CA hors du PC</b> : stockée sur la clé USB du responsable cyber après génération.",
        "<b>Mosquitto</b> : <font name='Mono'>tls_version tlsv1.2</font>, <font name='Mono'>allow_anonymous false</font>, "
        "fichier passwd haché, ACL par compte, <font name='Mono'>max_connections 10</font>, "
        "<font name='Mono'>message_size_limit 1024</font>.",
    ]))
    H2("7.2 Durcissement du serveur")
    add(table([
        ["Domaine", "Mesure", "Fichier", "Preuve attendue", "État"],
        ["Pare-feu", "UFW deny incoming / allow outgoing / deny routed ; 443, 8883, 67, 53, 123 sur wlan0 ; 22 en limit", "hardening/ufw-rules.sh", "ufw status verbose ; liste des ports en écoute", "Fourni"],
        ["SSH", "PasswordAuthentication no, PermitRootLogin no, AllowUsers, MaxAuthTries 3, pas de forwarding ; fail2ban", "hardening/sshd-sentinel.conf", "sshd -T ; tentative par mot de passe refusée", "Fourni"],
        ["Docker daemon", "no-new-privileges, icc false, live-restore, logs json-file 3 × 10 Mo", "hardening/docker-daemon.json", "docker info", "Fourni"],
        ["Conteneurs", "user non-root, cap_drop ALL, read_only, jamais privileged ni docker.sock", "docker-compose (INFRA)", "self-audit.sh section 4", "Exigence"],
        ["Ports Docker", "publication sur 10.10.11.1 seulement, base jamais publiée", "docker-compose (INFRA)", "ss -lntu", "Exigence"],
        ["Secrets", "secrets Docker (*_FILE), .env et certificats ignorés par Git", "backend/src/config.js", "self-audit.sh section 6", "Fourni"],
        ["Audit OS", "lynis audit system avant / après", "—", "écart de score", "[À compléter]"],
    ], [20, 58, 32, 42, 22]))
    H2("7.3 Contrôle d'accès applicatif")
    add(table([
        ["Compte", "Peut écrire", "Peut lire"],
        ["esp-g11 (boîtier)", "sentinel(x)/…/telemetry, event, status", "…/cmd uniquement"],
        ["api (backend)", "…/cmd", "tout le groupe (#)"],
        ["superviseur (Caddy)", "POST /api/v1/commands via HTTPS", "dashboard, API, flux vidéo"],
        ["clé superviseur (vision)", "routes employés / badges", "fiches et journal d'accès"],
    ], [42, 70, 62], first_bold=True))
    H2("7.4 Analyse STRIDE")
    add(table([
        ["Menace", "Scénario sur SENTINEL-X", "Contre-mesure", "Résiduel"],
        ["S — Usurpation", "Faux broker sur le Wi-Fi (evil twin), faux boîtier publiant des mesures", "Trust anchor CA du groupe ; comptes MQTT ; WPA2", "Faible"],
        ["T — Altération", "Commande forgée sur cmd, mesure modifiée en transit, injection SQL", "ACL, TLS, validation des corps, SQL paramétré", "Faible"],
        ["R — Répudiation", "Qui a déclenché le buzzer ?", "Journal Caddy (identifiant) ; à ajouter : tracer chaque commande dans api_alerts", "Moyen"],
        ["I — Divulgation", "Sniffing des mesures, flux caméra ouvert, secrets dans Git, CORS *", "MQTTS, vision sur 127.0.0.1, .gitignore, origines explicites", "Moyen (historique F1)"],
        ["D — Déni de service", "Flood MQTT ou HTTP, saturation des 10 connexions, désauthentification Wi-Fi", "Limites Mosquitto, express.json 10 Ko, UFW limit ; à ajouter : rate limit", "Moyen"],
        ["E — Élévation", "Évasion de conteneur, brute-force SSH", "non-root, cap_drop, no-new-privileges ; clés SSH, fail2ban", "Faible"],
    ], [26, 54, 70, 24], first_bold=True))
    H2("7.5 Failles relevées dans le code (audits du 6 et du 8 octobre)")
    add(table([
        ["#", "Faille", "Gravité", "Statut"],
        ["1", "Service vision sur 0.0.0.0:5001 en HTTP sans authentification", "Élevée", "Corrigé : 127.0.0.1"],
        ["2", "Access-Control-Allow-Origin: * sur la vision", "Moyenne", "Corrigé : FRONTEND_ORIGINS"],
        ["3", "Serveur de développement Flask pour la démo", "Faible", "Atténué : local uniquement"],
        ["4", "Dashboard servi par Vite (host: true, HTTP)", "Moyenne", "Exigence : build statique derrière Caddy"],
        ["5", "POST /api/v1/commands sans authentification", "Moyenne", "Exigence : API via proxy avec identifiant"],
        ["6", "Clé Wi-Fi en clair dans le firmware (F1)", "Élevée", "[À compléter] : clé changée ?"],
        ["7", "CORS_ORIGIN=* par défaut côté backend", "Moyenne", "À régler : URL du dashboard"],
        ["8", "Pas de limitation de débit sur l'API", "Moyenne", "À ajouter : rate limit Caddy ou express-rate-limit"],
    ], [8, 92, 20, 54]))
    H2("7.6 Preuve matérielle du chiffrement")
    p("Le jury attend une preuve matérielle que les flux de la table sont chiffrés. Elle se construit sur "
      "<b>notre propre trafic</b>, au niveau conceptuel suivant :")
    add(bullets([
        "<b>Observation du trafic de la table</b> : sur le port 8883, seuls des enregistrements TLS chiffrés sont "
        "visibles ; aucune mesure JSON n'apparaît en clair.",
        "<b>Contre-preuve</b> : l'ancien mode MQTT en clair (1883) est désactivé côté broker ; une connexion non "
        "chiffrée ou anonyme est refusée.",
        "<b>Validation du certificat</b> : le boîtier et l'API n'acceptent que le certificat signé par la CA du "
        "groupe (IP dans le SAN, dates de validité en cours).",
        "<b>Surface d'exposition</b> : la liste des ports en écoute sur l'interface de table se limite à 443 et 8883.",
    ]))
    add(todo("Joindre les preuves horodatées : capture d'écran du trafic 8883 chiffré, refus d'une connexion "
             "anonyme ou non chiffrée, liste des ports en écoute, sortie des scripts de contrôle du kit CYBER."))

    # 8 ------------------------------------------------------------------
    st.append(PageBreak())
    H1("8. IA vision : détection de présence")
    add(figure(img("vision"), 172, "Figure 7 — Chaîne de traitement de webcam-detection/stream_detection.py."))
    H2("8.1 Modèle et réglages")
    add(table([
        ["Paramètre", "Valeur", "Justification"],
        ["Modèle", "YOLOv8n (Ultralytics, yolov8n.pt, 3,2 M paramètres)", "Plus petit modèle YOLOv8, temps réel sur CPU de portable"],
        ["Classes", "0 = person uniquement (classes=[0])", "Seule la présence humaine est recherchée ; moins de faux positifs"],
        ["Seuil de confiance", "0,5 (conf=0.5) ; menace HIGH au-delà de 0,8 côté dashboard", "Confiances observées 0,60 à 0,93 sur personne réelle"],
        ["Entrée", "capture 1280×720 MJPG, redimensionnée en 640×480", "QR lisibles en haute définition, YOLO sur image réduite"],
        ["Parallélisme", "fil de capture (tampon d'une image), fil d'analyse, fil de rendu 20 img/s", "La vidéo ne attend pas l'inférence"],
        ["CPU", "YOLO_THREADS=4, OMP_WAIT_POLICY=PASSIVE", "Laisse du CPU à Docker et au navigateur"],
        ["Journal", "présence détectée / zone libre, rappel toutes les 5 s", "Anti-spam ; « présence » et non « intrus » sans badge"],
    ], [28, 72, 74], first_bold=True))
    H2("8.2 Performances")
    y = M.get("yolo", {})
    add(table([
        ["Mesure", "Valeur", "Source"],
        ["Inférence ponctuelle sur le serveur réel", "25 ms", "webcam-detection/COMPTE_RENDU_WEBCAM.md"],
        ["Moyenne glissante sur 30 images (MacBook Air)", "≈ 30 ms", "webcam-detection/CHANGELOG.md"],
        ["Âge de l'image affichée après optimisation (Core Ultra 7 155U)", "10 à 30 ms (contre 150 à 270 ms)", "CHANGELOG.md"],
        ["Cadence du flux HTTP", "≈ 18 images/s", "CHANGELOG.md"],
        [f"Banc du dossier : {y.get('frames', 60)} trames 640×480, 4 threads, PC sur batterie",
         f"{fr(y.get('inference_ms_mean', 0))} ms d'inférence moyenne · p95 total {fr(y.get('total_ms_p95', 0))} ms",
         "livrables/src/analyse_ia.py --yolo"],
        ["Mesure finale sur 1 minute, secteur, profil performances", "[À compléter] min / moy / max", "équipe IA"],
    ], [72, 56, 46]))
    p("Le banc réalisé pour ce dossier, sur batterie (mode économie d'énergie actif), dépasse nettement les 100 ms "
      "par trame. L'objectif est atteint dans les mesures de l'équipe (25 à 30 ms) mais dépend fortement de "
      "l'alimentation du portable. Pour la démonstration : portable sur secteur, profil « performances », et "
      "en cas de dépassement, trois leviers par ordre d'effort : réduire <font name='Mono'>imgsz</font> à 480 ou "
      "320, n'analyser qu'une image sur deux, exporter le modèle en OpenVINO "
      "(<font name='Mono'>model.export(format=\"openvino\")</font>) pour exploiter l'iGPU / NPU Intel du Core Ultra.")
    H2("8.3 Intégration et vie privée")
    add(bullets([
        "Sorties : <font name='Mono'>/video</font> (MJPEG annoté), <font name='Mono'>/status</font> (detection, "
        "personnes, latence_ms, fps, analyse_ms, age_image_ms, confiance), <font name='Mono'>/logs</font> (50 événements).",
        "<b>À brancher</b> : envoi automatique de <font name='Mono'>POST /api/v1/alerts</font> "
        "(<font name='Mono'>source: \"vision\"</font>, <font name='Mono'>type: \"person_detected\"</font>) à chaque "
        "début de présence, pour que la détection apparaisse dans l'historique et déclenche l'alerte du dashboard.",
        "Badges QR et reconnaissance faciale (InsightFace buffalo_s) : enregistrement sur consentement, empreintes "
        "stockées localement dans SQLite, routes protégées par clé superviseur. Données biométriques au sens du "
        "RGPD : à limiter à la démonstration et à effacer ensuite.",
    ]))

    # 9 ------------------------------------------------------------------
    st.append(PageBreak())
    H1("9. IA prédictive : maintenance par détection d'anomalies")
    add(figure(img("predictif"), 172, "Figure 8 — Chaîne de traitement (branche IA-maintenance-predictive)."))
    H2("9.1 Pourquoi pas de seuils statiques")
    p("Un seuil du type <font name='Mono'>if temp &gt; 40</font> ne voit qu'une valeur instantanée : il se déclenche "
      "trop tard (la surchauffe est déjà là) et ne voit pas une combinaison de signaux individuellement "
      "normaux. Le sujet cite l'exemple d'une hausse lente de température corrélée à une micro-dérive du gaz. Le "
      "modèle apprend donc le fonctionnement normal du boîtier sur ses propres données et repère les mesures qui "
      "s'en écartent, en regardant la <b>dynamique</b> des capteurs plutôt que leur seul niveau.")
    H2("9.2 Variables (features)")
    add(table([
        ["Variable", "Calcul", "Ce qu'elle capte"],
        ["temp, hum, gas", "valeur brute interpolée", "niveau"],
        ["*_vitesse", "différence / Δt (unités par seconde), par session", "montée ou chute brutale"],
        ["*_agitation", "écart-type glissant sur 5 mesures (10 s)", "instabilité, capteur perturbé"],
        ["pir_frequence", "moyenne glissante du PIR sur 15 mesures (30 s)", "présence prolongée inhabituelle"],
    ], [30, 80, 64], first_bold=True))
    p("Une <b>session</b> commence après plus de 10 s sans mesure (boîtier coupé) : aucune vitesse n'est calculée "
      "à travers une coupure. Les variables sont standardisées (<font name='Mono'>StandardScaler</font>) puis "
      "passées à un <font name='Mono'>IsolationForest(n_estimators=200, contamination=0.05, random_state=42)</font>.")
    H2("9.3 Entraînement sur les données réelles")
    add(table([
        ["Indicateur", "Valeur"],
        ["Jeu de données", f"{M['dump']} : {nb(M['mesures'])} mesures, {M['sessions']} sessions, du {M['debut']} au {M['fin']}"],
        ["Plages observées", f"temp {fr(M['plages']['temp'][0])}–{fr(M['plages']['temp'][1])} °C · hum {fr(M['plages']['hum'][0])}–{fr(M['plages']['hum'][1])} % · gaz {nb(int(M['plages']['gas'][0]))}–{nb(int(M['plages']['gas'][1]))} (ADC)"],
        ["Mesures jugées anormales", f"{nb(M['anomalies'])} ({fr(M['taux_anomalies'] * 100)} %), regroupées en {M['nb_periodes']} périodes"],
        ["Temps d'entraînement", f"{fr(M['fit_s'], 2)} s (CPU portable)"],
        ["Temps de prédiction", f"{fr(M['prediction_us_par_mesure'])} µs par mesure, compatible avec un scoring en ligne toutes les 2 s"],
    ], [44, 130], first_bold=True))
    add(figure(img("fig_if").with_name("fig_if_light.png"), 170,
               "Figure 9 — Mesures réelles et points jugés anormaux par l'Isolation Forest (rouge)."))
    rows = [["Période (heure de Paris)", "Mesures", "Temp. max", "Hum. max", "Gaz max"]]
    for pe in M["periodes"][:5]:
        rows.append([f"{pe['debut']} → {pe['fin']}", pe["n"], f"{fr(pe['temp_max'])} °C", f"{fr(pe['hum_max'])} %", pe["gas_max"]])
    add(table(rows, [62, 22, 30, 30, 30]))
    p("Les plus longues périodes correspondent aux essais menés sur le boîtier (gaz de briquet, souffle chaud, "
      "humidité) : le modèle les isole sans qu'aucun seuil n'ait été écrit.")
    add(todo("Annoter ces périodes avec le journal des essais réels (heure, action, opérateur) pour confirmer "
             "qu'il s'agit bien de tests et estimer le taux de faux positifs en fonctionnement calme."))

    H2("9.4 Évaluation par injection de dérives lentes")
    p("Faute d'incidents réels étiquetés, l'évaluation injecte 6 dérives synthétiques de 90 s dans les données "
      "réelles (même graine aléatoire pour toutes les méthodes) et compte les dérives détectées. Facteur ×1 : "
      "+0,05 °C et +2 unités de gaz par mesure.")
    add(figure(img("sensibilite"), 160, "Figure 10 — Dérives détectées sur 6 selon leur amplitude."))
    rows = [["Amplitude sur 90 s", "Seuil statique", "IF équipe", "IF + tendances 60 s", "Rappel par point (équipe / +tendances)"]]
    for e in M["injection"]["sensibilite"]:
        rows.append([f"×{e['facteur']} : +{fr(e['delta_temp'])} °C, +{e['delta_gas']} gaz", f"{e['statique']}/6", f"{e['v1']}/6",
                     f"{e['v2']}/6", f"{fr(e['v1_rappel'] * 100, 0)} % / {fr(e['v2_rappel'] * 100, 0)} %"])
    add(table(rows, [50, 26, 22, 34, 42]))
    add(bullets([
        "Dès une dérive de +8,8 °C et +352 unités de gaz en 90 s, l'Isolation Forest détecte les 6 épisodes, "
        "le seuil statique un seul (celui qui partait déjà d'une valeur élevée) : le modèle réagit à la "
        "<b>vitesse</b>, le seuil attend le <b>niveau</b>.",
        "Les dérives très lentes (×1, ×2) restent dans le bruit réel des capteurs : les données d'entraînement "
        "contiennent les essais volontaires (gaz jusqu'à 1024, humidité 100 %), que le modèle a appris comme "
        "« possibles ».",
        "Ajouter des tendances sur 60 s double le rappel par point à ×4 (38 % → 79 %) sans augmenter le taux "
        "d'alertes sur les données réelles (5 %).",
    ]))
    H2("9.5 Limites et suite")
    add(bullets([
        "Entraîner sur une session de référence calme, sans essais, et garder les sessions d'essais pour la "
        "validation (détection de nouveauté plutôt que d'anomalies).",
        "Ajouter les variables de tendance 60 s (évaluées ici) et la corrélation glissante température / gaz.",
        "Scorer en ligne : charger <font name='Mono'>modele_anomalies.joblib</font> dans un petit service Python "
        "abonné à <font name='Mono'>sentinel/sensors</font> et publier les anomalies par POST /api/v1/alerts "
        "(nouvelle source « predictive » à autoriser dans <font name='Mono'>backend/src/routes.js</font>).",
        "Réentraîner après chaque changement physique du boîtier (emplacement, MQ-2 remplacé).",
    ]))

    # 10 -----------------------------------------------------------------
    st.append(PageBreak())
    H1("10. Gabarit de rapport d'audit de sécurité")
    add(callout("Ce chapitre est un <b>gabarit vierge</b> que l'équipe complète après la journée d'audit du jeudi. "
                "Il recense les points de contrôle défensifs de notre propre table et les résultats observés. Il ne "
                "décrit aucune procédure offensive : l'audit se déroule dans le cadre fixé par les coachs.",
                "Cadre", CYAN, colors.HexColor("#E3F3F8")))
    H2("10.1 Identification de l'audit")
    add(table([
        ["Champ", "Valeur"],
        ["Date et créneau", "[À compléter]"],
        ["Périmètre audité", "Table du groupe : boîtier ESP8266, PC serveur, Wi-Fi de table, pile Docker"],
        ["Auditeurs / auditrices", "[À compléter]"],
        ["Version du système audité", "[À compléter] (commit Git, version firmware)"],
        ["Référent CYBER du groupe", "[À compléter]"],
    ], [50, 124], first_bold=True))

    H2("10.2 Grille des points de contrôle")
    p("Pour chaque point : <b>C</b> conforme, <b>NC</b> non conforme, <b>NA</b> non applicable. La colonne "
      "« Preuve » renvoie à une pièce jointe (capture, sortie de commande de contrôle, photo).")
    add(table([
        ["#", "Domaine", "Point de contrôle (état attendu)", "Résultat", "Preuve", "Gravité"],
        ["C1", "Chiffrement en transit", "Flux ESP8266 ↔ broker en MQTTS (TLS 1.2+), aucun flux capteur en clair", "", "", ""],
        ["C2", "Chiffrement en transit", "Dashboard et API servis en HTTPS uniquement", "", "", ""],
        ["C3", "Certificats", "Certificats signés par la CA du groupe, IP dans le SAN, en cours de validité", "", "", ""],
        ["C4", "Authentification broker", "Connexions anonymes refusées, un compte par client, ACL par topic", "", "", ""],
        ["C5", "Surface d'exposition", "Seuls 443 et 8883 accessibles depuis le Wi-Fi de table", "", "", ""],
        ["C6", "Pare-feu hôte", "Politique « refus par défaut » en entrée et en routage", "", "", ""],
        ["C7", "Administration", "SSH par clé uniquement (ou désactivé), pas de connexion root", "", "", ""],
        ["C8", "Conteneurs", "Utilisateur non-root, capacités retirées, aucun conteneur privilégié", "", "", ""],
        ["C9", "Secrets", "Aucun secret dans Git ; secrets Docker / fichiers ignorés", "", "", ""],
        ["C10", "Réseau de table", "WPA2, isolation des clients, pas de routage vers le campus", "", "", ""],
        ["C11", "Applicatif", "Validation des entrées API, requêtes SQL paramétrées, CORS restreint", "", "", ""],
        ["C12", "Supervision", "Journaux conservés et bornés, alertes de disponibilité actives", "", "", ""],
        ["C13", "Sauvegarde", "Export de la base réalisé et restauration testée", "", "", ""],
        ["C14", "Physique", "Boîtier fermé, port USB non exposé, câbles protégés", "", "", ""],
    ], [10, 30, 74, 18, 24, 18]))

    H2("10.3 Synthèse des constats")
    add(table([
        ["#", "Constat", "Gravité", "Recommandation défensive", "Responsable", "Échéance", "Statut"],
        *[[f"N{i}", "", "", "", "", "", ""] for i in range(1, 7)],
    ], [10, 42, 18, 46, 22, 18, 18]))

    H2("10.4 Échelle de gravité")
    add(table([
        ["Niveau", "Définition"],
        ["Critique", "Compromission possible de la confidentialité ou de l'intégrité des mesures ou des commandes ; "
                     "correction avant la démonstration."],
        ["Élevée", "Écart à une exigence du sujet (chiffrement, durcissement) ; correction prioritaire."],
        ["Moyenne", "Affaiblit la défense en profondeur sans exposition directe ; correction planifiée."],
        ["Faible", "Bonne pratique non appliquée, impact limité."],
        ["Information", "Observation sans impact de sécurité, à documenter."],
    ], [30, 144], first_bold=True))

    H2("10.5 Indicateurs avant / après durcissement")
    add(table([
        ["Indicateur", "Avant", "Après", "Commentaire"],
        ["Ports accessibles depuis le Wi-Fi de table", "", "", ""],
        ["Part des flux chiffrés (MQTT, HTTP)", "", "", ""],
        ["Comptes broker anonymes autorisés", "", "", ""],
        ["Conteneurs exécutés en root", "", "", ""],
        ["Secrets présents dans le dépôt Git", "", "", ""],
        ["Score de l'outil d'audit de configuration de l'OS", "", "", ""],
    ], [70, 24, 24, 56], first_bold=True))

    H2("10.6 Recommandations défensives génériques")
    add(bullets([
        "<b>Chiffrer tous les flux</b> entre le boîtier, le broker, l'API et le navigateur, et refuser toute "
        "connexion non chiffrée.",
        "<b>Authentifier chaque client</b> (boîtier, API, superviseur) avec un compte distinct et des droits limités "
        "au strict nécessaire.",
        "<b>Réduire la surface d'exposition</b> : refus par défaut au pare-feu, publication des ports Docker sur "
        "l'interface de table seulement, services internes liés à 127.0.0.1.",
        "<b>Appliquer le moindre privilège</b> aux conteneurs et aux services : non-root, capacités retirées, "
        "systèmes de fichiers en lecture seule quand c'est possible.",
        "<b>Protéger les secrets</b> : hors du dépôt Git, rotation après toute fuite, clé de la CA conservée hors "
        "ligne.",
        "<b>Administrer par clés</b> asymétriques, sans mot de passe ni compte root à distance.",
        "<b>Superviser et journaliser</b> les événements de sécurité (connexions refusées, redémarrages), avec une "
        "rétention bornée.",
        "<b>Tenir à jour</b> le système hôte, les images Docker et les bibliothèques du firmware.",
    ]))
    add(todo("Remplir les tableaux 10.1 à 10.5 après la journée d'audit, joindre les preuves en annexe et "
             "reporter les corrections effectuées (statut « corrigé », commit associé)."))

    # 11 -----------------------------------------------------------------
    st.append(PageBreak())
    H1("11. Supervision et maintien en condition opérationnelle")
    p("Le PC serveur reçoit une mesure toutes les 2 s, des images webcam en continu et les connexions du "
      "dashboard. Le MCO vise à garder la machine hôte disponible pendant toute la démonstration et à "
      "détecter tôt une dérive (saturation CPU, disque rempli par les journaux, boîtier hors ligne).")
    H2("11.1 Indicateurs suivis")
    add(table([
        ["Indicateur", "Source", "Seuil d'attention", "Action"],
        ["CPU hôte", "Gestionnaire des tâches / docker stats", "> 85 % pendant 1 min", "Réduire la résolution d'analyse YOLO, fermer les applications inutiles"],
        ["RAM hôte", "docker stats", "> 80 %", "Redémarrer le service le plus consommateur"],
        ["Espace disque / volumes Docker", "docker system df", "< 5 Go libres", "Purger les images inutilisées, exporter puis réduire l'historique"],
        ["Volume des journaux Mosquitto", "pilote json-file", "3 × 10 Mo (rotation)", "Rotation automatique, niveau de log réduit"],
        ["Débit MQTT", "compteur des mesures reçues par l'API", "< 1 mesure / 5 s", "Vérifier le Wi-Fi et l'alimentation du boîtier"],
        ["Boîtier en ligne", "GET /api/v1/status", "aucun message depuis 15 s", "Badge « hors ligne » au dashboard ; vérifier le boîtier"],
        ["Latence vision", "/status du service vision", "> 100 ms par trame", "Secteur, profil performances, imgsz réduit"],
        ["Validité des certificats", "dates du certificat", "< 7 jours restants", "Régénérer la PKI avant expiration"],
        ["Redémarrages de conteneurs", "docker compose ps", "> 2 par heure", "Lire les journaux du service concerné"],
    ], [34, 40, 34, 66], first_bold=True))
    H2("11.2 Résilience déjà en place")
    add(bullets([
        "<b>Redémarrage automatique</b> : <font name='Mono'>restart: unless-stopped</font> sur les trois services "
        "(<font name='Mono'>backend/docker-compose.yml</font>).",
        "<b>Ordre de démarrage</b> : l'API attend que PostgreSQL soit sain (<font name='Mono'>healthcheck "
        "pg_isready</font>) et réessaie la connexion à la base 20 fois.",
        "<b>Reconnexion MQTT</b> toutes les 2 s côté API ; un message mal formé est ignoré sans interrompre la "
        "réception.",
        "<b>Mode dégradé du boîtier</b> : sans serveur, l'OLED, le buzzer et les LED continuent de signaler "
        "localement gaz et présence.",
        "<b>Persistance</b> : volumes Docker nommés pour la base et le broker ; exports réguliers dans "
        "<font name='Mono'>backend/dumps/</font>.",
    ]))
    H2("11.3 Gestion des journaux et des données")
    add(table([
        ["Donnée", "Politique proposée"],
        ["Journaux des conteneurs", "json-file, 3 fichiers de 10 Mo maximum par conteneur"],
        ["Journal Mosquitto", "sortie standard (gérée par Docker), connexions et refus conservés"],
        ["Mesures api_measurements", "conservation 30 jours en démonstration, export avant purge"],
        ["Alertes api_alerts", "conservation intégrale pendant le workshop (traçabilité)"],
        ["Données biométriques (vision)", "consentement explicite, effacement à la fin du workshop"],
    ], [52, 122], first_bold=True))
    H2("11.4 Procédures d'exploitation")
    add(table([
        ["Symptôme", "Vérification", "Remédiation"],
        ["Dashboard « hors ligne »", "Statut des conteneurs, journaux de l'API", "Redémarrer l'API ; vérifier la connexion au broker"],
        ["Plus de mesures", "Boîtier alimenté, OLED « MQTT OK », Wi-Fi de table actif", "Redémarrer le boîtier ; vérifier l'heure (NTP) pour le TLS"],
        ["Vision lente", "Latence affichée par /status", "Brancher sur secteur, réduire la résolution d'analyse"],
        ["Disque presque plein", "Occupation des volumes Docker", "Exporter la base, purger les anciennes mesures"],
        ["Certificat expiré", "Dates du certificat broker / web", "Régénérer la PKI, redéployer ca.crt sur le boîtier"],
    ], [38, 64, 72], first_bold=True))
    add(todo("Relevés réels pendant une répétition de démonstration de 10 minutes : CPU et RAM moyens et "
             "maximaux, taille des journaux, nombre de mesures reçues, latence vision."))

    # 12 -----------------------------------------------------------------
    st.append(PageBreak())
    H1("12. Conclusion et perspectives")
    p("SENTINEL-X relie de bout en bout un boîtier de table ESP8266, une pile conteneurisée sur le PC portable "
      "serveur, une vision par ordinateur locale et un modèle de détection d'anomalies entraîné sur les mesures "
      "réelles du boîtier. L'option B tire parti de la puissance du portable pour l'IA et garde le boîtier "
      "compact.")
    p("La sécurité repose sur des principes défensifs simples et vérifiables : chiffrement de tous les flux, "
      "authentification de chaque client, surface d'exposition réduite à deux ports, moindre privilège pour les "
      "conteneurs et secrets hors du dépôt.")
    H2("Perspectives")
    add(bullets([
        "Scorer les anomalies en ligne et les publier comme alertes « predictive » sur le dashboard.",
        "Accélérer la vision (export OpenVINO) pour tenir l'objectif de 100 ms sur batterie.",
        "Signer les mises à jour du firmware et tracer chaque commande d'actionneur.",
        "Passer à plusieurs boîtiers par table avec un compte MQTT et un certificat par boîtier.",
    ]))
    add(callout("« Sentinel-X : la sécurité à la bordure. »", None, AMBER, colors.HexColor("#FFF4E0")))

    H1("Annexe — Glossaire")
    add(table([
        ["Terme", "Définition"],
        ["ACL", "Liste de contrôle d'accès : droits de lecture / écriture d'un compte sur les topics MQTT."],
        ["CA", "Autorité de certification : signe les certificats du broker et du serveur web du groupe."],
        ["Isolation Forest", "Modèle non supervisé qui isole les observations rares par partitions aléatoires."],
        ["MCO", "Maintien en condition opérationnelle de la plateforme."],
        ["MQTT / MQTTS", "Protocole de messagerie publication / abonnement ; MQTTS = MQTT sur TLS (port 8883)."],
        ["SAN", "Subject Alternative Name : noms et adresses IP pour lesquels un certificat est valide."],
        ["STRIDE", "Méthode de modélisation des menaces : usurpation, altération, répudiation, divulgation, "
                   "déni de service, élévation de privilèges."],
        ["TLS", "Protocole de chiffrement et d'authentification des flux réseau."],
        ["YOLOv8n", "Version « nano » du détecteur d'objets YOLO d'Ultralytics."],
    ], [32, 142], first_bold=True))

    # Annexe poster A3
    st.append(NextPageTemplate("poster"))
    st.append(PageBreak())
    st.append(TocMarker("Annexe — Poster A3"))
    return st


def build():
    doc = Dossier(OUT)
    doc.multiBuild(contenu())
    print("PDF écrit :", OUT)


if __name__ == "__main__":
    build()