# 🎓 Fiche de révision — tout expliquer en entretien

Cette fiche te prépare à défendre le projet **Météo des Marchés** à l'oral. Elle explique chaque brique simplement, avec l'intuition derrière. Objectif : que tu puisses répondre avec aisance, même à un recruteur en salle de marché.

---

## 1. Le pitch en 30 secondes

> « Météo des Marchés est un baromètre quotidien qui résume l'appétit pour le risque des investisseurs en un score de 0 à 100. Je combine 8 indicateurs *cross-asset* — actions, obligations, crédit, or, dollar, yen, volatilité — chacun standardisé en z-score sur un an, puis ramené sur une échelle commune. C'est l'esprit du Fear & Greed Index de CNN, mais cross-asset et entièrement transparent : la méthode est publique, et le site se met à jour tout seul chaque soir via GitHub Actions. »

## 2. Les concepts clés

**Risk-on / Risk-off.** Deux régimes de marché. En *risk-on*, les investisseurs recherchent le rendement : ils achètent actions, small caps, crédit risqué. En *risk-off*, ils cherchent la sécurité : obligations d'État, or, dollar, yen, cash. Mon score mesure où l'on se situe sur cet axe.

**Cross-asset.** Je ne regarde pas une seule classe d'actifs mais plusieurs (actions, taux, crédit, matières premières, devises). L'avantage : un signal confirmé par plusieurs marchés est plus fiable qu'un seul indicateur.

**Momentum sur 20 jours.** Pour les comparaisons entre actifs, je calcule le rendement sur 20 jours de bourse (~1 mois). On capte ainsi la *tendance récente*, pas le bruit d'une seule séance.

**Z-score (le cœur de la méthode).** Un z-score répond à : « cette valeur est-elle haute ou basse *par rapport à son habitude* ? »
```
z = (valeur − moyenne sur 1 an) / écart-type sur 1 an
```
- z = 0 → valeur dans la moyenne.
- z = +2 → très au-dessus de la normale (2 écarts-types).
- z = −2 → très en dessous.

Pourquoi c'est malin : ça rend des indicateurs **très différents comparables entre eux** (le VIX, un écart de rendement, une variation de change… tous ramenés à une même unité « nombre d'écarts-types »).

**Bornage à ±2 puis échelle 0–100.** Je coupe les valeurs extrêmes à ±2 (pour qu'un seul indicateur affolé ne domine pas tout), puis je convertis : z = −2 → **0**, z = 0 → **50**, z = +2 → **100**. Le score global est la **moyenne** des 8 sous-scores.

**Les zones.** 0–35 = risk-off, 35–65 = neutre, 65–100 = risk-on.

## 3. Les 8 indicateurs, un par un

| Indicateur | Ce qu'il compare | Logique risk-on / risk-off |
|------------|------------------|----------------------------|
| **VIX** (`^VIX`) | Le niveau de la volatilité implicite du S&P 500 | La « jauge de la peur ». VIX haut = les investisseurs paient cher pour se protéger = **risk-off**. *Indicateur inversé.* |
| **Actions vs Obligations** (`SPY`/`TLT`) | Actions US vs bons du Trésor longs | Si les actions battent les obligations refuge → on préfère le rendement à la sécurité = **risk-on**. |
| **Crédit risqué vs sûr** (`HYG`/`LQD`) | Dette *high yield* vs dette *investment grade* | Si le high yield (plus risqué) tient face à la dette de qualité → confiance = **risk-on**. C'est un proxy du *spread de crédit*. |
| **Cycliques vs Défensives** (`XLY`/`XLP`) | Consommation discrétionnaire vs produits de base | Les cycliques (loisirs, luxe) mènent quand on parie sur la croissance = **risk-on** ; rotation vers les défensives (alimentation) = **risk-off**. |
| **Small vs Large caps** (`IWM`/`SPY`) | Petites vs grandes capitalisations | Les small caps, plus fragiles, surperforment quand l'appétit pour le risque est fort = **risk-on**. |
| **Or vs Actions** (`GLD`/`SPY`) | L'or vs le S&P 500 | L'or est le refuge par excellence. S'il bat les actions → prudence = **risk-off**. *Indicateur inversé.* |
| **Dollar** (`DX-Y.NYB`) | La force du dollar (DXY) | Le dollar est la monnaie refuge mondiale. Une envolée = stress, pénurie de liquidités = **risk-off**. *Indicateur inversé.* |
| **Yen** (`JPY=X`, USD/JPY) | La force du yen | Le yen sert à financer les paris risqués (*carry trade*). Quand il se renforce brutalement (USD/JPY baisse), c'est un *débouclage* = **risk-off**. |

> Astuce d'oral : pour chaque indicateur, sache dire **(a)** ce qu'il compare, **(b)** pourquoi le sens choisi, **(c)** un exemple. Ex. : « Le crédit HYG/LQD, c'est un proxy du spread de crédit : en mars 2020 le high yield a décroché violemment, mon indicateur est tombé à zéro. »

## 4. Pourquoi ces choix (et leurs limites)

- **Pourquoi des ETF plutôt que des indices ?** Ils sont liquides, gratuits sur Yahoo Finance, et reflètent fidèlement chaque classe d'actifs. Facile à reproduire.
- **Pourquoi une fenêtre d'un an pour le z-score ?** Assez longue pour définir une « normale » stable, assez courte pour s'adapter aux changements de régime. C'est un **choix**, pas une vérité.
- **Pourquoi la moyenne simple des 8 ?** Simplicité et transparence. On pourrait pondérer les indicateurs, mais ça ajouterait des paramètres à justifier.
- **Limite honnête — la source :** Yahoo Finance via `yfinance` n'est pas une source officielle. Pour un usage pro on prendrait Bloomberg/Refinitiv.

## 5. ⭐ Le cas 2022 — la nuance qui impressionne

Un bon recruteur te demandera : *« Et pendant la crise de 2022, ton score plonge-t-il ? »* La vraie réponse est subtile — et c'est exactement ce qui montre que tu comprends les marchés :

> « Seulement **modérément**, et c'est voulu. 2022 n'était pas un krach de panique comme 2020, mais un marché baissier **piloté par la hausse des taux**. Résultat : les obligations (TLT) ont chuté *en même temps* que les actions, et le yen s'est effondré — alors qu'en temps normal ce sont des refuges. Deux de mes huit indicateurs (Actions/Obligations et le Yen) ont donc lu 2022 comme *risk-on*, ce qui a freiné la baisse du score. C'est une limite réelle de tout baromètre cross-asset qui suppose que les obligations protègent. Je l'assume et je la documente ; on pourrait la corriger en ajoutant un indicateur de *spread de crédit* pur ou en traitant le régime de taux à part. »

En revanche, **mars 2020 (Covid)** et **août 2024 (débouclage du carry trade yen)** font bien plonger le score : ce sont des épisodes de *peur* classiques où tous les refuges jouent leur rôle.

## ➕ Le tableau de bord des marchés

Au-delà du score, le site réunit **~60 indicateurs publics** en un coup d'œil, rangés par catégorie (L'essentiel, Indices, Largeur & style, Secteurs US, Volatilité, Taux & obligations, Macro, Devises, Matières premières, Crypto).

