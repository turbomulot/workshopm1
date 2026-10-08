# Scénarios de test — détection et contrôle d'accès

Ce document décrit les tests manuels du contrôle d'accès Sentinel-X : détection par le PIR, vérification faciale par positions, badge QR, alerte, et comportement de la LED, de l'écran OLED, du buzzer et de la caméra.

Chaque scénario donne la préparation, les actions et le résultat attendu. Cochez la case « Résultat » et notez toute différence dans la colonne « Remarques » du tableau de synthèse, en fin de document.

## 1. Rappel du fonctionnement attendu

| Étape | Durée | LED | Écran OLED |
|---|---|---|---|
| Repos (aucune détection) | — | Verte | Mesures (gaz, humidité, température, mouvement) |
| Mouvement détecté : la caméra s'allume, 3 positions tirées au hasard parmi 4 | 6 s par position | Rouge | « Position 1/3 », consigne et temps restant |
| Visage non reconnu ou position manquée : badge demandé | 15 s | Rouge | « Visage non reconnu – Montrez le badge » |
| Ni visage ni badge : alerte | Tant que la personne est dans le champ de la caméra | Rouge | « ALERTE ENVOYEE » |
| Accès accepté (visage ou badge) | Caméra en veille 20 s après | Verte | « ACCES ACCEPTE » pendant 5 s |

Une vérification faciale réussie reste valable 1 minute : la même personne qui revient pendant ce délai passe au vert sans refaire les positions. Un badge ne vaut que pour le passage en cours.

Les 4 positions possibles sont : tête à gauche, tête à droite, menton levé, menton baissé. « Gauche » et « droite » s'entendent du point de vue de la personne testée.

## 2. Préparation

### Matériel et personnes

- Le boîtier ESP8266 flashé avec `firmware/`, connecté au même réseau Wi-Fi que le PC.
- La webcam branchée sur le PC.
- Un badge QR valide, imprimé ou affiché sur un téléphone.
- Trois personnes, si possible :
  - **Testeur A** : employé actif, visage enregistré, badge valide.
  - **Testeur B** : employé actif, visage enregistré.
  - **Testeur C** : personne inconnue, sans visage enregistré ni badge.
- Une photo imprimée ou affichée du visage du testeur A (scénario T13).
- Un briquet à gaz non allumé (scénario T19).

### Services à lancer

```bash
# 1. Broker MQTT, base de données et backend
cd backend && docker compose up -d

# 2. Service vision (caméra, visages, badges)
MQTT_HOST=localhost .venv/bin/python webcam-detection/stream_detection.py

# 3. Dashboard
cd frontend && npm run dev
```

Le journal du service vision doit afficher `Broker MQTT connecté` puis `Reconnaissance faciale prête`.

### Données à créer

