from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ExtractRequest(BaseModel):
    text: str = ""


class ExtractResponse(BaseModel):
    vendor: str
    amount: float
    currency: str
    date: str


COMPANY_SUFFIXES = [
    "inc",
    "ltd",
    "llc",
    "limited",
    "corporation",
    "corp",
    "industries",
    "company",
    "co.",
    "gmbh",
    "plc",
    "solutions",
    "services"
]


AMOUNT_KEYWORD_PATTERNS = [
    r"(?i)total\s+due\s*[:\-]?\s*(?:USD|EUR|GBP)?\s*[$€£]?\s*([0-9][0-9.,]*)",
    r"(?i)amount\s+due\s*[:\-]?\s*(?:USD|EUR|GBP)?\s*[$€£]?\s*([0-9][0-9.,]*)",
    r"(?i)balance\s+due\s*[:\-]?\s*(?:USD|EUR|GBP)?\s*[$€£]?\s*([0-9][0-9.,]*)",
    r"(?i)grand\s+total\s*[:\-]?\s*(?:USD|EUR|GBP)?\s*[$€£]?\s*([0-9][0-9.,]*)",
    r"(?i)invoice\s+total\s*[:\-]?\s*(?:USD|EUR|GBP)?\s*[$€£]?\s*([0-9][0-9.,]*)",
    r"(?i)total\s*[:\-]?\s*(?:USD|EUR|GBP)?\s*[$€£]?\s*([0-9][0-9.,]*)",
]


def parse_number(s: str) -> float:
    s = s.strip()

    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            # European: 1.234,56
            s = s.replace(".", "")
            s = s.replace(",", ".")
        else:
            # US: 1,234.56
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")

        if len(parts[-1]) == 2:
            # Decimal comma
            s = s.replace(",", ".")
        else:
            # Thousands comma
            s = s.replace(",", "")

    return float(s)


@app.post("/extract", response_model=ExtractResponse)
def extract(req: ExtractRequest):

    try:
        text = (req.text or "").strip()

        if not text:
            return ExtractResponse(
                vendor="",
                amount=0.0,
                currency="",
                date=""
            )

        # ---------------- Vendor ----------------

        vendor = ""

        vendor_patterns = [
            r"(?i)vendor\s*:\s*(.+)",
            r"(?i)supplier\s*:\s*(.+)",
            r"(?i)bill\s+from\s*:\s*(.+)",
            r"(?i)issued\s+by\s*:\s*(.+)",
            r"(?i)payable\s+to\s*:\s*(.+)",
            r"(?i)from\s*:\s*(.+)",
        ]

        for pattern in vendor_patterns:
            m = re.search(pattern, text)
            if m:
                vendor = m.group(1).splitlines()[0].strip()
                break

        if not vendor:
            lines = [l.strip() for l in text.splitlines() if l.strip()]

            for line in lines:
                lower = line.lower()

                if any(suffix in lower for suffix in COMPANY_SUFFIXES):
                    vendor = line
                    break

        if not vendor:
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            vendor = lines[0] if lines else ""

        # ---------------- Amount ----------------

        amount = 0.0

        found = False

        for pattern in AMOUNT_KEYWORD_PATTERNS:
            m = re.search(pattern, text)

            if m:
                try:
                    amount = parse_number(m.group(1))
                    found = True
                    break
                except:
                    pass

        if not found:
            candidates = re.findall(
                r"(?:USD|EUR|GBP|\$|€|£)\s*([0-9][0-9.,]*)|([0-9][0-9.,]*)\s*(?:USD|EUR|GBP)",
                text,
                re.IGNORECASE,
            )

            values = []

            for a, b in candidates:
                value = a or b

                try:
                    values.append(parse_number(value))
                except:
                    pass

            if values:
                amount = max(values)

        if amount == 0.0:
            nums = re.findall(r"[0-9][0-9.,]*", text)

            values = []

            for n in nums:
                try:
                    values.append(parse_number(n))
                except:
                    pass

            if values:
                amount = max(values)

        # ---------------- Currency ----------------

        currency = ""

        m = re.search(r"\b(USD|EUR|GBP)\b", text, re.IGNORECASE)

        if m:
            currency = m.group(1).upper()
        elif "$" in text:
            currency = "USD"
        elif "€" in text:
            currency = "EUR"
        elif "£" in text:
            currency = "GBP"

        # ---------------- Date ----------------

        date = ""

        m = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)

        if m:
            date = m.group(1)

        return ExtractResponse(
            vendor=vendor,
            amount=amount,
            currency=currency,
            date=date,
        )

    except Exception:
        return ExtractResponse(
            vendor="",
            amount=0.0,
            currency="",
            date=""
        )
