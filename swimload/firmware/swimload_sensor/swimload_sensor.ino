/*
 * SwimLoad Sensor Firmware
 * Target: ESP32 + MPU6050 IMU + DRV2605 Haptic Driver
 *
 * Features:
 *  - Streams accelerometer + gyroscope data over BLE / Serial
 *  - Accumulates session load on-device
 *  - Haptic alert when load reaches previous-day maximum threshold
 *  - Stores threshold in non-volatile flash (Preferences)
 *
 * Libraries required (install via Arduino Library Manager):
 *  - Adafruit MPU6050
 *  - Adafruit BusIO
 *  - Adafruit Unified Sensor
 *  - Adafruit DRV2605 Library
 *  - ArduinoJson
 *  - ESP32 BLE Arduino (built-in with ESP32 board package)
 */

#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_DRV2605.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// ── BLE UUIDs ────────────────────────────────────────────────────
#define SERVICE_UUID        "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
#define CHAR_TX_UUID        "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  // notify → phone
#define CHAR_RX_UUID        "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  // write  ← phone

// ── Pins ─────────────────────────────────────────────────────────
#define LED_PIN             2
#define BUTTON_PIN          0   // boot button = session start/stop toggle

// ── Sampling ─────────────────────────────────────────────────────
#define SAMPLE_INTERVAL_MS  6   // ~166 Hz matches your 6 ms epoch data

// ── Objects ──────────────────────────────────────────────────────
Adafruit_MPU6050  mpu;
Adafruit_DRV2605  drv;
Preferences       prefs;
BLECharacteristic *pTxChar;
bool              deviceConnected = false;

// ── Session State ─────────────────────────────────────────────────
bool     sessionActive     = false;
float    sessionLoad       = 0.0f;   // accumulated gyro magnitude integral
float    prevDayMaxLoad    = 0.0f;   // loaded from flash, sent by app
bool     thresholdHit      = false;
uint32_t lastSampleTime    = 0;
uint32_t sessionStartTime  = 0;
uint32_t sampleCount       = 0;

// ── BLE Callbacks ─────────────────────────────────────────────────
class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *pServer)    { deviceConnected = true;  digitalWrite(LED_PIN, HIGH); }
  void onDisconnect(BLEServer *pServer) { deviceConnected = false; digitalWrite(LED_PIN, LOW);  }
};

/*
 * Commands received from app via BLE RX characteristic:
 *  {"cmd":"start"}                   – begin session
 *  {"cmd":"stop"}                    – end session, reply with summary
 *  {"cmd":"set_threshold","val":123.4} – update max load threshold
 */
class RxCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *pChar) {
    String rxVal = pChar->getValue().c_str();
    StaticJsonDocument<128> doc;
    if (deserializeJson(doc, rxVal) != DeserializationError::Ok) return;

    const char *cmd = doc["cmd"];
    if (strcmp(cmd, "start") == 0) {
      startSession();
    } else if (strcmp(cmd, "stop") == 0) {
      stopSession();
    } else if (strcmp(cmd, "set_threshold") == 0) {
      prevDayMaxLoad = doc["val"].as<float>();
      prefs.begin("swimload", false);
      prefs.putFloat("maxLoad", prevDayMaxLoad);
      prefs.end();
      Serial.printf("Threshold updated: %.2f\n", prevDayMaxLoad);
    }
  }
};

// ── Session Control ───────────────────────────────────────────────
void startSession() {
  sessionLoad    = 0.0f;
  thresholdHit   = false;
  sampleCount    = 0;
  sessionActive  = true;
  sessionStartTime = millis();
  Serial.println("Session STARTED");
  hapticPulse(1);  // single short buzz = started
}

void stopSession() {
  sessionActive = false;
  float elapsed = (millis() - sessionStartTime) / 1000.0f;

  // Persist this session's load as candidate for tomorrow's threshold
  prefs.begin("swimload", false);
  float stored = prefs.getFloat("maxLoad", 0.0f);
  if (sessionLoad > stored) {
    prefs.putFloat("maxLoad", sessionLoad);
  }
  prefs.end();

  // Send summary over BLE
  StaticJsonDocument<128> doc;
  doc["event"]        = "session_end";
  doc["total_load"]   = sessionLoad;
  doc["elapsed_s"]    = elapsed;
  doc["samples"]      = sampleCount;
  char buf[128];
  serializeJson(doc, buf);
  if (deviceConnected) pTxChar->setValue(buf); pTxChar->notify();
  Serial.printf("Session STOPPED | load=%.2f elapsed=%.1fs\n", sessionLoad, elapsed);
  hapticPulse(3);  // triple buzz = stopped
}

