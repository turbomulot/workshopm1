// Modèle : copier en secrets.h et remplir les valeurs.
#pragma once

#define WIFI_SSID     "mon-reseau"
#define WIFI_PASSWORD "mon-mot-de-passe"

// Adresse IP du PC qui fait tourner le broker (docker compose du backend).
#define MQTT_SERVER   "192.168.137.1"
#define MQTT_PORT     1883
// Laisser vide si le broker n'exige pas d'authentification.
#define MQTT_USER     ""
#define MQTT_PASSWORD ""
