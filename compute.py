#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Météo des Marchés — moteur de calcul du baromètre Risk-On / Risk-Off.
=====================================================================

Ce script :
  1. télécharge 8 indicateurs cross-asset via yfinance (données Yahoo Finance) ;
  2. calcule, pour chaque indicateur, un sous-score 0–100 (0 = risk-off / peur,
     100 = risk-on / appétit pour le risque) ;
  3. agrège ces sous-scores en un score global du jour ;
  4. écrit le fichier data/data.json que le site lit pour s'afficher.

Méthode (identique pour les 8 indicateurs) :
  - on calcule un « signal brut » qui mesure l'appétit pour le risque ;
  - on le standardise en z-score sur une fenêtre glissante de 252 jours (~1 an) :
        z = (signal - moyenne_252j) / écart_type_252j
  - on l'oriente (certains indicateurs sont inversés : VIX haut = peur) ;
  - on le borne à [-2, +2] puis on le ramène linéairement sur 0–100 :
        sous-score = (z_borné + 2) / 4 * 100   ->   z=-2 => 0, z=0 => 50, z=+2 => 100
  - le score global est la MOYENNE des sous-scores disponibles ce jour-là.

Usage :
  python compute.py             # télécharge les données réelles et écrit data/data.json
  python compute.py --selftest  # teste la LOGIQUE sans réseau (conditions de crise simulées)

Projet Météo des Marchés — Anatole.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# PARAMÈTRES
# ---------------------------------------------------------------------------

WINDOW_RET = 20     # rendement relatif calculé sur 20 jours de bourse (~1 mois)
WINDOW_Z   = 252    # fenêtre glissante du z-score (~1 an de bourse)
Z_CLIP     = 2.0    # on borne le z-score à +/- 2 écarts-types

DL_START   = "2017-06-01"   # on télécharge dès 2017 pour « remplir » le z-score avant 2019
HIST_START = "2019-01-01"   # mais on n'expose l'historique qu'à partir de 2019

HERE      = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(HERE, "data")
DATA_PATH = os.path.join(DATA_DIR, "data.json")

# Zones de couleur (bornes en score)
ZONE_OFF_MAX     = 35   # 0–35   = Risk-off
ZONE_NEUTRAL_MAX = 65   # 35–65  = Neutre ; 65–100 = Risk-on

# Les 8 indicateurs.
#   type = "level" : on standardise le NIVEAU de la série (ex. VIX).
#   type = "ret"   : on standardise le RENDEMENT 20 jours d'une seule série (ex. dollar).
#   type = "pair"  : on standardise la DIFFÉRENCE des rendements 20 jours de deux séries.
#   sign = +1 : signal élevé  -> risk-on ;  sign = -1 : signal élevé -> risk-off (inversé).
INDICATORS = [
    {
        "key": "vix", "name": "VIX — volatilité", "type": "level",
        "tickers": ["^VIX"], "sign": -1,
        "meaning": "La « jauge de la peur » de Wall Street. Quand elle monte, les "
                   "investisseurs paient cher pour se protéger : c'est du risk-off.",
        "tag_on": "la volatilité reste basse", "tag_off": "la volatilité s'envole",
    },
    {
        "key": "spy_tlt", "name": "Actions vs Obligations (SPY / TLT)", "type": "pair",
        "tickers": ["SPY", "TLT"], "sign": +1,
        "meaning": "Les actions américaines contre les obligations d'État longues. "
                   "Si les actions surperforment, l'argent cherche le rendement "
                   "plutôt que la sécurité : risk-on.",
        "tag_on": "les actions dominent les obligations", "tag_off": "les obligations refuge surperforment",
    },
    {
        "key": "hyg_lqd", "name": "Crédit risqué vs sûr (HYG / LQD)", "type": "pair",
        "tickers": ["HYG", "LQD"], "sign": +1,
        "meaning": "La dette d'entreprise à haut rendement (HYG) contre la dette de "
                   "qualité (LQD). Si le « high yield » tient, le marché a confiance : risk-on.",
        "tag_on": "le crédit risqué tient bon", "tag_off": "le crédit à risque se tend",
    },
    {
        "key": "xly_xlp", "name": "Cycliques vs Défensives (XLY / XLP)", "type": "pair",
        "tickers": ["XLY", "XLP"], "sign": +1,
        "meaning": "Consommation discrétionnaire (loisirs, luxe) contre produits de base "
                   "(alimentation). Les cycliques mènent quand on parie sur la croissance : risk-on.",
        "tag_on": "les secteurs cycliques mènent", "tag_off": "rotation vers les secteurs défensifs",
    },
    {
        "key": "iwm_spy", "name": "Small caps vs Large caps (IWM / SPY)", "type": "pair",
        "tickers": ["IWM", "SPY"], "sign": +1,
        "meaning": "Les petites capitalisations, plus fragiles, surperforment quand "
                   "l'appétit pour le risque est fort : risk-on.",
        "tag_on": "les petites valeurs surperforment", "tag_off": "fuite vers les grandes capitalisations",
    },
    {
        "key": "gld_spy", "name": "Or vs Actions (GLD / SPY)", "type": "pair",
        "tickers": ["GLD", "SPY"], "sign": -1,
        "meaning": "L'or est la valeur refuge par excellence. S'il bat les actions, "
                   "c'est un réflexe de prudence : risk-off.",
        "tag_on": "l'or reste en retrait", "tag_off": "ruée vers l'or refuge",
    },
    {
        "key": "dxy", "name": "Dollar (DXY)", "type": "ret",
        "tickers": ["DX-Y.NYB"], "sign": -1,
        "meaning": "Le dollar est la monnaie refuge mondiale. Quand il grimpe fort, "
                   "c'est souvent un signe de stress : risk-off.",
        "tag_on": "le dollar reste calme", "tag_off": "le dollar refuge se renforce",
    },
    {
        "key": "usdjpy", "name": "Yen (USD/JPY)", "type": "ret",
        "tickers": ["JPY=X"], "sign": +1,
        "meaning": "Le yen se renforce (USD/JPY baisse) quand les investisseurs "
                   "débouclent leurs positions risquées financées en yen : risk-off.",
        "tag_on": "le yen reste faible (carry serein)", "tag_off": "le yen se renforce (débouclage du carry)",
    },
]

