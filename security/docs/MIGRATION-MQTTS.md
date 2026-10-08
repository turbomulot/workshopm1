# Passage en MQTTS — guide pour l'équipe

But : chiffrer et authentifier la chaîne **boîtier → broker → backend**, aujourd'hui en clair. On ne change ni les capteurs, ni le dashboard, ni les topics `sentinel/*`. Seul le transport change : MQTT clair (port 1883) → MQTTS (port 8883, chiffré + mot de passe).

Réalisable en une demi-journée, réversible. **Règle d'or :** on teste le nouveau firmware sur la table AVANT de compter dessus pour la soutenance ; tant que ce n'est pas validé, l'ancien firmware en clair reste flashé.

Tout le monde utilise les **mêmes** certificats et comptes : ceux générés par le cyber à l'étape 1. Personne ne régénère de son côté, sinon plus rien ne se parle.

---

## Étape 1 — Cyber : générer et distribuer (fait)

```bash
cp security/.env.example security/.env     # GROUP_NUMBER=11, SERVER_IP=10.10.11.1
bash security/pki/make-pki.sh
bash security/mosquitto/make-accounts.sh
```

Puis distribution par **clé USB uniquement** (jamais par Git ni par message) :

**À Nino (serveur) :**
- `security/pki/certs/ca.crt` et le dossier `security/pki/certs/broker/`
- `security/mosquitto/mosquitto.conf`, `security/mosquitto/acl`, `security/mosquitto/passwd`
- `security/integration/docker-compose.backend.yml`
- le mot de passe du compte `api` (contenu de `security/secrets/mqtt_api_password.txt`)

**Au dev (boîtier) :**
- `security/pki/certs/ca.crt`
- le compte `esp-g11` et son mot de passe (contenu de `security/secrets/mqtt_esp_password.txt`)
- `security/integration/firmware/main.cpp` et `secrets.example.h`

Enfin, mettre `security/pki/certs/ca.key` sur la clé USB puis le supprimer du PC.

---

## Étape 2 — Nino (serveur) : broker et backend en TLS (~15 min)

Dans le dossier `backend/` du dépôt :

```bash
mkdir -p mosquitto certs secrets

# fichiers reçus du cyber (clé USB)
cp <clé>/mosquitto.conf  mosquitto/mosquitto.conf
cp <clé>/acl             mosquitto/acl
cp <clé>/passwd          mosquitto/passwd
cp <clé>/ca.crt          certs/ca.crt
cp -r <clé>/broker       certs/broker
cp <clé>/mqtt_api_password.txt  secrets/

# REMPLACER le docker-compose.yml par la version sécurisée
cp <clé>/docker-compose.backend.yml  docker-compose.yml

# dans .env : remplacer CORS_ORIGIN=* par l'URL du dashboard
#   CORS_ORIGIN=http://10.10.11.1:5173

docker compose up -d
```

Résultat : le broker écoute en 8883 (TLS), le port 1883 en clair disparaît, le backend se connecte avec le compte `api` et vérifie le certificat.

Vérifier que le backend est bien connecté :
```bash
docker compose logs backend | grep mqtt
# doit afficher : [mqtt] connecté à mqtts://mosquitto:8883
```

---

## Étape 3 — Dev (boîtier) : firmware sécurisé (~20 min + flash)

Dans le projet PlatformIO du boîtier :

```bash
cp <clé>/main.cpp           src/main.cpp
cp <clé>/secrets.example.h  .
```

Créer `secrets.h` (modèle `secrets.example.h`) avec les valeurs reçues :
- `WIFI_SSID` / `WIFI_PASS` : le Wi-Fi de table
- `MQTT_SERVER` : `10.10.11.1`
- `MQTT_USER` : `esp-g11`, `MQTT_PASS` : le mot de passe reçu
- `CA_CERT` : coller le contenu de `ca.crt`

Ajouter `secrets.h` au `.gitignore` (il ne doit jamais partir sur Git), puis flasher :

```bash
pio run -t upload
pio device monitor
```

À l'écran : `1/3 Wi-Fi` → `2/3 Heure` → `3/3` → **`MQTTS OK !`**.

Si ça bloque sur `3/3` : regarder le moniteur série, la ligne `TLS: ...` dit pourquoi (mauvais certificat, heure non synchronisée, mauvais compte).

---

## Étape 4 — Cyber : vérifier (preuves pour le dossier)

```bash
# BROKER_HOST = 10.10.11.1 dans security/.env
bash security/audit/test-broker.sh | tee security/audit/preuve-broker.txt
sudo tcpdump -i wlan0 -w preuve-mqtts.pcap port 8883   # Wireshark : uniquement du TLS
```

---

## Si quelque chose casse (retour arrière)

- Boîtier : re-flasher l'ancien firmware (branche `c_plus_plus`).
- Serveur : remettre l'ancien `docker-compose.yml` (branche `nino`), puis `docker compose up -d`.

On revient à la version en clair qui fonctionnait. À ne garder qu'en dernier recours : le but reste la version chiffrée.

---

## En plus (hors migration)

- Le mot de passe Wi-Fi écrit en dur dans l'ancien firmware reste dans l'historique Git : le changer sur le vrai routeur.
- `CORS_ORIGIN=*` → l'URL du dashboard (fait à l'étape 2).
