# Compte rendu global des ajouts - Webcam, badges QR et dashboard

Date : 6 octobre 2026.

Branche de travail : `IA-webcam-detection-reconnaissance-faciale`.

Ce document récapitule l'ensemble du travail ajouté depuis le commit `467e4b5` : installation et adaptation de la webcam à Windows, intégration des badges QR au dashboard existant, amélioration de la fluidité et documentation de reprise. Le nom historique de la branche est conservé, mais aucune reconnaissance faciale n'est implémentée.

Le dépôt contient maintenant trois documents complémentaires : ce compte rendu global, le [guide détaillé de reprise DEV web](REPRISE_DEV_WEB_BADGES.md) et le [compte rendu webcam initial](../webcam-detection/COMPTE_RENDU_WEBCAM.md).

## 1. Résultat fonctionnel

Le dashboard propose deux entrées : Supervision et Employés & badges. La page badges permet au superviseur de créer une fiche avec prénom, nom et photo facultative, de générer/télécharger un QR, de désactiver/réactiver le badge et de le renouveler. Le renouvellement invalide son ancien QR.

La même webcam assure la détection YOLO et la lecture des QR. Le serveur valide les identifiants contre le registre SQLite et conserve les résultats : badge valide, désactivé ou inconnu. Les personnes sans justificatif lisible restent « présence non authentifiée » ; elles ne sont pas automatiquement qualifiées d'intrus.

Le nom apparaît au-dessus d'une personne seulement lorsque le badge est valide et que son QR est entièrement dans un seul rectangle, sans chevauchement avec un autre rectangle, sans copie du même QR dans l'image et sans plusieurs badges dans le même rectangle. Sinon, la validation apparaît dans le dashboard sans attribution à une personne.

Le nom est précédé de « Badge : ». Il disparaît lorsque le QR n'est plus lisible ; aucune identité n'est suivie entre les images. La photo sert uniquement à une vérification visuelle. Le prototype valide un justificatif, pas l'identité réelle de son porteur.

## 2. Tous les fichiers ajoutés

| Fichier | Utilité |
| --- | --- |
| `frontend/src/pages/Employees.jsx` | Interface superviseur : connexion, création, recherche, photo, QR, activation, renouvellement, état caméra et validations. |
| `frontend/src/services/accessApi.js` | Client HTTP indépendant du service capteurs ; gestion du Bearer, du PNG et de la session locale. |
| `frontend/src/styles/access.css` | Navigation et styles de la page badges, y compris petits écrans. |
| `webcam-detection/badges.py` | Registre SQLite, traitement des photos, génération QR, validation, clé superviseur et routes API. |
| `webcam-detection/qr_vision.py` | Lecture QR, conversion des coordonnées, association prudente et annotation des noms. |
| `webcam-detection/capture_buffer.py` | Tampon d'une image : remplace les anciennes captures pour éviter une file d'attente. |
| `webcam-detection/test_badges.py` | Dix tests automatisés, utilisant exclusivement des données temporaires. |
| `webcam-detection/COMPTE_RENDU_WEBCAM.md` | Analyse initiale de la webcam par rapport au sujet, avant l'intégration QR. |
| `docs/REPRISE_DEV_WEB_BADGES.md` | Contrat API, détails techniques, responsabilités et parcours de test pour le développeur web. |
| `docs/COMPTE_RENDU_AJOUTS_2026-10-06.md` | Présent récapitulatif et procédure de reprise sur un autre PC. |

## 3. Tous les fichiers existants modifiés

