class RuntimeContractError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"{code}: {message}")

    def as_result(self) -> dict:
        return {
            "status": "blocked",
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }
