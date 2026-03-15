"""Helper utilities for truck1.eu tests."""

from dataclasses import dataclass
import random
import string

# Supported locales on truck1.eu
LOCALES = ["en", "de", "pl", "lt", "lv", "ee", "ru", "cs", "sk", "ro", "bg"]

BASE_URL = "https://www.truck1.eu"


@dataclass
class TestContact:
    name: str
    email: str
    phone: str
    message: str


def generate_test_contact(invalid_email: bool = False) -> TestContact:
    """Generate test contact data."""
    uid = random_string(6)
    email = f"test_{uid}@example.com" if not invalid_email else "not-an-email"
    return TestContact(
        name=f"Test User {uid}",
        email=email,
        phone="+48123456789",
        message=f"Automated test inquiry {uid}. Please ignore.",
    )


def random_string(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def get_locale_urls(path: str = "") -> list[tuple[str, str]]:
    """Return list of (locale, url) tuples for locale parameterization in tests."""
    return [(loc, f"{BASE_URL}/{loc}{path}") for loc in LOCALES]


def extract_number(text: str) -> int:
    """Extract first number from string (for ad counters)."""
    import re

    numbers = re.findall(r"\d+", text.replace(",", "").replace(" ", ""))
    return int(numbers[0]) if numbers else 0
