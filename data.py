"""Accès aux données : cache, horodatage, source et statut de fraîcheur."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf

import config


@dataclass
class Donnee:
    nom: str
    serie: pd.Series | None   # None = indisponible (jamais de valeur fictive)
    source: str
    recuperee_le: datetime    # horodatage UTC
    derniere_obs: pd.Timestamp | None
    statut: str               # "ok", "perime" ou "indisponible"
    message: str = ""
    seance_en_cours: bool = False
    ohlc: pd.DataFrame | None = None


_cache: dict = {}


def vider_cache():
    _cache.clear()


def maintenant_marche():
    return datetime.now(ZoneInfo(config.FUSEAU_MARCHE))


def marche_ouvert(t):
    """Lun-ven 9h30-16h, heure de New York (fériés non gérés)."""
    if t.weekday() >= 5:
        return False
    minutes = t.hour * 60 + t.minute
    return 9 * 60 + 30 <= minutes < 16 * 60


def evaluer_fraicheur(derniere_obs, aujourdhui):
    retard = int(np.busday_count(derniere_obs.date(), aujourdhui))
    if retard <= config.RETARD_MAX_JOURS_OUVRES:
        return "ok", ""
    return "perime", (
        f"Dernière observation du {derniere_obs:%d/%m/%Y} : "
        f"{retard} jours ouvrés de retard (un jour férié est possible)."
    )


def _telecharger(symbole, periode):
    df = yf.Ticker(symbole).history(period=periode)
    if df is None or df.empty or "Close" not in df:
        raise ValueError("aucune donnée reçue")
    df = df.dropna(subset=["Close"])
    if df.empty:
        raise ValueError("aucune donnée exploitable")
    colonnes = [c for c in ("Open", "High", "Low", "Close", "Volume") if c in df]
    df = df[colonnes].copy()
    df.index = pd.to_datetime(df.index.date)
    return df


def charger(symbole, periode, nom):
    cle = (symbole, periode)
    maintenant = datetime.now(timezone.utc)
    ancien = _cache.get(cle)
    if ancien and (maintenant - ancien.recuperee_le).total_seconds() < config.TTL_CACHE_S:
        return ancien
    try:
        df = _telecharger(symbole, periode)
    except Exception as e:
        if ancien:
            return replace(
                ancien,
                statut="perime",
                message=f"Rafraîchissement impossible ({e}) : anciennes données conservées.",
            )
        return Donnee(nom, None, config.SOURCE, maintenant, None,
                      "indisponible", f"Données indisponibles ({e}).")
    serie = df["Close"]
    t = maintenant_marche()
    statut, message = evaluer_fraicheur(serie.index[-1], t.date())
    d = Donnee(
        nom, serie, config.SOURCE, maintenant, serie.index[-1], statut, message,
        seance_en_cours=(serie.index[-1].date() == t.date() and marche_ouvert(t)),
        ohlc=df,
    )
    _cache[cle] = d
    return d