ALL_TICKERS = sorted({t for ind in INDICATORS for t in ind["tickers"]})

# Événements de test à annoter sur l'historique (fenêtres de recherche du minimum).
EVENTS = [
    {"id": "covid",  "label": "Covid-19 (krach)",       "start": "2020-02-15", "end": "2020-04-30"},
    {"id": "rates",  "label": "2022 — hausse des taux",  "start": "2022-01-01", "end": "2022-12-31"},
    {"id": "carry",  "label": "Débouclage carry yen",    "start": "2024-07-25", "end": "2024-08-20"},
]


# ---------------------------------------------------------------------------
# TÉLÉCHARGEMENT DES DONNÉES
# ---------------------------------------------------------------------------

def _close_series(ticker: str) -> pd.Series:
    """Télécharge la série des cours de clôture ajustés d'un ticker (index = dates naïves)."""
    import yfinance as yf
    hist = yf.Ticker(ticker).history(start=DL_START, auto_adjust=True)
    if hist is None or hist.empty or "Close" not in hist.columns:
        raise ValueError(f"aucune donnée pour {ticker}")
    s = hist["Close"].copy()
    # On enlève le fuseau horaire pour aligner proprement toutes les séries.
    s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
    s = s[~s.index.duplicated(keep="last")]
    return s.sort_index()


def fetch_prices():
    """Renvoie (DataFrame des clôtures alignées, liste des tickers en échec)."""
    series, missing = {}, []
    for t in ALL_TICKERS:
        try:
            series[t] = _close_series(t)
            print(f"  [ok]   {t:<12} {len(series[t])} points")
        except Exception as exc:  # noqa: BLE001 — on veut continuer malgré un ticker KO
            missing.append(t)
            print(f"  [ÉCHEC] {t:<12} -> {exc}")

    if "SPY" not in series:
        raise RuntimeError("SPY est indisponible : impossible de construire le calendrier de bourse.")

    prices = pd.DataFrame(series)
    # On aligne tout sur le calendrier de SPY (jours de bourse US) et on comble
    # les petits trous (change, indices) sur quelques jours maximum.
    prices = prices.reindex(series["SPY"].index).ffill(limit=5)
    return prices, missing


# ---------------------------------------------------------------------------
# CALCUL DES SIGNAUX ET DES SOUS-SCORES
# ---------------------------------------------------------------------------

def rel_return(series: pd.Series, window: int = WINDOW_RET) -> pd.Series:
    """Rendement sur `window` jours de bourse : prix / prix(t-window) - 1."""
    return series / series.shift(window) - 1.0


