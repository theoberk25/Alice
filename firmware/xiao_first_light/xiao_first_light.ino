/*
 * ALICE first-light node - Seeed XIAO ESP32-S3, one LED.
 *
 * Executes device commands for the Pi runtime over native USB CDC and reports
 * its own output state. It holds no authority: no networking, no policy, no
 * decisions. The Pi authorizes; this board only applies and acknowledges.
 *
 * Wiring (active HIGH):
 *   D0 (GPIO1) -> 270 ohm -> LED anode (long leg)
 *   LED cathode (short leg) -> GND
 * The onboard LED (GPIO21) is deliberately not used.
 *
 * Protocol (newline-delimited JSON, <=256 bytes/line, 115200 baud). See
 * docs/contracts/esp-serial-protocol.md.
 *   in   {"v":1,"id":"<cmd>","op":"set","state":"on"|"off"}
 *   in   {"v":1,"id":"<cmd>","op":"get"}
 *   out  {"v":1,"id":"<cmd>","ok":true,"state":"on","boot_id":"<8 hex>"}
 *   out  {"v":1,"id":"<cmd>","ok":false,"error":"<CODE>","boot_id":"<8 hex>"}
 *
 * "state" is this controller's own driven output, NOT measured illumination.
 * Any rejected frame leaves GPIO untouched. SET is explicit; there is no
 * toggle. Reset comes up OFF and no pending command is stored or replayed.
 *
 * Build: arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32S3
 * (default board options; USB CDC On Boot is enabled by default for this FQBN)
 */

#include <Arduino.h>

static const int LED_PIN = D0;  // D0 == GPIO1 on the XIAO ESP32-S3
static const int QUIESCENT_TX_PIN = D6;  // D6 == GPIO43, ROM UART0 TX (idles HIGH)
static const uint8_t PROTOCOL_VERSION = 1;
static const size_t MAX_LINE = 256;
static const size_t MAX_ID = 32;

static char g_line[MAX_LINE + 1];
static size_t g_len = 0;
static bool g_overflow = false;
static bool g_state_on = false;
static char g_boot_id[9];

/* ------------------------------------------------------------------ output */

static void emit_ok(const char *id, bool state_on) {
  Serial.print(F("{\"v\":1,\"id\":\""));
  Serial.print(id);
  Serial.print(F("\",\"ok\":true,\"state\":\""));
  Serial.print(state_on ? F("on") : F("off"));
  Serial.print(F("\",\"boot_id\":\""));
  Serial.print(g_boot_id);
  Serial.print(F("\"}\n"));
}

static void emit_error(const char *id, const char *code) {
  Serial.print(F("{\"v\":1,\"id\":\""));
  Serial.print(id);
  Serial.print(F("\",\"ok\":false,\"error\":\""));
  Serial.print(code);
  Serial.print(F("\",\"boot_id\":\""));
  Serial.print(g_boot_id);
  Serial.print(F("\"}\n"));
}

/* ------------------------------------------------------------------ parser */

static const char *skip_ws(const char *p) {
  while (*p == ' ' || *p == '\t') { p++; }
  return p;
}

/* Copy a JSON string literal into out. Returns the position after the closing
 * quote, or NULL on a malformed or oversized string. Only the escapes this
 * contract can produce are accepted; anything exotic is a rejection, not a
 * best-effort parse. */
static const char *parse_string(const char *p, char *out, size_t out_size) {
  if (*p != '"') { return NULL; }
  p++;
  size_t n = 0;
  while (*p && *p != '"') {
    if (*p == '\\') { return NULL; }
    if (n + 1 >= out_size) { return NULL; }
    out[n++] = *p++;
  }
  if (*p != '"') { return NULL; }
  out[n] = '\0';
  return p + 1;
}

static const char *parse_uint(const char *p, unsigned long *out) {
  if (*p < '0' || *p > '9') { return NULL; }
  unsigned long value = 0;
  size_t digits = 0;
  while (*p >= '0' && *p <= '9') {
    if (++digits > 9) { return NULL; }
    value = value * 10 + (unsigned long)(*p - '0');
    p++;
  }
  *out = value;
  return p;
}

struct Command {
  bool has_v, has_id, has_op, has_state;
  unsigned long v;
  char id[MAX_ID + 1];
  char op[8];
  char state[8];
};

/* Walk a flat JSON object against a key allow-list. Adding a channel field for
 * a future multi-light node is one more branch here and one more flag above.
 * Returns an error code, or NULL when the frame is structurally sound. */
