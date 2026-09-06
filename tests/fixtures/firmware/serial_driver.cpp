// Host-only parser/framing test. This does not emulate electrical hardware.
#include "Arduino.h"
#include <iostream>
#include <iterator>
#include <cassert>
SerialMock Serial;
int writes = 0;
#include "../../../firmware/xiao_first_light/xiao_first_light.ino"
int main(int argc, char** argv) {
  setup();
  writes = 0;
  if (argc > 1 && std::string(argv[1]) == "--interactive") {
    std::string line;
    Serial.output.clear();
    while (std::getline(std::cin, line)) {
      if (line.size() && line[0] == '@') {
        clock_ms = std::stoul(line.substr(1)); loop();
        std::cout << "{}\n" << std::flush;
      } else {
        Serial.input = line + "\n"; Serial.cursor = 0;
        loop();
        std::cout << Serial.output << std::flush;
        Serial.output.clear();
      }
    }
    return 0;
  }
  if (argc > 1 && std::string(argv[1]) == "--patterns") {
    handle_line("{\"v\":3,\"id\":\"p\",\"channel\":1,\"op\":\"pattern\",\"mode\":\"blink\",\"mhz\":5000}");
    assert(pin_levels[D0] == HIGH && pin_levels[D10] == HIGH);
    clock_ms = 95; loop(); assert(pin_levels[D0] == HIGH);
    const uint32_t phase = phases[0];
    handle_line("{\"v\":3,\"id\":\"p\",\"channel\":1,\"op\":\"pattern\",\"mode\":\"blink\",\"mhz\":5000}");
    assert(phases[0] == phase && phases[4] == phase);
    clock_ms = 100; loop(); assert(pin_levels[D0] == LOW && pin_levels[D10] == LOW);
    clock_ms = 605; loop(); assert(phases[0] == 25000 && phases[4] == phases[0]);
    handle_line("{\"v\":3,\"id\":\"w\",\"channel\":4,\"op\":\"pattern\",\"mode\":\"solid\",\"mhz\":0}");
    assert(pin_levels[D6] == HIGH && pin_levels[D7] == LOW);
    clock_ms = 2095; loop(); assert(modes[0] == UNAVAILABLE && stale_patterns[4]);
    handle_line("{\"v\":3,\"id\":\"k\",\"channel\":1,\"op\":\"keep\"}");
    assert(stale_patterns[0]);
    handle_line("{\"v\":2,\"id\":\"off\",\"channel\":1,\"op\":\"set\",\"state\":\"off\"}");
    assert(modes[0] == LEGACY && pin_levels[D0] == LOW && modes[4] == UNAVAILABLE);
    // Millisecond rollover preserves phase and lease subtraction on uint32_t.
    clock_ms = 0xfffffff0UL;
    handle_line("{\"v\":3,\"id\":\"b\",\"channel\":2,\"op\":\"pattern\",\"mode\":\"blink\",\"mhz\":5000}");
    clock_ms = 84; loop(); assert(phases[1] == 500000 && pin_levels[D3] == LOW);
    assert(!stale_patterns[1] && phases[5] == phases[1]);
    return 0;
  }
  if (argc > 1) {
    handle_line("{\"v\":2,\"id\":\"a\",\"channel\":8,\"op\":\"set\",\"state\":\"on\"}");
    assert(pin_levels[D7] == HIGH);
    clock_ms = 999; loop(); assert(pin_levels[D7] == HIGH);
    clock_ms = 1000; loop(); assert(pin_levels[D7] == LOW && light_states[7]);
    clock_ms = 2000; loop(); assert(pin_levels[D7] == HIGH);
    handle_line("{\"v\":2,\"id\":\"b\",\"channel\":8,\"op\":\"set\",\"state\":\"off\"}");
    clock_ms = 4000; loop(); assert(pin_levels[D7] == LOW && !light_states[7]);
    for (int pin : LIGHT_PINS) assert(pin_levels[pin] == LOW);
    return 0;
  }
  Serial.input.assign(std::istreambuf_iterator<char>(std::cin), std::istreambuf_iterator<char>());
  loop();
  std::cout << writes << '\n' << Serial.output;
}