def raw_signal(ind: dict, prices: pd.DataFrame):
    """Construit le signal brut (orienté risk-on avant z-score) d'un indicateur.
    Renvoie None si un ticker requis manque."""
    tks = ind["tickers"]
    if any(t not in prices.columns for t in tks):
        return None

    if ind["type"] == "level":
        return prices[tks[0]].astype(float)
    if ind["type"] == "ret":
        return rel_return(prices[tks[0]])
    if ind["type"] == "pair":
        a, b = tks
        return rel_return(prices[a]) - rel_return(prices[b])
    raise ValueError(f"type inconnu : {ind['type']}")


def to_subscore(raw: pd.Series, sign: int) -> pd.Series:
    """Transforme un signal brut en sous-score 0–100 via z-score glissant orienté."""
    mean = raw.rolling(WINDOW_Z, min_periods=WINDOW_Z).mean()
    std  = raw.rolling(WINDOW_Z, min_periods=WINDOW_Z).std()
    z = (raw - mean) / std.replace(0.0, np.nan)
    z = sign * z                          # orientation (inversion si sign = -1)
    z = z.clip(-Z_CLIP, Z_CLIP)           # bornage à +/- 2 sigma
    return (z + Z_CLIP) / (2 * Z_CLIP) * 100.0   # -> 0..100


def compute_subscores(prices: pd.DataFrame):
    """Renvoie (DataFrame des sous-scores par indicateur, liste des indicateurs indisponibles)."""
    cols, unavailable = {}, []
    for ind in INDICATORS:
        raw = raw_signal(ind, prices)
        if raw is None:
            unavailable.append(ind["key"])
            continue
        cols[ind["key"]] = to_subscore(raw, ind["sign"])
    sub = pd.DataFrame(cols)
    return sub, unavailable


def global_score(sub: pd.DataFrame) -> pd.Series:
    """Score global = moyenne des sous-scores disponibles chaque jour."""
    return sub.mean(axis=1, skipna=True)


# ---------------------------------------------------------------------------
# VERDICT AUTOMATIQUE
# ---------------------------------------------------------------------------

def zone_of(score: float) -> str:
    if score < ZONE_OFF_MAX:
        return "Risk-off"
    if score < ZONE_NEUTRAL_MAX:
        return "Neutre"
    return "Risk-on"


def tone_label(score: float) -> str:
    if score < 20:  return "Risk-off marqué"
    if score < 35:  return "Risk-off modéré"
    if score < 45:  return "Prudence"
    if score < 55:  return "Équilibre"
    if score < 65:  return "Appétit prudent"
    if score < 80:  return "Risk-on modéré"
    return "Risk-on marqué"


def make_verdict(score: float, today_subscores: dict) -> str:
    """Phrase-verdict à partir des indicateurs les plus extrêmes du jour."""
    by_key = {ind["key"]: ind for ind in INDICATORS}
    items = [(k, v) for k, v in today_subscores.items() if pd.notna(v)]
    if not items:
        return "Données insuffisantes pour un verdict."
    label = tone_label(score)
    lowest  = sorted(items, key=lambda kv: kv[1])[:2]      # plus risk-off
    highest = sorted(items, key=lambda kv: kv[1], reverse=True)[0]  # plus risk-on

    off_tags = [by_key[k]["tag_off"] for k, _ in lowest]
    on_tag = by_key[highest[0]]["tag_on"]

    if score < 45:      # tonalité prudente : on met en avant la nervosité
        txt = f"{label} : {off_tags[0]} et {off_tags[1]}"
        if highest[1] >= 55:
            txt += f", mais {on_tag}."
        else:
            txt += "."
    elif score > 55:    # tonalité sereine : on met en avant l'appétit
        highs = sorted(items, key=lambda kv: kv[1], reverse=True)[:2]
        on_tags = [by_key[k]["tag_on"] for k, _ in highs]
        txt = f"{label} : {on_tags[0]} et {on_tags[1]}"
        if lowest[0][1] <= 45:
            txt += f", même si {off_tags[0]}."
        else:
            txt += "."
    else:               # zone d'équilibre
        txt = (f"{label} : signaux partagés — {on_tag}, "
               f"tandis que {off_tags[0]}.")
    return txt


# ---------------------------------------------------------------------------
# CONSTRUCTION DU data.json
# ---------------------------------------------------------------------------

def _series_to_list(s: pd.Series, key: str = "s", ndig: int = 1):
    out = []
    for d, v in s.items():
        if pd.notna(v):
            out.append({"d": d.strftime("%Y-%m-%d"), key: round(float(v), ndig)})
    return out


