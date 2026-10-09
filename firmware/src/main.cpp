#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <time.h>
#include "secrets.h"

const char* TOPIC_SENSORS = "sentinel/sensors";
const char* TOPIC_ALERTS = "sentinel/alerts";
const char* TOPIC_CMD = "sentinel/cmd";
const char* TOPIC_STATUS = "sentinel/status";
// Publié par le service caméra quand il reconnaît un visage autorisé.
const char* TOPIC_VISION = "sentinel/vision";

Adafruit_SSD1306 display(128, 64, &Wire, -1);

const int brocheGaz = A0;
const int brocheHumidite = D6;
const int brochePIR = D5;

const int brocheBuzzer = D3;
const int brocheLedRouge = D4;
const int brocheLedVerte = D8;

#define DHTTYPE DHT22
DHT dht(brocheHumidite, DHTTYPE);

WiFiClient espClient;
PubSubClient client(espClient);

const unsigned long INTERVALLE_ENVOI = 2000;
const unsigned long INTERVALLE_RECONNEXION = 5000;
// Le MQ-2 et le PIR donnent des valeurs fausses pendant leur première minute.
const unsigned long DUREE_PRECHAUFFAGE = 60000;

const int SEUIL_GAZ_WARN = 400;
const int SEUIL_GAZ_CRITIQUE = 700;
// Écart sous le seuil avant de redescendre d'un niveau, pour éviter les alertes en rafale.
const int HYSTERESIS_GAZ = 50;

// Présence active tant que le PIR voit quelqu'un, puis 30 s (même délai que la caméra).
const unsigned long DUREE_PRESENCE = 30000;
// Gaz warning : un bip de 200 ms toutes les 2 s. Gaz critical : son continu.
const unsigned long PERIODE_BIP = 2000;
const unsigned long DUREE_BIP = 200;

enum EtatLed { LED_ETEINTE, LED_ROUGE, LED_VERTE };

// Dernier état demandé par le dashboard. Au repos, la LED est verte.
bool buzzerCommande = false;
EtatLed ledCommande = LED_VERTE;
// Le visage devant la caméra a passé la vérification (moins de 30 min) : LED verte.
// Une autre personne envoie « reconnu: false » et la LED repasse au rouge.
bool personneReconnue = false;
// Alerte envoyée par le service caméra (personne non identifiée), répétée chaque seconde
// tant que la personne est dans le champ : la LED reste rouge jusqu'à son départ.
const unsigned long DUREE_ALERTE_VISION = 3000;
unsigned long derniereAlerteVision = 0;

// Vérification faciale envoyée par le service caméra (répétée chaque seconde) :
// l'écran l'affiche à la place des mesures tant que les messages arrivent.
const unsigned long DUREE_AFFICHAGE_VERIF = 2500;
// Étape du contrôle d'accès : face, left, right, up, down (positions de la vérification faciale), badge,
// alerte, ou résultat (valid, refused, disabled).
char verification[12] = "";
int etapeVerif = 0;
int totalVerif = 0;
int restantVerif = 0;
unsigned long derniereVerif = 0;

int niveauGaz = 0; // 0 normal, 1 warn, 2 critical

// Hausses rapides : mesure actuelle comparée à son minimum de la dernière minute.
const unsigned long FENETRE_HAUSSE = 60000;
const int NB_MESURES_HAUSSE = FENETRE_HAUSSE / INTERVALLE_ENVOI;
struct Historique {
  float valeurs[NB_MESURES_HAUSSE];
  int index = 0;
  int nb = 0;
};
Historique historiqueTemp;
Historique historiqueGaz;

// Température : +3 °C en une minute (appareil qui chauffe, début d'incendie) = bip rapide.
const float HAUSSE_TEMP_ALERTE = 3.0;
bool alarmeTemperature = false;
// Gaz + température qui montent ensemble = risque d'incendie : buzzer continu, LED rouge,
// écran « ALERTE INCENDIE ». Hausse de gaz en points du capteur MQ-2 (0 à 1023).
const int HAUSSE_GAZ_ALERTE = 100;
bool alarmeIncendie = false;
// Bip rapide, distinct du gaz : 500 ms toutes les secondes.
const unsigned long PERIODE_BIP_TEMP = 1000;
const unsigned long DUREE_BIP_TEMP = 500;
int dernierPIR = LOW;
// 0 tant qu'aucune présence n'a été vue depuis la fin du préchauffage.
unsigned long dernierePresence = 0;
unsigned long dernierEnvoi = 0;
unsigned long derniereTentativeMqtt = 0;

