# Compte rendu webcam - SENTINEL-X

Date : 6 octobre 2026.

Ce compte rendu décrit l'état constaté avant l'ajout des badges QR. Pour l'implémentation ajoutée ensuite, consulter [le guide de reprise DEV web](../docs/REPRISE_DEV_WEB_BADGES.md), qui précise les évolutions du serveur, les nouveaux fichiers et les vérifications.

Sources : code du dépôt, vérifications réalisées pendant cette session et sujet « Workshop-2026-27 M1 - Sujet_Sentinel-X.pdf », notamment pages 2 à 4 et 7 à 8. Les exigences du sujet sont utilisées comme critères d'analyse ; elles ne constituent pas des instructions d'exécution supplémentaires.

## Rôle de la webcam dans le projet

La webcam constitue le capteur de vision de SENTINEL-X. Elle est raccordée directement au PC serveur local, qui peut être un ordinateur d'apprenant ou un Raspberry Pi 5 selon le choix du groupe. Le sujet impose une webcam USB, une analyse locale permettant d'isoler une présence humaine suspecte, un retour visuel dans le dashboard et un traitement inférieur à 100 ms par trame. Une résolution de 640 x 480 est proposée dans le sujet pour réduire la charge de calcul.

La vision doit s'intégrer au reste de la chaîne : acquisition, inférence, transmission des alertes à l'API, affichage dans le dashboard et, suivant les règles du système, commande des actionneurs. La reconnaissance d'identité par le visage n'est pas une exigence du sujet.

## Fonctionnement actuel

Le module utilise Python, OpenCV pour la capture et l'affichage, Ultralytics YOLOv8n pour détecter les personnes, PyTorch pour l'inférence et Flask pour l'accès HTTP.

| Fichier | Fonction |
| --- | --- |
| `test_webcam.py` | Ouvre une fenêtre locale avec le flux et les FPS ; touche Q pour quitter. |
| `detection.py` | Détecte les personnes, dessine les rectangles et affiche une alerte JSON dans le terminal, avec un intervalle minimal de cinq secondes. |
| `stream_detection.py` | Analyse en arrière-plan et expose la vidéo annotée, l'état et les événements sur le port 5001. |

La capture utilise l'index 0. Le backend est AVFoundation sur macOS et le backend automatique d'OpenCV sur Windows et Linux. Chaque image analysée est redimensionnée à 640 x 480. YOLO ne conserve que la classe personne avec un seuil de confiance de 0,5.

Le serveur fournit :

| Route | Contenu |
| --- | --- |
| `/video` | Flux MJPEG annoté. |
| `/status` | Présence détectée, nombre de personnes, durée de l'inférence et heure de l'analyse. |
| `/logs` | Jusqu'à 50 événements conservés en mémoire. |

Le journal du serveur enregistre les transitions entre présence et absence. Ce comportement diffère du script local `detection.py`, qui peut produire une nouvelle alerte après cinq secondes de présence continue.

## Travaux réalisés et preuves disponibles

- Création de l'environnement virtuel `.venv` et installation des dépendances caméra.
- Adaptation de NumPy : version 2.2.6 pour Python 3.13 et plus, maintien de 2.0.2 pour les versions précédentes. L'installation initiale de NumPy 2.0.2 échouait sur cette machine Python 3.13.
- Adaptation du choix du backend caméra pour Windows et Linux.
- Téléchargement local du modèle `yolov8n.pt` dans le dossier du module.
- Vérification des dépendances avec `pip check`, des imports et d'une inférence sur une image synthétique.
- Vérification du serveur réel : `/status` a répondu avec une personne détectée et une latence d'inférence de 25 ms ; `/logs` contenait des événements de présence et de retour à une zone libre.
- Windows signalait des périphériques USB Camera en état OK. Le périphérique réellement sélectionné à l'index 0 doit être confirmé pour la démonstration finale.

Ces vérifications prouvent un fonctionnement ponctuel du module. La mesure de 25 ms n'est ni une moyenne, ni une mesure de la chaîne complète ; elle ne suffit pas à démontrer à elle seule le respect de l'objectif de 100 ms par trame.

Lors du diagnostic d'affichage, le serveur `stream_detection.py` était déjà lancé. Il ne crée pas de fenêtre OpenCV : son image se consulte sur `http://localhost:5001/video`. L'essai d'une seconde capture n'a pas obtenu d'image alors que le serveur utilisait la caméra. Pour un test local fiable, il faut fermer le serveur avant de lancer `test_webcam.py`.

## Comparaison avec les exigences du sujet

