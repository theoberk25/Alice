#pragma once
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <cstdio>
#include <string>
#define D0 1
#define D6 43
#define HIGH 1
#define LOW 0
#define OUTPUT 1
#define F(x) x
struct SerialMock {
  std::string input, output;
  size_t cursor = 0;
  void print(const char *s) { output += s; }
  void begin(int) {}
  operator bool() { return true; }
  int available() { return cursor < input.size(); }
  int read() { return available() ? static_cast<unsigned char>(input[cursor++]) : -1; }
};
extern SerialMock Serial;
extern int writes;
inline void digitalWrite(int, int) { writes++; }
inline void pinMode(int, int) {}
inline unsigned long millis() { return 0; }
inline void delay(int) {}
inline unsigned int esp_random() { return 1; }
