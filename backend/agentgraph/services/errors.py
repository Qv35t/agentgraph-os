class AgentNotFoundError(Exception):
    pass


class RunNotFoundError(Exception):
    pass


class LifecycleConflictError(Exception):
    pass


class OrchestrationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
