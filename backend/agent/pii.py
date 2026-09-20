import re

PII_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN_REDACTED]"),
    (re.compile(r"\b(?:\d[ -]*?){13,19}\b"), "[CARD_NUMBER_REDACTED]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL_REDACTED]"),
    (re.compile(r"\b\d{3}[.\-\s]\d{3}[.\-\s]\d{4}\b"), "[PHONE_REDACTED]"),
]


def scrub_pii(text: str) -> str:
    for pattern, replacement in PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def scrub_record(record: dict) -> dict:
    scrubbed = dict(record)
    for key in ("origin_account", "dest_account"):
        value = scrubbed.get(key)
        if isinstance(value, str):
            scrubbed[key] = scrub_pii(value)
    return scrubbed