static const char *parse_command(const char *p, struct Command *cmd) {
  memset(cmd, 0, sizeof(*cmd));
  cmd->id[0] = '\0';

  p = skip_ws(p);
  if (*p != '{') { return "MALFORMED"; }
  p = skip_ws(p + 1);
  if (*p == '}') { return "MISSING_FIELD"; }

  for (;;) {
    char key[16];
    p = skip_ws(p);
    p = parse_string(p, key, sizeof(key));
    if (p == NULL) { return "MALFORMED"; }
    p = skip_ws(p);
    if (*p != ':') { return "MALFORMED"; }
    p = skip_ws(p + 1);

    if (strcmp(key, "v") == 0) {
      if (cmd->has_v) { return "MALFORMED"; }
      p = parse_uint(p, &cmd->v);
      if (p == NULL) { return "MALFORMED"; }
      cmd->has_v = true;
    } else if (strcmp(key, "id") == 0) {
      if (cmd->has_id) { return "MALFORMED"; }
      p = parse_string(p, cmd->id, sizeof(cmd->id));
      if (p == NULL) { return "MALFORMED"; }
      cmd->has_id = true;
    } else if (strcmp(key, "op") == 0) {
      if (cmd->has_op) { return "MALFORMED"; }
      p = parse_string(p, cmd->op, sizeof(cmd->op));
      if (p == NULL) { return "MALFORMED"; }
      cmd->has_op = true;
    } else if (strcmp(key, "state") == 0) {
      if (cmd->has_state) { return "MALFORMED"; }
      p = parse_string(p, cmd->state, sizeof(cmd->state));
      if (p == NULL) { return "MALFORMED"; }
      cmd->has_state = true;
    } else {
      return "UNKNOWN_FIELD";
    }

    p = skip_ws(p);
    if (*p == ',') { p = skip_ws(p + 1); continue; }
    if (*p == '}') { p = skip_ws(p + 1); break; }
    return "MALFORMED";
  }
  if (*p != '\0') { return "MALFORMED"; }
  return NULL;
}

/* ----------------------------------------------------------------- dispatch */

static void handle_line(const char *line) {
  struct Command cmd;
  const char *err = parse_command(line, &cmd);
  if (err != NULL) {
    /* cmd.id is set only if "id" was reached before the failure. */
    emit_error(cmd.has_id ? cmd.id : "", err);
    return;
  }
  if (!cmd.has_id || cmd.id[0] == '\0') { emit_error("", "MISSING_FIELD"); return; }
  if (!cmd.has_v) { emit_error(cmd.id, "MISSING_FIELD"); return; }
  if (cmd.v != PROTOCOL_VERSION) { emit_error(cmd.id, "BAD_VERSION"); return; }
  if (!cmd.has_op) { emit_error(cmd.id, "MISSING_FIELD"); return; }

  if (strcmp(cmd.op, "get") == 0) {
    if (cmd.has_state) { emit_error(cmd.id, "UNKNOWN_FIELD"); return; }
    emit_ok(cmd.id, g_state_on);  /* readback only; GPIO untouched */
    return;
  }
  if (strcmp(cmd.op, "set") != 0) { emit_error(cmd.id, "BAD_OP"); return; }
  if (!cmd.has_state) { emit_error(cmd.id, "MISSING_FIELD"); return; }

  bool want_on;
  if (strcmp(cmd.state, "on") == 0) { want_on = true; }
  else if (strcmp(cmd.state, "off") == 0) { want_on = false; }
  else { emit_error(cmd.id, "BAD_STATE"); return; }

  /* Apply first, acknowledge second: an ack always follows a real write. */
  digitalWrite(LED_PIN, want_on ? HIGH : LOW);
  g_state_on = want_on;
  emit_ok(cmd.id, g_state_on);
}

/* --------------------------------------------------------------- lifecycle */

void setup() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);  /* dark before the host can speak */
  g_state_on = false;

  /* D6 (GPIO43) is the ROM UART0 TX pin and idles HIGH, which lights anything
   * wired to it even though no code drives it. The protocol runs over native
   * USB CDC, so claim the pin and hold it low to keep the bench unambiguous.
   * This is pin hygiene, not a second controlled light: there is no action,
   * target or command for it, and nothing else in the firmware reads or
   * writes it. Removing these two lines restores UART0 TX for hardware-serial
   * debugging. */
  pinMode(QUIESCENT_TX_PIN, OUTPUT);
  digitalWrite(QUIESCENT_TX_PIN, LOW);

  snprintf(g_boot_id, sizeof(g_boot_id), "%08x", (unsigned)esp_random());

  Serial.begin(115200);
  /* Bounded: the node must run headless, so never wait forever for a monitor. */
  unsigned long started = millis();
  while (!Serial && (millis() - started) < 2000UL) { delay(10); }
}

void loop() {
  while (Serial.available() > 0) {
    int c = Serial.read();
    if (c < 0) { break; }
    if (c == '\r') { continue; }
    if (c == '\n') {
      g_line[g_len] = '\0';
      if (g_overflow) {
        emit_error("", "LINE_TOO_LONG");
      } else if (g_len > 0) {
        handle_line(g_line);
      }
      g_len = 0;
      g_overflow = false;
      continue;
    }
    if (g_len >= MAX_LINE) {
      /* Discard to the next newline; never parse a truncated frame. */
      g_overflow = true;
      continue;
    }
    g_line[g_len++] = (char)c;
  }
}