def build_payload(prices: pd.DataFrame, missing: list[str]) -> dict:
    sub, unavailable = compute_subscores(prices)
    score = global_score(sub).dropna()
    if score.empty:
        raise RuntimeError("Aucun score calculable (pas assez d'historique).")

    score = score[score.index >= pd.Timestamp(HIST_START)]
    sub = sub.loc[score.index]

    last_date = score.index[-1]
    today = float(score.iloc[-1])

    change_1d = float(today - score.iloc[-2]) if len(score) >= 2 else None
    change_1w = float(today - score.iloc[-6]) if len(score) >= 6 else None

    # ----- sous-scores du jour + mini-séries 3 mois + tendance -----
    indicators_out = []
    today_subs = {}
    cutoff_3m = last_date - pd.Timedelta(days=95)
    for ind in INDICATORS:
        k = ind["key"]
        available = k in sub.columns
        val = float(sub[k].iloc[-1]) if available and pd.notna(sub[k].iloc[-1]) else None
        today_subs[k] = val if val is not None else np.nan

        trend = "flat"
        if available and len(sub[k].dropna()) >= 6:
            prev = sub[k].dropna().iloc[-6]
            if pd.notna(prev) and val is not None:
                diff = val - prev
                trend = "up" if diff > 2 else ("down" if diff < -2 else "flat")

        mini = []
        if available:
            s3 = sub[k][sub[k].index >= cutoff_3m]
            mini = _series_to_list(s3, key="v")

        indicators_out.append({
            "key": k, "name": ind["name"], "tickers": ind["tickers"],
            "subscore": round(val, 1) if val is not None else None,
            "trend": trend, "available": available,
            "meaning": ind["meaning"],
            "series": mini,
        })

    # ----- historique global -----
    history = _series_to_list(score, key="s")

    # ----- événements : minimum de score sur chaque fenêtre -----
    events_out = []
    for ev in EVENTS:
        win = score[(score.index >= pd.Timestamp(ev["start"])) &
                    (score.index <= pd.Timestamp(ev["end"]))]
        if not win.empty:
            dmin = win.idxmin()
            events_out.append({
                "id": ev["id"], "label": ev["label"],
                "date": dmin.strftime("%Y-%m-%d"),
                "score": round(float(win.loc[dmin]), 1),
            })

    verdict = make_verdict(today, today_subs)

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of_date": last_date.strftime("%Y-%m-%d"),
        "score": round(today, 1),
        "zone": zone_of(today),
        "verdict": verdict,
        "change_1d": round(change_1d, 1) if change_1d is not None else None,
        "change_1w": round(change_1w, 1) if change_1w is not None else None,
        "zones": {"off_max": ZONE_OFF_MAX, "neutral_max": ZONE_NEUTRAL_MAX},
        "missing_tickers": missing,
        "unavailable_indicators": unavailable,
        "indicators": indicators_out,
        "history": history,
        "events": events_out,
        "params": {"window_ret": WINDOW_RET, "window_z": WINDOW_Z, "z_clip": Z_CLIP},
    }