// ── Haptics ───────────────────────────────────────────────────────
void hapticPulse(uint8_t times) {
  for (uint8_t i = 0; i < times; i++) {
    drv.setWaveform(0, 47);   // effect #47 = sharp click
    drv.setWaveform(1, 0);
    drv.go();
    delay(200);
  }
}

void hapticWarning() {
  // Long rumble = threshold reached
  drv.setWaveform(0, 14);   // effect #14 = strong buzz
  drv.setWaveform(1, 14);
  drv.setWaveform(2, 0);
  drv.go();
}

// ── Setup ─────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN,    OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  // Load persisted threshold
  prefs.begin("swimload", true);
  prevDayMaxLoad = prefs.getFloat("maxLoad", 0.0f);
  prefs.end();
  Serial.printf("Loaded threshold: %.2f\n", prevDayMaxLoad);

  // IMU
  if (!mpu.begin()) {
    Serial.println("MPU6050 not found!");
    while (1) delay(100);
  }
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  // Haptic driver
  if (!drv.begin()) {
    Serial.println("DRV2605 not found – haptics disabled");
  } else {
    drv.selectLibrary(1);
    drv.setMode(DRV2605_MODE_INTTRIG);
  }

  // BLE
  BLEDevice::init("SwimLoad-Sensor");
  BLEServer      *pServer  = BLEDevice::createServer();
  pServer->setCallbacks(new ServerCallbacks());
  BLEService     *pService = pServer->createService(SERVICE_UUID);

  pTxChar = pService->createCharacteristic(CHAR_TX_UUID,
              BLECharacteristic::PROPERTY_NOTIFY);
  pTxChar->addDescriptor(new BLE2902());

  BLECharacteristic *pRxChar = pService->createCharacteristic(CHAR_RX_UUID,
              BLECharacteristic::PROPERTY_WRITE);
  pRxChar->setCallbacks(new RxCallbacks());

  pService->start();
  pServer->getAdvertising()->start();
  Serial.println("BLE advertising started");
}

// ── Main Loop ─────────────────────────────────────────────────────
void loop() {
  uint32_t now = millis();

  // Button debounce: toggle session
  static uint32_t lastBtn = 0;
  if (digitalRead(BUTTON_PIN) == LOW && (now - lastBtn) > 500) {
    lastBtn = now;
    if (sessionActive) stopSession(); else startSession();
  }

  if (!sessionActive) return;
  if ((now - lastSampleTime) < SAMPLE_INTERVAL_MS) return;
  lastSampleTime = now;

  // Read sensors
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  float gx = g.gyro.x;  // rad/s
  float gy = g.gyro.y;
  float gz = g.gyro.z;

  // Gyro magnitude
  float gyroMag = sqrt(gx*gx + gy*gy + gz*gz);

  // Integrate load: magnitude × dt (seconds)
  float dt = SAMPLE_INTERVAL_MS / 1000.0f;
  sessionLoad += gyroMag * dt;
  sampleCount++;

  // Check threshold
  if (!thresholdHit && prevDayMaxLoad > 0.0f && sessionLoad >= prevDayMaxLoad) {
    thresholdHit = true;
    hapticWarning();
    Serial.printf("⚠ THRESHOLD HIT: %.2f / %.2f\n", sessionLoad, prevDayMaxLoad);
  }

  // Stream sample over BLE (every 5th sample to reduce bandwidth)
  if (deviceConnected && (sampleCount % 5 == 0)) {
    StaticJsonDocument<192> doc;
    doc["t"]  = now - sessionStartTime;  // ms since session start
    doc["ax"] = a.acceleration.x;
    doc["ay"] = a.acceleration.y;
    doc["az"] = a.acceleration.z;
    doc["gx"] = gx;
    doc["gy"] = gy;
    doc["gz"] = gz;
    doc["sl"] = sessionLoad;
    char buf[192];
    serializeJson(doc, buf);
    pTxChar->setValue(buf);
    pTxChar->notify();
  }

  // Also print to Serial for USB debug / direct laptop logging
  Serial.printf("%.3f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f\n",
    (now - sessionStartTime) / 1000.0f,
    a.acceleration.x, a.acceleration.y, a.acceleration.z,
    gx, gy, gz, sessionLoad);
}
