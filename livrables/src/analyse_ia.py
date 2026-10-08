"""Chiffres IA du dossier : Isolation Forest rejoué sur le dump réel + banc YOLOv8n.

Reprend à l'identique les variables et réglages de la branche
IA-maintenance-predictive (maintenance-predictive/entrainer.py) et les applique
au dump PostgreSQL le plus récent de backend/dumps/. Ajoute une évaluation par
injection d'anomalies synthétiques (dérive lente de température + micro-hausse
de gaz), le cas cité par le sujet, pour chiffrer rappel / précision.

    .venv\\Scripts\\python livrables\\src\\analyse_ia.py            (IA prédictive)
    .venv\\Scripts\\python livrables\\src\\analyse_ia.py --yolo     (+ banc vision)

Sortie : livrables/src/build/ia_metrics.json et figures PNG associées.
"""
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
BUILD = Path(__file__).resolve().parent / "build"
DUMPS = ROOT / "backend" / "dumps"

CAPTEURS = ["temp", "hum", "gas"]
COUPURE_SESSION_S = 10
FENETRE_AGITATION = 5
FENETRE_MOUVEMENT = 15
PART_ANOMALIES = 0.05
DEBUT_COPY = re.compile(r"^COPY public\.(\w+) \((.+)\) FROM stdin;$")


def lire_dump(chemin):
    blocs, table = {}, None
    with open(chemin, encoding="utf-8") as fichier:
        for ligne in fichier:
            ligne = ligne.rstrip("\n")
            if table is None:
                debut = DEBUT_COPY.match(ligne)
                if debut:
                    table = debut.group(1)
                    blocs[table] = ([c.strip() for c in debut.group(2).split(",")], [])
            elif ligne == "\\.":
                table = None
            else:
                blocs[table][1].append([None if v == "\\N" else v for v in ligne.split("\t")])
    return {t: pd.DataFrame(lignes, columns=cols) for t, (cols, lignes) in blocs.items()}


def preparer(mesures):
    mesures = mesures.copy()
    mesures["ts"] = pd.to_datetime(mesures["ts"], utc=True, format="ISO8601")
    for c in CAPTEURS + ["pir"]:
        mesures[c] = pd.to_numeric(mesures[c], errors="coerce")
    mesures = mesures.sort_values("ts").reset_index(drop=True)
    mesures[CAPTEURS + ["pir"]] = mesures[CAPTEURS + ["pir"]].interpolate().fillna(0)
    ecart_s = mesures["ts"].diff().dt.total_seconds()
    mesures["session"] = (ecart_s > COUPURE_SESSION_S).cumsum()
    mesures["dt"] = ecart_s.where(ecart_s <= COUPURE_SESSION_S).clip(lower=0.5)
    return mesures


def variables(mesures):
    v = pd.DataFrame(index=mesures.index)
    g = mesures.groupby("session")
    for c in CAPTEURS:
        v[c] = mesures[c]
        v[f"{c}_vitesse"] = (g[c].diff() / mesures["dt"]).fillna(0)
        v[f"{c}_agitation"] = (g[c].rolling(FENETRE_AGITATION, min_periods=1).std()
                               .reset_index(level=0, drop=True).fillna(0))
    v["pir_frequence"] = (g["pir"].rolling(FENETRE_MOUVEMENT, min_periods=1).mean()
                          .reset_index(level=0, drop=True))
    return v


FENETRE_TENDANCE = 30       # 30 mesures = 60 s (variante proposée)


