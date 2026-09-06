"""Compile actual firmware against a host GPIO/serial stub; not board acceptance."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(shutil.which('c++'), 'host C++ compiler required for firmware parser tests')
class SerialFirmwareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='alice-firmware-tests-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.binary = Path(cls.temp.name) / 'serial-driver'
        fixture = Path(__file__).parent / 'fixtures/firmware'
        subprocess.run(['c++', '-std=c++11', '-I', str(fixture),
                        str(fixture / 'serial_driver.cpp'), '-o', str(cls.binary)],
                       check=True, capture_output=True)

    def run_frames(self, frames):
        result = subprocess.run([str(self.binary)], input=frames, capture_output=True, check=True)
        count, _, replies = result.stdout.partition(b'\n')
        return int(count), replies

    def test_malformed_frames_never_write_and_next_valid_get_recovers(self):
        valid = b'{"v":1,"id":"a","op":"set","state":"on"}'
        cases = [valid.replace(b':1', b':01'), valid.replace(b'"a"', b'"a\t"'),
                 valid + b'\x00junk', valid.replace(b'"on"', b'"o\rn"')]
        for frame in cases:
            with self.subTest(frame=repr(frame)):
                writes, replies = self.run_frames(frame + b'\n{"v":1,"id":"get","op":"get"}\n')
                self.assertEqual(writes, 0)
                self.assertEqual(json.loads(replies.splitlines()[-1])['state'], 'off')

    def test_frame_limit_includes_newline(self):
        valid = b'{"v":1,"id":"a","op":"set","state":"on"}'
        for content_length, expected_writes in ((255, 1), (256, 0)):
            with self.subTest(content_length=content_length):
                writes, _ = self.run_frames(valid + b' ' * (content_length-len(valid)) + b'\n')
                self.assertEqual(writes, expected_writes)
