"""USB deployment guard; temporary directories simulate removal, not physical USB."""
from pathlib import Path
from unittest.mock import patch

import pytest
from dcamr.usb_storage import UsbStorage, StorageUnavailable


def test_requires_mounted_volume_and_never_creates_missing_mount(tmp_path):
    root = tmp_path / 'missing'
    with pytest.raises(StorageUnavailable):
        UsbStorage(root, root / 'data')
    assert not root.exists()
    root.mkdir()
    with pytest.raises(StorageUnavailable):
        UsbStorage(root, root / 'data')


def test_missing_replaced_and_read_only_volume_latches_failure(tmp_path):
    root = tmp_path / 'usb'
    root.mkdir()
    with patch.object(Path, 'is_mount', return_value=True):
        guard = UsbStorage(root, root / 'data')
        guard.check()
        root.rename(tmp_path / 'removed')
        root.mkdir()
        with pytest.raises(StorageUnavailable):
            guard.check()
        root.rmdir()
        (tmp_path / 'removed').rename(root)
        with pytest.raises(StorageUnavailable):
            guard.check()  # operator restart/revalidation required


def test_data_must_stay_on_selected_usb(tmp_path):
    with patch.object(Path, 'is_mount', return_value=True):
        with pytest.raises(StorageUnavailable):
            UsbStorage(tmp_path, tmp_path.parent / 'other')


def test_runtime_requires_private_key_off_usb_and_stops_after_removal(tmp_path):
    from dcamr.main import FirstLightRuntime, StartupError
    from lab.first_light import build_release
    from lab.first_light.terminal_client import build_envelope
    root = tmp_path / 'usb'
    root.mkdir()
    release = build_release.build(root / 'bundle')
    trust = bytes.fromhex((root / 'bundle/trust/manifest_public.hex').read_text().strip())
    seed = bytes.fromhex((root / 'bundle/client/term-agent-01-k1.seed').read_text().strip())
    with patch.object(Path, 'is_mount', return_value=True):
        with pytest.raises(StartupError):
            FirstLightRuntime(release_dir=release, trusted_manifest_key=trust,
                              data_dir=root / 'data', esp_base_url='http://127.0.0.1:1',
                              usb_root=root)
        key = tmp_path / 'private-ledger.seed'
        key.write_text('01' * 32)
        runtime = FirstLightRuntime(release_dir=release, trusted_manifest_key=trust,
                                   data_dir=root / 'data', esp_base_url='http://127.0.0.1:1',
                                   usb_root=root, ledger_key_file=key, initialize_ledger=True)
        try:
            assert (root / 'data/ledger.sqlite').is_file()
            assert not (root / 'data/ledger_key.seed').exists()
            root.rename(tmp_path / 'removed')
            code, result = runtime.handle_request(build_envelope(seed, state='on'))
            assert code == 503
            assert result['reason_code'] == 'STORAGE_UNAVAILABLE'
            assert not root.exists()
        finally:
            runtime.close()


def test_usb_data_subdirectories_cannot_redirect_evidence_off_volume(tmp_path):
    root = tmp_path / 'usb'
    root.mkdir()
    data = root / 'data'
    data.mkdir()
    outside = tmp_path / 'private-local'
    outside.mkdir()
    (data / 'evidence').symlink_to(outside, target_is_directory=True)
    with patch.object(Path, 'is_mount', return_value=True):
        with pytest.raises(StorageUnavailable):
            UsbStorage(root, data)


def test_missing_usb_sql_snapshot_is_not_replaced_with_empty_history(tmp_path):
    from dcamr.main import FirstLightRuntime, StartupError
    from lab.first_light import build_release
    root = tmp_path / 'usb'
    root.mkdir()
    release = build_release.build(root / 'bundle')
    trust = bytes.fromhex((root / 'bundle/trust/manifest_public.hex').read_text().strip())
    key = tmp_path / 'key.seed'
    key.write_text('01' * 32)
    with patch.object(Path, 'is_mount', return_value=True):
        with pytest.raises(StartupError, match='existing USB ledger'):
            FirstLightRuntime(release_dir=release, trusted_manifest_key=trust,
                              data_dir=root / 'data', esp_base_url='http://127.0.0.1:1',
                              usb_root=root, ledger_key_file=key)
    assert not (root / 'data/ledger.sqlite').exists()
