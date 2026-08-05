"""Minimal compatibility base for agents contributed on feature branches."""


class BaseAgent:
    def __init__(self, *, name: str, role: str) -> None:
        self.name = name
        self.role = role

