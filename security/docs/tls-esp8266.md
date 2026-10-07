# Exigences TLS du boîtier ESP8266 (pour le dev)

Le boîtier doit se connecter au broker en **MQTTS** (port 8883) et **vérifier le certificat du serveur**. Sans cette vérification, n'importe qui peut monter un faux broker sur le Wi-Fi et recevoir les mesures ou envoyer de fausses commandes : c'est la première chose testée au pentest de jeudi.

## Les règles

1. **Faire confiance uniquement à la CA du groupe** (`ca.crt`, fournie par la cyber) : `setTrustAnchors()`.
2. **Jamais `setInsecure()`**, même « pour tester » : c'est une faille, pas un raccourci.
3. **Récupérer l'heure (NTP) avant la connexion TLS** : sans heure, l'ESP ne peut pas vérifier la date de validité du certificat et refuse la connexion. Le serveur d'heure est le PC serveur (`SERVER_IP`).
4. **Les secrets ne vont jamais dans Git** : Wi-Fi, compte MQTT et certificat dans `include/secrets.h`, déjà ignoré par Git (règle `secrets.*` du `.gitignore`). Ne commiter qu'un `secrets.example.h` sans valeurs.
5. **Commandes en liste blanche** : n'exécuter que les commandes prévues (`BUZZER_ON`, `LED_RED_ON`…), ignorer tout le reste.
6. **Chaque mesure porte un numéro (`seq`) et une heure (`ts`)**, pour que le backend puisse rejeter les messages rejoués.

## `include/secrets.h` (modèle, valeurs fournies par la cyber)

```cpp
#pragma once
#define GROUP_NUM  "11"
#define SERVER_IP  "10.10.11.1"            // broker MQTTS + serveur d'heure
#define WIFI_SSID  "..."                   // Wi-Fi de table (infra)
#define WIFI_PASS  "..."
#define MQTT_USER  "esp-g11"
#define MQTT_PASS  "..."                   // security/secrets/mqtt_esp_password.txt
static const char CA_CERT[] PROGMEM = R"EOF(
-----BEGIN CERTIFICATE-----
...contenu de security/pki/certs/ca.crt...
-----END CERTIFICATE-----
)EOF";
```

## Le code de connexion sécurisée

Bibliothèques : `knolleary/PubSubClient`, `bblanchon/ArduinoJson@^7`. Ce code a été compilé pour la carte `nodemcuv2` (Lolin v3).

```cpp
#include <ESP8266WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <time.h>
#include "secrets.h"

BearSSL::WiFiClientSecure net;
BearSSL::X509List trustAnchors(CA_CERT);   // seule autorité acceptée : celle du groupe
PubSubClient mqtt(net);

String topic(const char* leaf) { return String("sentinelx/g") + GROUP_NUM + "/" + leaf; }

void syncClock() {                          // règle 3 : l'heure avant le TLS
  configTime(0, 0, SERVER_IP);
  const uint32_t start = millis();
  while (time(nullptr) < 1700000000) {
    delay(250);
    if (millis() - start > 30000) ESP.restart();
  }
}

void connectMqtt() {
  const String status = topic("status");
  const String id = String("sx-g") + GROUP_NUM + "-" + String(ESP.getChipId(), HEX);
  while (!mqtt.connected()) {
    // Last Will : si le boîtier disparaît, le broker publie "offline" à sa place
    if (mqtt.connect(id.c_str(), MQTT_USER, MQTT_PASS, status.c_str(), 1, true, "offline")) {
      mqtt.publish(status.c_str(), "online", true);
      mqtt.subscribe(topic("cmd").c_str(), 1);
    } else {
      char err[80];
      net.getLastSSLError(err, sizeof(err));   // explique un refus TLS sur le port série
      Serial.printf("Connexion refusee (MQTT %d, TLS: %s)\n", mqtt.state(), err);
      delay(3000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  // ... connexion au Wi-Fi de table (WIFI_SSID / WIFI_PASS) ...
  syncClock();
  net.setTrustAnchors(&trustAnchors);                      // règle 1
  if (net.probeMaxFragmentLength(SERVER_IP, 8883, 1024))  // petits tampons TLS si possible
    net.setBufferSizes(1024, 1024);                        // (économise ~25 Ko de RAM)
  // règle 2 : PAS de net.setInsecure()
  mqtt.setServer(SERVER_IP, 8883);
  mqtt.setCallback(onCommand);                             // règle 5 : liste blanche dedans
  mqtt.setBufferSize(512);
}

void loop() {
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();                  // à appeler en continu : pas de delay() de plus d'une seconde
  // ... lecture des capteurs, publication sur topic("telemetry") avec seq et ts (règle 6) ...
}
```

## Comment vérifier

- Moniteur série : la connexion passe, et aucune ligne `Connexion refusee` ne reste.
- Test du faux broker (fait par la cyber jeudi) : un broker avec un certificat d'une autre autorité doit être refusé (`Connexion refusee ... TLS: ...`).
- Capture Wireshark sur le port 8883 : uniquement du « TLS Application Data », aucune mesure lisible.