// Appelée à chaque tour de loop() : le gaz et la présence passent avant les commandes du dashboard,
// et fonctionnent même sans broker.
// LED : rouge si gaz critical ou personne non reconnue, verte si la personne est reconnue.
void appliquerSorties() {
  unsigned long maintenant = millis();
  bool presence = dernierePresence != 0 && maintenant - dernierePresence < DUREE_PRESENCE;
  // La reconnaissance ne vaut que pour la présence en cours.
  if (!presence) personneReconnue = false;
  bool bipWarning = niveauGaz == 1 && maintenant % PERIODE_BIP < DUREE_BIP;

  bool bipTemperature = alarmeTemperature && maintenant % PERIODE_BIP_TEMP < DUREE_BIP_TEMP;
  bool buzzer = buzzerCommande || niveauGaz == 2 || alarmeIncendie || bipWarning || bipTemperature;
  EtatLed led = ledCommande;
  bool alerteVision = derniereAlerteVision != 0 && maintenant - derniereAlerteVision < DUREE_ALERTE_VISION;
  if (niveauGaz == 2 || alarmeIncendie || alerteVision) led = LED_ROUGE;
  else if (presence) led = personneReconnue ? LED_VERTE : LED_ROUGE;
  digitalWrite(brocheBuzzer, buzzer ? HIGH : LOW);
  digitalWrite(brocheLedRouge, led == LED_ROUGE ? HIGH : LOW);
  digitalWrite(brocheLedVerte, led == LED_VERTE ? HIGH : LOW);
}

bool verificationAffichee() {
  return derniereVerif != 0 && millis() - derniereVerif < DUREE_AFFICHAGE_VERIF;
}

// Consigne sur deux lignes de 10 caractères au plus (texte taille 2, sans accents).
const char* consigneVerification(const char* etape) {
  if (strcmp(etape, "face") == 0) return "Regardez\nla camera";
  if (strcmp(etape, "left") == 0) return "Tete a\ngauche";
  if (strcmp(etape, "right") == 0) return "Tete a\ndroite";
  if (strcmp(etape, "up") == 0) return "Levez le\nmenton";
  if (strcmp(etape, "down") == 0) return "Baissez le\nmenton";
  if (strcmp(etape, "verify") == 0) return "Revenez\nde face";
  if (strcmp(etape, "badge") == 0) return "Montrez\nle badge";
  if (strcmp(etape, "alerte") == 0) return "ALERTE\nENVOYEE";
  if (strcmp(etape, "valid") == 0) return "ACCES\nACCEPTE";
  if (strcmp(etape, "disabled") == 0) return "FICHE\nDESACTIVEE";
  return "ACCES\nREFUSE";
}

const char* titreVerification() {
  if (strcmp(verification, "badge") == 0) return "Visage non reconnu";
  if (strcmp(verification, "alerte") == 0) return "Personne non identif.";
  if (strcmp(verification, "face") == 0) return "Reconnaissance";
  return "Controle d'acces";
}

void afficherVerification() {
  // L'alerte incendie garde l'écran.
  if (alarmeIncendie) return;
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 0);
  if (etapeVerif > 0) display.printf("Position %d/%d", etapeVerif, totalVerif);
  else display.print(titreVerification());
  display.drawFastHLine(0, 10, 128, SSD1306_WHITE);

  display.setTextSize(2);
  display.setCursor(0, 18);
  display.print(consigneVerification(verification));

  if (restantVerif > 0) {
    display.setTextSize(1);
    display.setCursor(0, 56);
    display.printf("Temps restant : %d s", restantVerif);
  }
  display.display();
}

