# 🌦️ Météo des Marchés

**Un baromètre quotidien Risk-On / Risk-Off *et* un tableau de bord complet des marchés financiers.**
Un score unique de **0 à 100** qui résume, chaque jour, si les investisseurs sont en mode *peur* (risk-off) ou *appétit pour le risque* (risk-on), calculé à partir de **8 indicateurs cross-asset** — complété par un **tableau de bord** réunissant ~60 indicateurs publics (actions, taux, macro, volatilité, matières premières, crypto) en un seul coup d'œil.

Inspiré du *Fear & Greed Index* de CNN, mais **cross-asset, transparent et pédagogique** : toute la méthode de calcul est publique et expliquée.

🔗 **Site en ligne :** <!-- Remplace ce lien par ton URL Netlify, ex : https://meteo-des-marches.netlify.app -->
`https://VOTRE-SITE.netlify.app`

---

## 💡 L'idée

Les marchés alternent entre deux régimes : la *recherche de sécurité* (on vend les actifs risqués, on achète le refuge) et l'*appétit pour le risque* (on achète les actifs qui paient quand tout va bien). Plutôt que de regarder dix graphiques séparés, **Météo des Marchés condense ce climat en un seul chiffre**, mis à jour automatiquement chaque soir.

## 🧮 Comment ça marche

Pour chacun des 8 indicateurs :

1. on calcule un **signal d'appétit pour le risque** (ex. : les actions battent-elles les obligations sur 20 jours de bourse ?) ;
2. on le standardise en **z-score** sur une fenêtre glissante d'un an : `z = (signal − moyenne 1 an) / écart-type 1 an` ;
3. on l'**oriente** (un VIX élevé = peur, donc on l'inverse) et on le **borne à ±2 écarts-types** ;
4. on le ramène sur une échelle **0–100**.

Le **score global** est la moyenne des sous-scores disponibles.

| Zone | Score | Signification |
|------|-------|---------------|
| 🔴 Risk-off | 0 – 35 | Prudence, fuite vers la sécurité |
| 🟡 Neutre | 35 – 65 | Climat mitigé |
| 🟢 Risk-on | 65 – 100 | Appétit pour le risque |

## 📊 Les 8 indicateurs

| # | Indicateur | Tickers | Logique |
|---|------------|---------|---------|
| 1 | Volatilité | `^VIX` | VIX élevé → peur *(inversé)* |
| 2 | Actions vs Obligations | `SPY` / `TLT` | Actions qui surperforment → risk-on |
| 3 | Crédit risqué vs sûr | `HYG` / `LQD` | High yield qui tient → risk-on |
| 4 | Cycliques vs Défensives | `XLY` / `XLP` | Cycliques qui mènent → risk-on |
| 5 | Small vs Large caps | `IWM` / `SPY` | Petites valeurs qui surperforment → risk-on |
| 6 | Or vs Actions | `GLD` / `SPY` | Or qui surperforme → peur *(inversé)* |
| 7 | Dollar | `DX-Y.NYB` | Dollar refuge qui grimpe → peur *(inversé)* |
| 8 | Yen | `JPY=X` | Yen qui se renforce → débouclage du risque |

## 📋 Le tableau de bord des marchés

En plus du score, le site affiche un **tableau de bord** de ~60 indicateurs publics, rangés par catégorie et cherchables : **L'essentiel** (les 15 à regarder en premier), **Indices actions**, **Largeur & style**, **Secteurs US**, **Volatilité & sentiment**, **Taux & obligations**, **Macroéconomie**, **Devises**, **Matières premières** et **Crypto**.

