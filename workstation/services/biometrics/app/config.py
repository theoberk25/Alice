from dataclasses import dataclass
from pathlib import Path
import os

@dataclass(frozen=True)
class Settings:
    token: str
    data_dir: Path
    model_root: Path
    threshold: float = 0.45
    model_name: str = "buffalo_l"

    @classmethod
    def from_env(cls):
        root = Path(__file__).resolve().parents[1]
        value = float(os.getenv("ALICE_FACE_THRESHOLD", "0.45"))
        if not 0 < value < 1:
            raise ValueError("ALICE_FACE_THRESHOLD must be between 0 and 1")
        return cls(os.getenv("ALICE_BIOMETRIC_TOKEN", ""), Path(os.getenv("ALICE_BIOMETRIC_DATA_DIR") or root / "data"), Path(os.getenv("ALICE_INSIGHTFACE_ROOT") or root / "models"), value)