void receptionCommande(char* topic, byte* payload, unsigned int length) {
  StaticJsonDocument<200> docCmd;
  DeserializationError error = deserializeJson(docCmd, payload, length);
  if (error) {
    Serial.printf("Commande ignorée (JSON invalide) : %s\n", error.c_str());
    return;
  }

  if (strcmp(topic, TOPIC_VISION) == 0) {
    if (docCmd.containsKey("reconnu")) personneReconnue = docCmd["reconnu"].as<bool>();
    if (docCmd["alerte"] == true) {
      derniereAlerteVision = millis();
      personneReconnue = false;
    }
    if (docCmd.containsKey("verification")) {
      strlcpy(verification, docCmd["verification"] | "", sizeof(verification));
      etapeVerif = docCmd["etape"] | 0;
      totalVerif = docCmd["total"] | 0;
      restantVerif = docCmd["restant"] | 0;
      derniereVerif = millis();
      afficherVerification();
    }
    return;
  }

  if (docCmd.containsKey("buzzer")) {
    buzzerCommande = docCmd["buzzer"].as<bool>();
  }

  if (docCmd.containsKey("led")) {
    // « | "" » évite un pointeur nul si « led » n'est pas une chaîne.
    const char* etatLed = docCmd["led"] | "";
    if (strcmp(etatLed, "red") == 0) ledCommande = LED_ROUGE;
    else if (strcmp(etatLed, "green") == 0) ledCommande = LED_VERTE;
    else if (strcmp(etatLed, "off") == 0) ledCommande = LED_ETEINTE;
  }
}

// Une tentative toutes les 5 s au plus : la boucle continue de lire les capteurs entre deux.
void connecterMqtt() {
  if (WiFi.status() != WL_CONNECTED) return;

  unsigned long maintenant = millis();
  if (derniereTentativeMqtt != 0 && maintenant - derniereTentativeMqtt < INTERVALLE_RECONNEXION) return;
  derniereTentativeMqtt = maintenant;

  String clientId = "SentinelNode-" + String(ESP.getChipId(), HEX);
  const char* user = strlen(MQTT_USER) > 0 ? MQTT_USER : nullptr;
  const char* motDePasse = strlen(MQTT_PASSWORD) > 0 ? MQTT_PASSWORD : nullptr;

  // Last Will : le broker publie « offline » si le boîtier disparaît.
  if (client.connect(clientId.c_str(), user, motDePasse, TOPIC_STATUS, 0, true, "offline")) {
    client.publish(TOPIC_STATUS, "online", true);
    client.subscribe(TOPIC_CMD);
    client.subscribe(TOPIC_VISION);
    Serial.println("MQTT connecté");
  } else {
    Serial.printf("Échec MQTT (état %d), nouvel essai dans 5 s\n", client.state());
  }
}

void publier(const char* topic, JsonDocument& doc) {
  if (!client.connected()) return;
  char buffer[200];
  serializeJson(doc, buffer);
  if (!client.publish(topic, buffer)) {
    Serial.printf("Publication sur %s échouée\n", topic);
  }
}

void publierAlerte(const char* type, const char* level, float value) {
  StaticJsonDocument<100> docAlerte;
  docAlerte["type"] = type;
  docAlerte["level"] = level;
  docAlerte["value"] = value;
  publier(TOPIC_ALERTS, docAlerte);
}

// Hausse de la mesure par rapport à son minimum sur la dernière minute (0 sans mesure valide).
float hausse(Historique& historique, float mesure) {
  if (isnan(mesure)) return 0;
  historique.valeurs[historique.index] = mesure;
  historique.index = (historique.index + 1) % NB_MESURES_HAUSSE;
  if (historique.nb < NB_MESURES_HAUSSE) historique.nb++;
  float minimum = mesure;
  for (int i = 0; i < historique.nb; i++) minimum = min(minimum, historique.valeurs[i]);
  return mesure - minimum;
}

void afficherIncendie() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("Gaz et temperature");
  display.drawFastHLine(0, 10, 128, SSD1306_WHITE);
  display.setTextSize(2);
  display.setCursor(0, 18);
  display.print("ALERTE\nINCENDIE");
  display.display();
}

