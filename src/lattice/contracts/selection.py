"""Durable exact atom-revision selections shown during a beat."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol


@dataclass(frozen=True)
class ContextAtomSelection:
    """One exact atom revision selected for one employee beat."""

    employee_id: str
    beat_run_id: str
    key: str
    revision: int

    def __post_init__(self) -> None:
        if self.revision < 1:
            raise ValueError("selection revision must be positive")


class ContextSelectionConflictError(RuntimeError):
    """A selection replay conflicts with durable beat lineage."""


@dataclass(frozen=True)
class ContextSelectionSnapshot:
    """One capture attempt, including whether every selected hit was versioned."""

    employee_id: str
    beat_run_id: str
    selections: tuple[ContextAtomSelection, ...]
    complete: bool

    def __post_init__(self) -> None:
        _validate_selection_set(self.employee_id, self.beat_run_id, self.selections)

    @property
    def selected_count(self) -> int:
        return len(self.selections)

    @property
    def selected_digest(self) -> bytes:
        return context_selection_digest(self.selections)


@dataclass(frozen=True)
class ContextSelectionCaptureOutcome:
    """Cumulative durable state after one capture transaction commits."""

    employee_id: str
    beat_run_id: str
    selections: tuple[ContextAtomSelection, ...]
    complete: bool

    def __post_init__(self) -> None:
        _validate_selection_set(self.employee_id, self.beat_run_id, self.selections)


class ContextSelectionJournal(Protocol):
    """Append-only durable context selections, sealed by an APPLIED beat."""

    def capture(
        self,
        snapshot: ContextSelectionSnapshot,
    ) -> ContextSelectionCaptureOutcome: ...

    def list_for_run(
        self,
        employee_id: str,
        beat_run_id: str,
    ) -> tuple[ContextAtomSelection, ...]: ...


def context_selection_digest(selections: tuple[ContextAtomSelection, ...]) -> bytes:
    """Return the stable digest of a canonical exact-revision selection set."""
    digest = sha256()
    for selection in sorted(selections, key=lambda item: (item.key, item.revision)):
        encoded_key = selection.key.encode("utf-8")
        digest.update(len(encoded_key).to_bytes(8, byteorder="big"))
        digest.update(encoded_key)
        digest.update(selection.revision.to_bytes(8, byteorder="big"))
    return digest.digest()


def _validate_selection_set(
    employee_id: str,
    beat_run_id: str,
    selections: tuple[ContextAtomSelection, ...],
) -> None:
    if any(
        (selection.employee_id, selection.beat_run_id) != (employee_id, beat_run_id)
        for selection in selections
    ):
        raise ValueError("snapshot selections must match the snapshot employee and beat")
    members = tuple((selection.key, selection.revision) for selection in selections)
    if len({key for key, _revision in members}) != len(members):
        raise ValueError("snapshot selections cannot contain duplicate atom keys")
