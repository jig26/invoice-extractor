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
    text: str


class ExtractResponse(BaseModel):
    vendor: str
    amount: float
    currency: str
    date: str


@app.post("/extract", response_model=ExtractResponse)
def extract(req: ExtractRequest):

    text = req.text.strip()

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
        r"(?i)from\s*:\s*(.+)",
    ]

    for p in vendor_patterns:
        m = re.search(p, text)
        if m:
            vendor = m.group(1).splitlines()[0].strip()
            break

    if not vendor:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            vendor = lines[0]

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

    # ---------------- Amount ----------------

    amount = 0.0

    values = []

    for m in re.finditer(r"\d[\d,]*\.\d{2}", text):
        try:
            values.append(float(m.group().replace(",", "")))
        except ValueError:
            pass

    if values:
        amount = max(values)

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
