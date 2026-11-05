import time
from datetime import datetime

import numpy as np
import yfinance as yf
from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

BARRES = "▁▂▃▄▅▆▇█"
RAFRAICHISSEMENT = 30  # secondes


def sparkline(valeurs):
    mini, maxi = min(valeurs), max(valeurs)
    ecart = (maxi - mini) or 1
    return "".join(BARRES[int((v - mini) / ecart * 7)] for v in valeurs)


def niveau(vxn):
    if vxn < 15:
        return "CALME", "green"
    if vxn < 20:
        return "NORMAL", "cyan"
    if vxn < 30:
        return "TENDU", "yellow"
    return "PANIQUE", "red"


def construire():
    try:
        ndx = yf.Ticker("^NDX").history(period="3mo")["Close"]
        vxn = yf.Ticker("^VXN").history(period="3mo")["Close"]
    except Exception as e:
        return Panel(f"Erreur de connexion : {e}", border_style="red")

    prix = ndx.iloc[-1]
    variation = (prix / ndx.iloc[-2] - 1) * 100
    rend = np.log(ndx / ndx.shift(1)).dropna()
    vol20 = rend.tail(20).std() * np.sqrt(252) * 100
    v = vxn.iloc[-1]
    nom, couleur = niveau(v)
    col_var = "green" if variation >= 0 else "red"

    table = Table.grid(padding=(0, 3))
    table.add_column(style="bold")
    table.add_column(justify="right")
    table.add_row("Nasdaq-100", f"{prix:,.2f}")
    table.add_row("Variation jour", Text(f"{variation:+.2f} %", style=col_var))
    table.add_row("VXN (implicite)", Text(f"{v:.2f}", style=couleur))
    table.add_row("Vol. réalisée 20j", f"{vol20:.2f} %")

    etat = Text(f"\n  ● {nom}  ", style=f"bold {couleur}")
    graphe = Text(f"\nVXN 30 jours\n{sparkline(list(vxn.tail(30)))}", style=couleur)
    heure = Text(
        f"\nMàj {datetime.now():%H:%M:%S} · toutes les {RAFRAICHISSEMENT}s · Ctrl+C pour quitter",
        style="dim",
    )

    return Panel(
        Group(table, etat, graphe, heure),
        title="📈 NASDAQ VOLATILITÉ",
        border_style=couleur,
        padding=(1, 3),
    )


try:
    with Live(construire(), refresh_per_second=1) as live:
        while True:
            time.sleep(RAFRAICHISSEMENT)
            live.update(construire())
except KeyboardInterrupt:
    pass
