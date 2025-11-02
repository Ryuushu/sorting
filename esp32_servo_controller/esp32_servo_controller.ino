#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

Servo servo1, servo2, servo3, servo4, servo5, servo6;
const int servoPins[6] = {13, 12, 14, 27, 26, 25};
int servoPositions[6] = {90, 90, 90, 90, 90, 90};

WebServer server(80);
const int LED_PIN = 2;

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  
  servo1.attach(servoPins[0]);
  servo2.attach(servoPins[1]);
  servo3.attach(servoPins[2]);
  servo4.attach(servoPins[3]);
  servo5.attach(servoPins[4]);
  servo6.attach(servoPins[5]);
  
  for (int i = 0; i < 6; i++) {
    moveServo(i, 90);
  }
  
  WiFi.begin(ssid, password);
  Serial.print("Connecting");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
  }
  Serial.println("\nConnected!");
  Serial.println(WiFi.localIP());
  digitalWrite(LED_PIN, HIGH);
  
  server.on("/", handleRoot);
  server.on("/servo/1", []() { handleServo(0); });
  server.on("/servo/2", []() { handleServo(1); });
  server.on("/servo/3", []() { handleServo(2); });
  server.on("/servo/4", []() { handleServo(3); });
  server.on("/servo/5", []() { handleServo(4); });
  server.on("/servo/6", []() { handleServo(5); });
  server.on("/status", handleStatus);
  server.on("/reset", handleReset);
  
  server.begin();
}

void loop() {
  server.handleClient();
}

void handleRoot() {
  server.send(200, "text/html", "<h1>ESP32 Servo Controller</h1>");
}

void handleServo(int idx) {
  if (server.hasArg("angle")) {
    int angle = server.arg("angle").toInt();
    if (angle >= 0 && angle <= 180) {
      moveServo(idx, angle);
    }
  } else {
    moveServo(idx, 180);
    delay(500);
    moveServo(idx, 90);
  }
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", "{\"status\":\"ok\"}");
}

void handleStatus() {
  String json = "{\"servos\":[";
  for (int i = 0; i < 6; i++) {
    json += "{\"id\":" + String(i+1) + ",\"position\":" + String(servoPositions[i]) + "}";
    if (i < 5) json += ",";
  }
  json += "]}";
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", json);
}

void handleReset() {
  for (int i = 0; i < 6; i++) moveServo(i, 90);
  server.send(200, "application/json", "{\"status\":\"reset\"}");
}

void moveServo(int idx, int angle) {
  servoPositions[idx] = angle;
  switch(idx) {
    case 0: servo1.write(angle); break;
    case 1: servo2.write(angle); break;
    case 2: servo3.write(angle); break;
    case 3: servo4.write(angle); break;
    case 4: servo5.write(angle); break;
    case 5: servo6.write(angle); break;
  }
  delay(15);
}