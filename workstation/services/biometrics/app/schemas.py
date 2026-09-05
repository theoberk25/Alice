from pydantic import BaseModel, ConfigDict, Field

class Identity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    technician_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")

class Capture(Identity):
    frames: list[str] = Field(min_length=1, max_length=10)

class Enrollment(Capture):
    frames: list[str] = Field(min_length=5, max_length=10)

class VerificationResult(BaseModel):
    result: str
    similarity: float
    threshold: float
    provider: str = "arcface"
    liveness: str = "NOT_CONFIGURED"
