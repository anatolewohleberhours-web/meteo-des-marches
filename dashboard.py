#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Météo des Marchés — moteur du TABLEAU DE BORD.
==============================================

Ce script complète `compute.py` (qui calcule la jauge Risk-On / Risk-Off).
Il récupère un large ensemble d'indicateurs financiers et macro-économiques
PUBLICS ET GRATUITS, les range par catégorie, et écrit `data/dashboard.json`
que le site lit pour afficher la page « Tableau de bord ».

Trois sources, toutes gratuites et SANS clé d'API :
  • yfinance  (Yahoo Finance) — indices, volatilité, taux, matières premières,
    devises, crypto ;
  • FRED      (Réserve fédérale de St. Louis) — via l'export CSV public
    `fredgraph.csv` (aucune clé requise) : inflation, emploi, spreads de crédit,
    courbe des taux, liquidité, masse monétaire… ;
  • CoinGecko (API publique /global) — dominance du Bitcoin, capi crypto totale.

Chaque téléchargement est isolé dans un try/except : si une source échoue,
l'indicateur est simplement marqué « indisponible » et le reste s'affiche.

Usage :
  python dashboard.py                # récupère les vraies données -> data/dashboard.json
  python dashboard.py --placeholder  # génère un jeu de DÉMONSTRATION (sans réseau)

Projet Météo des Marchés — Anatole.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import sys

import numpy as np
import pandas as pd

HERE      = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(HERE, "data")
DATA_PATH = os.path.join(DATA_DIR, "dashboard.json")

SPARK_DAYS = 45   # longueur de la mini-courbe stockée par indicateur

# Ordre d'affichage des catégories sur le site.
CATEGORIES = [
    ("essentiel",   "L'essentiel",            "Les 15 indicateurs à regarder en premier avant d'investir."),
    ("indices",     "Indices actions",        "Les grands marchés actions mondiaux."),
    ("largeur",     "Largeur & style",        "La hausse est-elle large ou portée par quelques géantes ?"),
    ("secteurs",    "Secteurs US",            "Rotation sectorielle : où va l'argent dans le S&P 500."),
    ("volatilite",  "Volatilité & sentiment", "Le niveau de peur ou de complaisance du marché."),
    ("taux",        "Taux & obligations",     "Le prix de l'argent et le stress sur le crédit."),
    ("macro",       "Macroéconomie",          "Inflation, emploi, liquidité : le décor de fond."),
    ("devises",     "Devises",                "Le dollar et les grandes paires."),
    ("matieres",    "Matières premières",     "Énergie, métaux et thermomètres de l'économie réelle."),
    ("crypto",      "Crypto",                 "Bitcoin, Ethereum et l'état du marché crypto."),
]

