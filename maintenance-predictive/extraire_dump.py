"""Extrait les tables d'un dump PostgreSQL (.sql) en fichiers CSV.

Pas besoin de PostgreSQL : le script lit directement les blocs COPY du dump.

    python3 extraire_dump.py ~/Downloads/sentinel_postgres_2026-10-07_1525.sql
"""
import csv
import re
import sys
from pathlib import Path

TABLES = ["api_measurements", "api_alerts"]
DOSSIER_SORTIE = Path(__file__).parent / "data"

# Ligne de début d'un bloc : COPY public.api_measurements (id, ts, temp, ...) FROM stdin;
DEBUT_COPY = re.compile(r"^COPY public\.(\w+) \((.+)\) FROM stdin;$")


def lire_blocs_copy(chemin_dump):
    """Retourne {table: (colonnes, lignes)} pour chaque bloc COPY du dump."""
    blocs = {}
    table = None
    with open(chemin_dump, encoding="utf-8") as fichier:
        for ligne in fichier:
            ligne = ligne.rstrip("\n")
            if table is None:
                debut = DEBUT_COPY.match(ligne)
                if debut:
                    table = debut.group(1)
                    colonnes = [c.strip() for c in debut.group(2).split(",")]
                    blocs[table] = (colonnes, [])
            elif ligne == "\\.":            # fin du bloc
                table = None
            else:
                # Colonnes séparées par des tabulations, \N = valeur vide
                valeurs = ["" if v == "\\N" else v for v in ligne.split("\t")]
                blocs[table][1].append(valeurs)
    return blocs


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage : python3 extraire_dump.py <fichier_dump.sql>")

    blocs = lire_blocs_copy(sys.argv[1])
    DOSSIER_SORTIE.mkdir(exist_ok=True)

    for table in TABLES:
        if table not in blocs:
            print(f"[!] table {table} absente du dump")
            continue
        colonnes, lignes = blocs[table]
        lignes.sort(key=lambda valeurs: int(valeurs[0]))   # tri par id
        chemin_csv = DOSSIER_SORTIE / f"{table}.csv"
        with open(chemin_csv, "w", newline="", encoding="utf-8") as fichier:
            ecrivain = csv.writer(fichier)
            ecrivain.writerow(colonnes)
            ecrivain.writerows(lignes)
        print(f"{table} : {len(lignes)} lignes -> {chemin_csv}")


if __name__ == "__main__":
    main()
