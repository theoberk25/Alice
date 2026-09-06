"""Console-local evidence contract. None of these objects grants authorization."""
from enum import Enum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

POLICY = "alice.live-face.v3"
POSES = ("CENTER", "LEFT", "RIGHT", "UP", "DOWN", "UP_LEFT", "UP_RIGHT")

class Outcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_CONFIGURED = "NOT_CONFIGURED"

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

class Control(Strict):
    result: Outcome
    model: str
    reason: str = Field(max_length=200)
    score: float | None = Field(default=None, ge=-1, le=1)

class Begin(Strict):
    schema_version: Literal["2.0"]
    session_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    nonce: str = Field(pattern=r"^[a-f0-9-]{36}$")
    boot_epoch: str = Field(pattern=r"^[a-f0-9-]{36}$")
    helper_epoch: str = Field(pattern=r"^[a-f0-9-]{36}$")
    policy: Literal["alice.live-face.v3"]
    purpose: Literal["ENROLLMENT", "LOGIN", "APPROVAL"]
    technician_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    generation: str = Field(min_length=1, max_length=100)

class Observation(Strict):
    session_id: str
    nonce: str
    service_epoch: str
    sequence: int = Field(ge=1, le=360)
    elapsed_ms: int = Field(ge=0, le=90_000)
    jpeg: str = Field(min_length=1, max_length=700_000)

class Binding(Strict):
    session_id: str
    nonce: str
    service_epoch: str

class GenerationCommit(Strict):
    technician_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    generation: str = Field(pattern=r"^[a-f0-9-]{36}$")
    previous_generation: str = Field(min_length=1, max_length=100)

class GenerationRemoval(Strict):
    technician_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    removal_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    expected_generations: list[str] = Field(min_length=1, max_length=2)

    @field_validator('expected_generations')
    @classmethod
    def bounded_generations(cls, values):
        if len(set(values)) != len(values) or any(not 1 <= len(v) <= 100 for v in values):
            raise ValueError('INVALID_REMOVAL_GENERATIONS')
        return values

def all_pass(controls: dict[str, Control]) -> bool:
    required = {"identity", "quality", "capture_integrity", "pose", "pad"}
    return set(controls) == required and all(c.result == Outcome.PASS for c in controls.values())
