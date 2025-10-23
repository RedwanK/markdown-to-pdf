# Guide d'utilisation du template LaTeX

Ce guide explique comment fonctionne le template LaTeX fourni par `markdown-pdf` et comment le personnaliser pour créer vos propres rendus. Les exemples ci-dessous se basent sur le template par défaut situé dans `src/markdown_pdf/templates/document.tex.j2` et sur ses partiels `cover.tex.j2` et `toc.tex.j2`.

## 1. Vue d'ensemble du pipeline

1. Les fichiers Markdown sont pré-traités (diagrammes Mermaid/PlantUML, images distantes, front matter).
2. Pandoc convertit le Markdown en LaTeX "pur" (`body`).
3. Jinja2 injecte ce contenu dans le template LaTeX, avec les métadonnées et les variables de contexte décrites ci-dessous.
4. Le moteur LaTeX (XeLaTeX par défaut) compile le document final.

Le template contrôle donc l'apparence (polices, couleurs, en-têtes/pieds, couverture, table des matières) tandis que Pandoc se concentre sur le contenu généré à partir du Markdown.

## 2. Variables disponibles dans le template

Le renderer Jinja appelle `document.tex.j2` avec les variables suivantes :

| Variable         | Type                     | Description |
|------------------|--------------------------|-------------|
| `body`           | `str` LaTeX              | Contenu principal généré par Pandoc (`{{ body | safe }}`). |
| `metadata`       | `DocumentMetadata`       | Métadonnées normalisées (cf. section 3). Les champs sont déjà échappés côté Python si nécessaire. |
| `preamble`       | `str | None`       | Chaîne LaTeX à ajouter après vos `\usepackage`. Construite depuis `--preamble`, `--preamble-inline` et la clé `preamble` du front matter. |
| `toc_entries`    | `list[dict]`             | Titres détectés dans le contenu : `level`, `title`, `target`, `label`. Sert à construire une table des matières custom. |
| `show_cover`     | `bool`                   | Vrai si la couverture doit être rendue (`--no-cover` la force à `False`). |
| `show_toc`       | `bool`                   | Vrai si la table des matières doit être affichée (`--no-toc` la force à `False`). |
| `front_matter`   | `dict`                   | Front matter Markdown fusionné (dernier champ gagne). Utile pour des variables sur mesure.

Toutes les partials Jinja (`cover.tex.j2`, `toc.tex.j2`) reçoivent le même contexte.

## 3. Configurer les métadonnées

Les métadonnées pilotent autant le template que les en-têtes/pieds. Elles peuvent provenir :

- d'un fichier YAML/JSON passé à `--meta` ;
- d'entrées additionnelles `--meta-entry cle=valeur` ;
- du front matter YAML présent en tête d'un fichier Markdown.

Champs principaux (voir `src/markdown_pdf/config.py`) :

| Champ        | Effet dans le template |
|--------------|-----------------------|
| `title`      | Texte principal de la couverture et de l'en-tête. |
| `company`    | Affiché sur la couverture et dans l'en-tête si `title` est absent. |
| `author`     | Sous le titre de la couverture et dans l'en-tête. |
| `contact`    | Coin supérieur droit de l'en-tête, et bas de la couverture. |
| `address`    | Pied de page gauche et bas de couverture. |
| `logo_path`  | Logo sur la couverture (chemin relatif au fichier de métadonnées ou absolu). |
| `title_color`| Couleur des titres, liens, en-têtes, format hex (`#RRGGBB`) ou nom LaTeX. |
| `title_font` | Police dédiée aux titres (XeLaTeX `\newfontfamily`). |
| `body_font`  | Police principale (`\setmainfont`). |
| `extra.subtitle`   | Sous-titre optionnel sur la couverture. |
| `extra.cover_notes`| Bloc de texte en bas de couverture. |

Exemple de fichier `metadata.yaml` :

