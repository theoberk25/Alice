"""USB mount guard for the user-approved offline SQL storage configuration.

Ledger algorithms remain in dcamr.audit. This deployment guard detects a missing
or replaced mount and latches failure until runtime restart/revalidation. It is
not protection against a malicious kernel or a device that lies about fsync.
Working rules: AGENTS.md.
"""
from pathlib import Path
import os


class StorageUnavailable(RuntimeError):
    pass


class UsbStorage:
    def __init__(self, root, data_dir):
        self.root = Path(root).absolute()
        self.data_dir = Path(data_dir).absolute()
        self.failed = False
        try:
            if self.root.is_symlink() or not self.root.is_mount():
                raise OSError('USB root is not mounted')
            if not self.data_dir.resolve().is_relative_to(self.root.resolve()):
                raise OSError('Runtime data must stay on USB')
            st = self.root.stat()
            self.identity = (st.st_dev, st.st_ino)
            self.check()
        except OSError as exc:
            raise StorageUnavailable('USB storage unavailable; no local fallback') from exc

    def check(self):
        try:
            st = self.root.stat()
            if (self.failed or not self.root.is_mount() or self.root.is_symlink()
                    or (st.st_dev, st.st_ino) != self.identity
                    or not self.data_dir.resolve().is_relative_to(self.root.resolve())
                    or os.statvfs(self.root).f_flag & os.ST_RDONLY):
                raise OSError('USB mount lost, replaced or read-only')
            if self.data_dir.exists() and self.data_dir.stat().st_dev != st.st_dev:
                raise OSError('Data directory is on a different filesystem')
            for path in (self.data_dir, self.data_dir / 'evidence', self.data_dir / 'ledger.sqlite'):
                if (path.is_symlink() or not path.resolve().is_relative_to(self.root.resolve())
                        or (path.exists() and path.stat().st_dev != st.st_dev)):
                    raise OSError('Runtime data path redirects outside selected USB')
        except OSError as exc:
            self.failed = True
            raise StorageUnavailable('USB storage unavailable; restart and revalidate before execution') from exc
