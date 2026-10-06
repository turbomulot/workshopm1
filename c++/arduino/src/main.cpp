#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>


Adafruit_SSD1306 display(128, 64, &Wire, -1);


const int brochePIR = D5; 

void setup() {
  Wire.begin(); 
  

  pinMode(brochePIR, INPUT);
  

  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    for(;;); 
  }
  
  display.setTextColor(SSD1306_WHITE);
}

void loop() {
  display.clearDisplay(); 
  

  int detection = digitalRead(brochePIR);
  

  display.setTextSize(2); 
  display.setCursor(5, 25);
  
  if (detection == HIGH) {
    display.print("OUI");
  } else {
    display.print("NON");
  }
  

  display.display(); 
  

  delay(20); 
}