# ---------------------------------------------------------------------------
# CATALOGUE DES INDICATEURS
# ---------------------------------------------------------------------------
#  Champs :
#    id       identifiant unique
#    name     nom affiché
#    cat      catégorie (clé de CATEGORIES)
#    src      "yf" (yfinance) | "fred" | "fred_calc" | "cg" (CoinGecko)
#    code     ticker yfinance, id FRED, ou clé de calcul
#    fmt      format d'affichage : "pts" | "price" | "pct" | "num" | "bn" | "tn"
#    invert   True  -> une HAUSSE est un signal risk-off (coloré en rouge)
#    featured True  -> fait aussi partie de « L'essentiel »
#    transform "yoy" pour une série FRED affichée en variation sur 1 an
#    meaning  phrase pédagogique : pourquoi c'est important / comment le lire
#    ref      valeur de référence (uniquement pour le mode --placeholder)
CATALOG = [
    # ---------------- Indices actions ----------------
    dict(id="spx",   name="S&P 500",            cat="indices", src="yf", code="^GSPC",  fmt="pts", featured=True,
         meaning="L'indice de référence des 500 plus grandes entreprises américaines. Le baromètre mondial du risque actions.", ref=6480),
    dict(id="ndx",   name="Nasdaq Composite",   cat="indices", src="yf", code="^IXIC",  fmt="pts",
         meaning="Dominé par la tech. Plus volatil que le S&P 500 et très sensible aux taux d'intérêt.", ref=21800),
    dict(id="dji",   name="Dow Jones",          cat="indices", src="yf", code="^DJI",   fmt="pts",
         meaning="30 grandes valeurs industrielles américaines. Plus « old economy » que le Nasdaq.", ref=47200),
    dict(id="rut",   name="Russell 2000",       cat="indices", src="yf", code="^RUT",   fmt="pts",
         meaning="Les petites capitalisations américaines : un bon thermomètre de l'économie réelle et de l'appétit pour le risque.", ref=2410),
    dict(id="cac",   name="CAC 40",             cat="indices", src="yf", code="^FCHI",  fmt="pts",
         meaning="La place de Paris. Ton marché domestique, très exposé au luxe et aux banques.", ref=8120),
    dict(id="sx5e",  name="Euro Stoxx 50",      cat="indices", src="yf", code="^STOXX50E", fmt="pts",
         meaning="Les 50 plus grandes valeurs de la zone euro. La référence actions européenne.", ref=5460),
    dict(id="dax",   name="DAX (Allemagne)",    cat="indices", src="yf", code="^GDAXI", fmt="pts",
         meaning="Le marché allemand, moteur industriel de l'Europe.", ref=24200),
    dict(id="nky",   name="Nikkei 225",         cat="indices", src="yf", code="^N225",  fmt="pts",
         meaning="La Bourse de Tokyo. Central pour comprendre le yen et le carry trade.", ref=51000),

    # ---------------- Largeur & style ----------------
    dict(id="rsp_spy", name="S&P équipondéré / classique", cat="largeur", src="yf", code="RSP/SPY", fmt="num", featured=True,
         meaning="Compare le S&P 500 équipondéré au S&P classique. S'il baisse, la hausse ne tient qu'à quelques méga-caps tech : marché plus fragile.", ref=0.345),
    dict(id="iwm_spy", name="Small caps / Large caps",     cat="largeur", src="yf", code="IWM/SPY", fmt="num",
         meaning="Les petites valeurs face aux grandes. En hausse quand l'appétit pour le risque est fort.", ref=0.345),
    dict(id="qqq_spy", name="Tech / Marché (QQQ/SPY)",     cat="largeur", src="yf", code="QQQ/SPY", fmt="num",
         meaning="La domination de la tech. En hausse = leadership des valeurs de croissance.", ref=0.88),

    # ---------------- Secteurs US (SPDR) ----------------
    dict(id="xlk", name="Technologie (XLK)",          cat="secteurs", src="yf", code="XLK", fmt="price",
         meaning="Le secteur techno. Moteur des marchés, sensible aux taux.", ref=268),
    dict(id="xlf", name="Finance (XLF)",              cat="secteurs", src="yf", code="XLF", fmt="price",
         meaning="Banques et assurances. Profite de taux élevés et d'une économie solide.", ref=54),
    dict(id="xle", name="Énergie (XLE)",              cat="secteurs", src="yf", code="XLE", fmt="price",
         meaning="Pétrole et gaz. Lié au prix du brut et à l'inflation.", ref=92),
    dict(id="xlv", name="Santé (XLV)",                cat="secteurs", src="yf", code="XLV", fmt="price",
         meaning="Secteur défensif : on s'y réfugie quand l'économie ralentit.", ref=138),
    dict(id="xly", name="Conso discrétionnaire (XLY)", cat="secteurs", src="yf", code="XLY", fmt="price",
         meaning="Loisirs, luxe, automobile. Cyclique : mène quand on parie sur la croissance.", ref=228),
    dict(id="xlp", name="Conso de base (XLP)",        cat="secteurs", src="yf", code="XLP", fmt="price",
         meaning="Alimentation, hygiène. Défensif par excellence.", ref=81),
    dict(id="xli", name="Industrie (XLI)",            cat="secteurs", src="yf", code="XLI", fmt="price",
         meaning="Machines, transport, défense. Sensible au cycle économique.", ref=152),
    dict(id="xlu", name="Services publics (XLU)",     cat="secteurs", src="yf", code="XLU", fmt="price",
         meaning="Électricité, eau. Très défensif, se comporte comme une obligation.", ref=84),

    # ---------------- Volatilité & sentiment ----------------
    dict(id="vix",   name="VIX",            cat="volatilite", src="yf", code="^VIX",  fmt="num", invert=True, featured=True,
         meaning="L'« indice de la peur ». Sous 15 = marché serein ; au-dessus de 30 = panique, souvent une opportunité d'achat historiquement.", ref=16.5),
    dict(id="vix3m", name="VIX 3 mois",     cat="volatilite", src="yf", code="^VIX3M", fmt="num", invert=True,
         meaning="La volatilité attendue à 3 mois. Quand le VIX court terme la dépasse, c'est un signal de stress aigu.", ref=18.5),
    dict(id="vvix",  name="VVIX",           cat="volatilite", src="yf", code="^VVIX", fmt="num", invert=True,
         meaning="La volatilité du VIX lui-même : la nervosité sur la nervosité.", ref=95),
    dict(id="vxn",   name="VXN (Nasdaq)",   cat="volatilite", src="yf", code="^VXN",  fmt="num", invert=True,
         meaning="L'équivalent du VIX pour le Nasdaq : la peur sur la tech.", ref=20),
    dict(id="skew",  name="SKEW",           cat="volatilite", src="yf", code="^SKEW", fmt="num", invert=True,
         meaning="Le coût de l'assurance contre un krach. Élevé = les pros se couvrent contre un choc.", ref=145),

    # ---------------- Taux & obligations ----------------
    dict(id="us10y", name="Taux US 10 ans",     cat="taux", src="yf", code="^TNX", fmt="pct", featured=True,
         meaning="LE taux de référence mondial. Quand il monte vite, la tech et la crypto souffrent.", ref=4.15),
    dict(id="us2y",  name="Taux US 2 ans",      cat="taux", src="yf", code="^FVX", fmt="pct",
         meaning="Taux court américain : reflète surtout les anticipations sur la Fed. (Proxy 5 ans sur Yahoo.)", ref=3.85),
    dict(id="us30y", name="Taux US 30 ans",     cat="taux", src="yf", code="^TYX", fmt="pct",
         meaning="Taux long : reflète les anticipations d'inflation et de croissance à très long terme.", ref=4.75),
    dict(id="t10y2y", name="Courbe 10 ans − 2 ans", cat="taux", src="fred", code="T10Y2Y", fmt="pct", featured=True,
         meaning="Le signal de récession le plus connu : négatif (courbe inversée), une récession a souvent suivi dans 12 à 24 mois.", ref=0.55),
    dict(id="t10y3m", name="Courbe 10 ans − 3 mois", cat="taux", src="fred", code="T10Y3M", fmt="pct",
         meaning="La version préférée de la Fed de New York pour anticiper une récession.", ref=0.70),
    dict(id="hy",    name="Spread High Yield",   cat="taux", src="fred", code="BAMLH0A0HYM2", fmt="pct", invert=True, featured=True,
         meaning="La prime exigée sur la dette d'entreprise risquée. Quand elle s'écarte brutalement, le marché craint les faillites : alerte précoce.", ref=3.10),
    dict(id="ig",    name="Spread Investment Grade", cat="taux", src="fred", code="BAMLC0A0CM", fmt="pct", invert=True,
         meaning="La prime sur la dette d'entreprise de qualité. Plus calme que le High Yield, mais révélateur du stress.", ref=0.85),
    dict(id="be10",  name="Inflation anticipée 10 ans", cat="taux", src="fred", code="T10YIE", fmt="pct",
         meaning="L'inflation que le marché anticipe en moyenne sur 10 ans (point mort / breakeven).", ref=2.35),
    dict(id="real10", name="Taux réel 10 ans",   cat="taux", src="fred", code="DFII10", fmt="pct",
         meaning="Le taux 10 ans une fois l'inflation retirée. Un taux réel élevé pèse sur l'or et les actifs risqués.", ref=1.80),
    dict(id="sofr",  name="SOFR",                cat="taux", src="fred", code="SOFR", fmt="pct",
         meaning="Le taux interbancaire de référence aux États-Unis, qui a remplacé le LIBOR.", ref=4.35),

    # ---------------- Macroéconomie ----------------
    dict(id="fedfunds", name="Taux directeur Fed", cat="macro", src="fred", code="DFF", fmt="pct", featured=True,
         meaning="Le prix de l'argent fixé par la Fed. Il influence absolument tout, des actions à l'immobilier.", ref=4.33),
    dict(id="cpi",   name="Inflation US (CPI, a/a)", cat="macro", src="fred", code="CPIAUCSL", fmt="pct", transform="yoy", invert=True, featured=True,
         meaning="La hausse des prix sur un an. C'est elle qui décide de ce que fera la Fed.", ref=2.9),
    dict(id="pce",   name="Inflation cœur (PCE, a/a)", cat="macro", src="fred", code="PCEPILFE", fmt="pct", transform="yoy", invert=True,
         meaning="L'inflation sous-jacente, la mesure préférée de la Fed pour piloter ses taux.", ref=2.8),
    dict(id="unrate", name="Chômage US",         cat="macro", src="fred", code="UNRATE", fmt="pct", invert=True, featured=True,
         meaning="Le taux de chômage américain. Sa dégradation est le signal de récession le plus fiable.", ref=4.3),
    dict(id="sahm",  name="Règle de Sahm",       cat="macro", src="fred", code="SAHMREALTIME", fmt="pct", invert=True,
         meaning="Un signal de récession : quand il dépasse 0,50, une récession a historiquement déjà commencé.", ref=0.15),
    dict(id="m2",    name="Masse monétaire M2",  cat="macro", src="fred", code="M2SL", fmt="tn", scale=0.001, featured=True,
         meaning="La quantité de dollars en circulation. Quand elle augmente, les actifs risqués montent (très corrélé au Bitcoin).", ref=21.8),
    dict(id="walcl", name="Bilan de la Fed",     cat="macro", src="fred", code="WALCL", fmt="tn", scale=1e-6,
         meaning="La taille du bilan de la Fed. Il gonfle quand elle injecte des liquidités (QE), se réduit en QT.", ref=6.6),
    dict(id="netliq", name="Liquidité nette Fed", cat="macro", src="fred_calc", code="NETLIQ", fmt="tn", featured=True,
         meaning="Bilan de la Fed − compte du Trésor − reverse repo. La vraie liquidité disponible pour les marchés, très suivie des traders.", ref=5.9),

    # ---------------- Devises ----------------
    dict(id="dxy",   name="Dollar (DXY)",        cat="devises", src="yf", code="DX-Y.NYB", fmt="num", invert=True, featured=True,
         meaning="L'indice du dollar face aux grandes devises. Un dollar fort pèse sur les actions mondiales, les matières premières et la crypto.", ref=99.5),
    dict(id="eurusd", name="EUR / USD",          cat="devises", src="yf", code="EURUSD=X", fmt="num",
         meaning="L'euro face au dollar. La paire de change la plus échangée au monde.", ref=1.085),
    dict(id="usdjpy", name="USD / JPY",          cat="devises", src="yf", code="JPY=X", fmt="num",
         meaning="Le dollar face au yen. Quand le yen se renforce (paire en baisse), gare au débouclage du carry trade.", ref=152),
    dict(id="gbpusd", name="GBP / USD",          cat="devises", src="yf", code="GBPUSD=X", fmt="num",
         meaning="La livre face au dollar.", ref=1.27),

    # ---------------- Matières premières ----------------
    dict(id="wti",   name="Pétrole WTI",         cat="matieres", src="yf", code="CL=F", fmt="price",
         meaning="Le brut américain. Clé pour l'inflation et le secteur de l'énergie.", ref=66),
    dict(id="brent", name="Pétrole Brent",       cat="matieres", src="yf", code="BZ=F", fmt="price",
         meaning="Le brut de référence mondial (mer du Nord).", ref=70),
    dict(id="gold",  name="Or",                  cat="matieres", src="yf", code="GC=F", fmt="price",
         meaning="La valeur refuge par excellence. Monte en période de peur et quand les taux réels baissent.", ref=4050),
    dict(id="silver", name="Argent",             cat="matieres", src="yf", code="SI=F", fmt="price",
         meaning="À la fois métal précieux et industriel, plus volatil que l'or.", ref=49),
    dict(id="copper", name="Cuivre (Dr Copper)", cat="matieres", src="yf", code="HG=F", fmt="price",
         meaning="Surnommé « Dr Copper » : un excellent thermomètre de la santé de l'économie mondiale.", ref=5.1),
    dict(id="natgas", name="Gaz naturel",        cat="matieres", src="yf", code="NG=F", fmt="price",
         meaning="Très volatil, sensible à la météo et à la géopolitique.", ref=4.2),
    dict(id="copper_gold", name="Ratio Cuivre / Or", cat="matieres", src="yf", code="HG=F/GC=F", fmt="num",
         meaning="Un très bon indicateur avancé des taux longs et de la croissance : en hausse = optimisme économique.", ref=0.00126),

    # ---------------- Crypto ----------------
    dict(id="btc",   name="Bitcoin",             cat="crypto", src="yf", code="BTC-USD", fmt="price", featured=True,
         meaning="La plus grande cryptomonnaie. Très liée à la liquidité mondiale et à l'appétit pour le risque.", ref=92000),
    dict(id="eth",   name="Ethereum",            cat="crypto", src="yf", code="ETH-USD", fmt="price", featured=True,
         meaning="La deuxième crypto, support de la finance décentralisée (DeFi).", ref=3100),
    dict(id="eth_btc", name="Ratio ETH / BTC",   cat="crypto", src="yf", code="ETH-USD/BTC-USD", fmt="num",
         meaning="En hausse quand les investisseurs prennent plus de risque que le simple Bitcoin (saison des altcoins).", ref=0.0337),
    dict(id="btc_dom", name="Dominance Bitcoin",  cat="crypto", src="cg", code="btc_dominance", fmt="pct",
         meaning="La part du Bitcoin dans toute la crypto. En baisse = les altcoins prennent le relais.", ref=58),
    dict(id="crypto_mcap", name="Capi crypto totale", cat="crypto", src="cg", code="total_mcap", fmt="tn",
         meaning="La taille de tout le marché crypto. Mesure l'ampleur du cycle en cours.", ref=3.1),
]


