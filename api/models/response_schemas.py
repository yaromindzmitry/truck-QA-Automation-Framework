"""
response_schemas.py — schemas and validators for truck1.eu API responses.

Used for:
  - Checking JSON response structure
  - Validating required fields
  - Documenting API contract

Implemented as dataclass + static from_dict method for convenience.
"""

from dataclasses import dataclass, field
from typing import Optional, List


# ── Listing ────────────────────────────────────────────────────────────────

@dataclass
class ListingSchema:
    """Schema of a single listing from API."""
    id: Optional[str | int] = None
    title: Optional[str] = None
    price: Optional[float | str] = None
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    mileage: Optional[int] = None
    country: Optional[str] = None
    images: List[str] = field(default_factory=list)
    url: Optional[str] = None
    category: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "ListingSchema":
        return cls(
            id=data.get("id"),
            title=data.get("title") or data.get("name"),
            price=data.get("price"),
            year=data.get("year"),
            make=data.get("make") or data.get("brand"),
            model=data.get("model"),
            mileage=data.get("mileage") or data.get("km"),
            country=data.get("country"),
            images=data.get("images", []) or data.get("photos", []),
            url=data.get("url") or data.get("slug"),
            category=data.get("category"),
        )

    def is_valid(self) -> tuple[bool, list]:
        """Returns (is_valid, list of errors)."""
        errors = []
        if not self.id:
            errors.append("Missing required field: id")
        if not self.title:
            errors.append("Missing required field: title")
        return len(errors) == 0, errors


# ── Catalog (list of listings) ───────────────────────────────────────────────

@dataclass
class CatalogResponseSchema:
    """Schema of catalog response."""
    total: Optional[int] = None
    page: Optional[int] = None
    per_page: Optional[int] = None
    items: List[ListingSchema] = field(default_factory=list)
    has_next_page: Optional[bool] = None

    @classmethod
    def from_dict(cls, data: dict) -> "CatalogResponseSchema":
        items_raw = (
            data.get("items")
            or data.get("listings")
            or data.get("data")
            or data.get("results")
            or []
        )
        items = [ListingSchema.from_dict(item) for item in items_raw]

        return cls(
            total=data.get("total") or data.get("count"),
            page=data.get("page") or data.get("current_page"),
            per_page=data.get("per_page") or data.get("limit"),
            items=items,
            has_next_page=data.get("has_next_page") or data.get("next_page") is not None,
        )


# ── Contact form ──────────────────────────────────────────────────────────

@dataclass
class ContactFormSchema:
    """Schema of Contact the seller form request."""
    listing_id: str
    name: str
    email: str
    phone: str = ""
    message: str = ""

    def is_valid(self) -> tuple[bool, list]:
        errors = []
        if not self.listing_id:
            errors.append("listing_id is required")
        if not self.name or len(self.name.strip()) < 2:
            errors.append("name must be at least 2 characters")
        if not self.email or "@" not in self.email:
            errors.append("email is invalid")
        if len(self.message.strip()) < 5:
            errors.append("message too short")
        return len(errors) == 0, errors


# ── Leasing form ────────────────────────────────────────────────────────────

@dataclass
class LeasingRequestSchema:
    """Schema of Request a leasing offer form request."""
    listing_id: str
    name: str
    email: str
    phone: str = ""
    company: str = ""
    message: str = ""
    down_payment: Optional[float] = None
    term_months: Optional[int] = None

    def is_valid(self) -> tuple[bool, list]:
        errors = []
        if not self.listing_id:
            errors.append("listing_id is required")
        if not self.name or len(self.name.strip()) < 2:
            errors.append("name is required")
        if not self.email or "@" not in self.email:
            errors.append("email is invalid")
        return len(errors) == 0, errors


# ── API error ───────────────────────────────────────────────────────────────

@dataclass
class ApiErrorSchema:
    """Schema of API error."""
    status_code: int
    message: Optional[str] = None
    errors: dict = field(default_factory=dict)

    @classmethod
    def from_response(cls, resp) -> "ApiErrorSchema":
        try:
            body = resp.json()
            return cls(
                status_code=resp.status_code,
                message=body.get("message") or body.get("error"),
                errors=body.get("errors", {}),
            )
        except Exception:
            return cls(status_code=resp.status_code, message=resp.text[:200])
