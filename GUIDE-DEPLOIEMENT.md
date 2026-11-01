# 🚀 Guide de mise en ligne — pas à pas, pour débutant

Objectif : passer des fichiers sur ton ordinateur à **un site en ligne qui se met à jour tout seul chaque soir**, sans écrire une ligne de code et sans rien payer.

Compte à prévoir (gratuits, 2 min chacun) :
- un compte **GitHub** → https://github.com
- un compte **Netlify** → https://netlify.com (connecte-toi avec GitHub, c'est plus simple)

Durée totale : environ **15 minutes**.

---

## Étape 1 — Créer le dépôt GitHub

1. Connecte-toi sur https://github.com.
2. En haut à droite, clique sur **+** puis **New repository**.
3. **Repository name** : `meteo-des-marches`.
4. Laisse **Public** coché (c'est ce que verront les recruteurs).
5. Ne coche **rien** d'autre (pas de README, on a déjà le nôtre).
6. Clique **Create repository**.

Tu arrives sur une page qui dit « …or upload an existing file ». Parfait.

## Étape 2 — Mettre les fichiers dans le dépôt

> Si tu as reçu un fichier `.zip`, **décompresse-le d'abord** : tu dois voir les fichiers `index.html`, `compute.py`, etc., pas le zip.

1. Sur la page du dépôt, clique sur **Add file ▸ Upload files**.
2. Fais glisser dans la zone **tous ces fichiers et dossiers** :
   - `index.html`, `styles.css`, `app.js`
   - `compute.py`, `requirements.txt`
   - `README.md`, `GUIDE-DEPLOIEMENT.md`, `FICHE-REVISION.md`
   - le dossier **`data`** (avec `data.json` dedans)
3. En bas, clique **Commit changes**.

> ⚠️ **Le dossier `.github` est « caché »** (son nom commence par un point) et ne se glisse pas toujours bien. On va donc créer ce fichier à la main :
> 1. Clique **Add file ▸ Create new file**.
> 2. Dans le champ du nom, tape exactement : `.github/workflows/update.yml`
>    *(les `/` créent automatiquement les dossiers)*
> 3. Ouvre le fichier `update.yml` fourni sur ton ordinateur, **copie tout son contenu**, et colle-le dans la grande zone de texte.
> 4. Clique **Commit changes**.

✅ Ton dépôt contient maintenant tout le projet.

## Étape 3 — Autoriser et lancer GitHub Actions

GitHub Actions est le « robot » qui calcule le score chaque soir. Il faut l'autoriser à écrire dans le dépôt, puis le lancer une première fois.

1. Onglet **Settings** (du dépôt) ▸ menu de gauche **Actions ▸ General**.
2. Tout en bas, section **Workflow permissions** : choisis **Read and write permissions**, puis **Save**.
3. Reviens sur l'onglet **Actions** (en haut).
   - S'il demande d'activer les workflows, clique **I understand my workflows, enable them**.
4. À gauche, clique sur **Mise à jour quotidienne des données**.
5. À droite, bouton **Run workflow ▸ Run workflow** (branche `main`).
6. Attends 1 à 2 minutes et rafraîchis : une coche verte ✅ signifie que **les vraies données de marché ont été téléchargées** et que `data/data.json` a été mis à jour.

> À partir de maintenant, ce calcul se relance **tout seul** chaque jour de semaine vers 22h30–23h30 (heure de Paris).

## Étape 4 — Mettre le site en ligne avec Netlify

1. Va sur https://app.netlify.com et connecte-toi **avec GitHub**.
2. Clique **Add new site ▸ Import an existing project**.
3. Choisis **GitHub**, autorise l'accès, puis sélectionne le dépôt **`meteo-des-marches`**.
4. Réglages de déploiement (laisse quasiment tout vide, c'est un site statique) :
   - **Build command** : *(laisser vide)*
   - **Publish directory** : `.` *(un simple point — la racine du dépôt)*
5. Clique **Deploy**.
6. Après ~30 secondes, Netlify affiche une adresse du type `https://nom-aleatoire-123.netlify.app`. **Clique dessus : ton site est en ligne !** 🎉

> Pour une adresse plus propre : **Site configuration ▸ Change site name**, et mets par exemple `meteo-des-marches`.

## Étape 5 — La boucle automatique (rien à faire)

Voici ce qui se passe chaque soir, tout seul :

```
GitHub Actions calcule le score  ──►  commit de data/data.json  ──►  Netlify redéploie le site
```

Comme Netlify est relié à ton dépôt GitHub, **chaque fois que le robot met à jour les données, le site se remet à jour automatiquement**. Tu n'as plus rien à faire.

## Étape 6 — Vérifier que tout tourne

- **Le score change-t-il ?** Onglet **Actions** du dépôt → tu dois voir une exécution verte chaque jour de semaine.
- **Le site est-il à jour ?** Sur Netlify, onglet **Deploys** → un nouveau déploiement apparaît après chaque mise à jour des données.
- **Mettre à jour le lien dans le README** (optionnel mais propre) : sur GitHub, ouvre `README.md`, clique le crayon ✏️, remplace `https://VOTRE-SITE.netlify.app` par ta vraie adresse Netlify, **Commit changes**.

---

## 🛠️ En cas de souci

| Problème | Solution |
|----------|----------|
| Le site affiche « Impossible de charger les données » | `data/data.json` n'est pas encore présent : relance l'Action (Étape 3), ou vérifie que le dossier `data` a bien été envoyé. |
| L'Action échoue avec une erreur de `push` / permission | Étape 3.2 : « Read and write permissions » doit être activé. |
| L'Action échoue sur un ticker | Normal de temps en temps (Yahoo indisponible) : le score se calcule sur les indicateurs restants. Relance-la plus tard. |
| Le site ne se met pas à jour | Vérifie dans Netlify ▸ Deploys qu'un déploiement récent existe ; sinon, reconnecte le dépôt dans Netlify. |
| Je veux tester en local | `python -m http.server 8000` dans le dossier, puis ouvre `http://localhost:8000` (double-cliquer `index.html` ne marche pas : le navigateur bloque la lecture du JSON). |

Besoin d'aide ? Reviens me voir avec le message d'erreur exact, je te débloque.