**Comment en parler :**
> « Le score répond à *une* question — peur ou appétit ? Le tableau de bord, lui, donne tout le contexte autour : les grands indices, la courbe des taux, l'inflation, la liquidité de la Fed, les spreads de crédit, le dollar, les matières premières, la crypto. Chaque indicateur est coloré selon que sa variation est favorable ou défavorable au risque, avec une phrase qui explique *pourquoi il compte*. »

**Les 3 sources, toutes gratuites et sans clé d'API** (une vraie décision d'ingénierie à assumer) :
- **Yahoo Finance** (`yfinance`) — tout ce qui est coté : indices, VIX, taux, matières premières, devises, crypto.
- **FRED** (Fed de St. Louis), via l'export CSV public `fredgraph.csv` — la macro : inflation (CPI, PCE), chômage, règle de Sahm, courbe des taux, spreads High Yield / Investment Grade, M2, bilan de la Fed, **liquidité nette** (bilan Fed − compte du Trésor − reverse repo, que je recalcule moi-même).
- **CoinGecko** (API publique `/global`) — dominance du Bitcoin et capitalisation crypto totale.

**La question piège probable — « Pourquoi colorer le VIX en rouge quand il monte, mais le S&P en vert ? »**
> « Parce que tous les indicateurs n'ont pas le même sens. Pour la plupart, une hausse est favorable au risque (vert). Mais pour le VIX, les spreads de crédit, le dollar, l'inflation ou le chômage, c'est l'inverse : une hausse est un signal *risk-off*, donc je les marque comme "inversés" et la couleur suit ce sens-là. Ça montre que je comprends ce que chaque chiffre veut dire, pas juste s'il monte ou descend. »

**Indicateurs qui font pro à citer :** la **liquidité nette de la Fed** (très corrélée aux actifs risqués et au Bitcoin), le **ratio cuivre/or** (indicateur avancé des taux longs), la **courbe 10 ans − 2 ans** (signal de récession), le **spread High Yield** (alerte précoce avant les actions).

## 6. Questions probables en entretien

- **« Pourquoi un z-score et pas juste la variation ? »** → Pour rendre comparables des indicateurs d'échelles différentes, et pour mesurer l'anormalité relative, pas la valeur absolue.
- **« Que se passe-t-il si un ticker est manquant ? »** → Le score se calcule sur les indicateurs restants et le site l'affiche. Robustesse avant tout.
- **« Ton score est à 58, qu'est-ce que ça veut dire concrètement ? »** → Zone neutre à légèrement risk-on : pas de stress marqué, appétit prudent. Je regarde ensuite *quels* sous-scores tirent le score — c'est tout l'intérêt de la grille des 8.
- **« C'est prédictif ? »** → Non, c'est **descriptif**. Ça mesure le climat actuel, pas une prévision. Je ne vends jamais ça comme un signal d'achat.
- **« Comment tu le ferais en mieux avec plus de moyens ? »** → Données pro (Bloomberg), pondération des indicateurs, ajout du spread de crédit et des flux, backtest de la valeur prédictive.

## 7. Mini-lexique FR → EN (pour l'oral en anglais)

| Français | Anglais |
|----------|---------|
| Appétit pour le risque | Risk appetite / risk-on |
| Aversion au risque | Risk aversion / risk-off |
| Valeur refuge | Safe-haven asset |
| Obligation d'État | Government bond / Treasury |
| Haut rendement / qualité | High yield / investment grade |
| Écart de crédit | Credit spread |
| Volatilité implicite | Implied volatility |
| Débouclage (de position) | Unwinding |
| Portage | Carry (trade) |
| Capitalisation boursière | Market capitalization |

---

**Conseil final :** entraîne-toi à dire le pitch (partie 1) à voix haute, puis à dérouler un ou deux indicateurs avec leur intuition. Si tu maîtrises la partie 5 (le cas 2022), tu auras une longueur d'avance : tu montreras que tu comprends *pourquoi* un modèle peut se tromper, ce qui vaut bien plus qu'un modèle « parfait » récité par cœur.
