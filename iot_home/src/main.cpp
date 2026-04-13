#include <WiFi.h>
#include <HTTPClient.h>

// 🔹 WiFi credentials
const char* ssid = "YOUR_WIFI";
const char* password = "YOUR_PASSWORD";

// 🔹 ✅ YOUR CORRECT SERVER IP
String serverURL = "http://10.247.97.141:5000/predict";

void setup() {
  Serial.begin(115200);

  WiFi.begin(ssid, password);
  Serial.print("Connecting");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\n✅ WiFi Connected!");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {

  if (WiFi.status() == WL_CONNECTED) {

    HTTPClient http;

    Serial.println("\n🔄 Connecting to server...");
    Serial.println(serverURL);

    http.begin(serverURL);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(5000);  // 🔥 important

    // 🔹 Sample data
    int bpm = random(70, 100);
    float temp = random(360, 380) / 10.0;

    String jsonData = "{\"hr\":" + String(bpm) + ",\"temp\":" + String(temp) + "}";

    Serial.println("📤 Sending: " + jsonData);

    int httpResponseCode = http.POST(jsonData);

    if (httpResponseCode > 0) {
      Serial.print("✅ Response Code: ");
      Serial.println(httpResponseCode);

      String response = http.getString();
      Serial.println("📥 Server Response: " + response);

    } else {
      Serial.print("❌ Error: ");
      Serial.println(httpResponseCode);

      Serial.println("⚠️ Check:");
      Serial.println("✔ Flask running?");
      Serial.println("✔ Same WiFi?");
      Serial.println("✔ Firewall OFF?");
    }

    http.end();

  } else {
    Serial.println("❌ WiFi Disconnected");
  }

  delay(5000);
}