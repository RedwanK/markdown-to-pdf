# Tableaux Markdown

Les tableaux utilisent l'environnement `longtable` afin de gérer les débordements multi-pages.

## Capacités principales

| Bloc              | Description                                         | Support PDF |
|-------------------|-----------------------------------------------------|-------------|
| Mermaid           | Diagrammes de flux et de séquence via `mmdc`.       | ✅          |
| PlantUML          | Diagrammes UML en sortie PDF vectorielle.           | ✅          |
| Tableaux          | Style alterné, largeur centrée, prise en charge multi-pages. | ✅ |
| Code listings     | Mise en forme via `listings`, avec fond gris.        | ✅          |

## Extrait multi-colonnes

| Statut | Priorité | Responsable | Commentaire |
|:-------|:---------|:------------|:------------|
| En cours | Haute | @alice | Prévoir un plan de charge pour Q2. |
| À faire | Moyenne | @bob | En attente de specs validées. |
| Terminé | Basse | @carol | Documentation publiée dans Confluence. |

## Astuces

- Utilisez `:---` pour aligner le texte à gauche, `:---:` pour centrer, `---:` pour aligner à droite.
- Sur les gros tableaux, envisagez de réduire le contenu ou de le découper en sous-sections pour améliorer la lisibilité.
