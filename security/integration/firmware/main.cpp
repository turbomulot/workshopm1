// Sentinel-X — firmware du boîtier, version SÉCURISÉE (MQTTS)
// Repris du firmware de l'équipe (branche c_plus_plus) : capteurs, écran et
// commandes INCHANGÉS, mêmes topics (sentinel/sensors, /alerts, /cmd).
// Seul le transport change : MQTT clair (1883) -> MQTTS chiffré (8883),
// avec vérification du certificat du broker et compte + mot de passe.
// Les identifiants sortent du code : ils vont dans secrets.h (jamais commité).
#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>
#include <ESP8266WiFi.h>
#include <WiFiClientSecure.h>   // + TLS
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <time.h>
#include "secrets.h"            // WIFI_SSID, WIFI_PASS, MQTT_SERVER, MQTT_USER, MQTT_PASS, CA_CERT

const int mqtt_port = 8883;     // MQTTS (était 1883 en clair)

Adafruit_SSD1306 display(128, 64, &Wire, -1);

const int brocheGaz = A0;
const int brocheHumidite = D6;
const int brochePIR = D5;

const int brocheBuzzer = D3;
const int brocheLedRouge = D4;
const int brocheLedVerte = D8;

#define DHTTYPE DHT22
DHT dht(brocheHumidite, DHTTYPE);

BearSSL::WiFiClientSecure espClient;       // était WiFiClient
BearSSL::X509List caCert(CA_CERT);         // autorité du groupe
PubSubClient client(espClient);

unsigned long dernierEnvoi = 0;

void receptionCommande(char* topic, byte* payload, unsigned int length) {
  StaticJsonDocument<200> docCmd;
  DeserializationError error = deserializeJson(docCmd, payload, length);

  if (!error) {
    if (docCmd.containsKey("buzzer")) {
      bool activeBuzzer = docCmd["buzzer"];
      digitalWrite(brocheBuzzer, activeBuzzer ? HIGH : LOW);
    }

    if (docCmd.containsKey("led")) {
      const char* etatLed = docCmd["led"];
      if (strcmp(etatLed, "red") == 0) {
        digitalWrite(brocheLedRouge, HIGH);
        digitalWrite(brocheLedVerte, LOW);
      } else if (strcmp(etatLed, "green") == 0) {
        digitalWrite(brocheLedRouge, LOW);
        digitalWrite(brocheLedVerte, HIGH);
      } else if (strcmp(etatLed, "off") == 0) {
        digitalWrite(brocheLedRouge, LOW);
        digitalWrite(brocheLedVerte, LOW);
      }
    }
  }
}

void reconnect() {
  while (!client.connected()) {
    display.clearDisplay();
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println("Connexion MQTTS...");
    display.print("IP: "); display.println(MQTT_SERVER);
    display.display();

    String clientId = "SentinelNode-";
    clientId += String(random(0xffff), HEX);

    // + compte et mot de passe (était client.connect(clientId) sans identifiants)
    if (client.connect(clientId.c_str(), MQTT_USER, MQTT_PASS)) {
      client.subscribe("sentinel/cmd");
      display.println("MQTTS OK !");
      display.display();
      delay(1000);
    } else {
      char err[80];
      espClient.getLastSSLError(err, sizeof(err));   // explique un refus TLS
      display.print("Echec ("); display.print(client.state()); display.println(")");
      display.println(err);
      display.display();
      Serial.printf("Echec MQTT %d, TLS: %s\n", client.state(), err);
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  dht.begin();

  pinMode(brochePIR, INPUT);
  pinMode(brocheBuzzer, OUTPUT);
  pinMode(brocheLedRouge, OUTPUT);
  pinMode(brocheLedVerte, OUTPUT);

  digitalWrite(brocheBuzzer, LOW);
  digitalWrite(brocheLedRouge, LOW);
  digitalWrite(brocheLedVerte, LOW);

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) for (;;);
  display.setTextColor(SSD1306_WHITE);

  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("1/3 Wi-Fi...");
  display.display();

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(500); }   // (le ')' en trop a été retiré)

  display.println("Wi-Fi OK!");
  display.println("2/3 Synchro Heure...");
  display.display();

  // L'heure est OBLIGATOIRE avant le TLS (vérification de la validité du certificat).
  // Serveur d'heure = le PC serveur (MQTT_SERVER), avec les serveurs publics en secours.
  configTime(0, 0, MQTT_SERVER, "pool.ntp.org", "time.nist.gov");
  int timeoutNTP = 0;
  while (time(nullptr) < 1000000000 && timeoutNTP < 40) {
    delay(500);
    timeoutNTP++;
  }

  display.println("3/3 Serveur MQTTS...");
  display.display();
  delay(1000);

  espClient.setTrustAnchors(&caCert);      // n'accepte que la CA du groupe (PAS setInsecure)
  espClient.setBufferSizes(1024, 1024);    // économise de la RAM pendant la poignée de main

  client.setServer(MQTT_SERVER, mqtt_port);
  client.setCallback(receptionCommande);
}

void loop() {
  if (!client.connected()) { reconnect(); }
  client.loop();

  unsigned long tempsActuel = millis();

  if (tempsActuel - dernierEnvoi >= 2000) {
    dernierEnvoi = tempsActuel;

    int valeurGaz = analogRead(brocheGaz);
    float tauxHumidite = dht.readHumidity();
    float temperature = dht.readTemperature();
    int etatPIR = digitalRead(brochePIR);
    long timestamp = time(nullptr);

    StaticJsonDocument<200> docSensors;
    docSensors["temp"] = isnan(temperature) ? 0 : temperature;
    docSensors["hum"] = isnan(tauxHumidite) ? 0 : tauxHumidite;
    docSensors["gas"] = valeurGaz;
    docSensors["pir"] = etatPIR;
    docSensors["ts"] = timestamp;

    char payloadSensors[200];
    serializeJson(docSensors, payloadSensors);
    client.publish("sentinel/sensors", payloadSensors);

    if (etatPIR == HIGH) {
      StaticJsonDocument<100> docAlertPIR;
      docAlertPIR["type"] = "motion";
      docAlertPIR["level"] = "warn";
      docAlertPIR["value"] = 1;
      char alertPIR[100];
      serializeJson(docAlertPIR, alertPIR);
      client.publish("sentinel/alerts", alertPIR);
    }

    if (valeurGaz > 400) {
      StaticJsonDocument<100> docAlertGaz;
      docAlertGaz["type"] = "gas";
      docAlertGaz["level"] = (valeurGaz > 700) ? "critical" : "warn";
      docAlertGaz["value"] = valeurGaz;
      char alertGaz[100];
      serializeJson(docAlertGaz, alertGaz);
      client.publish("sentinel/alerts", alertGaz);
    }

    display.clearDisplay();
    display.setTextSize(2);
    display.setCursor(0, 0);
    display.print("Gaz: "); display.print(valeurGaz);

    display.setCursor(0, 16);
    display.print("Hum: ");
    if (isnan(tauxHumidite)) display.print("Err"); else { display.print(tauxHumidite, 0); display.print("%"); }

    display.setCursor(0, 32);
    display.print("Tmp: ");
    if (isnan(temperature)) display.print("Err"); else { display.print(temperature, 1); display.print("C"); }

    display.setCursor(0, 48);
    display.print("Mvt: "); display.print(etatPIR == HIGH ? "OUI" : "NON");

    display.display();
  }
}
