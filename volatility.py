"""Indicateurs de volatilité (fonctions pures, indépendantes de Streamlit)."""
from __future__ import annotations

import numpy as np
import pandas as pd

import config

JOURS_BOURSE_AN = 252
NIVEAUX = [("Faible", "🟢"), ("Normale", "🔵"), ("Élevée", "🟡"), ("Tendue", "🔴")]
HORIZONS = {
    "Aujourd'hui": 0,
    "Il y a 1 semaine (5 séances)": 5,
    "Il y a 1 mois (21 séances)": 21,
    "Il y a 3 mois (63 séances)": 63,
}


def vol_realisee(close, n):
    """Écart-type des rendements log sur n séances, annualisé (x racine de 252), en %."""
    rend = np.log(close / close.shift(1))
    return rend.rolling(n).std() * np.sqrt(JOURS_BOURSE_AN) * 100


def atr_wilder(ohlc, n=14):
    """ATR de Wilder en points. None si High/Low/Close manquent ou historique trop court."""
    if ohlc is None or not {"High", "Low", "Close"} <= set(ohlc.columns):
        return None
    d = ohlc[["High", "Low", "Close"]].dropna()
    if len(d) < n + 1:
        return None
    pc = d["Close"].shift(1)
    tr = pd.concat(
        [d["High"] - d["Low"], (d["High"] - pc).abs(), (d["Low"] - pc).abs()], axis=1
    ).max(axis=1).iloc[1:]
    valeurs = np.full(len(tr), np.nan)
    valeurs[n - 1] = tr.iloc[:n].mean()
    for i in range(n, len(tr)):
        valeurs[i] = (valeurs[i - 1] * (n - 1) + tr.iloc[i]) / n
    return pd.Series(valeurs, index=tr.index)


def derniere_annee(serie):
    s = serie.dropna()
    if s.empty:
        return s
    return s[s.index > s.index[-1] - pd.DateOffset(years=1)]


def percentile_rang(serie, valeur):
    """Part (en %) des observations inférieures à la valeur (égalités = moitié)."""
    s = serie.dropna()
    if len(s) == 0:
        return None
    return float(((s < valeur).sum() + 0.5 * (s == valeur).sum()) / len(s) * 100)


def seuils_niveaux(vxn_annee):
    """Seuils manuels (config) ou percentiles de l'historique. None si indisponibles."""
    if config.SEUILS_MANUELS is not None:
        return {"seuils": tuple(float(x) for x in config.SEUILS_MANUELS),
                "origine": "seuils manuels (config.py)"}
    s = vxn_annee.dropna()
    if len(s) < config.HISTORIQUE_MIN_OBS:
        return None
    p = np.percentile(s, config.PERCENTILES_NIVEAUX)
    noms = " / ".join(f"P{q}" for q in config.PERCENTILES_NIVEAUX)
    return {"seuils": tuple(float(x) for x in p),
            "origine": f"{noms} du VXN sur 1 an ({len(s)} séances)"}


def classer(valeur, seuils):
    a, b, c = seuils
    i = 0 if valeur < a else 1 if valeur < b else 2 if valeur < c else 3
    return NIVEAUX[i]


def variation(serie, n=1):
    """Variation sur n séances : (points, %). None si historique insuffisant."""
    s = serie.dropna()
    if len(s) <= n:
        return None
    pts = s.iloc[-1] - s.iloc[-1 - n]
    return float(pts), float(pts / s.iloc[-1 - n] * 100)


def tendance(serie, n=None, facteur=None):
    """Hausse / baisse / stable, comparée à la dispersion habituelle des variations."""
    n = n or config.SEANCES_TENDANCE
    facteur = config.FACTEUR_STABILITE if facteur is None else facteur
    s = serie.dropna()
    ecarts = s.diff(n).dropna()
    if len(ecarts) < 30:
        return None
    seuil = float(facteur * ecarts.std())
    delta = float(s.iloc[-1] - s.iloc[-1 - n])
    if delta > seuil:
        etat, icone = "En hausse", "⬆️"
    elif delta < -seuil:
        etat, icone = "En baisse", "⬇️"
    else:
        etat, icone = "Stable", "➡️"
    return {"etat": etat, "icone": icone, "delta": delta, "seuil": seuil, "n": n}


def tableau_evolution(series, horizons=HORIZONS):
    """Valeur de chaque série aujourd'hui et il y a k séances. NaN si manquant."""
    lignes = {}
    for nom, k in horizons.items():
        ligne = {}
        for col, s in series.items():
            s = s.dropna()
            ligne[col] = float(s.iloc[-1 - k]) if len(s) > k else np.nan
        lignes[nom] = ligne
    return pd.DataFrame(lignes).T
