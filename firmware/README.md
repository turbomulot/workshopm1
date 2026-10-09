# Sentinel-X — Firmware du boîtier ESP8266

Projet PlatformIO pour l'ESP8266 (NodeMCU ESP-12E) : capteurs (gaz MQ-2, DHT22, PIR), écran OLED, LED bicolore et buzzer, reliés au broker MQTT du backend.

## Installation

1. Copier `include/secrets.example.h` en `include/secrets.h`, puis renseigner le Wi-Fi et l'adresse IP du PC qui fait tourner le broker. `secrets.h` n'est jamais commité.
2. Ouvrir ce dossier `firmware/` dans PlatformIO, puis téléverser (`pio run -t upload`).

## Câblage

| Composant | Broche |
|---|---|
| MQ-2 (AO, via 220 kΩ) | A0 |
| PIR HC-SR501 | D5 |
| DHT22 | D6 |
| OLED SSD1306 (SCL / SDA) | D1 / D2 |
| Buzzer actif | D3 |
| LED rouge / LED verte (220 Ω) | D4 / D8 |

D3 et D4 sont des broches de démarrage : si l'ESP démarre mal, déplacer le buzzer sur D7 et la LED rouge sur D0, puis changer `brocheBuzzer` et `brocheLedRouge` dans `src/main.cpp`.

## Topics MQTT (racine `sentinel`)

| Topic | Sens | Contenu |
|---|---|---|
| `sensors` | ESP → broker, toutes les 2 s | `{temp, hum, gas, pir, ts}` (`null` si capteur en erreur) |
| `alerts` | ESP → broker | `{type: "motion" \| "gas" \| "temp_rise" \| "fire", level, value}` (`temp_rise` : hausse en °C ; `fire` : valeur du gaz) |
| `status` | ESP → broker | `online`, ou `offline` publié par le broker (Last Will) |
| `cmd` | dashboard → ESP | `{buzzer: bool, led: "red" \| "green" \| "off"}` |
| `vision` | service caméra → ESP | `{reconnu}` (LED), `{alerte: true}` (LED rouge maintenue), `{verification, etape, total, restant}` (écran) |

Comportement local, même sans broker : gaz > 700 = buzzer continu et LED rouge, gaz > 400 = bip toutes les 2 s. Hausse de température de 3 °C ou plus en moins d'1 minute = bip rapide (500 ms chaque seconde) et alerte `temp_rise` de niveau `critical` ; l'alarme s'arrête environ 1 minute après la fin de la hausse. Gaz qui monte de 100 points ou plus **et** température qui monte de 3 °C ou plus dans la même minute = alerte `fire` (`critical`) : buzzer continu, LED rouge et écran « ALERTE INCENDIE », prioritaire sur les autres écrans. Aucune alerte pendant la première minute (préchauffage du MQ-2 et du PIR). La séquence de contrôle d'accès est décrite dans le [README du module vision](../webcam-detection/README.md).
