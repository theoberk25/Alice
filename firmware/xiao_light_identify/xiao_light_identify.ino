/* Bench identification only. Not an ALICE authorization endpoint.
 * A digit 1..8 turns on exactly one user-specified LED; 0 turns all off.
 * Restore the production firmware before resuming the Pi runtime.
 * Use one series resistor per active-HIGH LED. No simulated-grid semantics.
 */
#include <Arduino.h>
static const int PINS[] = {D0, D3, D5, D6, D10, D9, D8, D7};
static const char* NAMES[] = {"D0", "D3", "D5", "D6", "D10", "D9", "D8", "D7"};
static void selectLight(int selected) {
  for (int i = 0; i < 8; ++i) digitalWrite(PINS[i], LOW);
  if (selected >= 0) digitalWrite(PINS[selected], HIGH);
}
void setup() {
  for (int i = 0; i < 8; ++i) { digitalWrite(PINS[i], LOW); pinMode(PINS[i], OUTPUT); }
  Serial.begin(115200);
}
void loop() {
  if (!Serial.available()) return;
  int c = Serial.read();
  if (c >= '0' && c <= '8') {
    int selected = c - '1';
    selectLight(selected);
    Serial.print("IDENTIFY ");
    Serial.println(selected < 0 ? "ALL_OFF" : NAMES[selected]);
  }
}