def variables_v2(mesures):
    """Variante proposée : ajoute l'écart à la moyenne glissante sur 60 s (dérive lente)."""
    v = variables(mesures)
    g = mesures.groupby("session")
    for c in ["temp", "gas"]:
        moyenne = (g[c].rolling(FENETRE_TENDANCE, min_periods=1).mean()
                   .reset_index(level=0, drop=True))
        v[f"{c}_tendance"] = (g[c].diff(FENETRE_TENDANCE // 2).fillna(0))
        v[f"{c}_ecart_moyenne"] = mesures[c] - moyenne
    return v


def evaluer(pipe, fn_variables, m2, bloc):
    pred = pipe.predict(fn_variables(m2)) == -1
    vrai = m2["injecte"].to_numpy()
    episodes = sum(bool(pred[d:f].any()) for d, f in zip(bloc[::2], bloc[1::2]))
    return pred, episodes, float((pred & vrai).sum() / max(1, vrai.sum()))


def modele():
    return make_pipeline(StandardScaler(),
                         IsolationForest(n_estimators=200, contamination=PART_ANOMALIES, random_state=42))


def injecter(mesures, rng, n_episodes=6, duree=45, facteur=1.0):
    """Dérive lente : +0,05 °C et +2 unités de gaz par mesure (x facteur), sur 90 s."""
    m = mesures.copy()
    m["injecte"] = False
    sessions = m.groupby("session").size()
    longues = sessions[sessions > duree * 3].index.tolist()
    for _ in range(n_episodes):
        s = rng.choice(longues)
        idx = m.index[m["session"] == s]
        debut = rng.integers(idx[0] + duree, idx[-1] - duree)
        rampe = np.arange(duree)
        sel = np.arange(debut, debut + duree)
        m.loc[sel, "temp"] += 0.05 * facteur * rampe
        m.loc[sel, "gas"] += 2.0 * facteur * rampe
        m.loc[sel, "injecte"] = True
    return m


def figure_anomalies(m, chemin, theme="light"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    dark = theme == "dark"
    bg, fg, grid = ("#0B1220", "#E6EDF3", "#24324A") if dark else ("white", "#1B2433", "#D9DEE7")
    line, red = ("#38BDF8", "#FF5D73") if dark else ("#1F6FB2", "#D7263D")
    heure = m["ts"].dt.tz_convert("Europe/Paris")
    titres = {"temp": "Température (°C)", "hum": "Humidité (%)", "gas": "Gaz MQ-2 (brut ADC)", "pir": "PIR"}
    fig, axes = plt.subplots(4, 1, figsize=(11, 6.6), sharex=True, facecolor=bg)
    a = m["anomalie"]
    for ax, c in zip(axes, titres):
        ax.set_facecolor(bg)
        ax.plot(heure, m[c], lw=0.7, color=line)
        ax.scatter(heure[a], m.loc[a, c], s=7, color=red, zorder=3, label="anomalie (Isolation Forest)")
        ax.set_ylabel(titres[c], color=fg, fontsize=9)
        ax.tick_params(colors=fg, labelsize=8)
        ax.grid(color=grid, lw=0.5)
        for s in ax.spines.values():
            s.set_color(grid)
    axes[0].legend(loc="upper left", fontsize=8, facecolor=bg, edgecolor=grid, labelcolor=fg)
    import matplotlib.dates as mdates
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %H:%M", tz=heure.dt.tz))
    fig.tight_layout()
    fig.savefig(chemin, dpi=170, facecolor=bg)
    plt.close(fig)


def banc_yolo(n=60):
    import os
    os.environ.setdefault("OMP_WAIT_POLICY", "PASSIVE")
    import cv2
    import torch
    from ultralytics import YOLO
    import ultralytics
    torch.set_num_threads(4)
    poids = ROOT / "webcam-detection" / "yolov8n.pt"
    model = YOLO(str(poids))
    image = cv2.imread(str(Path(ultralytics.__file__).parent / "assets" / "bus.jpg"))
    image = cv2.resize(image, (640, 480))
    for _ in range(5):
        model(image, classes=[0], conf=0.5, verbose=False)
    total, inference, personnes, confs = [], [], 0, []
    for _ in range(n):
        t0 = time.perf_counter()
        r = model(image, classes=[0], conf=0.5, verbose=False)[0]
        total.append((time.perf_counter() - t0) * 1000)
        inference.append(r.speed["inference"])
        personnes = len(r.boxes)
        confs = [round(float(c), 2) for c in r.boxes.conf]
    total = np.array(total)
    return {
        "frames": n, "resolution": "640x480", "image": "ultralytics/assets/bus.jpg",
        "total_ms_mean": round(float(total.mean()), 1), "total_ms_p95": round(float(np.percentile(total, 95)), 1),
        "total_ms_max": round(float(total.max()), 1),
        "inference_ms_mean": round(float(np.mean(inference)), 1),
        "personnes": personnes, "confiances": confs,
    }


def main():
    BUILD.mkdir(exist_ok=True)
    dump = max(DUMPS.glob("*.sql"), key=lambda p: p.stat().st_size)
    tables = lire_dump(dump)
    mesures = preparer(tables["api_measurements"])
    alertes = tables.get("api_alerts", pd.DataFrame())
    X = variables(mesures)

    t0 = time.perf_counter()
    pipe = modele().fit(X)
    fit_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    mesures["anomalie"] = pipe.predict(X) == -1
    pred_us = (time.perf_counter() - t0) / len(X) * 1e6
    mesures["score"] = pipe.decision_function(X)

    nouvelle = mesures.loc[mesures["anomalie"], "ts"].diff().dt.total_seconds().fillna(999) > 6
    periodes = []
    for _, p in mesures[mesures["anomalie"]].groupby(nouvelle.cumsum()):
        periodes.append({
            "debut": p["ts"].iloc[0].tz_convert("Europe/Paris").strftime("%d/%m %H:%M:%S"),
            "fin": p["ts"].iloc[-1].tz_convert("Europe/Paris").strftime("%H:%M:%S"),
            "n": int(len(p)), "temp_max": round(float(p["temp"].max()), 1),
            "hum_max": round(float(p["hum"].max()), 1), "gas_max": int(p["gas"].max()),
        })
    periodes.sort(key=lambda p: -p["n"])

    # Évaluation par injection : modèle entraîné sur les données réelles,
    # appliqué aux mêmes données avec 6 dérives lentes injectées.
    rng = np.random.default_rng(7)
    m2 = injecter(mesures[["ts", "temp", "hum", "gas", "pir", "session", "dt"]], rng)
    vrai = m2["injecte"].to_numpy()
    bloc = np.flatnonzero(np.diff(np.r_[0, vrai.astype(int), 0]))
    _, episodes_detectes, rappel_points = evaluer(pipe, variables, m2, bloc)
    X2 = variables_v2(mesures)
    pipe_v2 = modele().fit(X2)
    _, episodes_v2, rappel_v2 = evaluer(pipe_v2, variables_v2, m2, bloc)
    taux_v2 = float((pipe_v2.predict(X2) == -1).mean())

    sensibilite = []
    for facteur in [1, 2, 4, 8]:
        m3 = injecter(mesures[["ts", "temp", "hum", "gas", "pir", "session", "dt"]],
                      np.random.default_rng(7), facteur=facteur)
        v3 = m3["injecte"].to_numpy()
        b3 = np.flatnonzero(np.diff(np.r_[0, v3.astype(int), 0]))
        _, ep1, r1 = evaluer(pipe, variables, m3, b3)
        _, ep2, r2 = evaluer(pipe_v2, variables_v2, m3, b3)
        st = ((m3["temp"] > 40) | (m3["gas"] > 400)).to_numpy()
        ep_st = sum(bool(st[d:f].any()) for d, f in zip(b3[::2], b3[1::2]))
        sensibilite.append({"facteur": facteur, "delta_temp": round(0.05 * facteur * 44, 1),
                            "delta_gas": int(2 * facteur * 44), "v1": ep1, "v2": ep2,
                            "statique": int(ep_st), "v1_rappel": round(r1, 3), "v2_rappel": round(r2, 3)})
    # Seuil statique (if temp > 40 / gas > 400, seuils du firmware) sur les mêmes dérives
    statique = ((m2["temp"] > 40) | (m2["gas"] > 400)).to_numpy()
    statique_ep = sum(statique[d:f].any() for d, f in zip(bloc[::2], bloc[1::2]))

    resultats = {
        "dump": dump.name,
        "mesures": int(len(mesures)), "sessions": int(mesures["session"].nunique()),
        "debut": mesures["ts"].iloc[0].tz_convert("Europe/Paris").strftime("%d/%m/%Y %H:%M"),
        "fin": mesures["ts"].iloc[-1].tz_convert("Europe/Paris").strftime("%d/%m/%Y %H:%M"),
        "alertes_en_base": int(len(alertes)),
        "variables": list(X.columns),
        "anomalies": int(mesures["anomalie"].sum()),
        "taux_anomalies": round(float(mesures["anomalie"].mean()), 4),
        "periodes": periodes[:6], "nb_periodes": len(periodes),
        "fit_s": round(fit_s, 2), "prediction_us_par_mesure": round(pred_us, 1),
        "plages": {c: [round(float(mesures[c].min()), 1), round(float(mesures[c].max()), 1)] for c in CAPTEURS},
        "injection": {
            "episodes": int(len(bloc) // 2), "episodes_detectes": int(episodes_detectes),
            "rappel_points": round(float(rappel_points), 3),
            "seuil_statique_episodes_detectes": int(statique_ep),
            "v2_episodes_detectes": int(episodes_v2), "v2_rappel_points": round(rappel_v2, 3),
            "v2_taux_anomalies_reel": round(taux_v2, 4),
            "v2_variables_ajoutees": ["temp_tendance", "temp_ecart_moyenne", "gas_tendance", "gas_ecart_moyenne"],
            "description": "6 dérives de 90 s : +0,05 °C et +2 unités de gaz par mesure (2 s)",
            "sensibilite": sensibilite,
        },
    }
    precedent = BUILD / "ia_metrics.json"
    if "--yolo" in sys.argv:
        resultats["yolo"] = banc_yolo()
    elif precedent.exists():
        ancien = json.loads(precedent.read_text(encoding="utf-8"))
        if "yolo" in ancien:
            resultats["yolo"] = ancien["yolo"]

    (BUILD / "ia_metrics.json").write_text(json.dumps(resultats, ensure_ascii=False, indent=2), encoding="utf-8")
    figure_anomalies(mesures, BUILD / "fig_if_light.png", "light")
    figure_anomalies(mesures, BUILD / "fig_if_dark.png", "dark")
    print(json.dumps(resultats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