Chaque carreau montre la **valeur du jour**, sa **variation** (colorée selon qu'elle est favorable ou non au risque), une **mini-courbe** et une **phrase d'explication** (pourquoi c'est important, comment le lire). Trois sources, toutes gratuites et **sans clé d'API** :

| Source | Ce qu'elle fournit |
|--------|--------------------|
| **Yahoo Finance** (`yfinance`) | indices, volatilité, taux, matières premières, devises, crypto |
| **FRED** (Fed de St. Louis, export CSV public) | inflation, emploi, spreads de crédit, courbe des taux, liquidité nette, M2, bilan de la Fed |
| **CoinGecko** (API publique `/global`) | dominance du Bitcoin, capitalisation crypto totale |

## ⚙️ Architecture — zéro serveur, zéro coût, zéro clé API

```
compute.py    ──►  data/data.json
dashboard.py  ──►  data/dashboard.json
   ▲                      │
   │                      └──►  site statique (HTML/CSS/JS)  ──►  Netlify
   └── GitHub Actions (chaque soir, du lundi au vendredi)
```

- **`compute.py`** calcule le score Risk-On / Risk-Off → `data/data.json`.
- **`dashboard.py`** récupère les ~60 indicateurs du tableau de bord → `data/dashboard.json`.
- **GitHub Actions** exécute les deux scripts automatiquement chaque soir et commit les JSON mis à jour. Aucun secret à configurer : les trois sources sont publiques.
- Le **site statique** (sans framework, Chart.js via CDN) lit simplement ces JSON.
- **Robuste aux pannes** : si un indicateur est indisponible, il est marqué comme tel et le reste s'affiche normalement.

## 📁 Structure du projet

```
meteo-des-marches/
├── compute.py                 # moteur du score Risk-On / Risk-Off (Python)
├── dashboard.py               # moteur du tableau de bord (~60 indicateurs)
├── requirements.txt           # dépendances Python
├── data/
│   ├── data.json              # score, historique, sous-scores
│   └── dashboard.json         # indicateurs du tableau de bord
├── .github/workflows/
│   └── update.yml             # automatisation quotidienne (GitHub Actions)
├── index.html                 # page du site
├── styles.css                 # mise en forme
├── app.js                     # logique d'affichage (jauge, cartes, graphe)
├── README.md                  # ce fichier
├── GUIDE-DEPLOIEMENT.md       # guide pas à pas pour mettre en ligne
└── FICHE-REVISION.md          # aide-mémoire pour tout expliquer en entretien
```

## 🖥️ Lancer le calcul en local (optionnel)

```bash
pip install -r requirements.txt
python compute.py                  # calcule le score -> data/data.json
python compute.py --selftest       # teste la logique sans réseau (scénarios de crise)
python dashboard.py                # récupère le tableau de bord -> data/dashboard.json
python dashboard.py --placeholder  # génère un jeu de démonstration (sans réseau)
```

Pour prévisualiser le site en local, lance un petit serveur (sinon le navigateur bloque la lecture du JSON) :

```bash
python -m http.server 8000     # puis ouvre http://localhost:8000
```

## 🚀 Mise en ligne

Tout est expliqué pas à pas, pour débutant, dans **[GUIDE-DEPLOIEMENT.md](GUIDE-DEPLOIEMENT.md)** : créer le dépôt GitHub, activer GitHub Actions, connecter Netlify, vérifier la mise à jour quotidienne.

## ⚠️ Limites

- **Ce n'est pas un conseil en investissement** — c'est un outil pédagogique qui décrit le climat de marché.
- **Source non officielle** : données Yahoo Finance via `yfinance`, sans garantie.
- **Fenêtre de 20 jours arbitraire** : capte le momentum récent ; un autre choix donnerait un score légèrement différent.
- **Krach « piloté par les taux »** : en 2022, obligations et yen ont chuté *avec* les actions au lieu de servir de refuge — le baromètre reste alors seulement modérément risk-off (limite assumée et documentée).

## 👤 Auteur

**Anatole** — étudiant entrepreneur passionné par les marchés financiers.
[LinkedIn](https://www.linkedin.com/in/anatole-hours-wohleber) · [Mon site de briefings de marché](https://anatole-point-de-marche.netlify.app)
