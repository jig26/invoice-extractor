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
    vendor = ""

    patterns = [
        r"Vendor[:\s]+(.+)",
        r"Supplier[:\s]+(.+)",
        r"Bill From[:\s]+(.+)",
        r"From[:\s]+(.+)",
    ]

    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            vendor = m.group(1).split("\n")[0].strip()
            break

    if vendor == "":
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            vendor = lines[0]

    # -------- Amount --------
    amount = 0.0

    amount_patterns = [
        r"Total(?: Due)?[:\s]*[$€£]?\s*([0-9]+(?:\.[0-9]{1,2})?)",
        r"Amount(?: Due)?[:\s]*[$€£]?\s*([0-9]+(?:\.[0-9]{1,2})?)",
        r"[$€£]\s*([0-9]+(?:\.[0-9]{1,2})?)",
    ]

    for p in amount_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            amount = float(m.group(1))
            break

    # -------- Currency --------
    currency = ""

    m = re.search(r"\b(USD|EUR|GBP|INR|JPY|AUD|CAD)\b", text, re.IGNORECASE)

    if m:
        currency = m.group(1).upper()
    else:
        if "$" in text:
            currency = "USD"
        elif "€" in text:
            currency = "EUR"
        elif "£" in text:
            currency = "GBP"

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