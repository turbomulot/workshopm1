#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>

Adafruit_SSD1306 display(128, 64, &Wire, -1);

const int brocheGaz = A0;
const int brocheHumidite = D6;
const int brochePIR = D5; 

#define DHTTYPE DHT22
DHT dht(brocheHumidite, DHTTYPE);

void setup() {
  Wire.begin(); 
  dht.begin(); 
  
  pinMode(brochePIR, INPUT);

  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    for(;;); 
  }
  display.setTextColor(SSD1306_WHITE);
}

void loop() {
  display.clearDisplay(); 
  
  int valeurGaz = analogRead(brocheGaz);
  float tauxHumidite = dht.readHumidity();
  float temperature = dht.readTemperature(); // Nouvelle lecture de la température
  int etatPIR = digitalRead(brochePIR);

  display.setTextSize(2);

  display.setCursor(0, 0);
  display.print("Gaz: ");
  display.print(valeurGaz);

  display.setCursor(0, 16);
  display.print("Hum: ");
  if (isnan(tauxHumidite)) {
    display.print("Err");
  } else {
    display.print(tauxHumidite, 0); 
    display.print("%");
  }

  display.setCursor(0, 32);
  display.print("Tmp: ");
  if (isnan(temperature)) {
    display.print("Err");
  } else {
    display.print(temperature, 1);
    display.print("C"); 
  }

  display.setCursor(0, 48);
  display.print("Mvt: ");
  if (etatPIR == HIGH) {
    display.print("OUI");
  } else {
    display.print("NON");
  }

  display.display(); 
  
  delay(2000); 
}