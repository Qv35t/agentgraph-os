from enum import StrEnum


class VisionMode(StrEnum):
    DESCRIBE = "describe"
    DETAILED = "detailed"
    OCR = "ocr"
    OBJECTS = "objects"
    GROUNDING = "grounding"
    UI = "ui"
    CUSTOM = "custom"


class VisionAnalysisStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
