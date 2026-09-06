"""Serial owner, real host-compiled firmware, telemetry integration and recovery."""
import json
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch

import pytest
from dcamr.enforcement.serial_light_controller import SerialLightController, _decode
from dcamr.enforcement.enforcement_gateway import ControllerError
from dcamr.display.renderer import PatternRenderer


@pytest.fixture
def firmware(tmp_path):
    if not shutil.which('c++'):
        pytest.skip('host C++ compiler required')
    fixture = Path(__file__).parent/'fixtures/firmware'
    binary = tmp_path/'firmware'
    subprocess.run(['c++','-std=c++11','-I',str(fixture),str(fixture/'serial_driver.cpp'),'-o',str(binary)], check=True)
    process = subprocess.Popen([str(binary), '--interactive'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    class Transport:
        def __init__(self):
            self.pending = b''
            self.frames = []
        def write(self, raw):
            self.frames.append(json.loads(raw))
            process.stdin.write(raw)
            process.stdin.flush()
            self.pending += process.stdout.readline()
            return len(raw)
        def read(self, count):
            raw, self.pending = self.pending[:count], self.pending[count:]
            return raw
        def advance(self, ms):
            process.stdin.write(f'@{ms}\n'.encode())
            process.stdin.flush()
            assert process.stdout.readline() == b'{}\n'
    transport = Transport()
    controller = SerialLightController('host-fixture', transport=transport, timeout=1)
    yield controller, transport
    process.stdin.close()
    process.wait(timeout=3)
    process.stdout.close()


def state(fan=60, status='RUNNING'):
    return {'status': status, 'values': {'fan_actual_pct':fan, 'fan_target_pct':100,
            'temperature_f':160, 'power_w':421.6, 'battery_pct':60}}


def test_actual_firmware_mapping_readback_keep_and_stale(firmware):
    controller, transport = firmware
    now = [0]
    renderer = PatternRenderer(controller, clock=lambda: now[0])
    renderer.update(state(), received_at=0)
    assert renderer.status['state'] == 'CONFIGURED'
    assert len(transport.frames) == 5
    assert controller.pattern(2, operation='get')['mhz'] == 3200  # actual 60, not proposed 100
    assert controller.pattern(6, operation='get')['mhz'] == 3200
    assert controller.pattern(4, operation='get')['mode'] == 'solid'
    assert controller.pattern(8, operation='get')['mhz'] == 4100
    count = len(transport.frames)
    now[0] = .1
    renderer.update(state(), received_at=.1)
    assert len(transport.frames) == count
    now[0] = .6
    transport.advance(600)
    renderer.update(state(), received_at=.6)
    assert all(f['op'] == 'keep' for f in transport.frames[-5:])
    transport.advance(2600)
    assert controller.pattern(4, operation='get')['stale']
    now[0] = 2.6
    renderer.update(state(), received_at=2.6)
    assert renderer.status['state'] == 'STALE_OR_OVERRIDDEN'
    renderer.update(state(), received_at=2.6)
    assert controller.pattern(4, operation='get')['mode'] == 'solid'
    renderer.update(state(), received_at=0)
    assert controller.pattern(4, operation='get')['mode'] == 'unavailable'


def test_unknown_write_get_reconciliation_then_new_snapshot(firmware):
    controller, transport = firmware
    renderer = PatternRenderer(controller, clock=lambda: 0)
    original = controller.pattern
    def lost(*args, **kwargs):
        original(*args, **kwargs)
        raise ControllerError('lost acknowledgment')
    with patch.object(controller, 'pattern', side_effect=lost):
        renderer.update(state(), received_at=0)
    assert renderer.status['state'] == 'RECONCILIATION_REQUIRED'
    renderer.update(state(), received_at=0)
    assert transport.frames[-1]['op'] == 'get'
    renderer.update(state(fan=90), received_at=0)
    assert controller.pattern(2, operation='get')['mhz'] == 4550


def test_exhausted_battery_latches_all_channels_off(firmware):
    controller, _ = firmware
    renderer = PatternRenderer(controller, clock=lambda: 0)
    renderer.update(state(status='EXHAUSTED'), received_at=0)
    assert renderer.status['state'] == 'EXHAUSTED_OFF'
    for channel in range(1, 9):
        assert controller.pattern(channel, operation='get')['mode'] == 'off'


def test_legacy_override_and_malformed_v3_reply(firmware):
    controller, _ = firmware
    controller.pattern(1, mode='solid')
    controller.execute({'state':'off'})
    assert controller.pattern(1, operation='get')['mode'] == 'legacy'
    assert controller.pattern(5, operation='get')['mode'] == 'solid'
    raw = {'v':3,'id':'x','channel':1,'ok':True,'mode':'blink','mhz':True,'stale':False,'boot_id':'00000001'}
    assert _decode(json.dumps(raw).encode()) is None
