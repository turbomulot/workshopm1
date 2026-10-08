# Reprise développeur web - Employés et badges QR

Date : 6 octobre 2026. Fonctionnalité intégrée au dépôt existant sur la branche `IA-webcam-detection-reconnaissance-faciale`. Voir le [compte rendu global des ajouts](COMPTE_RENDU_AJOUTS_2026-10-06.md) pour l'inventaire complet et la reprise sur un autre PC.

## Objectif et périmètre

Ajouter au dashboard SENTINEL-X la création de fiches employés (prénom, nom, photo facultative), la génération d'un QR individuel, l'activation/désactivation et le renouvellement du badge, ainsi que l'affichage des validations de la webcam.

Il s'agit de fiches administrées par le superviseur, pas de comptes employés avec mot de passe. La photo de la fiche est une illustration pour une vérification humaine : elle ne sert pas à la reconnaissance faciale. Le badge ne prouve pas l'identité de son porteur ; un QR statique peut être copié ou prêté.

Mise à jour du 8 octobre 2026 : le prototype de reconnaissance faciale de la branche `IA-webcam-detection-reconnaissance-faciale` (`face_app.py`, InsightFace) est intégré au serveur caméra. Le superviseur enregistre le visage d'un employé depuis sa fiche, avec son accord, en le capturant à la webcam. La vérification d'accès par visage se fait ensuite par étapes (de face, tête à gauche, tête à droite, menton levé, de nouveau de face) pour écarter une photo. Voir [Reconnaissance faciale](#reconnaissance-faciale).

Les routes de gestion et les résultats nominatifs sont protégés par une clé superviseur locale. Cette clé est une protection de prototype, pas un système de comptes ou de rôles prêt pour la production.

## Fichiers ajoutés

| Fichier | Responsabilité |
| --- | --- |
| `frontend/src/pages/Employees.jsx` | Page Employés & badges : connexion superviseur, création, recherche, photo, aperçu/téléchargement du QR, désactivation, renouvellement et événements en direct. |
| `frontend/src/services/accessApi.js` | Client HTTP du service badges, en-tête Bearer et URL du flux. Séparé du client capteurs existant. |
| `frontend/src/styles/access.css` | Styles de la navigation et de la page ; adaptés aux petits écrans et alignés sur les variables existantes. |
| `webcam-detection/badges.py` | Registre SQLite, traitement des photos, génération des badges, validation, anti-répétition et routes Flask. |
| `webcam-detection/qr_vision.py` | Lecture des QR, association spatiale conservatrice et annotation du prénom/nom dans la vidéo. |
| `webcam-detection/capture_buffer.py` | Tampon d'une seule capture : l'analyse prend la plus récente, sans accumuler de retard. |
| `webcam-detection/test_badges.py` | Tests automatisés avec identités fictives, images synthétiques et base temporaire. |
| `webcam-detection/faces.py` | Reconnaissance faciale (InsightFace), vérification de vivacité, annotation vidéo et routes Flask des visages. Repris du prototype `face_app.py`. |
| `webcam-detection/test_faces.py` | Tests de la reconnaissance faciale avec des visages synthétiques, sans modèle ni caméra. |
| `docs/REPRISE_DEV_WEB_BADGES.md` | Ce document de transmission. |

`webcam-detection/COMPTE_RENDU_WEBCAM.md` a été créé lors de l'analyse précédente : il décrit l'état initial, avant cette intégration, et doit être lu avec ce document.

## Fichiers existants modifiés pour cette fonctionnalité

| Fichier | Changement et raison |
| --- | --- |
| `frontend/src/App.jsx` | Navigation Supervision / Employés & badges ; conserve le composant Dashboard d'origine. |
| `frontend/src/config.js` | Une URL caméra explicite fonctionne même lorsque les capteurs restent en mode simulé. Sans URL explicite, comportement initial conservé. |
| `frontend/src/components/CameraFeed.jsx` | Bouton de nouvelle tentative lorsque le flux échoue. |
| `frontend/vite.config.js` | Proxy `/access-api` vers `127.0.0.1:5001`, avec suppression du préfixe. Port 5173 strict pour éviter une adresse changeante. |
| `frontend/.env.example` | Variables du service badges et exemple de flux caméra. |
| `webcam-detection/stream_detection.py` | Un seul propriétaire de la webcam ; intègre le registre, la lecture QR et l'annotation. Ajoute une fabrique `create_app()` sans ouverture caméra à l'import, un état cohérent, la reconnexion et l'arrêt propre. |
| `webcam-detection/requirements.txt` | Ajout de `qrcode==8.2`. |
| `.gitignore` | Exclusion des données locales, de `.env.local`, de `node_modules` et de `dist`. |
| `webcam-detection/README.md`, `frontend/README.md` | Instructions et liens de reprise. |

Les modifications déjà présentes avant cette fonctionnalité (compatibilité Python 3.13/NumPy, choix du backend Windows/macOS dans les scripts et documentation Windows) sont conservées.

La logique capteurs de `services/api.js`, les mocks, les commandes d'actionneurs et `hooks/useSentinelData.js` ne sont pas modifiés. Le nouveau module peut donc être repris sans devoir réécrire la partie capteurs.

## Données et configuration locales non versionnées

- `webcam-detection/.data/badges.sqlite3` : employés, photos normalisées, secrets des badges et historique.
- `webcam-detection/.data/admin-token.txt` : clé superviseur créée automatiquement au premier démarrage et conservée ensuite.
- `frontend/.env.local` : créé localement avec `VITE_CAMERA_URL=/access-api/video` pour afficher la caméra sur Supervision tout en gardant les capteurs simulés.
- `.venv/` : environnement Python et journaux du lancement local.

Ne pas joindre le dossier `.data` à l'archive du code et ne pas publier la base, les photos, la clé ou les badges. Les nouvelles machines initialisent leur propre registre vide et leur propre clé.

- `~/.insightface/models/buffalo_s/` : modèle de reconnaissance faciale (environ 120 Mo), téléchargé au premier démarrage du serveur.

La base contient les tables `employees`, `events` et `face_embeddings`. Cette dernière contient des empreintes faciales, données biométriques : elle ne quitte pas le poste et s'efface fiche par fiche avec « Effacer le visage ». Les noms des événements sont des instantanés lors du scan. La base conserve au maximum 1000 événements ; l'API expose les 50 derniers. Les secrets QR sont conservés localement pour permettre le téléchargement ultérieur du même badge, mais ne sont jamais inclus dans la liste des employés ni dans les événements.

## Lancement sous Windows

Depuis la racine du dépôt, installer une fois :

```powershell
.\.venv\Scripts\python.exe -m pip install -r webcam-detection/requirements.txt
cd frontend
npm ci
```

Terminal caméra, depuis la racine :

```powershell
.\.venv\Scripts\python.exe webcam-detection/stream_detection.py
```

Terminal dashboard :

```powershell
cd frontend
npm run dev
```

Ouvrir `http://127.0.0.1:5173`, puis Employés & badges. Depuis la racine, lire la clé locale et la coller dans le formulaire superviseur :

```powershell
Get-Content webcam-detection/.data/admin-token.txt
```

La clé est conservée dans `sessionStorage` de l'onglet, pas dans le code. Fermer la session la retire. Ne pas l'envoyer à une autre personne ni la mettre dans une capture d'écran. Cette gestion ne remplace pas l'authentification de production du développeur web.

Ne pas lancer `test_webcam.py` ou `detection.py` en parallèle du serveur : un seul programme doit lire la caméra. Plusieurs navigateurs peuvent consulter son flux HTTP.

## Contrat API de reprise

Base de développement frontend : `/access-api`. Base directe : `http://127.0.0.1:5001`. Le préfixe `/access-api` est un proxy Vite ; il n'existe pas dans Flask.

Toutes les routes ci-dessous demandent `Authorization: Bearer <clé superviseur>`. Réponses JSON sauf le PNG.

| Méthode | Route Flask | Corps / réponse |
| --- | --- | --- |
| GET | `/api/v1/employees` | Tableau des fiches. |
| POST | `/api/v1/employees` | `{first_name, last_name, photo?}` ; fiche créée, HTTP 201. |
| PATCH | `/api/v1/employees/<id>` | `{active: true/false}` ; fiche mise à jour. |
| GET | `/api/v1/employees/<id>/badge.png` | PNG téléchargeable contenant le QR. |
| POST | `/api/v1/employees/<id>/badge/rotate` | Nouveau secret ; ancien QR immédiatement invalide, état actif conservé. |
| GET | `/api/v1/access/events` | 50 derniers scans enregistrés, du plus récent au plus ancien. |
| GET | `/api/v1/access/status` | État caméra et badges lus dans la dernière image. |
| POST | `/api/v1/badges/validate` | `{payload: "sentinel-x:badge:..."}` ; test manuel protégé, source `manual`, sans attribution dans la vidéo. |
| POST | `/api/v1/employees/<id>/faces` | Capture le visage visible dans l'image caméra actuelle ; fiche mise à jour, HTTP 201. HTTP 409 si aucun visage, plusieurs visages, image trop ancienne ou visage déjà enregistré sur une autre fiche ; 503 si la reconnaissance n'est pas prête. |
| DELETE | `/api/v1/employees/<id>/faces` | Efface toutes les captures du visage de la fiche. |
| GET | `/api/v1/cameras` | Caméras du PC : `[{index, name, current}]`. Noms Windows via `pygrabber`, sinon « Caméra 1 », « Caméra 2 »… |
| PUT | `/api/v1/camera` | `{index}` ; bascule à chaud sur cette caméra et mémorise le choix dans `.data/camera.txt` (prioritaire sur `CAMERA_INDEX`). |
| POST | `/api/v1/faces/check` | Lance une vérification d'accès par visage ; HTTP 202 avec l'état `face_check`, 409 si une vérification est en cours ou si aucun visage n'est enregistré. |

Une fiche contient : `id`, `first_name`, `last_name`, `photo` (data URL JPEG ou null), `active`, `created_at`, `faces` (nombre de captures du visage). Nom et prénom sont obligatoires, limités à 80 caractères. Photo acceptée en JPEG, PNG ou WebP, 2 Mo maximum ; réencodée en JPEG, métadonnées supprimées et dimensions réduites à 512 pixels maximum.

Une validation contient `result` (`valid`, `disabled`, `unknown`) et `employee` (fiche sans photo ou null). Dans l'état caméra, elle ajoute `association` (`clear`, `unassigned`) et `person_index` (index du rectangle à partir de zéro, ou null).

Un événement contient : `id`, `timestamp` ISO UTC, `employee_id`, `first_name`, `last_name`, `result`, `source` (`camera`, `manual`, `face`). Pour `face`, `result` vaut `valid`, `disabled` ou `refused`. Un badge renouvelé dont l'ancien QR est scanné apparaît comme inconnu, sans divulguer la fiche autrefois associée.

Les erreurs utilisent `{error: "message"}` avec HTTP 400, 401, 404 ou 413. Le client web montre les erreurs ; il ne considère pas une indisponibilité comme une validation.

Le client télécharge le PNG par `fetch` avec Bearer, puis crée un URL Blob pour l'aperçu et le téléchargement. Ne pas mettre la clé superviseur dans l'URL d'une image ou d'un lien.

Les routes existantes `/video`, `/status`, `/logs` sont conservées pour la caméra. Elles ne demandent pas la clé locale. `/status` n'expose pas les fiches badges. Le flux vidéo peut contenir les noms associés aux badges : le serveur écoute donc seulement sur `127.0.0.1` par défaut. Ne pas exposer ces routes sur un réseau sans ajouter contrôle d'accès et HTTPS.

## Reconnaissance faciale

`GET /api/v1/access/status` ajoute trois champs :

- `face_engine` : `{state, message}`, avec `state` parmi `starting`, `loading`, `ready`, `unavailable` (InsightFace non installé), `error` et `disabled` (`FACE_RECOGNITION=0`). Seul ce champ figure aussi dans `/status`, sans nom.
- `faces` : visages de la dernière analyse, `[{employee_id, name, active, score, authenticated}]` ; `employee_id` et `name` valent null pour un visage inconnu. `authenticated` vaut true pour un employé authentifié par le visage (badge inutile).
- `face_check` : null hors vérification. Pendant une vérification : `{state: "running", auto, step, total, instruction, remaining_s, steps}`, où `steps` est la liste `[{key, label, state}]` des 5 étapes avec `state` parmi `done`, `current`, `pending`. À la fin, pendant 5 secondes : `{state: "valid" | "disabled" | "refused", message, steps}` ; en cas de refus, l'étape en cause vaut `failed`.

Le service analyse les visages dans son propre fil, 4 fois par seconde hors vérification et à chaque image pendant une vérification. La détection YOLO et le flux vidéo gardent ainsi leur cadence. Le flux affiche un cadre par visage (nom et score, ou « Visage inconnu ») et, pendant une vérification, la consigne en haut de l'image.

Déroulement d'une vérification, en 5 étapes dans l'ordre, affichées en liste à cocher sur la page et rappelées en haut du flux (« Étape 2/5 : … ») :

1. Reconnaissance de face : le visage est reconnu sur 3 analyses consécutives (10 s maximum). Ces images donnent la pose de référence.
2. Tête à gauche, 3. Tête à droite, 4. Menton levé : 8 s par geste. Le geste doit tenir sur 2 analyses de suite ; visage perdu plus de 1,5 s = échec.
5. Confirmation de face : l'identité est reconfirmée (5 s).

Une fiche désactivée donne `disabled`. Chaque fin de vérification est enregistrée dans les événements, source `face`.

Pourquoi plus de clignement des yeux : à la cadence d'analyse du PC portable (environ 6 images par seconde avec le modèle de points du visage), un clignement, qui dure 100 à 300 ms, tombe entre deux images. De plus, les modèles de points d'InsightFace lissent les paupières : sur 15 s de vidéo réelle, aucun clignement n'a été mesuré. Les gestes de tête utilisent les 5 points du détecteur (yeux, nez, coins de la bouche), sans modèle supplémentaire. Une photo inclinée, déplacée ou agrandie garde les mêmes rapports entre ces points et ne valide donc aucun geste.

Authentification sans badge : par défaut, un employé enregistré, à la fiche active, reconnu sur 3 analyses consécutives lance seul la vérification. Elle démarre à l'étape 1, déjà presque validée, sans clic du superviseur (`face_check.auto` vaut true). Le bouton manuel reste disponible. Une vérification réussie authentifie l'employé : son rectangle de personne affiche « Authentifié (visage) : Prénom Nom » en vert, comme un badge valide, et aucun badge n'est demandé. L'authentification tombe si le visage reste hors champ plus de 5 s, au bout de 2 minutes, ou si la fiche est désactivée ; il faut alors repasser les étapes. Après un échec, aucune vérification automatique n'est relancée pour cet employé pendant 10 s. Jamais d'authentification sans les 5 étapes réussies ni pour une fiche désactivée. Le nom n'est posé sur un rectangle de personne que si le visage authentifié est dans un seul rectangle et qu'il est le seul dans ce rectangle.

Réglages par variables d'environnement :

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `FACE_RECOGNITION` | `1` | `0` désactive la reconnaissance. |
| `FACE_AUTO_CHECK` | `1` | `0` désactive le démarrage automatique : la vérification ne se lance plus que par le bouton. |
| `FACE_MODEL` | `buffalo_s` | Pack InsightFace. `buffalo_l` (celui du prototype) est plus précis mais environ 6 fois plus lent sur le PC portable de test. Changer de pack impose de réenregistrer les visages : les empreintes ne sont comparées qu'à celles du même pack. |
| `FACE_THRESHOLD` | `0.45` | Ressemblance minimale (cosinus) pour reconnaître une fiche. À calibrer avec les vrais visages et la vraie caméra. |
| `FACE_DET_SIZE` | `320` | Taille de détection ; plus grand détecte des visages plus petits, plus lentement. |
| `FACE_YAW_SIGN` | `1` | `-1` si les consignes gauche et droite sont inversées avec la caméra utilisée. |
| `FACE_PITCH_THRESHOLD` | `0.08` | Amplitude demandée pour « Menton levé ». Plus petit = geste plus facile. |

Limites du prototype : les gestes rendent une photo ou une vidéo figée inutilisable, mais pas une vidéo rejouée qui exécuterait les mêmes gestes. L'ordre fixe des étapes rend ce rejeu un peu plus simple qu'avec des gestes tirés au hasard ; c'est le prix d'un parcours lisible. Pendant les gestes, seule la géométrie du visage est suivie ; l'identité est reconfirmée à la fin.

## Règles vidéo en présence de plusieurs personnes

YOLO analyse une image de 640 x 480. La capture demande 1280 x 720 (selon les capacités de la caméra). Le lecteur QR analyse d'abord un aperçu en niveaux de gris de 960 pixels de large maximum ; si aucun QR n'est décodé, une tentative à résolution complète est effectuée au maximum deux fois par seconde. Les coordonnées retournées sont ramenées à la capture d'origine puis à l'image d'analyse.

Un nom est annoté seulement si :

1. Le badge est valide.
2. Son QR est entièrement contenu dans le rectangle d'une seule personne.
3. Aucun autre rectangle ne touche la zone du QR.
4. Le même QR n'est pas présent deux fois dans l'image.
5. La personne ne présente pas plusieurs QR décodés dans le même rectangle.

Le nom est précédé de « Badge : » pour décrire l'association du justificatif. Chaque image publiée recalcule les associations. Aucun nom n'est conservé après disparition du QR et aucun suivi d'identité n'est réalisé entre les images. Les numéros Personne 1/2 sont les indices de détection de cette image, pas des identifiants persistants.

Un QR valide sans association claire est montré dans la page et dans l'historique, sans nom sur la personne. Un QR désactivé ou inconnu associé clairement reçoit une étiquette correspondante. Les autres personnes restent « présence non authentifiée », sans accusation d'intrusion.

Un scan identique de même résultat et même source crée au maximum un événement toutes les cinq secondes. La lecture reste active pendant ce délai ; la désactivation ou le renouvellement est pris en compte immédiatement à la prochaine validation. Le journal mémoire de présence reste distinct de l'historique des badges.

La limite initiale de 10 analyses/images par seconde a été supprimée après un signalement de manque de fluidité. Un thread possède la caméra et l'acquiert en continu (30 FPS demandés, selon le périphérique). Il remplace la capture précédente dans un tampon d'une seule image. Le thread d'analyse prend la capture la plus récente et publie seulement des images réellement analysées ; le nom et la géométrie QR proviennent toujours de cette même image. Les anciens résultats d'une connexion caméra sont rejetés après déconnexion/reconnexion.

Le flux MJPEG est réveillé à chaque publication, limité à 30 images/seconde au maximum et encodé en JPEG qualité 80. Un client lent ne crée pas de file d'images à rattraper. Le fallback QR n'exécute plus une deuxième détection complète à chaque image sans badge.

Mesures : `latence_ms` = YOLO ; `analyse_ms` = redimensionnement, YOLO, QR, SQLite, annotation et JPEG ; `traitement_ms` = durée de lecture de la capture concernée + analyse (les threads se chevauchent, ce n'est donc pas l'intervalle entre images) ; `age_image_ms` = temps depuis la fin de capture jusqu'à publication ; `fps` = cadence réelle de publication sur environ deux secondes. La page affiche maintenant les images/seconde. Le budget de 100 ms et la performance avec des QR physiques restent à mesurer sur la durée.

## Pannes et sécurité de reprise

La caméra tente une reconnexion après trois secondes en cas de lecture impossible. L'état et les badges courants sont invalidés ; une image de remplacement est diffusée. Si l'analyse cesse de produire une image pendant plus de trois secondes, les anciennes associations ne sont plus présentées comme actuelles.

La page actualise statut et historique toutes les secondes, sans lancer une seconde requête de cycle avant la fin de la précédente. Elle annule les requêtes lors de la sortie. En cas d'erreur, elle retire l'état live et précise que l'historique affiché peut être ancien.

Variables serveur facultatives : `CAMERA_INDEX` (0), `CAMERA_PORT` (5001), `CAMERA_HOST` (127.0.0.1), `FRONTEND_ORIGINS` (origines localhost/127.0.0.1 port 5173). Ces variables d'environnement ne sont pas chargées depuis un fichier `.env` Python automatiquement.

Pour le déploiement : le proxy Vite n'existe pas dans les fichiers de `npm run build`. Configurer un reverse proxy `/access-api`, ou `VITE_ACCESS_API_URL` vers le service au moment du build. Adapter séparément `VITE_CAMERA_URL` pour Supervision. Reprendre ensuite l'authentification/les rôles, HTTPS, les accès au flux, la politique de conservation et les limites de requêtes avec les équipes DEV/CYBER. Le QR statique ne protège pas contre la copie ou le prêt du badge.

## Vérifications réalisées

Tests automatisés :

```powershell
cd webcam-detection
..\.venv\Scripts\python.exe -m unittest test_badges -v
```

Dix tests couvrent les routes protégées, les entrées invalides, la normalisation des photos, la génération/lecture réelle d'un QR, deux QR dans une grande image avec conversion des coordonnées, l'anti-répétition, la désactivation, le renouvellement, la persistance, les associations ambiguës, l'invalidation d'un état caméra ancien, le rejet des captures en retard et la diffusion sans pause de 100 ms. Toutes les données de ces tests sont fictives et temporaires.

Le frontend est vérifié par `npm run build`, les dépendances Python par `pip check`. Les routes réelles et le proxy Vite ont répondu correctement ; la caméra était connectée. Une observation après intégration a montré YOLO à 26 ms et le traitement complet à 78 ms, sans démontrer une moyenne ni les performances avec des badges physiques.

Après optimisation de fluidité, une mesure HTTP de six secondes a reçu environ 17,8 images/seconde, contre 9,3 sur quatre secondes avant correction. La publication indiquait 18,1 FPS. Les images JPEG strictement différentes étaient environ 15,2/seconde (un sujet immobile et la compression peuvent produire des images identiques). Cette mesure locale ne garantit pas une cadence constante ni le rendu final dans le navigateur.

L'automatisation du navigateur était indisponible dans cette session. Le parcours visuel complet et le scan d'un badge physique restent à confirmer manuellement. Aucun employé réel ni fictif n'a été ajouté dans le registre de travail par les tests.

L'installation du frontend signale deux vulnérabilités dans l'arbre de dépendances existant et la compilation signale un bundle supérieur à 500 Ko. Aucune mise à niveau majeure des bibliothèques du développeur web n'a été effectuée dans cette fonctionnalité.

## Parcours de validation manuelle conseillé

1. Ouvrir Employés & badges et saisir la clé locale.
2. Créer une fiche fictive, avec puis sans photo ; vérifier la recherche et l'affichage.
3. Afficher/télécharger son QR et le présenter sur un téléphone ou sur papier devant le torse.
4. Vérifier le nom dans la vidéo lorsque le badge est lisible et l'historique des validations.
5. Retirer le QR : le nom doit disparaître. Désactiver le badge : le prochain scan doit indiquer désactivé.
6. Renouveler le badge : l'ancien QR doit devenir inconnu, le nouveau valide.
7. Faire présenter deux QR par deux personnes espacées, puis provoquer un chevauchement : aucune attribution de nom ne doit être maintenue si elle devient ambiguë.
8. Débrancher la caméra puis la rebrancher ; vérifier l'état indisponible, l'absence de badge périmé et la reprise du flux.

Pour la prochaine itération, prévoir l'édition/suppression maîtrisée des fiches et une authentification intégrée à celle du dashboard. La présente version couvre création, recherche, désactivation et renouvellement ; elle ne gère ni visiteurs, ni droits par zone/horaire, ni actionnement automatique du buzzer.