// Niveau de gaz avec hystérésis : on monte au seuil, on redescend 50 points plus bas.
int calculerNiveauGaz(int valeurGaz) {
  if (valeurGaz > SEUIL_GAZ_CRITIQUE) return 2;
  if (niveauGaz == 2 && valeurGaz > SEUIL_GAZ_CRITIQUE - HYSTERESIS_GAZ) return 2;
  if (valeurGaz > SEUIL_GAZ_WARN) return 1;
  if (niveauGaz >= 1 && valeurGaz > SEUIL_GAZ_WARN - HYSTERESIS_GAZ) return 1;
  return 0;
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  dht.begin();

  pinMode(brochePIR, INPUT);
  pinMode(brocheBuzzer, OUTPUT);
  pinMode(brocheLedRouge, OUTPUT);
  pinMode(brocheLedVerte, OUTPUT);
  appliquerSorties();

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("Écran OLED introuvable");
    for (;;) delay(1000);
  }
  display.setTextColor(SSD1306_WHITE);

  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("1/3 Wi-Fi...");
  display.display();

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  // 20 s max : sans Wi-Fi, le boîtier affiche quand même les mesures et garde l'alarme locale.
  for (int essai = 0; essai < 40 && WiFi.status() != WL_CONNECTED; essai++) { delay(500); }

  display.println(WiFi.status() == WL_CONNECTED ? "Wi-Fi OK!" : "Wi-Fi absent");
  display.println("2/3 Synchro Heure...");
  display.display();

  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  int timeoutNTP = 0;
  while (time(nullptr) < 100000 && timeoutNTP < 20) {
    delay(500);
    timeoutNTP++;
  }

  display.println("3/3 Serveur MQTT...");
  display.display();
  delay(1000);

  client.setServer(MQTT_SERVER, MQTT_PORT);
  client.setCallback(receptionCommande);
}

void loop() {
  if (client.connected()) client.loop();
  else connecterMqtt();
  appliquerSorties();

  unsigned long tempsActuel = millis();
  if (tempsActuel - dernierEnvoi < INTERVALLE_ENVOI) return;
  dernierEnvoi = tempsActuel;

  int valeurGaz = analogRead(brocheGaz);
  float tauxHumidite = dht.readHumidity();
  float temperature = dht.readTemperature();
  int etatPIR = digitalRead(brochePIR);
  time_t maintenant = time(nullptr);
  bool prechauffage = tempsActuel < DUREE_PRECHAUFFAGE;
  // Calculée aussi pendant le préchauffage, pour que la minute d'historique soit déjà remplie.
  float hausseTemp = hausse(historiqueTemp, temperature);
  float hausseGaz = hausse(historiqueGaz, valeurGaz);

  // null plutôt que 0 : le backend distingue un capteur en panne d'une vraie mesure.
  StaticJsonDocument<200> docSensors;
  if (isnan(temperature)) docSensors["temp"] = nullptr; else docSensors["temp"] = temperature;
  if (isnan(tauxHumidite)) docSensors["hum"] = nullptr; else docSensors["hum"] = tauxHumidite;
  docSensors["gas"] = valeurGaz;
  docSensors["pir"] = etatPIR;
  // Sans NTP, time() compte depuis l'allumage : on laisse le backend dater la mesure.
  if (maintenant > 1000000000) docSensors["ts"] = (long)maintenant;
  publier(TOPIC_SENSORS, docSensors);

  // Alertes seulement sur changement d'état, et pas pendant le préchauffage.
  // Une présence n'est pas un danger : niveau info, donc pas de buzzer.
  if (!prechauffage) {
    if (etatPIR == HIGH) dernierePresence = tempsActuel;
    if (etatPIR == HIGH && dernierPIR == LOW) {
      publierAlerte("motion", "info", 1);
    }

    int nouveauNiveau = calculerNiveauGaz(valeurGaz);
    if (nouveauNiveau > niveauGaz) {
      publierAlerte("gas", nouveauNiveau == 2 ? "critical" : "warn", valeurGaz);
    }
    niveauGaz = nouveauNiveau;

    // Les alarmes cessent d'elles-mêmes une minute après la fin de la hausse.
    bool hausseRapide = hausseTemp >= HAUSSE_TEMP_ALERTE;
    if (hausseRapide && !alarmeTemperature) {
      publierAlerte("temp_rise", "critical", round(hausseTemp * 10) / 10.0);
    }
    alarmeTemperature = hausseRapide;

    bool incendie = hausseRapide && hausseGaz >= HAUSSE_GAZ_ALERTE;
    if (incendie && !alarmeIncendie) {
      publierAlerte("fire", "critical", valeurGaz);
    }
    alarmeIncendie = incendie;
  }
  dernierPIR = etatPIR;

  if (alarmeIncendie) {
    afficherIncendie();
    return;
  }
  // Pendant une vérification faciale, l'écran garde ses consignes.
  if (verificationAffichee()) return;

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
