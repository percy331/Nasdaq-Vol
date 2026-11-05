import yfinance as yf
import numpy as np

vxn = yf.Ticker("^VXN").history(period="5d")["Close"].iloc[-1]

px = yf.Ticker("^NDX").history(period="3mo")["Close"]
rend = np.log(px / px.shift(1)).dropna()
vol20 = rend.tail(20).std() * np.sqrt(252) * 100

print(f"VXN (implicite)   : {vxn:.2f}")
print(f"Vol. réalisée 20j : {vol20:.2f} %")
