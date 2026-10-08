#pragma once
// MODÈLE — le vrai secrets.h ne doit JAMAIS être commité.
// (ajouter "secrets.h" au .gitignore du dossier firmware)
#define WIFI_SSID   "SentinelX-G11"     // Wi-Fi de table (infra)
#define WIFI_PASS   "..."
#define MQTT_SERVER "10.10.11.1"        // PC serveur (broker + heure)
#define MQTT_USER   "esp-g11"
#define MQTT_PASS   "..."               // security/secrets/mqtt_esp_password.txt
// Coller ici le contenu de security/pki/certs/ca.crt :
static const char CA_CERT[] PROGMEM = R"EOF(
-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----
)EOF";
