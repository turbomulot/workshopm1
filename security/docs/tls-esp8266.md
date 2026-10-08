# Exigences TLS du boîtier ESP8266 (pour le dev)

Le boîtier doit se connecter au broker en **MQTTS** (port 8883) et **vérifier le certificat du serveur**. Sans cette vérification, n'importe qui peut monter un faux broker sur le Wi-Fi et recevoir les mesures ou envoyer de fausses commandes : c'est la première chose testée au pentest.

Le firmware déjà adapté (mêmes capteurs, mêmes topics `sentinel/*`, mêmes commandes `{ "buzzer": true, "led": "red" }`, seulement le transport sécurisé) est fourni prêt à l'emploi dans **`security/integration/firmware/main.cpp`** — il compile pour la carte `nodemcuv2`. Ce document explique les règles qu'il applique, pour comprendre et vérifier.

## Les règles

1. **Faire confiance uniquement à la CA du groupe** (`ca.crt`, fournie par la cyber) : `espClient.setTrustAnchors(&caCert)`.
2. **Jamais `setInsecure()`**, même « pour tester » : c'est une faille, pas un raccourci.
3. **Récupérer l'heure (NTP) avant la connexion TLS** : sans heure, l'ESP ne peut pas vérifier la validité du certificat et refuse la connexion. Serveur d'heure = le PC serveur (`MQTT_SERVER`), serveurs publics en secours.
4. **Les secrets ne vont jamais dans Git** : Wi-Fi, compte MQTT et certificat dans `secrets.h`, à ajouter au `.gitignore`. Ne commiter qu'un `secrets.example.h` sans valeurs.
5. **Se connecter avec un compte** : `client.connect(id, MQTT_USER, MQTT_PASS)` — le compte `esp-g<n>` fourni par la cyber, limité par l'ACL à ses propres topics.
6. **Garder le même contrat que le backend** : publier sur `sentinel/sensors` et `sentinel/alerts`, s'abonner à `sentinel/cmd`, commandes au format `{ "buzzer": bool, "led": "red"|"green"|"off" }`.

## `secrets.h` (modèle : `security/integration/firmware/secrets.example.h`)

Valeurs fournies par la cyber : `esp-g<n>`, son mot de passe (`security/secrets/mqtt_esp_password.txt`) et le contenu de `security/pki/certs/ca.crt`.

## Comment vérifier

- Moniteur série : la connexion passe, aucune ligne d'erreur `TLS:` ne reste, l'écran affiche `MQTTS OK !`.
- Faux broker (test cyber) : un broker avec un certificat d'une autre autorité est refusé.
- Wireshark sur le port 8883 : uniquement du « TLS Application Data », aucune mesure lisible.
