#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Adafruit_MLX90614.h>
#include <ESP32Servo.h>

// Pines y objetos
Servo servoX;
int posX = 0;
#define LED_PIN 23
#define LED_ESPERA 32
Adafruit_MLX90614 mlx = Adafruit_MLX90614();

// Datos de red WiFi
const char* ssid = "CLARO_2.4GHz_7F54B8";
const char* password = "hPha6w7MuWS?tMW";
const char* serverUrl = "http://192.168.1.9:8000/post-sensor";

// Configuración I2C
#define I2C_ADDRESS_CAM (0x08)

void setup() {
  Serial.begin(115200);
  Wire.begin(); // Inicializar I2C
  // Configurar LEDs y servomotor
  pinMode(LED_PIN, OUTPUT);
  pinMode(LED_ESPERA, OUTPUT);
  servoX.attach(14);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(LED_ESPERA, LOW);

  // Inicializar WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    digitalWrite(LED_ESPERA, HIGH);
    delay(500);
    digitalWrite(LED_ESPERA, LOW);
    delay(500);
    Serial.println("Conectando a WiFi...");
  }
  digitalWrite(LED_PIN, HIGH);
  Serial.println("Conectado a WiFi");

  // Inicializar sensor MLX90614
  if (!mlx.begin()) {
    Serial.println("Error iniciando MLX90614");
    while (1);
  }
}

void loop() {
  for (posX = 0; posX <= 180; posX += 10) {
    servoX.write(posX);
    delay(15);

    float temp = mlx.readObjectTempC();
    Serial.print("PosX: ");
    Serial.print(posX);
    Serial.print(" Temp: ");
    Serial.println(temp);

    if (temp > 30.0) {
      enviarDatos(posX, temp);
      // Enviar comando a ESP32-CAM para capturar imagen
      enviarComandoCaptura();
    }

    delay(500);
  }
}

void enviarDatos(int x, float temperatura) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.setTimeout(5000);
    // Formatea el timestamp en ISO 8601
    String timestamp = String(millis());
    String jsonData = "{\"x\": " + String(x) + 
                     ", \"temp\": " + String(temperatura) + 
                     ", \"timestamp\": \"2024-11-04T" + timestamp + "\"}";
    
    Serial.println("Enviando datos: " + jsonData);
    
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");
    
    int httpResponseCode = http.POST(jsonData);
    
    if(httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("HTTP Response code: " + String(httpResponseCode));
      Serial.println("Response: " + response);
    } else {
      Serial.println("Error en HTTP POST: " + String(httpResponseCode));
      Serial.println("Error: " + http.errorToString(httpResponseCode));
    }
    
    http.end();
  } else {
    Serial.println("Error en la conexión WiFi");
  }
  
  // Espera antes del próximo envío
  delay(1000);
}

void enviarComandoCaptura() {
  Wire.beginTransmission(0x08);
  Wire.write((const uint8_t*)"CAPTURA", 7);
  Wire.endTransmission();
  Serial.println("Comando CAPTURA enviado a ESP32-CAM");
  // Procesa la respuesta del esclavo
  while (Wire.available()) {
    char c = Wire.read();
    Serial.print(c);  // Imprime la respuesta recibida
  }
  Serial.println();  // Salto de línea para organización en el monitor

  delay(1000);  // Espera para la siguiente transmisión
}