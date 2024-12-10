from enum import Enum


class TaskStatus(Enum):  # (Enum)
    INIT = 'init'
    UPLOADING = 'uploading'
    QUEUED = 'queued'
    IN_PROGRESS = 'in progress'
    COMPLETED = 'completed'
    FAILED = 'failed'
    STOPPED = 'stopped'

    # def __str__(self) -> str:
    #     return str.__str__(self)
