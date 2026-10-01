import yfinance as yf


TICKERS=["RELIANCE.NS","TCS.NS","HINDUNILVR.NS","MARUTI.NS","ITC.NS"]

d
    
for t in TICKERS:
    stock=yf.Ticker(t)
    info=stock.info

    roe=info.get("returnOnEquity")
    if roe is None:
        roe=get_roe(stock)

    


    print(f"\n --- {t} ---")
    print("Revenue growth:",info.get("revenueGrowth"))
    print("Profit Margin:",info.get("profitMargins"))
    print("ROE:",roe)
    print("Current Price:",info.get("currentPrice"))

    financials=stock.financials
    print("YOE:",financials.shape[1]
    if not financials.empty else 0)