```yaml
---
title: Dossier stratégique 2024
company: ACME Corp
author: Équipe Produit
contact: produit@example.com
address: 42 avenue des Docs, 75000 Paris
logo_path: examples/assets/logo.jpg

# Palette & polices
title_color: "#0F4C81"
title_font: "TeX Gyre Heros"
body_font: "IBM Plex Sans"

extra:
  subtitle: Version confidentielle
  cover_notes: Diffusion interne uniquement.
---
```

Conseils :

- `logo_path` est résolu en chemin absolu pendant le rendu : via `--meta`, le chemin est interprété depuis le dossier du fichier de métadonnées ; dans un front matter Markdown, il reste relatif au fichier Markdown.
- Les polices doivent être installées sur le système et disponibles pour XeLaTeX (`fc-list | grep "Nom"` pour vérifier).

## 4. Créer un template personnalisé

1. Copiez le template par défaut :
   ```bash
   cp src/markdown_pdf/templates/document.tex.j2 templates/document-personnalise.tex.j2
   ```
2. Modifiez ce fichier pour ajuster les `\usepackage`, marges, couleurs, ou pour injecter vos propres blocs (ex. `\fbox`, `\newcommand`).
3. Optionnel : personnalisez aussi `cover.tex.j2` et `toc.tex.j2` dans le même dossier si vous souhaitez changer la page de couverture ou la mise en page de la table des matières.
4. Lancez la conversion en précisant votre template :
   ```bash
   markdown-pdf convert docs/rapport.md --template templates/document-personnalise.tex.j2 --meta metadata.yaml
   ```

Le moteur Jinja charge les templates à partir du répertoire du fichier principal. Les includes (`{% include 'cover.tex.j2' %}`) restent résolus tant qu'ils se trouvent dans le même dossier.

## 5. Étendre le préambule LaTeX

- `--preamble chemin.tex` ajoute le contenu du fichier après les `\usepackage` du template.
- `--preamble-inline "\\usepackage{tikz}"` permet d'ajouter une commande ponctuelle sans créer de fichier.
- Dans le front matter Markdown, vous pouvez ajouter :
  ```yaml
  preamble: |
    % commandes spécifiques à ce document
    \usepackage{tikz}
    \usetikzlibrary{arrows.meta}
  ```
  Cette clé est fusionnée avec le préambule passé en CLI.

Use cases fréquents : charger des packages supplémentaires, redéfinir `\lstset`, ajouter des commandes `\newcommand`, modifier `\hypersetup`.

## 6. Gérer couverture et table des matières

- `--no-cover` supprime la couverture et réactive la numérotation dès la première page de contenu.
- `--no-toc` évite de générer `toc.tex.j2` ; vous pouvez aussi modifier ce partial pour adapter le libellé, l'espacement ou le formatage.
- Le template par défaut désactive temporairement la numérotation (`\pagenumbering{gobble}`) le temps de la couverture/ToC, puis relance `\pagenumbering{arabic}`.

Si vous créez votre propre logique de couverture, pensez à remettre `\cleardoublepage` ou `\clearpage` avant de repasser à la numérotation classique.

## 7. Bonnes pratiques et dépannage

- Vérifiez la compilation XeLaTeX en activant `--keep-temp` : le `.tex` généré et les logs sont conservés dans un dossier temporaire pour inspection.
- Si vous ajoutez des packages, assurez-vous qu'ils sont installés dans votre distribution LaTeX (`tlmgr install <package>` ou équivalent).
- Le template utilise `fontspec` : restez sur XeLaTeX ou LuaLaTeX pour bénéficier des polices système. Passer à `pdflatex` nécessiterait d'adapter le préambule.
- Utilisez `metadata.extra` pour transmettre des variables custom supplémentaires à votre template (par exemple `extra.version` ou `extra.project_code`).
- Gardez le préambule léger : chaque package supplémentaire rallonge la compilation et peut entrer en conflit avec ceux déjà chargés.

Avec ces éléments, vous pouvez dériver un template LaTeX adapté à votre charte graphique tout en tirant parti de la chaîne d'outils `markdown-pdf`.
