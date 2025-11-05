#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_camera.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

// WiFi credentials
const char* ssid = "Yuco";
const char* password = "257u38sg";

// Flask server endpoints
const char* streamUrl = "http://192.168.100.205:5000/stream"; // realtime preview
const char* uploadUrl = "http://192.168.100.205:5000/upload"; // capture manual

// Flash LED pin
#define FLASH_LED_PIN 4

// Kamera pin mapping (AI-Thinker ESP32-CAM)
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// Interval stream (ms)
unsigned long lastStreamTime = 0;
const unsigned long streamInterval = 1000; // realtime tiap 1 detik

void setup() {
  Serial.begin(115200);
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

  pinMode(FLASH_LED_PIN, OUTPUT);
  digitalWrite(FLASH_LED_PIN, LOW);

  // WiFi connect
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  // Kamera config
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  if (psramFound()) {
    config.frame_size = FRAMESIZE_VGA;  // 640x480
    config.jpeg_quality = 10;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_SVGA; // 800x600
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed 0x%x\n", err);
    return;
  }

  Serial.println("Camera initialized successfully!");
}

void loop() {
  unsigned long now = millis();

  // =============== 1️⃣ STREAM REALTIME (tiap 1 detik) ===============
  if (now - lastStreamTime >= streamInterval) {
    lastStreamTime = now;

    camera_fb_t *fb = esp_camera_fb_get();
    if (fb) {
      if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        http.begin(streamUrl);
        http.addHeader("Content-Type", "image/jpeg");
        int code = http.POST(fb->buf, fb->len);
        if (code > 0)
          Serial.printf("Stream sent (%d)\n", code);
        http.end();
      }
      esp_camera_fb_return(fb);
    }
  }

  // =============== 2️⃣ MANUAL CAPTURE (via Serial) ===============
  if (Serial.available() > 0) {
    char c = Serial.read();
    if (c == 'Y' || c == 'y') {
      Serial.println("Manual capture triggered!");

      digitalWrite(FLASH_LED_PIN, HIGH);
      delay(150); // beri waktu nyala

      camera_fb_t *captureFb = esp_camera_fb_get();
      if (captureFb) {
        if (WiFi.status() == WL_CONNECTED) {
          HTTPClient http;
          http.begin(uploadUrl);
          http.addHeader("Content-Type", "image/jpeg");

          int code = http.POST(captureFb->buf, captureFb->len);
          if (code > 0)
            Serial.printf("Upload success (%d)\n", code);
          else
            Serial.printf("Upload failed (%d)\n", code);

          http.end();
        }
        esp_camera_fb_return(captureFb);
      }

      digitalWrite(FLASH_LED_PIN, LOW);
    }
  }

  delay(10);
}
