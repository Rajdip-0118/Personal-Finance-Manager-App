# investment/utils.py
import yfinance as yf
from decimal import Decimal
import datetime as dt

def _annualized_return(start_price, end_price, years):
    if start_price <= 0:
        return None
    return round(((end_price / start_price) ** (1 / years) - 1) * 100, 2)

def get_yahoo_return(symbol, years=5):
    """Fetch annualized return using Yahoo Finance (live)."""
    end = dt.date.today()
    start = end - dt.timedelta(days=365 * years)
    try:
        data = yf.download(symbol, start=start, end=end, progress=False)
        if data.empty:
            return None
        start_price = float(data["Close"].iloc[0])
        end_price = float(data["Close"].iloc[-1])
        return _annualized_return(start_price, end_price, years)
    except Exception:
        return None

def get_expected_return_by_type(inv_type):
    t = (inv_type or "").lower()

    mapping = {
        "stock": lambda: get_yahoo_return("^NSEI"),  # Nifty 50 index in India
        "etf": lambda: get_yahoo_return("NIFTYBEES.NS"),  # Nifty ETF in India
        "crypto": lambda: get_yahoo_return("BTC-INR"),
        "gold": lambda: get_yahoo_return("GOLDBEES.NS"),  # Gold ETF in India
        "mutual fund": lambda: get_yahoo_return("^NSMIDCP"),  # or USA’s ^GSPC
        "bond": lambda: get_yahoo_return("ICICIB22.NS"),  # 10-year ICICI bond yield
        "real estate": lambda: get_yahoo_return("EMBASSY.NS"),  # US REIT ETF
        
    }


    func = mapping.get(t)
    if not func:
        return None  # ❌ skip unknown types

    rate = func()
    if rate is None:
        # ❌ do NOT fallback — skip update if live data unavailable
        return None

    return rate

