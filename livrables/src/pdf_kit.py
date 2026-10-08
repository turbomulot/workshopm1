"""Briques ReportLab communes : polices, styles, tableaux, encadrés « À compléter »."""
from pathlib import Path

import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, Image, KeepTogether, Paragraph, Spacer, Table, TableStyle

WIN = Path("C:/Windows/Fonts")
MPL = Path(matplotlib.get_data_path()) / "fonts" / "ttf"


def _register():
    candidats = {
        "Body": [WIN / "segoeui.ttf", MPL / "DejaVuSans.ttf"],
        "Body-Bold": [WIN / "segoeuib.ttf", MPL / "DejaVuSans-Bold.ttf"],
        "Body-Italic": [WIN / "segoeuii.ttf", MPL / "DejaVuSans-Oblique.ttf"],
        "Body-Semi": [WIN / "seguisb.ttf", WIN / "segoeuib.ttf", MPL / "DejaVuSans-Bold.ttf"],
        "Mono": [WIN / "consola.ttf", MPL / "DejaVuSansMono.ttf"],
        "Mono-Bold": [WIN / "consolab.ttf", MPL / "DejaVuSansMono-Bold.ttf"],
    }
    for nom, chemins in candidats.items():
        chemin = next(p for p in chemins if p.exists())
        pdfmetrics.registerFont(TTFont(nom, str(chemin)))
    pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body-Italic", boldItalic="Body-Bold")
    pdfmetrics.registerFontFamily("Mono", normal="Mono", bold="Mono-Bold", italic="Mono", boldItalic="Mono-Bold")


_register()

NAVY = colors.HexColor("#0A1020")
INK = colors.HexColor("#142033")
MUTED = colors.HexColor("#56657C")
CYAN = colors.HexColor("#0B7A99")
CYAN_L = colors.HexColor("#E3F3F8")
AMBER = colors.HexColor("#B86200")
AMBER_L = colors.HexColor("#FFF4E0")
RED = colors.HexColor("#C42B45")
GREEN = colors.HexColor("#178A5B")
PANEL = colors.HexColor("#F3F6FA")
LINE = colors.HexColor("#C9D3E3")

S = {
    "body": ParagraphStyle("body", fontName="Body", fontSize=9.6, leading=13.6, textColor=INK, spaceAfter=5,
                           alignment=TA_LEFT),
    "small": ParagraphStyle("small", fontName="Body", fontSize=8.2, leading=11, textColor=MUTED),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=8.1, leading=10.6, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Body-Bold", fontSize=8.1, leading=10.6, textColor=INK),
    "head": ParagraphStyle("head", fontName="Body-Bold", fontSize=8.1, leading=10.4, textColor=colors.white),
    "h1": ParagraphStyle("h1", fontName="Body-Bold", fontSize=19, leading=23, textColor=NAVY, spaceBefore=4,
                         spaceAfter=10, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="Body-Bold", fontSize=12.8, leading=16, textColor=CYAN, spaceBefore=10,
                         spaceAfter=5, keepWithNext=1),
    "h3": ParagraphStyle("h3", fontName="Body-Semi", fontSize=10.4, leading=13.5, textColor=INK, spaceBefore=6,
                         spaceAfter=3, keepWithNext=1),
    "bullet": ParagraphStyle("bullet", fontName="Body", fontSize=9.6, leading=13.4, textColor=INK, leftIndent=12,
                             bulletIndent=2, spaceAfter=2.5),
    "code": ParagraphStyle("code", fontName="Mono", fontSize=7.8, leading=10.2, textColor=INK),
    "caption": ParagraphStyle("caption", fontName="Body-Italic", fontSize=8.2, leading=10.5, textColor=MUTED,
                              spaceBefore=3, spaceAfter=9, alignment=1),
    "todo": ParagraphStyle("todo", fontName="Body", fontSize=8.9, leading=12.2, textColor=INK),
    "callout": ParagraphStyle("callout", fontName="Body", fontSize=9.2, leading=12.8, textColor=INK),
}


class Heading(Paragraph):
    """Titre qui alimente le sommaire (niveau 0 ou 1)."""

    def __init__(self, text, level):
        super().__init__(text, S["h1"] if level == 0 else S["h2"])
        self.toc_level = level
        self.toc_text = text


class TocMarker(Flowable):
    """Entrée de sommaire invisible (page poster)."""

    def __init__(self, text, level=0):
        super().__init__()
        self.toc_level, self.toc_text = level, text
        self.width = self.height = 0

    def draw(self):
        pass


def P(text, style="body"):
    return Paragraph(text, S[style])


def bullets(items, style="bullet"):
    return [Paragraph(t, S[style], bulletText="•") for t in items]


def code(text):
    lignes = text.strip("\n").split("\n")
    esc = [l.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(" ", "&nbsp;") for l in lignes]
    t = Table([[Paragraph("<br/>".join(esc), S["code"])]], colWidths=[None])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PANEL), ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                           ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return [t, Spacer(1, 6)]


TODO_TAG = '<font name="Body-Bold" color="#B86200">[À COMPLÉTER]</font>'


def todo(text, titre="À COMPLÉTER PAR L'ÉQUIPE"):
    t = Table([[Paragraph(f'<font name="Body-Bold" color="#B86200">{titre}</font><br/>{text}', S["todo"])]])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), AMBER_L), ("BOX", (0, 0), (-1, -1), 0.8, AMBER),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return [t, Spacer(1, 8)]


def callout(text, titre=None, color=CYAN, bg=CYAN_L):
    head = f'<font name="Body-Bold" color="{color.hexval().replace("0x", "#")}">{titre}</font><br/>' if titre else ""
    t = Table([[Paragraph(head + text, S["callout"])]])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("BOX", (0, 0), (-1, -1), 0.6, color),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return [t, Spacer(1, 8)]


def _cell(v, bold=False):
    if isinstance(v, Flowable):
        return v
    v = "" if v is None else str(v)
    v = v.replace("[À COMPLÉTER]", TODO_TAG).replace("[À compléter]", TODO_TAG)
    return Paragraph(v, S["cellb" if bold else "cell"])


def table(rows, widths, header=True, first_bold=False, zebra=True, head_bg=INK, keep=False):
    data = []
    for i, r in enumerate(rows):
        if header and i == 0:
            data.append([Paragraph(str(c), S["head"]) for c in r])
        else:
            data.append([_cell(c, bold=(first_bold and j == 0)) for j, c in enumerate(r)])
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 4.5), ("RIGHTPADDING", (0, 0), (-1, -1), 4.5),
          ("TOPPADDING", (0, 0), (-1, -1), 3.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.6)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), head_bg))
    if zebra:
        for i in range(1 if header else 0, len(data)):
            if (i % 2 == 0) == header:
                st.append(("BACKGROUND", (0, i), (-1, i), PANEL))
    t.setStyle(TableStyle(st))
    return [KeepTogether([t]) if keep else t, Spacer(1, 8)]


def figure(path, width_mm, caption=None):
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        w, h = im.size
    img = Image(str(path), width=width_mm * mm, height=width_mm * mm * h / w)
    out = [img]
    if caption:
        out.append(Paragraph(caption, S["caption"]))
    return [KeepTogether(out)]
