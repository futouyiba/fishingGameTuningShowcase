from __future__ import annotations


class ContractViolation(ValueError):
    """Structured failure used by the reference harness."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        message = code if not detail else f"{code}: {detail}"
        super().__init__(message)
