# Changelog et backlog — Partie IA (Sentinel-X)

Ce fichier est versionné dans Git. Il sert à deux choses :
1. **Historique** : ce qui a été fait, version par version (sections `[x.y.z]`).
2. **Backlog** : ce qu'il reste à faire et les idées à explorer (section `Backlog`).

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).

## Mode d'emploi (à lire une fois)

- Une tâche = une case : `- [ ]` à faire, `- [x]` fait.
- Quand une tâche est finie : coche-la, ajoute une ligne dans la prochaine version (section `[Non publié]`), puis commite le tout.
- Quand une version est prête : renomme `[Non publié]` en `[0.x.0] - date` et recrée une section `[Non publié]` vide au-dessus.
- Étiquettes : `[VISION]` (webcam, YOLO), `[PRÉDICTIF]` (capteurs, Isolation Forest), `[INTÉGRATION]` (API, MQTT, dashboard), `[DOC]`, `[SÉCU]`.
- Priorités : `P1` obligatoire pour le sujet, `P2` important, `P3` bonus.
- Message de commit conseillé : `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.

---

## [Non publié]

### Ajouté
- `stream_detection.py` : serveur Flask qui diffuse la caméra avec détection YOLO (`/video`), l'état courant (`/status`) et le journal des événements (`/logs`).
- Détection exécutée en arrière-plan (thread), indépendante des visiteurs de la page.
- Journal limité à 50 entrées, une ligne seulement quand l'état change (intrusion détectée, zone libre).
- Autorisation CORS pour que le frontend puisse lire les réponses.
- `requirements.txt` : liste des dépendances Python du projet.

### Modifié
- Journal : une ligne `Présence toujours détectée` toutes les 5 secondes tant que quelqu'un est présent, en plus de `Intrusion détectée` (arrivée) et `Zone libre` (départ).
- Route `/` qui liste les routes disponibles (évite le 404).
- (rien pour l'instant)

### Corrigé
- (rien pour l'instant)

---

## [0.1.0] - 2026-10-05

### Ajouté
- `test_webcam.py` : test de la webcam avec redimensionnement en 640x480 et affichage des FPS.
- `detection.py` : détection de personnes avec YOLOv8n (classe 0, seuil de confiance 0,5).
- Mesure de la latence d'inférence avec moyenne glissante sur 30 images (environ 30 ms sur MacBook Air).
- Alerte JSON (`source`, `type`, `score`, `timestamp`) à chaque intrusion détectée.
- Délai anti-spam de 5 secondes entre deux alertes.
- `.gitignore` : environnements virtuels, modèles `.pt`, secrets (`.env`, `*.key`, `*.pem`), logs, fichiers macOS.

### Tests manuels validés (2026-10-05)
- Présence continue devant la caméra : une alerte immédiate, puis une toutes les 5 secondes.
- Sortie du champ pendant 10 secondes : aucune alerte envoyée.
- Retour dans le champ : alerte quasi immédiate (plus de 5 secondes écoulées depuis la précédente).
- Scores de confiance observés : entre 0,60 et 0,93.

### Notes
- Les alertes sont affichées dans le terminal, pas encore envoyées à l'API.
- Latence mesurée sur MacBook Air : à revalider si le groupe choisit le Raspberry Pi 5 (option A).

---

# Backlog

## Décisions à prendre avec le groupe (lundi)

- [ ] `P1` `[INTÉGRATION]` Choisir l'option matérielle : A (Raspberry Pi 5) ou B (PC d'un apprenant). Conditionne le poids du modèle.
- [ ] `P1` `[INTÉGRATION]` Fixer le format JSON des alertes avec l'équipe DEV pour `POST /api/v1/alerts`.
- [ ] `P1` `[INTÉGRATION]` Obtenir de l'équipe INFRA l'adresse du broker MQTT, le nom des topics et le format des payloads de l'ESP8266.
- [ ] `P2` `[INTÉGRATION]` Décider comment la webcam arrive au dashboard (flux MJPEG, captures sur alerte, ou les deux).
- [ ] `P2` `[SÉCU]` Demander à l'équipe CYBER comment seront gérés les certificats TLS et les identifiants MQTT (variables d'environnement, jamais en clair).
- [ ] `P2` Se répartir les rôles du duo : un binôme sur la vision, l'autre sur le prédictif.

## Vision (webcam + YOLO)

### Reste à faire
- [ ] `P1` `[VISION]` Envoyer l'alerte JSON à l'API au lieu de l'afficher dans le terminal.
- [ ] `P1` `[VISION]` Tester la détection avec la webcam USB (index de caméra différent de celui du MacBook).
- [ ] `P1` `[VISION]` Mesurer la latence moyenne, minimale et maximale sur 1 minute, et noter les chiffres pour le dossier.
- [ ] `P1` `[VISION]` Lire la configuration (seuil, délai, URL de l'API, index caméra) depuis un fichier `.env` ou `config.py`.
- [ ] `P2` `[VISION]` Gérer proprement les pannes : caméra débranchée, API indisponible (réessayer plutôt que planter).
- [ ] `P2` `[VISION]` Sauvegarder une capture d'écran (image) à chaque alerte, utile comme preuve et pour le dashboard.
- [ ] `P2` `[VISION]` Tester le script sur le Raspberry Pi 5 si l'option A est retenue, et mesurer la latence réelle.
- [ ] `P2` `[VISION]` Ajouter un mode sans fenêtre (`--headless`) pour le serveur, qui n'a pas d'écran.
- [ ] `P2` `[DOC]` Documenter le choix de YOLOv8n, le seuil de confiance et la méthode de mesure de la latence.

### Idées à explorer
- [ ] `P3` `[VISION]` Zone d'intérêt (ROI) : ne déclencher l'alerte que si la personne est dans une zone définie.
- [ ] `P3` `[VISION]` Exporter le modèle en ONNX ou NCNN pour accélérer l'inférence sur Raspberry Pi.
- [ ] `P3` `[VISION]` Ne traiter qu'une image sur deux (frame skipping) si la latence dépasse 100 ms.
- [ ] `P3` `[VISION]` Compter le temps de présence : alerte « rôdeur » si quelqu'un reste plus de N secondes.
- [ ] `P3` `[VISION]` Mode faible luminosité : tester la détection dans une pièce sombre et ajuster le seuil.
- [ ] `P3` `[VISION]` Afficher dans l'interface le nombre de personnes et le score de confiance en temps réel.

## Maintenance prédictive (capteurs + Isolation Forest)

### Reste à faire
- [ ] `P1` `[PRÉDICTIF]` Script d'abonnement MQTT (`paho-mqtt`) qui enregistre température, humidité, gaz et présence dans un CSV horodaté.
- [ ] `P1` `[PRÉDICTIF]` Collecter un dataset « fonctionnement normal » (20 à 30 minutes, table calme).
- [ ] `P1` `[PRÉDICTIF]` Provoquer et noter des anomalies : chaleur sur le DHT22, gaz sans flamme sur le MQ-2, mouvement devant le PIR.
- [ ] `P1` `[PRÉDICTIF]` Calculer des features sur fenêtre glissante : moyenne, écart-type, pente, corrélation entre capteurs.
- [ ] `P1` `[PRÉDICTIF]` Entraîner l'Isolation Forest uniquement sur les données normales, sauvegarder le modèle avec `joblib`.
- [ ] `P1` `[PRÉDICTIF]` Faire tourner le modèle en direct : chaque message MQTT met à jour la fenêtre et le score.
- [ ] `P1` `[PRÉDICTIF]` Envoyer l'alerte d'anomalie à l'API (`source: "capteurs"`, `type: "anomalie"`, score, timestamp).
- [ ] `P1` `[PRÉDICTIF]` Aucune règle `if temp > seuil` : vérifier que tout passe par le modèle (interdit par le sujet).
- [ ] `P2` `[PRÉDICTIF]` Évaluer le modèle : tableau des anomalies provoquées contre celles détectées (détectées, manquées, fausses alertes).
- [ ] `P2` `[PRÉDICTIF]` Régler `contamination` et la taille de la fenêtre, et noter les essais.
- [ ] `P2` `[DOC]` Documenter les features, le choix du modèle et les résultats pour le dossier PDF.

### Idées à explorer
- [ ] `P3` `[PRÉDICTIF]` Comparer avec un second modèle (Random Forest, One-Class SVM) pour argumenter le choix.
- [ ] `P3` `[PRÉDICTIF]` Alerte « prédictive » : repérer la dérive lente avant le seuil critique (scénario du sujet).
- [ ] `P3` `[PRÉDICTIF]` Réentraînement périodique ou adaptation du modèle aux conditions de la pièce.
- [ ] `P3` `[PRÉDICTIF]` Courbe du score d'anomalie dans le temps, à proposer à l'équipe DEV pour le dashboard.
- [ ] `P3` `[PRÉDICTIF]` Lisser le score (moyenne sur N mesures) pour éviter les fausses alertes ponctuelles.

## Fusion vision + capteurs

- [ ] `P3` `[INTÉGRATION]` Corroboration : relever le niveau de gravité si la caméra voit une personne **et** le PIR détecte un mouvement.
- [ ] `P3` `[INTÉGRATION]` Score global de risque combinant l'état de la caméra et le score d'anomalie des capteurs.
- [ ] `P3` `[INTÉGRATION]` Détecter une incohérence (PIR actif mais personne vue) et la signaler comme alerte de niveau inférieur.

## Intégration et qualité

- [ ] `P1` `[INTÉGRATION]` Test de bout en bout mercredi : capteur physique, modèle, API, dashboard, avec la latence mesurée.
- [ ] `P1` `[DOC]` `requirements.txt` à jour (`pip freeze > requirements.txt`).
- [ ] `P1` `[DOC]` Section « Partie IA » ajoutée au `README.md` de l'équipe : installation, lancement, configuration. Ne pas écraser le README existant.
- [ ] `P2` `[INTÉGRATION]` Journalisation (`logging`) à la place des `print`, avec niveaux (info, warning, erreur).
- [ ] `P2` Tests unitaires simples (format JSON des alertes, calcul des features, anti-spam).
- [ ] `P2` Structurer le code en modules (`vision/`, `predictif/`, `common/`) quand les scripts grossissent.
- [ ] `P3` Script de lancement unique (`run.sh` ou `Makefile`) pour démarrer vision et prédictif ensemble.
- [ ] `P3` Dockerfile pour la partie IA, en accord avec l'équipe INFRA.

## Sécurité (avec l'équipe CYBER)

- [ ] `P1` `[SÉCU]` Aucun secret en clair dans le dépôt : mots de passe MQTT, clés et certificats dans `.env`, ignoré par Git.
- [ ] `P1` `[SÉCU]` Se connecter au broker en MQTTS (TLS) et vérifier le certificat.
- [ ] `P2` `[SÉCU]` Valider les messages reçus (champs attendus, plages de valeurs plausibles) avant de les donner au modèle.
- [ ] `P2` `[SÉCU]` Prévoir le pentest de jeudi : que fait le script si on lui envoie des messages mal formés ou en rafale ?
- [ ] `P2` `[SÉCU]` Limiter le nombre d'alertes par minute envoyées à l'API (protection contre le spam et le déni de service).
- [ ] `P3` `[SÉCU]` Surveiller l'usage CPU et RAM de la partie IA (maintien en condition opérationnelle).

## Documentation et rendus

- [ ] `P1` `[DOC]` Rédiger la documentation IA du dossier PDF : modèles, features, résultats, latence.
- [ ] `P2` `[DOC]` Garder des captures d'écran de la détection et des courbes pour le dossier et la vidéo.
- [ ] `P2` `[DOC]` Préparer les chiffres clés à citer à l'oral : latence, précision, nombre de fausses alertes.
- [ ] `P3` `[DOC]` Préparer une démo de secours (vidéo enregistrée) au cas où la webcam ou le Wi-Fi plante devant le jury.

---

## Planning indicatif de la semaine

| Jour | Objectif pour la partie IA |
|---|---|
| Lundi | Option A/B choisie, formats JSON et topics MQTT fixés, détection webcam fonctionnelle |
| Mardi | Dataset collecté, premier modèle prédictif entraîné, alertes envoyées à l'API |
| Mercredi | Intégration complète (capteurs, API, dashboard), mesures de latence |
| Jeudi | Gel du code, documentation IA, tests de robustesse pour le pentest |
| Vendredi | Démo live, soutenance, démo de secours prête |
