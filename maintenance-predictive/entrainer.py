"""Détection d'anomalies sur les séries temporelles des capteurs (Isolation Forest).

Aucun seuil fixe du type « if temp > 40 » : le modèle apprend à quoi ressemble
le fonctionnement normal du boîtier et signale les mesures qui s'en écartent.
Il regarde les valeurs, mais surtout leur dynamique (vitesse de variation,
agitation sur les dernières secondes) : ce sont les anomalies cinétiques.

    python3 entrainer.py            # après extraire_dump.py
"""
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")                   # pas de fenêtre : on enregistre une image
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

DOSSIER = Path(__file__).parent
DOSSIER_DATA = DOSSIER / "data"

CAPTEURS = ["temp", "hum", "gas"]
COUPURE_SESSION_S = 10      # plus de 10 s sans mesure = le boîtier a été coupé
FENETRE_AGITATION = 5       # 5 mesures = 10 s
FENETRE_MOUVEMENT = 15      # 15 mesures = 30 s
PART_ANOMALIES = 0.05       # le modèle considère ~5 % des mesures comme anormales


def charger_mesures():
    mesures = pd.read_csv(DOSSIER_DATA / "api_measurements.csv")
    mesures["ts"] = pd.to_datetime(mesures["ts"], utc=True, format="ISO8601")
    mesures = mesures.sort_values("ts").reset_index(drop=True)
    mesures[CAPTEURS + ["pir"]] = mesures[CAPTEURS + ["pir"]].interpolate().fillna(0)

    # Une session = une période sans coupure : on ne calcule pas de vitesse
    # entre la dernière mesure avant une coupure et la première après.
    ecart_s = mesures["ts"].diff().dt.total_seconds()
    mesures["session"] = (ecart_s > COUPURE_SESSION_S).cumsum()
    mesures["dt"] = ecart_s.where(ecart_s <= COUPURE_SESSION_S).clip(lower=0.5)
    return mesures


def calculer_variables(mesures):
    """Variables cinétiques données au modèle."""
    variables = pd.DataFrame(index=mesures.index)
    par_session = mesures.groupby("session")

    for capteur in CAPTEURS:
        variables[capteur] = mesures[capteur]
        # Vitesse de variation (unités par seconde)
        variables[f"{capteur}_vitesse"] = (par_session[capteur].diff() / mesures["dt"]).fillna(0)
        # Agitation : écart-type sur les 10 dernières secondes
        variables[f"{capteur}_agitation"] = (
            par_session[capteur]
            .rolling(FENETRE_AGITATION, min_periods=1).std()
            .reset_index(level=0, drop=True)
            .fillna(0)
        )

    # Part du temps avec mouvement sur les 30 dernières secondes
    variables["pir_frequence"] = (
        par_session["pir"]
        .rolling(FENETRE_MOUVEMENT, min_periods=1).mean()
        .reset_index(level=0, drop=True)
    )
    return variables


def periodes_anormales(mesures):
    """Regroupe les mesures anormales consécutives en périodes."""
    anormales = mesures[mesures["anomalie"]]
    nouvelle_periode = anormales["ts"].diff().dt.total_seconds().fillna(999) > 6
    for _, periode in anormales.groupby(nouvelle_periode.cumsum()):
        yield periode


def tracer(mesures, chemin_image):
    figure, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)
    heure = mesures["ts"].dt.tz_convert("Europe/Paris")
    anormales = mesures["anomalie"]
    titres = {"temp": "Température (°C)", "hum": "Humidité (%)", "gas": "Gaz (MQ-2)", "pir": "Mouvement (PIR)"}

    for axe, capteur in zip(axes, titres):
        axe.plot(heure, mesures[capteur], linewidth=0.8, color="tab:blue")
        axe.scatter(heure[anormales], mesures.loc[anormales, capteur], color="tab:red", s=10, label="anomalie")
        axe.set_ylabel(titres[capteur])
        axe.grid(alpha=0.3)
    axes[0].legend(loc="upper left")
    axes[0].set_title("Isolation Forest : mesures jugées anormales en rouge")
    figure.tight_layout()
    figure.savefig(chemin_image, dpi=120)


def main():
    mesures = charger_mesures()
    variables = calculer_variables(mesures)

    modele = make_pipeline(
        StandardScaler(),       # met toutes les variables à la même échelle
        IsolationForest(n_estimators=200, contamination=PART_ANOMALIES, random_state=42),
    )
    modele.fit(variables)

    # predict : -1 = anomalie, 1 = normal. score : plus il est bas, plus c'est anormal.
    mesures["anomalie"] = modele.predict(variables) == -1
    mesures["score"] = modele.decision_function(variables)

    joblib.dump({"modele": modele, "variables": list(variables.columns)}, DOSSIER / "modele_anomalies.joblib")
    pd.concat([mesures, variables.add_prefix("x_")], axis=1).to_csv(DOSSIER_DATA / "predictions.csv", index=False)
    tracer(mesures, DOSSIER / "anomalies.png")

    print(f"{len(mesures)} mesures, {mesures['session'].nunique()} sessions, "
          f"{mesures['anomalie'].sum()} anomalies ({mesures['anomalie'].mean():.1%})\n")
    print("Périodes anormales (heure de Paris) :")
    for periode in periodes_anormales(mesures):
        debut = periode["ts"].iloc[0].tz_convert("Europe/Paris").strftime("%H:%M:%S")
        fin = periode["ts"].iloc[-1].tz_convert("Europe/Paris").strftime("%H:%M:%S")
        print(f"  {debut} -> {fin}  {len(periode):3d} mesures  "
              f"temp max {periode['temp'].max():.1f}  hum max {periode['hum'].max():.1f}  "
              f"gaz max {periode['gas'].max():.0f}")
    print("\nModèle : modele_anomalies.joblib | Graphique : anomalies.png | Détail : data/predictions.csv")


if __name__ == "__main__":
    main()
