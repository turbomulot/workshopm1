"""Rend les pages d'un PDF en PNG pour la relecture visuelle.

    .venv\\Scripts\\python livrables\\src\\apercu.py <fichier.pdf> <préfixe> [pages...]

Sortie : livrables/src/build/apercu/<préfixe>-NN.png
"""
import sys
from pathlib import Path

import pypdfium2 as pdfium

OUT = Path(__file__).resolve().parent / "build" / "apercu"


def main():
    pdf_path, prefixe, *pages = sys.argv[1:]
    OUT.mkdir(parents=True, exist_ok=True)
    pdf = pdfium.PdfDocument(pdf_path)
    voulues = {int(p) for p in pages} or set(range(1, len(pdf) + 1))
    for i, page in enumerate(pdf, start=1):
        if i in voulues:
            page.render(scale=1.3).to_pil().save(OUT / f"{prefixe}-{i:02d}.png")
    print(f"{len(pdf)} pages, rendu dans {OUT}")


if __name__ == "__main__":
    main()
