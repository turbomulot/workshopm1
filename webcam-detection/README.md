# Sentinel-X — Vision par ordinateur (webcam-detection)

Module de **vision intelligente** du projet Sentinel-X (filière IA & Data).
Il lit le flux d'une webcam, détecte la présence d'une personne avec **YOLOv8n**, et expose le résultat à l'équipe frontend via un petit serveur web.

## Ajout du registre employés et badges QR

Le serveur intègre maintenant les fiches employés, la génération/validation des QR et une association visuelle prudente entre badge et rectangle de personne. Le nom ne reste affiché que lorsque le QR est visible et associé sans ambiguïté. La photo de la fiche n'est utilisée pour aucune reconnaissance faciale.

## Reconnaissance faciale

Le prototype `face_app.py` est intégré au serveur (`faces.py`). Le superviseur enregistre le visage d'un employé depuis sa fiche, à la webcam, avec son accord. Le flux vidéo nomme ensuite les visages reconnus. Le bouton « Vérifier l'accès par visage » de la page Employés & badges lance une vérification par étapes (de face, tête à gauche, tête à droite, menton levé, de nouveau de face). Le modèle InsightFace `buffalo_s` (environ 120 Mo) se télécharge au premier démarrage. Les empreintes faciales restent dans `.data/badges.sqlite3`. Routes, réglages et limites : [guide de reprise](../docs/REPRISE_DEV_WEB_BADGES.md#reconnaissance-faciale).

`face_app.py` reste utilisable seul, en ligne de commande, serveur arrêté (un seul programme peut lire la caméra). Ses empreintes (`embeddings.pkl`) ne sont pas partagées avec le serveur.

Voir [le guide de reprise DEV web](../docs/REPRISE_DEV_WEB_BADGES.md) pour le contrat API complet, la clé superviseur, le lancement et les tests. Les données sont stockées dans `.data/`, ignoré par Git. Le serveur écoute sur `127.0.0.1` par défaut ; les routes nominatives sont protégées par la clé locale.

Le journal de présence du serveur indique désormais « présence détectée », sans assimiler automatiquement une personne à un intrus. La capture demande 1280 x 720 pour lire les QR puis redimensionne à 640 x 480 pour YOLO. L'état ajoute le temps de traitement complet, la connexion caméra et un horodatage ; l'état badges est disponible sur la route protégée `/api/v1/access/status`.

## Sommaire

1. [Ce que fait ce module](#1-ce-que-fait-ce-module)
2. [Contenu du dossier](#2-contenu-du-dossier)
3. [Installation](#3-installation)
4. [Utilisation](#4-utilisation)
5. [API pour le frontend](#5-api-pour-le-frontend)
6. [Configuration](#6-configuration)
7. [Performances](#7-performances)
8. [Dépannage](#8-dépannage)
9. [Sécurité](#9-sécurité)
10. [Suivi du projet](#10-suivi-du-projet)

---

## 1. Ce que fait ce module

- Capture le flux vidéo d'une webcam USB (ou de la caméra intégrée pour les tests).
- Redimensionne chaque image en **640x480** pour tenir sous **100 ms par trame** (exigence du sujet).
- Détecte les **personnes** (classe 0 du modèle YOLOv8n) avec un seuil de confiance de **0,5**.
- Écrit un journal d'événements : intrusion détectée à l'arrivée, rappel toutes les 5 secondes tant que la présence continue, zone libre au départ.
- Expose l'image annotée, l'état courant et le journal en HTTP pour le dashboard.

La détection tourne **en arrière-plan** dans un thread : elle fonctionne même si personne ne regarde la page vidéo.

## 2. Contenu du dossier

| Fichier | Rôle |
|---|---|
| `test_webcam.py` | Test de la caméra : affiche l'image en direct avec les FPS. À lancer en premier. |
| `detection.py` | Détection YOLO dans une fenêtre locale. Génère une alerte JSON (anti-spam de 5 s) affichée dans le terminal. |
| `stream_detection.py` | **Serveur principal** : diffuse la vidéo annotée (`/video`), l'état (`/status`) et le journal (`/logs`). |
| `requirements.txt` | Dépendances Python du module. |
| `CHANGELOG.md` | Historique des versions et backlog (reste à faire, idées). |

Le modèle `yolov8n.pt` n'est pas versionné : il se télécharge automatiquement au premier lancement (connexion internet nécessaire).

## 3. Installation

**Prérequis :** Python 3.9 ou plus récent, une webcam, Git.

Depuis la racine du dépôt, sur Mac / Linux :

```bash
# 1. Créer l'environnement virtuel (une seule fois)
python3 -m venv .venv

# 2. L'activer (à refaire à chaque nouveau terminal)
source .venv/bin/activate

# 3. Mettre pip à jour, puis installer les dépendances
python -m pip install --upgrade pip
pip install -r webcam-detection/requirements.txt
```

Sur Windows, dans l'invite de commandes `cmd` (chemins avec des antislashs) :

```bat
py -3 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r webcam-detection\requirements.txt
```

L'installation peut durer plusieurs minutes : PyTorch (embarqué par `ultralytics`) est volumineux, 2 à 3 Go.

Le fichier `requirements.txt` ne fige pas les versions : pip prend celles qui existent en binaire pour le Python installé. Une version figée pour un autre Python (par exemple `numpy==2.0.2` sous Python 3.13) obligerait pip à compiler, ce qui échoue sans compilateur C.

**Mac :** à la première utilisation, macOS demande l'accès à la caméra pour le terminal (ou VS Code). Accepte, ou active-le dans *Réglages Système → Confidentialité et sécurité → Caméra*.

## 4. Utilisation

Lance les commandes depuis le dossier `webcam-detection`, avec l'environnement activé.

**Tester la caméra**

```bash
python3 test_webcam.py
```

Une fenêtre s'ouvre avec l'image et les FPS. Appuie sur `Q` pour quitter.

**Voir la détection dans une fenêtre locale**

```bash
python3 detection.py
```

Les alertes JSON s'affichent dans le terminal, au maximum une toutes les 5 secondes. Appuie sur `Q` pour quitter.

**Lancer le serveur pour le frontend**

```bash
python3 stream_detection.py
```

Sous Windows sans activer l'environnement : `..\.venv\Scripts\python stream_detection.py` depuis `webcam-detection`.

Le serveur écoute sur le port **5001**. Ouvre ensuite `http://localhost:5001/video` dans un navigateur. `Ctrl + C` pour arrêter.

> Une webcam ne peut être utilisée que par **un seul programme à la fois** : ferme les autres scripts avant d'en lancer un.

## 5. API pour le frontend

Base : `http://<adresse-du-serveur>:5001`

| Route | Méthode | Réponse |
|---|---|---|
| `/video` | GET | Flux vidéo MJPEG avec rectangles de détection |
| `/status` | GET | État courant (JSON) |
| `/logs` | GET | 50 derniers événements (JSON) |

### `/video`

Flux d'images en continu. Dans une page HTML, il s'affiche avec une simple balise `img` :

```html
<img src="http://localhost:5001/video" alt="Flux caméra Sentinel-X" />
```

### `/status`

```json
{
  "detection": true,
  "personnes": 1,
  "latence_ms": 31,
  "heure": "16:25:03"
}
```

| Champ | Type | Sens |
|---|---|---|
| `detection` | booléen | `true` si au moins une personne est détectée |
| `personnes` | entier | Nombre de personnes dans l'image |
| `latence_ms` | entier | Durée de l'inférence YOLO sur la dernière image |
| `heure` | texte | Heure de la dernière analyse (`HH:MM:SS`) |

### `/logs`

```json
[
  {"id": 1, "heure": "16:30:00", "niveau": "INFO", "message": "Surveillance démarrée"},
  {"id": 2, "heure": "16:30:05", "niveau": "ALERTE", "message": "Intrusion détectée (1 personne(s), confiance 0.91)"},
  {"id": 3, "heure": "16:30:12", "niveau": "INFO", "message": "Zone libre"}
]
```

Niveaux possibles : `INFO`, `ALERTE`, `ERREUR`. L'`id` augmente à chaque ligne : le frontend peut s'en servir pour n'afficher que les nouveautés.

### Exemple d'intégration (JavaScript)

```javascript
const BASE = "http://localhost:5001";

async function rafraichir() {
  const etat = await (await fetch(`${BASE}/status`)).json();
  console.log(etat.detection ? "Intrusion" : "Zone libre", etat);

  const logs = await (await fetch(`${BASE}/logs`)).json();
  console.log(logs);
}

setInterval(rafraichir, 1000);   // une fois par seconde
```

Les réponses autorisent les appels depuis un autre domaine (CORS), donc le dashboard peut être servi depuis une autre adresse ou un autre port.

### Format des alertes

Les alertes produites par `detection.py` suivent le format prévu pour `POST /api/v1/alerts` :

```json
{"source": "camera", "type": "intrusion", "score": 0.91, "timestamp": "2026-10-05T16:30:05"}
```

L'envoi automatique vers l'API de l'équipe DEV n'est pas encore branché (voir le backlog).

## 6. Configuration

Les réglages se trouvent en tête des scripts.

| Réglage | Valeur actuelle | Où |
|---|---|---|
| Index de la caméra | `0` (caméra intégrée) | `cv2.VideoCapture(0, ...)` dans chaque script |
| Résolution | 640x480 | `cv2.resize(image, (640, 480))` |
| Seuil de confiance | 0,5 | `conf=0.5` dans l'appel au modèle |
| Délai entre deux alertes | 5 s | `DELAI_ENTRE_ALERTES` dans `detection.py` |
| Taille du journal | 50 entrées | `deque(maxlen=50)` dans `stream_detection.py` |
| Port du serveur | 5001 | `app.run(...)` dans `stream_detection.py` |

**Utiliser la webcam USB** au lieu de la caméra intégrée : remplace `0` par `1` (ou `2`) dans `cv2.VideoCapture(...)`.

Les scripts sélectionnent automatiquement `cv2.CAP_AVFOUNDATION` sur macOS et `cv2.CAP_ANY` sur Windows / Linux.

Le port **5001** est choisi volontairement : sur macOS, le port 5000 est déjà pris par AirPlay.

## 7. Performances

Mesures sur MacBook Air (puce Apple) avec YOLOv8n, images en 640x480 :

| Indicateur | Valeur | Exigence du sujet |
|---|---|---|
| Latence d'inférence | environ 30 ms | inférieure à 100 ms |
| Confiance observée | 0,60 à 0,93 | seuil à 0,5 |

Ces chiffres sont à **revalider sur la machine finale**. Si le groupe retient le Raspberry Pi 5 (option A), la latence sera plus élevée : l'export du modèle en ONNX ou NCNN et une résolution plus basse seront alors à envisager.

## 8. Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `Impossible d'ouvrir la caméra` | Accès caméra refusé | Autoriser le terminal dans les réglages de confidentialité, puis le relancer |
| Image noire | Mauvaise caméra | Changer l'index (`0`, `1`, `2`) |
| `Address already in use` (port 5001) | Un ancien serveur tourne encore | `Ctrl + C` dans son terminal, ou changer le port |
| La caméra ne s'ouvre pas | Un autre programme l'utilise | Fermer les autres scripts et applications |
| `python: command not found` | Environnement non activé | `source .venv/bin/activate` ; sur Mac, utiliser `python3` hors environnement |
| La page `/video` ne s'ouvre pas depuis un autre PC | Réseau différent, ou Wi-Fi bloquant les échanges entre appareils | Se connecter au même réseau, utiliser l'adresse IP du serveur (pas `localhost`) |
| `/status` figé | Le serveur a perdu la caméra | Consulter `/logs` : une ligne `ERREUR` l'indique |

## 9. Sécurité

- Le serveur est un prototype local : les routes employés/badges sont protégées par une clé superviseur, mais `/video`, `/status` et `/logs` restent accessibles sans clé. Le flux vidéo peut contenir des noms de badges. Le serveur écoute uniquement sur localhost par défaut et le CORS est limité aux origines frontend configurées. Ajouter authentification du flux et HTTPS avant tout accès réseau.
- Aucun secret, mot de passe ou clé ne doit être écrit dans le code : ils vont dans un fichier `.env`, ignoré par Git.
- À terme, le flux doit transiter par la couche chiffrée mise en place par l'équipe CYBER (HTTPS / TLS).

## 10. Suivi du projet

Le fichier [`CHANGELOG.md`](CHANGELOG.md) contient :
- l'historique des versions de ce module ;
- le **backlog** : ce qu'il reste à faire, les priorités (`P1` obligatoire, `P2` important, `P3` bonus) et les idées à explorer.

Convention de commits : `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
