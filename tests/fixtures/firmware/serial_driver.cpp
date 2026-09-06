// Host-only parser/framing test. This does not emulate electrical hardware.
#include "Arduino.h"
#include <iostream>
#include <iterator>
SerialMock Serial;
int writes = 0;
#include "../../../firmware/xiao_first_light/xiao_first_light.ino"
int main() {
  setup();
  writes = 0;
  Serial.input.assign(std::istreambuf_iterator<char>(std::cin), std::istreambuf_iterator<char>());
  loop();
  std::cout << writes << '\n' << Serial.output;
}
