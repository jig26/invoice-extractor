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

    # -------- Vendor --------
    vendor_patterns = [
    r"(?i)vendor\s*:\s*(.+)",
    r"(?i)supplier\s*:\s*(.+)",
    r"(?i)bill\s+from\s*:\s*(.+)",
    r"(?i)from\s*:\s*(.+)",
    ]

    vendor = ""

    for p in vendor_patterns:
        m = re.search(p, text)
        if m:
            vendor = m.group(1).splitlines()[0].strip()
            break

    if not vendor:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        vendor = lines[0] if lines else ""

    # -------- Amount --------

amount = 0.0

amount_patterns = [
    r"(?i)(?:total(?:\s+due)?|amount(?:\s+due)?|balance(?:\s+due)?|grand\s+total|invoice\s+total|total\s+invoice)\s*[:\-]?\s*(?:USD|EUR|GBP)?\s*[$€£]?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",

    r"(?i)(?:USD|EUR|GBP)\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",

    r"[$€£]\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
]

for p in amount_patterns:
    m = re.search(p, text)
    if m:
        amount = float(m.group(1).replace(",", ""))
        break

    # -------- Currency --------
    m = re.search(r"\b(USD|EUR|GBP)\b", text, re.I)

    if m:
        currency = m.group(1).upper()
    elif "$" in text:
        currency = "USD"
    elif "€" in text:
        currency = "EUR"
    elif "£" in text:
        currency = "GBP"
    else:
        currency = ""

    # -------- Date --------
    date = ""

    m = re.search(r"\b(20\d\d-\d\d-\d\d)\b", text)

    if m:
        date = m.group(1)

    return ExtractResponse(
        vendor=vendor,
        amount=amount,
        currency=currency,
        date=date,
    )