| Attendu | État constaté | Travail restant |
| --- | --- | --- |
| Webcam USB sur le serveur local | Périphériques USB détectés ; capture serveur fonctionnelle | Confirmer que l'index 0 correspond à la webcam USB retenue. |
| Script Python local de vision | Réalisé | Vérifier sur le matériel final choisi par le groupe. |
| Détection de présence humaine | Réalisée avec YOLOv8n | Évaluer les personnes manquées et les fausses détections. |
| Redimensionnement des images | Réalisé en 640 x 480 | Mesurer son effet sur précision et performances. |
| Traitement inférieur à 100 ms | Une inférence observée à 25 ms | Mesurer capture, redimensionnement, inférence, annotation et encodage sur une durée représentative. |
| Retour vidéo dans le dashboard | Flux HTTP disponible | Configurer le frontend et vérifier l'affichage de bout en bout. |
| Centralisation des alertes | Partielle : journal mémoire et JSON terminal | Envoyer les événements à `POST /api/v1/alerts` et les enregistrer côté backend. |
| Documentation IA | README, backlog et présent compte rendu | Ajouter les résultats de tests et captures au dossier collectif. |

Le sujet impose aussi la maintenance prédictive sur les capteurs : ce livrable est distinct de la vision et n'est pas validé par le fonctionnement de la webcam.

## Limites techniques actuelles

**Présence et intrusion.** Le code appelle toute apparition d'une personne « intrusion ». YOLO détecte une personne ; il ne connaît ni son identité, ni son droit d'accès. Pour une décision exploitable, il faut une règle de zone surveillée, de période de surveillance ou une validation d'accès indépendante.

**Intégration frontend.** Le dashboard est en mode simulé par défaut. Il attend notamment `/api/v1/ai/latest` et `/api/v1/camera/stream`, alors que Flask expose `/status` et `/video` avec d'autres formats. `VITE_CAMERA_URL=http://localhost:5001/video` peut définir le flux lorsque `VITE_USE_MOCK=false`, mais cela ne fournit pas les autres routes backend attendues. Pour une autre machine, remplacer localhost par l'adresse du serveur.

**Pannes et état périmé.** Si la lecture caméra échoue, le thread d'analyse s'arrête sans tentative de reconnexion. L'état et la dernière image peuvent rester affichés. Il faut exposer un indicateur caméra connectée, un horodatage exploitable et un état indisponible après expiration des données.

**Qualité des alertes.** Des passages rapides entre présence et absence sont visibles dans le journal. Le serveur ne possède pas le délai anti-spam du script local. Une confirmation temporelle et un délai entre alertes limiteraient les événements répétitifs.

**Synchronisation et arrêt.** Le verrou protège l'image, mais pas l'ensemble du dictionnaire d'état et du journal. Un instantané cohérent doit être produit pour les lecteurs HTTP. L'arrêt doit libérer explicitement la caméra. Le serveur est aussi lancé dès l'import du module, ce qui complique les tests.

**Sécurisation.** Le serveur Flask actuel écoute sur toutes les interfaces, sans authentification, en HTTP et avec CORS ouvert. Pour l'intégration finale, prévoir un accès authentifié, une restriction des origines et une terminaison HTTPS avec l'équipe CYBER. Le chiffrement obligatoire décrit dans le sujet concerne notamment le lien ESP8266 vers la stack serveur ; sa validation appartient au travail collectif.

## Évolution proposée : identification par justificatif d'accès

Une évolution sans identification biométrique peut associer la détection de présence à la présentation volontaire d'un badge QR ou RFID/NFC. Elle reste une proposition, non implémentée dans cette version.

1. La webcam détecte une présence, sans déterminer d'identité.
2. La personne présente son badge à un point de passage dédié.
3. Le serveur valide le justificatif et les droits pour la zone et la période concernées.
4. L'interface affiche le nom et le prénom associés au justificatif validé, ainsi que le statut d'accès.
5. Une présence sans validation reçoit le statut « présence non authentifiée » ; une alerte peut être déclenchée selon les règles de surveillance.

Le nom doit provenir du registre serveur, pas d'un texte libre dans le QR code. Pour un prototype, utiliser des identités fictives et des justificatifs de démonstration. Pour une intégration opérationnelle, prévoir expiration, révocation et résistance à la copie ou au rejeu des justificatifs.

Un badge valide ne prouve pas que son porteur est son titulaire. Il ne doit pas autoriser automatiquement toutes les personnes visibles dans l'image. La validation doit concerner un passage individuel ; les visiteurs autorisés doivent pouvoir être représentés. Le statut recommandé à l'écran est « badge valide - accès autorisé », accompagné du nom associé au badge, plutôt qu'une affirmation d'identité tirée de la vidéo.

## Priorités pour terminer la partie webcam

1. Brancher le flux vidéo et les événements réels dans le dashboard, en harmonisant les routes et les formats avec l'équipe DEV.
2. Mesurer les performances sur le matériel final : moyenne, médiane, maximum et percentile 95 du temps de traitement complet, puis délai jusqu'à l'affichage de l'alerte.
3. Tester absence, une personne, plusieurs personnes, éclairage faible, débranchement et reconnexion ; noter les détections correctes, manquées et fausses alertes.
4. Ajouter configuration externe, reprise caméra, indication d'état périmé, temporisation des alertes et arrêt propre.
5. Préparer les preuves pour le dossier et la soutenance : schéma du flux, captures annotées, mesures et démonstration de bout en bout.

La base de vision est fonctionnelle. La priorité du workshop est maintenant de démontrer son intégration fiable au système complet ; l'identification par justificatif d'accès peut ensuite être ajoutée comme évolution distincte.
