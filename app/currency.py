"""
Currency conversion using exchangerate-api.com free tier.
Rates are cached for 1 hour to avoid excessive API calls.
Falls back to showing original currency if conversion fails.
"""
import requests
import logging
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

_cache = {
    "rates": {},
    "updated_at": None,
}

CACHE_TTL_MINUTES = 60
EXCHANGE_API_URL  = "https://api.exchangerate-api.com/v4/latest/AUD"

CURRENCY_SYMBOLS = {
    "AED": "AED ", "AFN": "؋",   "ALL": "L",    "AMD": "֏",   "ANG": "ƒ",
    "AOA": "Kz",   "ARS": "AR$", "AUD": "A$",   "AWG": "ƒ",   "AZN": "₼",
    "BAM": "KM",   "BBD": "Bds$","BDT": "৳",   "BGN": "лв",  "BHD": "BD",
    "BIF": "Fr",   "BMD": "BD$", "BND": "B$",   "BOB": "Bs.", "BRL": "R$",
    "BSD": "BS$",  "BTN": "Nu",  "BWP": "P",    "BYN": "Br",  "BZD": "BZ$",
    "CAD": "C$",   "CDF": "Fr",  "CHF": "Fr",   "CLP": "CL$", "CNY": "¥",
    "COP": "CO$",  "CRC": "₡",  "CUP": "CU$",  "CVE": "Esc", "CZK": "Kč",
    "DJF": "Fr",   "DKK": "kr",  "DOP": "RD$",  "DZD": "DA",  "EGP": "E£",
    "ERN": "Nfk",  "ETB": "Br",  "EUR": "€",    "FJD": "FJ$", "FKP": "FK£",
    "GBP": "£",    "GEL": "₾",  "GHS": "GH₵",  "GIP": "£",   "GMD": "D",
    "GNF": "Fr",   "GTQ": "Q",   "GYD": "GY$",  "HKD": "HK$", "HNL": "L",
    "HRK": "kn",   "HTG": "G",   "HUF": "Ft",   "IDR": "Rp",  "ILS": "₪",
    "INR": "₹",   "IQD": "IQ",  "IRR": "YER",  "ISK": "kr",  "JMD": "J$",
    "JOD": "JD",   "JPY": "¥",   "KES": "KSh",  "KGS": "с",   "KHR": "៛",
    "KMF": "Fr",   "KPW": "₩",  "KRW": "₩",   "KWD": "KD",  "KYD": "CI$",
    "KZT": "₸",   "LAK": "₭",  "LBP": "L£",   "LKR": "Rs",  "LRD": "L$",
    "LSL": "L",    "LYD": "LD",  "MAD": "MAD",  "MDL": "L",   "MGA": "Ar",
    "MKD": "ден",  "MMK": "K",   "MNT": "₮",   "MOP": "P",   "MRU": "UM",
    "MUR": "Rs",   "MVR": "Rf",  "MWK": "MK",   "MXN": "MX$", "MYR": "RM",
    "MZN": "MT",   "NAD": "N$",  "NGN": "₦",   "NIO": "C$",  "NOK": "kr",
    "NPR": "Rs",   "NZD": "NZ$", "OMR": "OMR",  "PAB": "B/.", "PEN": "S/.",
    "PGK": "K",    "PHP": "₱",  "PKR": "Rs",   "PLN": "zł",  "PYG": "₲",
    "QAR": "QAR",  "RON": "lei", "RSD": "din",  "RUB": "₽",  "RWF": "Fr",
    "SAR": "SAR",  "SBD": "SI$", "SCR": "Rs",   "SDG": "SD£", "SEK": "kr",
    "SGD": "S$",   "SHP": "£",   "SLL": "Le",   "SOS": "Sh",  "SRD": "SR$",
    "STN": "Db",   "SVC": "₡",  "SYP": "S£",   "SZL": "L",   "THB": "฿",
    "TJS": "SM",   "TMT": "T",   "TND": "DT",   "TOP": "T$",  "TRY": "₺",
    "TTD": "TT$",  "TWD": "NT$", "TZS": "Sh",   "UAH": "₴",  "UGX": "Sh",
    "USD": "US$",  "UYU": "UY$", "UZS": "som",  "VES": "Bs.S","VND": "₫",
    "VUV": "Vt",   "WST": "T",   "XAF": "Fr",   "XCD": "EC$", "XOF": "Fr",
    "XPF": "Fr",   "YER": "YER", "ZAR": "R",    "ZMW": "ZK",  "ZWL": "Z$",
}

PRIORITY_CURRENCIES = [
    "AUD", "USD", "EUR", "GBP", "NZD", "SGD", "JPY",
    "HKD", "CAD", "CHF", "INR", "AED", "ZAR", "THB",
    "MYR", "IDR", "PHP", "KRW", "CNY", "QAR", "SAR",
]

def _refresh_rates():
    """Fetch latest exchange rates from API."""
    try:
        response = requests.get(EXCHANGE_API_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            _cache["rates"]      = data.get("rates", {})
            _cache["updated_at"] = datetime.utcnow()
            log.info("Exchange rates refreshed — %d currencies",
                     len(_cache["rates"]))
            return True
    except Exception as e:
        log.error("Failed to fetch exchange rates: %s", e)
    return False

def _get_rates():
    """Return cached rates, refreshing if stale."""
    now     = datetime.utcnow()
    updated = _cache.get("updated_at")
    if (not updated or
            now - updated > timedelta(minutes=CACHE_TTL_MINUTES)):
        _refresh_rates()
    return _cache.get("rates", {})

def convert(amount, from_currency, to_currency):
    """Convert amount from one currency to another."""
    if from_currency == to_currency:
        return amount
    rates = _get_rates()
    if not rates:
        return amount
    try:
        if from_currency == "AUD":
            aud_amount = amount
        elif from_currency in rates:
            aud_amount = amount / rates[from_currency]
        else:
            log.warning("No rate for %s — returning original", from_currency)
            return amount
        if to_currency == "AUD":
            return round(aud_amount, 2)
        elif to_currency in rates:
            return round(aud_amount * rates[to_currency], 2)
        else:
            log.warning("No rate for %s — returning original", to_currency)
            return amount
    except Exception as e:
        log.error("Currency conversion error: %s", e)
        return amount

def format_price(amount, currency):
    """Format a price with currency symbol for display."""
    symbol = CURRENCY_SYMBOLS.get(currency, currency + " ")
    return f"{symbol}{amount:,.2f}"

def get_supported_currencies():
    """
    Return full list of supported currencies as (code, label) tuples
    for the profile dropdown. Priority currencies appear first,
    remainder sorted alphabetically. Built from the live rate cache.
    """
    rates = _get_rates()
    if not rates:
        return [(c, _currency_label(c)) for c in PRIORITY_CURRENCIES]
    all_codes = sorted(rates.keys())
    priority  = [c for c in PRIORITY_CURRENCIES if c in rates]
    remainder = [c for c in all_codes if c not in PRIORITY_CURRENCIES]
    return [(c, _currency_label(c)) for c in priority + remainder]

def _currency_label(code):
    """Build a human-readable dropdown label for a currency code."""
    symbol = CURRENCY_SYMBOLS.get(code)
    if symbol and symbol.strip() != code:
        return f"{code} ({symbol.strip()})"
    return code