Sur la page **Employés & badges** du dashboard (http://localhost:5173), avec la clé superviseur de `webcam-detection/.data/admin-token.txt` :

1. Créer la fiche du testeur A, enregistrer son visage et imprimer son badge.
2. Créer la fiche du testeur B et enregistrer son visage.
3. Créer une fiche « Testeur désactivé », enregistrer un visage, imprimer son badge, puis désactiver la fiche (scénarios T11 et T14).

**Refermer la page Employés & badges avant les tests** : tant qu'elle est ouverte, la caméra reste allumée en permanence (voir T17).

### Outils d'observation

- **Journal du service vision** : le terminal où tourne `stream_detection.py`.
- **Messages MQTT** échangés avec le boîtier :
  ```bash
  cd backend && docker compose exec mosquitto mosquitto_sub -t 'sentinel/#' -v
  ```
- **État du service vision** : http://127.0.0.1:5001/status (champs `veille`, `detection`, `personnes`).
- **Vidéo annotée** : http://127.0.0.1:5001/video.
- **Alertes enregistrées** : http://localhost:3000/api/v1/alerts.

### Avant chaque scénario

- Attendre que la caméra soit en veille (`"veille": true` dans `/status`) et que la LED soit verte.
- Sortir du champ du PIR et de la caméra pendant au moins 5 s : la séquence ne démarre que sur un **nouveau** mouvement.
- Pour les scénarios qui supposent une première visite, attendre plus d'1 minute depuis la dernière vérification faciale réussie du testeur.

### Raccourcir les délais (facultatif)

Pour enchaîner les tests plus vite, relancer le service vision avec des délais plus courts :

| Variable | Défaut | Rôle |
|---|---|---|
| `FACE_POSITION_S` | 6 | Temps par position |
| `ACCESS_BADGE_S` | 15 | Temps pour présenter le badge |
| `ACCESS_VALID_S` | 60 | Validité d'une vérification faciale réussie |
| `ACCESS_RECOGNISED_S` | 20 | Caméra encore allumée après un accès accepté |
| `ACCESS_ALERT_CLEAR_S` | 3 | Absence dans le champ qui met fin à une alerte |

Les résultats attendus ci-dessous utilisent les valeurs par défaut.

## 3. Scénarios

### T01 — Repos et mise en veille

**Objectif** : sans détection, la caméra reste éteinte.

1. Démarrer tous les services. Ne passer devant ni le PIR ni la caméra pendant 1 minute.

**Attendu** :
- `/status` indique `"veille": true` ; `/video` affiche « Camera en veille - en attente du PIR ».
- LED verte, écran OLED sur les mesures, buzzer muet.

Résultat : ☐ OK ☐ KO

### T02 — Préchauffage au démarrage du boîtier

**Objectif** : aucune alerte pendant la première minute après la mise sous tension.

1. Débrancher puis rebrancher le boîtier.
2. Passer devant le PIR dans les 60 premières secondes.

**Attendu** :
- Aucune alerte `motion` ni `gas` publiée sur `sentinel/alerts` pendant cette minute.
- Après 1 minute, un passage devant le PIR déclenche normalement la séquence.

Résultat : ☐ OK ☐ KO

### T03 — Visage reconnu, positions réussies

**Objectif** : cas nominal de la reconnaissance faciale.

1. Le testeur A entre dans le champ du PIR et se place face à la caméra.
2. Il suit les 3 consignes affichées sur l'écran OLED, chacune en moins de 6 s.

**Attendu** :
- Dès la détection : caméra allumée, LED rouge, écran « Position 1/3 » avec la consigne et le temps restant.
- Les 3 positions s'enchaînent ; les consignes diffèrent d'un essai à l'autre (tirage au hasard).
- Après la 3ᵉ position : LED verte, écran « ACCES ACCEPTE », journal `Accès accepté par visage`.
- Caméra en veille 20 s après l'acceptation.
- Aucun son du buzzer.

Résultat : ☐ OK ☐ KO

### T04 — Retour de la même personne dans la minute

**Objectif** : une vérification faciale réussie dispense des positions pendant 1 minute.

1. Juste après T03, le testeur A sort du champ, attend la mise en veille de la caméra, puis revient devant le PIR avant la fin de la minute.

**Attendu** :
- Caméra allumée, puis LED verte en 1 à 2 s, sans positions demandées.
- Écran « ACCES ACCEPTE ».

Résultat : ☐ OK ☐ KO

### T05 — Retour de la même personne après la minute

**Objectif** : passé 1 minute, la séquence complète recommence.

1. Le testeur A revient devant le PIR plus d'1 minute après sa vérification réussie.

**Attendu** : séquence complète, comme en T03 (LED rouge, 3 positions).

Résultat : ☐ OK ☐ KO

### T06 — Autre personne enregistrée pendant la minute du testeur A

**Objectif** : la minute de validité est propre à la personne reconnue.

1. Le testeur A réussit ses positions (T03).
2. Dans la minute, après la mise en veille, le testeur B passe seul devant le PIR.

**Attendu** :
- La LED reste rouge, les positions sont demandées au testeur B.
- S'il les réussit : LED verte, accès accepté.

Résultat : ☐ OK ☐ KO

### T07 — Position manquée

**Objectif** : un échec de position fait passer au badge.

1. Le testeur A passe devant le PIR.
2. À la 2ᵉ consigne, il fait un autre mouvement que celui demandé, ou reste immobile.

**Attendu** :
- Au bout des 6 s de la position : écran « Visage non reconnu – Montrez le badge », avec 15 s de compte à rebours.
- LED rouge. Journal `Visage non reconnu : présentation du badge demandée`.

Résultat : ☐ OK ☐ KO

### T08 — Personne inconnue

**Objectif** : un visage non enregistré n'est pas accepté.

1. Le testeur C passe devant le PIR et se place face à la caméra.

**Attendu** :
- Écran « Position 1/3 », puis, au bout de 6 s, demande du badge.
- LED rouge. Sur `/video`, rectangle « présence non authentifiée ».

Résultat : ☐ OK ☐ KO

### T09 — Badge valide

**Objectif** : le badge permet l'accès quand le visage n'est pas reconnu.

1. Le testeur C passe devant le PIR (même début que T08).
2. Quand l'écran demande le badge, il présente le badge valide du testeur A devant la caméra.

**Attendu** :
- LED verte, écran « ACCES ACCEPTE », journal `Accès accepté par badge`.
- Sur `/video`, le rectangle passe de « présence non authentifiée » à « Personne authentifiée (badge) : Prénom Nom », et le reste une fois le badge rangé, tant qu'une seule personne est dans l'image.
- Caméra en veille 20 s après.

Résultat : ☐ OK ☐ KO

**Variante** : présenter le badge dès le début, pendant les positions. Attendu : accès accepté immédiatement.

### T10 — Retour après un accès par badge

**Objectif** : un badge ne vaut que pour le passage en cours.

1. Juste après T09, sortir du champ, attendre la mise en veille, puis revenir devant le PIR avant la fin de la minute.

**Attendu** :
- Séquence complète : LED rouge, positions, puis badge à présenter de nouveau.
- Le rectangle n'affiche plus « Personne authentifiée (badge) ».

Résultat : ☐ OK ☐ KO

### T11 — Badge désactivé ou inconnu

**Objectif** : un badge refusé ne donne pas l'accès.

1. Le testeur C passe devant le PIR.
2. À la demande du badge, il présente le badge de la fiche désactivée, ou un QR code quelconque.

**Attendu** :
- Rectangle rouge « Badge désactivé » ou « Badge inconnu ».
- LED rouge. À la fin des 15 s, alerte (voir T12).

Résultat : ☐ OK ☐ KO

### T12 — Alerte : ni visage ni badge

**Objectif** : l'alerte est envoyée et maintenue tant que la personne est présente.

1. Le testeur C passe devant le PIR et reste face à la caméra, sans badge.
2. Il reste dans le champ de la caméra au moins 30 s après l'alerte.
3. Il sort du champ de la caméra.

**Attendu** :
- Après les positions et les 15 s du badge : écran « ALERTE ENVOYEE », LED rouge, journal `Personne non identifiée (ni visage ni badge) : alerte envoyée`.
- Une alerte `intrusion` de niveau `critical`, source `vision`, dans http://localhost:3000/api/v1/alerts et dans la liste des alertes du dashboard.
- Tant que la personne est dans le champ : écran « ALERTE ENVOYEE » et LED rouge maintenus ; message `{"alerte": true}` chaque seconde sur `sentinel/vision`.
- Environ 3 s après sa sortie : journal `Personne sortie du champ de la caméra : fin de l'alerte`, caméra en veille, puis l'écran revient aux mesures.
- Le buzzer ne sonne pas (il est réservé au gaz).

Résultat : ☐ OK ☐ KO

### T13 — Photo du visage d'un employé

**Objectif** : une photo ne passe pas les positions.

1. Le testeur C passe devant le PIR en tenant face à la caméra une photo du testeur A.
2. Il incline ou décale la photo pour tenter de suivre les consignes.

**Attendu** :
- Le visage de la photo peut être identifié, mais aucune position n'est validée.
- Au bout de 6 s : demande du badge, puis alerte sans badge.

Résultat : ☐ OK ☐ KO

### T14 — Fiche désactivée avec visage enregistré

**Objectif** : un employé désactivé n'est pas accepté par son visage.

1. La personne de la fiche désactivée passe devant le PIR et réussit les 3 positions.

**Attendu** :
- Pas d'accès : vérification « fiche désactivée », passage à la demande du badge, LED rouge.

Résultat : ☐ OK ☐ KO

### T15 — Personne qui reste devant le PIR

**Objectif** : la séquence ne redémarre pas en boucle.

1. Le testeur C déclenche une séquence et reste immobile devant le PIR et la caméra jusqu'à l'alerte, puis 1 minute de plus.

**Attendu** :
- Une seule séquence et une seule alerte.
- Aucune nouvelle séquence tant que la personne ne quitte pas le champ du PIR puis ne revient pas.

Résultat : ☐ OK ☐ KO

### T16 — Plusieurs personnes dans le champ

**Objectif** : vérifier le comportement avec deux personnes.

1. Le testeur A et le testeur C passent ensemble devant le PIR, le testeur A au premier plan.
2. Refaire l'essai avec le testeur C au premier plan.

**Attendu** :
- Le visage pris en compte est le plus grand, c'est-à-dire celui de la personne la plus proche de la caméra.
- Testeur A au premier plan : il peut valider ses positions.
- Testeur C au premier plan : demande du badge, puis alerte.
- Après un badge accepté, l'étiquette « Personne authentifiée (badge) » ne s'affiche pas tant que deux personnes sont dans l'image.

Résultat : ☐ OK ☐ KO

### T17 — Page Employés & badges

**Objectif** : la caméra s'allume sans détection quand la page est ouverte.

1. La caméra étant en veille, ouvrir la page **Employés & badges** et saisir la clé superviseur.
2. Fermer la page, ou se déconnecter.

**Attendu** :
- La caméra s'allume en 1 à 2 s, sans passage devant le PIR ; la vidéo s'affiche sur la page.
- Environ 5 s après la fermeture : caméra en veille.

Résultat : ☐ OK ☐ KO

### T18 — Broker MQTT arrêté

**Objectif** : fonctionnement dégradé sans broker.

1. Arrêter le broker : `cd backend && docker compose stop mosquitto`.
2. Observer la caméra et le boîtier, puis relancer : `docker compose start mosquitto`.

**Attendu** :
- Broker arrêté : la caméra reste allumée en permanence ; le boîtier garde son alarme gaz locale.
- Broker relancé : le service vision et le boîtier se reconnectent seuls ; la caméra repasse en veille ; le PIR pilote de nouveau la séquence.

Résultat : ☐ OK ☐ KO

### T19 — Gaz en warning et en critical

**Objectif** : le buzzer ne sonne que pour le gaz, et le gaz critique passe avant l'accès accepté.

**Sécurité** : briquet **non allumé**, pièce aérée, ne libérer le gaz que quelques secondes à environ 10 cm du capteur MQ-2.

1. Approcher le briquet du MQ-2 et libérer un peu de gaz.
2. Pendant une alarme critique, faire passer le testeur A et réussir ses positions.

**Attendu** :
- Valeur de gaz > 400 : un bip toutes les 2 s, alerte `gas` de niveau `warn`.
- Valeur de gaz > 700 : son continu, LED rouge, alerte `gas` de niveau `critical`.
- Pendant l'alarme critique, la LED reste rouge même après l'acceptation du testeur A.
- Retour à la normale quand la valeur redescend sous les seuils (avec une marge de 50).

Résultat : ☐ OK ☐ KO

### T20 — Boîtier hors ligne

**Objectif** : le dashboard signale la perte du boîtier.

1. Débrancher le boîtier pendant 30 s, puis le rebrancher.

**Attendu** :
- Après environ 15 s : le dashboard affiche « Connection lost ».
- Après le rebranchement : le boîtier se reconnecte ; le dashboard redevient normal (recharger la page si le message persiste).

Résultat : ☐ OK ☐ KO

### T21 — Aucun visage enregistré

**Objectif** : sans visage enregistré, la séquence passe directement au badge.

1. Lancer le service vision avec une base sans visage enregistré (par exemple un dossier de données vide).
2. Passer devant le PIR.

**Attendu** :
- Journal `Vérification faciale impossible : Aucun visage enregistré…`.
- Demande du badge immédiate, puis alerte au bout de 15 s sans badge.

Résultat : ☐ OK ☐ KO

## 4. Synthèse

| Test | Cas | Résultat | Remarques |
|---|---|---|---|
| T01 | Repos et mise en veille | | |
| T02 | Préchauffage | | |
| T03 | Visage reconnu, positions réussies | | |
| T04 | Retour dans la minute | | |
| T05 | Retour après la minute | | |
| T06 | Autre personne pendant la minute | | |
| T07 | Position manquée | | |
| T08 | Personne inconnue | | |
| T09 | Badge valide | | |
| T10 | Retour après un badge | | |
| T11 | Badge désactivé ou inconnu | | |
| T12 | Alerte maintenue jusqu'au départ | | |
| T13 | Photo du visage | | |
| T14 | Fiche désactivée | | |
| T15 | Personne qui reste devant le PIR | | |
| T16 | Plusieurs personnes | | |
| T17 | Page Employés & badges | | |
| T18 | Broker arrêté | | |
| T19 | Gaz warning et critical | | |
| T20 | Boîtier hors ligne | | |
| T21 | Aucun visage enregistré | | |

Date : ____________ Testeurs : ______________________ Version (commit) : ____________
