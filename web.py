from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

import config
import data
import volatility as volat

st.set_page_config(page_title="Nasdaq Volatilité", page_icon="📈", layout="wide")
st.title("📈 Nasdaq – Volatilité")

MOIS = {"3mo": 3, "6mo": 6, "1y": 12, "2y": 24}
periode = st.sidebar.selectbox("Période d'affichage", list(MOIS), index=1)
fenetre = st.sidebar.slider("Fenêtre vol. réalisée (séances)", 5, 60, 20)
if st.sidebar.button("🔄 Rafraîchir"):
    data.vider_cache()


def fmt(x, spec):
    return "—" if x is None or pd.isna(x) else format(x, spec)


def afficher_statut(d):
    pastille = {"ok": "🟢", "perime": "🟡", "indisponible": "⚪"}[d.statut]
    if d.serie is None:
        st.error(f"{pastille} {d.nom} : {d.message}")
        return
    heure = d.recuperee_le.astimezone(ZoneInfo(config.FUSEAU_AFFICHAGE))
    ligne = (
        f"{pastille} **{d.nom}** · {d.source} · dernière obs. {d.derniere_obs:%d/%m/%Y}"
        f" · récupérée à {heure:%H:%M %Z}"
    )
    if d.seance_en_cours:
        ligne += " · séance en cours (valeur provisoire)"
    st.caption(ligne)
    if d.message:
        st.warning(d.message)


# --- Données (1 an minimum : nécessaire au percentile et aux seuils) ---
periode_calc = "2y" if periode == "2y" else "1y"
ndx_d = data.charger("^NDX", periode_calc, "Nasdaq-100")
vxn_d = data.charger("^VXN", periode_calc, "VXN")
afficher_statut(ndx_d)
afficher_statut(vxn_d)
if not config.TEMPS_REEL:
    st.caption("⏱ Données différées : non garanties en temps réel.")
if ndx_d.serie is None or vxn_d.serie is None:
    st.stop()

ndx, vxn = ndx_d.serie, vxn_d.serie
if len(ndx) < 40 or len(vxn) < 40:
    st.error("Historique insuffisant pour calculer les indicateurs.")
    st.stop()

# --- Calculs ---
vol_f = volat.vol_realisee(ndx, fenetre)
vol_20 = volat.vol_realisee(ndx, 20)
vol_30 = volat.vol_realisee(ndx, 30)
atr = volat.atr_wilder(ndx_d.ohlc, 14)
vxn_an = volat.derniere_annee(vxn)
seuils = volat.seuils_niveaux(vxn_an)

prix = ndx.iloc[-1]
var_prix = (prix / ndx.iloc[-2] - 1) * 100
v = vxn.iloc[-1]
var_j = volat.variation(vxn, 1)
var_5 = volat.variation(vxn, 5)
pct_vxn = volat.percentile_rang(vxn_an, v) if len(vxn_an) >= config.HISTORIQUE_MIN_OBS else None
atr_val = float(atr.iloc[-1]) if atr is not None else None

# --- Indicateurs principaux ---
l1 = st.columns(4)
l1[0].metric("Nasdaq-100", f"{prix:,.0f}", f"{var_prix:+.2f} %")
l1[1].metric(
    "VXN (implicite, ~30 j)", f"{v:.2f}",
    f"{var_j[0]:+.2f} pt ({var_j[1]:+.1f} %)" if var_j else None, delta_color="off",
)
l1[2].metric(f"Vol. réalisée {fenetre} séances", f"{fmt(vol_f.iloc[-1], '.2f')} %")
if seuils:
    nom_niveau, icone = volat.classer(v, seuils["seuils"])
    l1[3].metric("Niveau de volatilité", f"{icone} {nom_niveau}")
else:
    l1[3].metric("Niveau de volatilité", "⚪ Indisponible")

l2 = st.columns(4)
l2[0].metric("Vol. réalisée 30 séances", f"{fmt(vol_30.iloc[-1], '.2f')} %")
l2[1].metric(
    "ATR 14 séances", f"{fmt(atr_val, ',.0f')} pts",
    f"{atr_val / prix * 100:.2f} % du cours" if atr_val else None, delta_color="off",
)
l2[2].metric(
    "Percentile du VXN (1 an)", f"{pct_vxn:.0f}e" if pct_vxn is not None else "—",
    help="Part des séances de l'année écoulée où le VXN était plus bas qu'aujourd'hui.",
)
l2[3].metric(
    "VXN sur 5 séances", f"{var_5[0]:+.2f} pt" if var_5 else "—",
    f"{var_5[1]:+.1f} %" if var_5 else None, delta_color="off",
)

if seuils:
    a, b, c = seuils["seuils"]
    st.caption(
        f"Niveaux : Faible < {a:.1f} ≤ Normale < {b:.1f} ≤ Élevée < {c:.1f} ≤ Tendue. "
        f"Seuils relatifs ({seuils['origine']}) : ils décrivent l'historique récent, "
        "ce ne sont pas des valeurs universelles."
    )
else:
    st.caption("⚪ Niveau indisponible : historique du VXN insuffisant pour calculer des seuils.")

# --- Direction de la volatilité ---
st.subheader("Direction de la volatilité")
for nom, serie in (("VXN (implicite)", vxn), (f"Réalisée {fenetre} séances", vol_f)):
    t = volat.tendance(serie)
    if t:
        st.markdown(
            f"**{nom}** : {t['icone']} {t['etat']} — {t['delta']:+.2f} pt sur {t['n']} séances "
            f"(zone de stabilité : ±{t['seuil']:.2f} pt)"
        )
    else:
        st.markdown(f"**{nom}** : ⚪ historique insuffisant")

# --- Implicite vs réalisée ---
st.subheader("Implicite vs réalisée")
if pd.notna(vol_f.iloc[-1]):
    ecart = v - vol_f.iloc[-1]
    sens = "au-dessus" if ecart > 0 else "en dessous"
    lecture = (
        "les options anticipent plus de mouvement que celui observé récemment"
        if ecart > 0 else
        "les options anticipent moins de mouvement que celui observé récemment"
    )
    st.markdown(f"Le VXN est **{sens}** de la réalisée de {abs(ecart):.2f} pt : {lecture}.")
st.caption(
    "VXN : volatilité implicite, anticipée par les options sur environ 30 jours, annualisée, "
    "en points de %. Volatilité réalisée : passée, calculée sur les N dernières séances à partir "
    "des rendements logarithmiques journaliers, annualisée (× √252), en %. "
    "ATR : amplitude moyenne journalière (lissage de Wilder), en points d'indice."
)

# --- Évolution sur plusieurs périodes ---
st.subheader("Évolution sur plusieurs périodes")
evol = volat.tableau_evolution(
    {"VXN": vxn, "Réalisée 20 séances": vol_20, "Réalisée 30 séances": vol_30}
)
evol["Écart VXN − réalisée 20"] = evol["VXN"] - evol["Réalisée 20 séances"]
st.dataframe(evol.apply(lambda col: col.map(lambda x: fmt(x, ".2f"))))

# --- Graphiques ---
debut = ndx.index[-1] - pd.DateOffset(months=MOIS[periode])
st.subheader("Volatilité implicite vs réalisée")
df = pd.DataFrame(
    {"VXN (implicite)": vxn, f"Réalisée {fenetre}j": vol_f, "Réalisée 30j": vol_30}
).dropna()
st.line_chart(df[df.index >= debut])

st.subheader("Nasdaq-100")
st.line_chart(ndx[ndx.index >= debut])