| Fichier | Modification |
| --- | --- |
| `.gitignore` | Ignore les données badges, `.env.local`, dépendances et sortie de compilation frontend. |
| `README.md` | Ajoute la partie vision au sommaire et les liens vers les comptes rendus. |
| `frontend/.env.example` | Documente le service badges et l'URL caméra locale. |
| `frontend/README.md` | Présente la page badges et renvoie au guide de reprise. |
| `frontend/src/App.jsx` | Ajoute la navigation entre Supervision et Employés & badges. |
| `frontend/src/components/CameraFeed.jsx` | Ajoute un bouton de nouvelle tentative en cas de flux inaccessible. |
| `frontend/src/config.js` | Permet une caméra réelle explicitement configurée pendant que les capteurs restent simulés. |
| `frontend/vite.config.js` | Ajoute le proxy `/access-api` vers Flask et fixe strictement le port 5173. |
| `webcam-detection/CHANGELOG.md` | Enregistre fonctionnalités, corrections et vérifications. |
| `webcam-detection/README.md` | Ajoute Windows, badges, sécurité locale et liens de reprise. |
| `webcam-detection/detection.py` | Sélectionne le backend caméra selon Windows/Linux ou macOS. |
| `webcam-detection/test_webcam.py` | Même adaptation du backend pour le test local. |
| `webcam-detection/requirements.txt` | NumPy adapté à Python 3.13 et ajout de `qrcode==8.2`. |
| `webcam-detection/stream_detection.py` | Intègre badges, API, capture continue, annotations, état cohérent, FPS, reconnexion et arrêt propre ; supprime le lancement à l'import. |

La logique capteurs, les mocks et les commandes du développeur web restent dans leurs modules existants. La page badges utilise son propre client et fonctionne indépendamment de `VITE_USE_MOCK`. Aucune mise à niveau majeure du frontend n'a été réalisée ; le `package-lock.json` est conservé.

## 4. Architecture et routes

```text
Webcam USB -> thread de capture -> tampon dernière image
                                   |
                                   v
                            YOLO + lecture QR
                                   |
                        validation dans SQLite
                                   |
                         annotation + JPEG
                                   |
               Flask : vidéo, état, employés et événements
                                   |
                  proxy Vite /access-api -> dashboard React
```

Flask écoute sur `127.0.0.1:5001`. Vite écoute sur `127.0.0.1:5173`. Un seul programme ouvre la webcam ; les navigateurs consomment le flux HTTP.

Les routes ajoutées, protégées par la clé superviseur, sont :

| Méthode | Route |
| --- | --- |
| GET / POST | `/api/v1/employees` |
| PATCH | `/api/v1/employees/<id>` |
| GET | `/api/v1/employees/<id>/badge.png` |
| POST | `/api/v1/employees/<id>/badge/rotate` |
| GET | `/api/v1/access/events` |
| GET | `/api/v1/access/status` |
| POST | `/api/v1/badges/validate` (test manuel protégé) |

Les routes `/video`, `/status` et `/logs` sont conservées. Le guide DEV web détaille les corps JSON, les champs, les codes d'erreur et l'authentification. Le proxy Vite est un outil de développement : il faut configurer un reverse proxy ou les URLs de service pour un déploiement.

## 5. Fluidité et robustesse

La première intégration QR plafonnait le flux à 10 images/s. Cette limite a été supprimée. La capture fonctionne maintenant dans un thread distinct, et l'analyse prend toujours la dernière image disponible. Les captures anciennes sont abandonnées au lieu d'être accumulées.

La caméra demande 1280 x 720 à 30 FPS, selon ses capacités. YOLO travaille en 640 x 480. Les QR sont d'abord lus sur un aperçu gris de 960 pixels de large maximum ; un secours en pleine résolution est limité à deux tentatives par seconde si aucun QR n'est décodé. Le JPEG utilise une qualité de 80 et le flux est réveillé à chaque publication, dans la limite de 30 images/s.

Le dashboard distingue maintenant les FPS de la latence YOLO. Le serveur fournit aussi la durée d'analyse, le temps de lecture caméra plus analyse et l'âge de l'image. Ces mesures ne sont pas interchangeables.

Sur ce PC, un test court du flux est passé d'environ 9,3 à 17,8 images reçues/s ; l'état indiquait environ 18 FPS après optimisation. Des observations YOLO se situaient autour de 24 à 32 ms. Ces chiffres ne constituent pas une garantie pour un autre PC, pour des badges physiques ou pour un Raspberry Pi.

Une perte de caméra déclenche des tentatives de reconnexion toutes les trois secondes. Les états et badges anciens sont invalidés ; les résultats d'une ancienne connexion ne doivent pas être republiés après reconnexion. Une absence d'image récente masque également les associations périmées.

## 6. Tests et limites

Les dix tests automatisés passent : authentification, entrées invalides, photos, lecture des QR générés, deux QR et conversion des coordonnées, anti-répétition, activation/renouvellement, persistance, association ambiguë, panne/expiration, tampon et cadence de diffusion.

