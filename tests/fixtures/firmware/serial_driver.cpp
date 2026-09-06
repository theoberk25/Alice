// Host-only parser/framing test. This does not emulate electrical hardware.
#include "Arduino.h"
#include <iostream>
#include <iterator>
#include <cassert>
SerialMock Serial;
int writes = 0;
#include "../../../firmware/xiao_first_light/xiao_first_light.ino"
int main(int argc, char**) {
  setup();
  writes = 0;
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