# ---------------------------------------------------------------------------
# OUTILS DE TÉLÉCHARGEMENT
# ---------------------------------------------------------------------------

def _yf_close(ticker: str) -> pd.Series:
    """Série de clôtures ajustées (≈ 6 mois) pour un ticker yfinance."""
    import yfinance as yf
    hist = yf.Ticker(ticker).history(period="6mo", auto_adjust=True)
    if hist is None or hist.empty or "Close" not in hist.columns:
        raise ValueError(f"aucune donnée yfinance pour {ticker}")
    s = hist["Close"].copy()
    s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
    return s[~s.index.duplicated(keep="last")].sort_index().dropna()


def _fred_series(series_id: str, days: int = 500) -> pd.Series:
    """Série FRED via l'export CSV public fredgraph.csv (aucune clé requise)."""
    start = (dt.date.today() - dt.timedelta(days=days)).strftime("%Y-%m-%d")
    url = (f"https://fred.stlouisfed.org/graph/fredgraph.csv"
           f"?id={series_id}&cosd={start}")
    df = pd.read_csv(url)
    # Le CSV a 2 colonnes : la date (observation_date / DATE) et la valeur (= series_id).
    date_col = df.columns[0]
    val_col = df.columns[1]
    df[date_col] = pd.to_datetime(df[date_col])
    df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
    s = df.set_index(date_col)[val_col].dropna()
    s.index = s.index.normalize()
    if s.empty:
        raise ValueError(f"série FRED vide : {series_id}")
    return s.sort_index()


