// SmartBlaster ESP32 IR Bridge (reference scaffold)
// Receives line-delimited JSON over Serial and sends Midea AC IR.

#include <Arduino.h>
#include <ArduinoJson.h>
#include <IRremoteESP8266.h>
#include <IRsend.h>
#include <ir_Midea.h>

namespace {
constexpr uint16_t kIrLedPin = 4;  // change for your board wiring
constexpr uint32_t kBaudRate = 115200;

IRsend irsend(kIrLedPin);
IRMideaAC midea(kIrLedPin);

String readLine() {
  static String buf;
  while (Serial.available() > 0) {
    char c = static_cast<char>(Serial.read());
    if (c == '\n') {
      String line = buf;
      buf = "";
      return line;
    }
    if (c != '\r') buf += c;
  }
  return "";
}

void sendAck(const String &requestId, bool ok, const char *errorCode = nullptr, const char *errorMessage = nullptr) {
  StaticJsonDocument<256> ack;
  ack["v"] = 1;
  ack["topic"] = "midea_ir.ack";
  ack["request_id"] = requestId;
  ack["ok"] = ok;
  if (!ok) {
    ack["error_code"] = errorCode ? errorCode : "tx_failed";
    if (errorMessage) ack["error_message"] = errorMessage;
  }
  serializeJson(ack, Serial);
  Serial.println();
}

bool applyPayload(const JsonObject &payload, const String &requestId) {
  const char *mode = payload["mode"] | "off";

  if (strcmp(mode, "off") == 0) {
    midea.off();
    midea.send();
    return true;
  }

  if (!payload.containsKey("temperature_c")) {
    sendAck(requestId, false, "invalid_command", "temperature_c is required");
    return false;
  }

  float t = payload["temperature_c"].as<float>();
  if (t < 17 || t > 30) {
    sendAck(requestId, false, "invalid_command", "temperature_c out of range");
    return false;
  }

  midea.on();
  midea.setTemp(static_cast<uint8_t>(t));

  // Mode mapping (extend with model-specific validation as needed)
  if (strcmp(mode, "cool") == 0) midea.setMode(kMideaACCool);
  else if (strcmp(mode, "heat") == 0) midea.setMode(kMideaACHeat);
  else if (strcmp(mode, "dry") == 0) midea.setMode(kMideaACDry);
  else if (strcmp(mode, "fan_only") == 0) midea.setMode(kMideaACFan);
  else midea.setMode(kMideaACAuto);

  const char *fan = payload["fan"] | "auto";
  if (strcmp(fan, "low") == 0) midea.setFan(kMideaACFanLow);
  else if (strcmp(fan, "medium") == 0) midea.setFan(kMideaACFanMed);
  else if (strcmp(fan, "high") == 0) midea.setFan(kMideaACFanHigh);
  else midea.setFan(kMideaACFanAuto);

  // Swing toggle command can be model/state dependent.
  // Keep explicit toggle handling conservative in first revision.
  // TODO: map "swing" payload and special packet commands.

  midea.send();
  return true;
}

void handleLine(const String &line) {
  StaticJsonDocument<512> doc;
  auto err = deserializeJson(doc, line);
  if (err) {
    sendAck("", false, "bad_json", "invalid json");
    return;
  }

  JsonObject obj = doc.as<JsonObject>();
  int v = obj["v"] | -1;
  const char *topic = obj["topic"] | "";
  String requestId = String(obj["request_id"] | "");

  if (v != 1) {
    sendAck(requestId, false, "unsupported_version", "expected v=1");
    return;
  }
  if (strcmp(topic, "midea_ir.command") != 0) {
    sendAck(requestId, false, "bad_schema", "unsupported topic");
    return;
  }
  if (requestId.length() == 0) {
    sendAck(requestId, false, "bad_schema", "request_id required");
    return;
  }

  if (!obj.containsKey("payload") || !obj["payload"].is<JsonObject>()) {
    sendAck(requestId, false, "bad_schema", "payload object required");
    return;
  }

  JsonObject payload = obj["payload"].as<JsonObject>();
  bool ok = applyPayload(payload, requestId);
  if (ok) sendAck(requestId, true);
}
}  // namespace

void setup() {
  Serial.begin(kBaudRate);
  irsend.begin();
  midea.begin();
}

void loop() {
  String line = readLine();
  if (line.length() > 0) {
    handleLine(line);
  }
}
