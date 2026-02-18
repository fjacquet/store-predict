"""DRR (Data Reduction Ratio) reference table service.

Loads workload categories and their DRR values from a semicolon-delimited CSV.
Handles embedded newlines, trailing junk rows, and whitespace in fields.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class DRREntry:
    """A single DRR reference entry."""

    category: str
    subcategory: str
    ratio: float


class DRRTable:
    """Immutable DRR reference data loaded from CSV."""

    def __init__(self, entries: list[DRREntry]) -> None:
        self._entries = entries
        self._lookup: dict[tuple[str, str], float] = {
            (e.category, e.subcategory): e.ratio for e in entries
        }

    @classmethod
    def from_csv(cls, path: Path) -> DRRTable:
        """Load DRR entries from a semicolon-delimited CSV file.

        Handles:
        - Embedded newlines in quoted fields (PostgreSQL entry)
        - Trailing empty/junk rows
        - Whitespace in category/subcategory fields
        """
        df = pd.read_csv(
            path,
            sep=";",
            names=["category", "subcategory", "ratio"],
            skiprows=1,
            quoting=csv.QUOTE_ALL,
            engine="python",
        )
        # Drop rows with missing category (empty trailing rows)
        df = df.dropna(subset=["category"])
        # Convert ratio to numeric, coercing errors to NaN
        df["ratio"] = pd.to_numeric(df["ratio"], errors="coerce")
        # Drop rows with non-numeric ratio (junk rows like "Unknown (Reducible);;")
        df = df.dropna(subset=["ratio"])
        # Strip whitespace from string fields
        df["category"] = df["category"].str.strip()
        df["subcategory"] = df["subcategory"].str.strip()

        entries = [
            DRREntry(
                category=str(row["category"]),
                subcategory=str(row["subcategory"]),
                ratio=float(row["ratio"]),
            )
            for _, row in df.iterrows()
        ]
        return cls(entries)

    def get_ratio(self, category: str, subcategory: str) -> float:
        """Look up DRR for a category/subcategory pair. Returns 5.0 if not found."""
        return self._lookup.get((category, subcategory), 5.0)

    def get_conservative_ratio(self, workloads: list[tuple[str, str]]) -> float:
        """Return the minimum (most conservative) DRR for multiple workloads.

        Pre-sales needs defensible sizing: use the lowest ratio.
        Returns 5.0 for an empty workload list.
        """
        if not workloads:
            return 5.0
        return min(self.get_ratio(c, s) for c, s in workloads)

    @property
    def categories(self) -> list[str]:
        """Sorted unique category names."""
        return sorted(set(e.category for e in self._entries))

    @property
    def entries(self) -> list[DRREntry]:
        """Copy of the entries list (protects internal state)."""
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)
