"""Paramètres du projet (modifiables)."""

# --- Données ---
SOURCE = "Yahoo Finance (via yfinance)"
TEMPS_REEL = False                    # données différées
TTL_CACHE_S = 300                     # durée du cache, en secondes
FUSEAU_MARCHE = "America/New_York"
FUSEAU_AFFICHAGE = "Europe/Paris"     # change-le si besoin
RETARD_MAX_JOURS_OUVRES = 1           # au-delà : donnée périmée

# --- Classification de la volatilité (VXN des 12 derniers mois) ---
# Faible < P25 <= Normale < P75 <= Élevée < P90 <= Tendue
PERCENTILES_NIVEAUX = (25, 75, 90)
SEUILS_MANUELS = None                 # ex. (15, 20, 30) pour imposer tes seuils
HISTORIQUE_MIN_OBS = 200              # séances minimum pour les percentiles

# --- Tendance de la volatilité ---
SEANCES_TENDANCE = 5                  # comparaison à il y a 5 séances
FACTEUR_STABILITE = 0.5               # stable si variation < 0,5 x écart-type habituel