La compilation frontend, `pip check` et les vérifications du serveur réel/proxy réussissent. Le navigateur automatisé n'était pas disponible : le parcours visuel complet, les badges présentés physiquement, les croisements et la reconnexion matérielle restent à confirmer manuellement sur la machine de démonstration.

Le frontend conserve deux vulnérabilités signalées par `npm ci` dans l'arbre de dépendances existant et un avertissement de bundle supérieur à 500 Ko. Ce travail n'effectue pas une migration des bibliothèques de l'équipe DEV.

Le prototype ne gère pas encore l'édition/suppression des fiches, les comptes employés, les visiteurs, les droits par zone/horaire ni le déclenchement automatique d'actionneurs selon le badge. Le QR statique est copiable. La clé locale est une protection de prototype ; les routes vidéo restent sans authentification et le service reste limité à localhost par défaut.

## 7. Ce qui part sur GitHub et ce qui reste local

Sont versionnés : sources, exemples de configuration, liste des dépendances, tests et documentation.

Restent exclus : `.venv`, `node_modules`, `dist`, `.env.local`, modèle `.pt`, journaux et dossier `webcam-detection/.data` (base employés/photos/historique, secrets des badges, clé superviseur).

La base locale était vide au moment de la préparation de ce compte rendu. Sur l'autre PC, une nouvelle base vide et une nouvelle clé seront créées. GitHub ne transporte pas un environnement installé ni les données privées. Pour conserver un futur registre et ses QR, il faudra transférer sa base par un canal privé approprié ; ne pas la committer et ne pas copier la base pendant une écriture active.

## 8. Reprendre sur un autre PC Windows

Prérequis : Git, Python 3.13 et Node.js/npm. La configuration vérifiée dans cette session utilisait Python 3.13.1 et Node.js 22.15.0.

Pour un nouveau clone :

```powershell
git clone --branch IA-webcam-detection-reconnaissance-faciale --single-branch https://github.com/turbomulot/workshopm1.git
cd workshopm1
```

Si le dépôt existe déjà, conserver d'abord son travail local, puis :

```powershell
git fetch origin
git switch IA-webcam-detection-reconnaissance-faciale
git pull --ff-only
```

Depuis la racine, recréer l'environnement et installer les dépendances :

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r webcam-detection/requirements.txt
cd frontend
npm ci
```

Pour afficher aussi la caméra sur Supervision, créer `frontend/.env.local` avec ces lignes. Si un fichier local existe déjà, y ajouter les variables utiles en conservant les autres réglages :

```dotenv
VITE_CAMERA_URL=/access-api/video
VITE_ACCESS_API_URL=/access-api
```

Terminal 1, depuis la racine :

```powershell
.\.venv\Scripts\python.exe webcam-detection/stream_detection.py
```

Le modèle `yolov8n.pt` se télécharge au premier démarrage si absent : une connexion internet est nécessaire. Autoriser les applications de bureau à accéder à la caméra dans Windows si nécessaire.

Terminal 2, depuis la racine :

```powershell
cd frontend
npm run dev
```

Ouvrir `http://127.0.0.1:5173`, sélectionner Employés & badges, puis lire la nouvelle clé depuis la racine et la saisir dans le formulaire :

```powershell
Get-Content webcam-detection/.data/admin-token.txt
```

Ne pas afficher cette clé dans une capture ni la publier. Si la mauvaise caméra est sélectionnée, définir `$env:CAMERA_INDEX='1'` dans le terminal caméra avant le lancement (adapter l'index). Ne pas lancer les autres scripts webcam en parallèle du serveur.

Pour valider l'installation :

```powershell
# Depuis la racine
.\.venv\Scripts\python.exe -m pip check
cd webcam-detection
..\.venv\Scripts\python.exe -m unittest test_badges -v
cd ../frontend
npm run build
```

## 9. Suite du travail

Priorité : reproduire les tests sur l'autre PC, créer une fiche fictive, présenter le QR, vérifier la disparition du nom, désactiver/renouveler le badge et essayer deux personnes. Mesurer ensuite les performances sur une durée représentative.

Le développeur web peut reprendre la page et son client HTTP avec le guide DEV web ; les équipes DEV/CYBER pourront intégrer authentification, reverse proxy HTTPS, droits d'accès et stockage de production. La chaîne capteurs/IA prédictive reste un livrable distinct à intégrer pour le workshop.
