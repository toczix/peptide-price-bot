"""Fuzzy peptide name matching with alias support."""

from thefuzz import fuzz, process


class PeptideMatcher:
    def __init__(self, peptides: list[dict]):
        self.index: dict[str, dict] = {}
        for p in peptides:
            self.index[p["name"].lower()] = p
            self.index[p["slug"]] = p
            # Add aliases if present
            for alias in p.get("aliases") or []:
                if alias:
                    self.index[alias.lower().strip()] = p

    def match(self, query: str) -> tuple[dict | None, float]:
        """Match a user query to a peptide. Returns (peptide, confidence)."""
        q = query.strip().lower()

        # Exact match
        if q in self.index:
            return self.index[q], 100.0

        # Substring match (e.g., "bpc" matches "bpc-157")
        for key, peptide in self.index.items():
            if len(q) >= 3 and (q in key or key in q):
                return peptide, 90.0

        # Fuzzy match
        keys = list(self.index.keys())
        if not keys:
            return None, 0.0

        result = process.extractOne(q, keys, scorer=fuzz.ratio)
        if result and result[1] >= 65:
            return self.index[result[0]], result[1]

        return None, 0.0