def write_payload(payload: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
    kb = os.path.getsize(DATA_PATH) / 1024
    print(f"\n✓ data/data.json écrit ({kb:.0f} Ko).")


# ---------------------------------------------------------------------------
# VALIDATION SUR DONNÉES RÉELLES (affichée après un run réel)
# ---------------------------------------------------------------------------

def print_validation(payload: dict) -> None:
    print("\n" + "=" * 60)
    print("SCORE DU JOUR")
    print("=" * 60)
    print(f"  Date      : {payload['as_of_date']}")
    print(f"  Score     : {payload['score']}/100  ->  {payload['zone']}")
    print(f"  Variation : 1j {payload['change_1d']:+}   1 sem {payload['change_1w']:+}")
    print(f"  Verdict   : {payload['verdict']}")

    print("\n" + "=" * 60)
    print("VALIDATION — le score chute-t-il pendant les 3 crises ?")
    print("=" * 60)
    for ev in payload["events"]:
        verdict = "✓ chute confirmée" if ev["score"] < ZONE_OFF_MAX else \
                  ("~ risk-off léger" if ev["score"] < 45 else "✗ pas de chute nette")
        print(f"  {ev['label']:<26} min {ev['score']:>5}/100  le {ev['date']}   {verdict}")


# ---------------------------------------------------------------------------
# AUTO-TEST DE LA LOGIQUE (SANS RÉSEAU)
# ---------------------------------------------------------------------------

def selftest() -> int:
    """Vérifie que la mécanique de score est correctement ORIENTÉE, en faisant
    passer les conditions caractéristiques de chaque crise dans le pipeline.
    (Valeurs représentatives, PAS les vraies données : cela teste la logique,
    pas l'histoire exacte.)"""

    def subscore_from_z(sign, z_raw):
        z = max(-Z_CLIP, min(Z_CLIP, sign * z_raw))
        return (z + Z_CLIP) / (2 * Z_CLIP) * 100.0

    # Pour chaque scénario : z-score représentatif du SIGNAL BRUT de chaque
    # indicateur (avant orientation), tel qu'observé historiquement.
    scenarios = {
        "Mars 2020 (Covid)": {
            "vix": +8.0,    # VIX ~82 : explosion de la volatilité
            "spy_tlt": -4.0,  # actions s'effondrent, obligations montent
            "hyg_lqd": -3.5,  # le high yield décroche
            "xly_xlp": -3.0,  # cycliques massacrées
            "iwm_spy": -2.5,  # small caps écrasées
            "gld_spy": +2.0,  # l'or surperforme (refuge)
            "dxy": +2.5,      # ruée sur le dollar (pénurie de liquidités)
            "usdjpy": -0.3,   # yen volatil, globalement neutre
        },
        "2022 (hausse des taux)": {
            "vix": +1.0,     # volatilité élevée mais pas extrême
            "spy_tlt": +0.4,  # PIÈGE : les obligations chutent + que les actions
            "hyg_lqd": +0.6,  # PIÈGE : HYG (duration courte) bat LQD
            "xly_xlp": -2.5,  # cycliques (tech, conso) effondrées
            "iwm_spy": -1.0,  # small caps à la traîne
            "gld_spy": +0.9,  # l'or résiste mieux que les actions
            "dxy": +2.5,      # envolée du dollar
            "usdjpy": +2.5,   # PIÈGE : yen massivement affaibli -> lu « risk-on »
        },
        "Août 2024 (carry trade yen)": {
            "vix": +3.0,     # pic de VIX (jusqu'à ~65 en séance)
            "spy_tlt": -2.0,  # actions baissent, obligations montent
            "hyg_lqd": -1.5,  # crédit nerveux
            "xly_xlp": -1.8,  # cycliques en repli
            "iwm_spy": -1.8,  # small caps décrochent
            "gld_spy": +0.2,  # or ~neutre
            "dxy": -1.5,      # dollar baisse (anticipations de baisse de taux)
            "usdjpy": -3.5,   # yen bondit : LE signal du débouclage
        },
    }
    sign = {ind["key"]: ind["sign"] for ind in INDICATORS}

    print("=" * 64)
    print("AUTO-TEST DE LA LOGIQUE (données simulées — teste l'orientation)")
    print("=" * 64)
    ok = True
    for name, zs in scenarios.items():
        subs = {k: subscore_from_z(sign[k], z) for k, z in zs.items()}
        score = sum(subs.values()) / len(subs)
        zone = zone_of(score)
        flag = "✓ risk-off" if score < 45 else "✗ ATTENDU risk-off"
        if score >= 45:
            ok = False
        print(f"\n  {name}")
        print(f"    Score simulé : {score:5.1f}/100  ({zone})   {flag}")
        detail = "  ".join(f"{k}:{v:4.0f}" for k, v in subs.items())
        print(f"    Sous-scores  : {detail}")

    print("\n" + "-" * 64)
    print("Lecture : le moteur place bien les 3 crises du côté risk-off.")
    print("Mars 2020 et août 2024 plongent ; 2022 est un risk-off plus MODÉRÉ,")
    print("car 2 indicateurs sur 8 (SPY/TLT et le yen) ne jouent pas leur rôle")
    print("de refuge cette année-là (krach piloté par les TAUX : les obligations")
    print("ET le yen chutent avec les actions). C'est une limite assumée et")
    print("explicable — un bon sujet d'entretien.")
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# POINT D'ENTRÉE
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Météo des Marchés — moteur de calcul.")
    parser.add_argument("--selftest", action="store_true",
                        help="teste la logique sans réseau (données de crise simulées)")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    print("Téléchargement des données (Yahoo Finance via yfinance)…")
    prices, missing = fetch_prices()
    if missing:
        print(f"\n⚠ Tickers indisponibles : {', '.join(missing)} "
              f"(le score sera calculé sur les indicateurs restants).")

    payload = build_payload(prices, missing)
    write_payload(payload)
    print_validation(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
