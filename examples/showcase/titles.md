# Titres et Structure

Ce document présente les différents niveaux de titres et leur rendu dans le PDF.

## Niveau 2

Le niveau 2 (`##`) s'affiche avec la couleur et la police configurées dans les métadonnées (`title_color`, `title_font`).

### Niveau 3

À utiliser pour structurer finement une section.

#### Niveau 4

Recommandé pour des cas spécifiques ; au-delà, préférez les listes afin de maintenir une bonne lisibilité.

## Front matter YAML

```yaml
---
title: Mon Rapport
author: Jane Doe
company: ACME Corp
contact: data-team@example.com
logo_path: assets/logo.png
---
```

Les clés du front matter sont fusionnées avec la configuration CLI pour personnaliser la couverture et les en-têtes.