def _coingecko_global() -> dict:
    """Dominance BTC et capitalisation totale via l'API publique CoinGecko."""
    import urllib.request
    req = urllib.request.Request("https://api.coingecko.com/api/v3/global",
                                 headers={"User-Agent": "meteo-des-marches"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    d = payload["data"]
    return {
        "btc_dominance": float(d["market_cap_percentage"]["btc"]),
        "total_mcap": float(d["total_market_cap"]["usd"]),
    }


# ---------------------------------------------------------------------------
# CONSTRUCTION D'UN INDICATEUR À PARTIR D'UNE SÉRIE
# ---------------------------------------------------------------------------

def _spark(series: pd.Series, n: int = SPARK_DAYS) -> list[float]:
    """Mini-courbe : n derniers points, normalisée en float arrondi."""
    tail = series.dropna().tail(n)
    return [round(float(v), 4) for v in tail.values]


def _pct_change(series: pd.Series) -> float | None:
    s = series.dropna()
    if len(s) < 2 or s.iloc[-2] == 0:
        return None
    return float((s.iloc[-1] / s.iloc[-2] - 1.0) * 100.0)


def _abs_change(series: pd.Series) -> float | None:
    s = series.dropna()
    if len(s) < 2:
        return None
    return float(s.iloc[-1] - s.iloc[-2])


def build_indicator(meta: dict, series: pd.Series) -> dict:
    """Transforme une série temporelle en bloc JSON prêt pour le site.

    - value       : dernière valeur
    - change      : variation (% pour les marchés, points pour taux/spreads/macro)
    - change_kind : "pct" ou "pt" (unité de la variation)
    - spark       : mini-courbe
    """
    s = series.dropna()
    value = float(s.iloc[-1])
    # Les marchés (indices, prix, ratios, devises) -> variation en %.
    # Les taux, spreads et séries macro (déjà en %) -> variation en points.
    if meta["fmt"] in ("pct",) or meta.get("transform") == "yoy":
        change = _abs_change(s)
        change_kind = "pt"
    else:
        change = _pct_change(s)
        change_kind = "pct"

    return {
        "id": meta["id"], "name": meta["name"], "cat": meta["cat"],
        "fmt": meta["fmt"], "invert": bool(meta.get("invert", False)),
        "featured": bool(meta.get("featured", False)),
        "meaning": meta["meaning"], "source": _source_label(meta["src"]),
        "value": round(value, 4),
        "change": round(change, 3) if change is not None else None,
        "change_kind": change_kind,
        "asof": s.index[-1].strftime("%Y-%m-%d"),
        "spark": _spark(s),
        "available": True,
    }


def _source_label(src: str) -> str:
    return {
        "yf": "Yahoo Finance", "fred": "FRED (Fed de St. Louis)",
        "fred_calc": "FRED (calcul)", "cg": "CoinGecko",
    }.get(src, src)


def _unavailable(meta: dict) -> dict:
    return {
        "id": meta["id"], "name": meta["name"], "cat": meta["cat"],
        "fmt": meta["fmt"], "invert": bool(meta.get("invert", False)),
        "featured": bool(meta.get("featured", False)),
        "meaning": meta["meaning"], "source": _source_label(meta["src"]),
        "value": None, "change": None, "change_kind": "pct",
        "asof": None, "spark": [], "available": False,
    }


# ---------------------------------------------------------------------------
# RÉCUPÉRATION RÉELLE
# ---------------------------------------------------------------------------

def _resolve_yf(code: str, cache: dict) -> pd.Series:
    """Gère les tickers simples ET les ratios 'A/B' (téléchargés une seule fois)."""
    if "/" in code:
        a, b = code.split("/")
        sa, sb = _resolve_yf(a, cache), _resolve_yf(b, cache)
        joined = pd.concat([sa, sb], axis=1).ffill().dropna()
        return (joined.iloc[:, 0] / joined.iloc[:, 1])
    if code not in cache:
        cache[code] = _yf_close(code)
    return cache[code]


def _transform_yoy(series: pd.Series) -> pd.Series:
    """Variation sur un an (%) d'une série mensuelle FRED."""
    monthly = series.resample("MS").last().dropna()
    return (monthly.pct_change(12) * 100.0).dropna()


def fetch_all() -> tuple[list[dict], list[str]]:
    out, missing = [], []
    yf_cache: dict[str, pd.Series] = {}
    cg_cache: dict | None = None

    for meta in CATALOG:
        try:
            src = meta["src"]
            if src == "yf":
                series = _resolve_yf(meta["code"], yf_cache)

            elif src == "fred":
                series = _fred_series(meta["code"])
                if meta.get("transform") == "yoy":
                    series = _transform_yoy(series)
                elif meta.get("scale"):
                    series = series * meta["scale"]

            elif src == "fred_calc" and meta["code"] == "NETLIQ":
                walcl = _fred_series("WALCL")                    # bilan Fed (M$)
                tga   = _fred_series("WTREGEN")                  # compte du Trésor (M$)
                rrp   = _fred_series("RRPONTSYD")                # reverse repo (Md$)
                df = pd.concat([walcl, tga, rrp * 1000.0], axis=1).ffill().dropna()
                series = (df.iloc[:, 0] - df.iloc[:, 1] - df.iloc[:, 2]) / 1_000_000.0  # -> trillions $

            elif src == "cg":
                nonlocal_cg = cg_cache if cg_cache is not None else _coingecko_global()
                cg_cache = nonlocal_cg
                val = nonlocal_cg["btc_dominance"] if meta["code"] == "btc_dominance" \
                    else nonlocal_cg["total_mcap"] / 1e12  # -> trillions $
                # Pas d'historique via /global : série à un seul point.
                series = pd.Series([val], index=[pd.Timestamp(dt.date.today())])

            else:
                raise ValueError(f"source inconnue : {src}")

            if src == "yf" and meta["fmt"] == "tn":
                series = series / 1e12

            out.append(build_indicator(meta, series))
            print(f"  [ok]    {meta['id']:<14} {meta['name']}")

        except Exception as exc:  # noqa: BLE001
            missing.append(meta["id"])
            out.append(_unavailable(meta))
            print(f"  [ÉCHEC] {meta['id']:<14} -> {exc}")

    return out, missing


# ---------------------------------------------------------------------------
# MODE DÉMONSTRATION (sans réseau)
# ---------------------------------------------------------------------------

def fake_all(seed: int = 7) -> list[dict]:
    """Génère des valeurs de démonstration plausibles autour des 'ref' du catalogue."""
    rng = random.Random(seed)
    today = dt.date.today()
    out = []
    for meta in CATALOG:
        ref = meta.get("ref", 100.0)
        # mini-courbe : marche aléatoire douce autour de la référence
        spark, v = [], ref
        for _ in range(SPARK_DAYS):
            v *= (1 + rng.uniform(-0.012, 0.012))
            spark.append(round(v, 4))
        value = spark[-1]
        if meta["fmt"] in ("pct",) or meta.get("transform") == "yoy":
            change = round(rng.uniform(-0.15, 0.15), 3); kind = "pt"
        else:
            change = round(rng.uniform(-1.8, 1.8), 3); kind = "pct"
        out.append({
            "id": meta["id"], "name": meta["name"], "cat": meta["cat"],
            "fmt": meta["fmt"], "invert": bool(meta.get("invert", False)),
            "featured": bool(meta.get("featured", False)),
            "meaning": meta["meaning"], "source": _source_label(meta["src"]),
            "value": round(value, 4), "change": change, "change_kind": kind,
            "asof": today.strftime("%Y-%m-%d"), "spark": spark, "available": True,
        })
    return out


# ---------------------------------------------------------------------------
# ÉCRITURE DU JSON
# ---------------------------------------------------------------------------

def write_payload(indicators: list[dict], missing: list[str], placeholder: bool) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    dates = [i["asof"] for i in indicators if i.get("asof")]
    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of_date": max(dates) if dates else None,
        "placeholder": placeholder,
        "missing": missing,
        "categories": [{"key": k, "name": n, "desc": d} for k, n, d in CATEGORIES],
        "indicators": indicators,
    }
    with open(DATA_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
    kb = os.path.getsize(DATA_PATH) / 1024
    kind = "DÉMO" if placeholder else "réel"
    print(f"\n✓ data/dashboard.json écrit ({kb:.0f} Ko, {len(indicators)} indicateurs, mode {kind}).")


def main() -> int:
    parser = argparse.ArgumentParser(description="Météo des Marchés — tableau de bord.")
    parser.add_argument("--placeholder", action="store_true",
                        help="génère un jeu de démonstration sans réseau")
    args = parser.parse_args()

    if args.placeholder:
        print("Génération de données de DÉMONSTRATION (sans réseau)…")
        write_payload(fake_all(), [], placeholder=True)
        return 0

    print("Téléchargement des indicateurs (Yahoo Finance, FRED, CoinGecko)…")
    indicators, missing = fetch_all()
    if missing:
        print(f"\n⚠ Indicateurs indisponibles : {', '.join(missing)}")
    write_payload(indicators, missing, placeholder=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
