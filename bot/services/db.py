"""Supabase database layer — reads peptides, vendors, and products."""

from supabase import create_client, Client


class PeptideDB:
    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)
        self.peptides: list[dict] = []

    def load_peptides(self):
        """Load all peptides into memory for fast matching."""
        res = self.client.table("peptides").select("*").execute()
        self.peptides = res.data
        print(f"Loaded {len(self.peptides)} peptides")

    def get_products(self, peptide_id: str, limit: int = 8) -> list[dict]:
        """Get top products for a peptide, sorted by price_per_mg.

        Mirrors the filters from the website:
        - No blends
        - No capsules/tablets (URL pattern filter)
        - Must have price >= 1
        - Must be in stock
        """
        res = (
            self.client.table("products")
            .select("*, vendor:vendors(name, url, affiliate_url, affiliate_param, coupon_code, coupon_description, finnrick_avg_score)")
            .eq("peptide_id", peptide_id)
            .eq("is_blend", False)
            .eq("in_stock", True)
            .gte("price", 1)
            .filter("price_per_mg", "not.is", "null")
            .order("price_per_mg")
            .limit(limit)
            .execute()
        )
        # Filter out capsules/tablets in Python (Supabase doesn't support NOT ILIKE well)
        skip = ("capsule", "caps", "tablet", "oral", "nasal-spray")
        return [
            p for p in res.data
            if not any(s in (p.get("product_url") or "").lower() for s in skip)
        ]

    def get_dosages(self, peptide_id: str) -> list[dict]:
        """Get available dosages for a peptide with vendor counts."""
        products = self.get_products(peptide_id, limit=100)
        dosages: dict[float, int] = {}
        for p in products:
            qty = p.get("quantity_mg")
            if qty:
                dosages[qty] = dosages.get(qty, 0) + 1
        return sorted(
            [{"mg": mg, "vendors": count} for mg, count in dosages.items()],
            key=lambda d: d["vendors"],
            reverse=True,
        )

    def get_products_by_dose(self, peptide_id: str, dose_mg: float, limit: int = 8) -> list[dict]:
        """Get products for a specific dosage."""
        all_products = self.get_products(peptide_id, limit=50)
        return [p for p in all_products if p.get("quantity_mg") == dose_mg][:limit]

    def get_vendor(self, vendor_id: str) -> dict | None:
        res = (
            self.client.table("vendors")
            .select("*")
            .eq("id", vendor_id)
            .single()
            .execute()
        )
        return res.data
