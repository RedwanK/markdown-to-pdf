# Diagrammes Mermaid

Ce document illustre comment l'outil convertit des blocs ```mermaid``` en images centrées dans le PDF. Comme le rendu s'appuie sur `@mermaid-js/mermaid-cli`, assurez-vous que le binaire `mmdc` est présent dans le `PATH`.

## Diagramme de flux

```mermaid
graph TD;
    A[Collecte de données] --> B{Validation};
    B -->|ok| C[Stockage temps réel];
    B -->|ko| D[File d'anomalies];
    C --> E[Dashboards];
    D --> E;
```

## Diagramme de séquence

```mermaid
sequenceDiagram
autopilot ->> API: POST /jobs
API -->> Queue: dispatch
Queue -->> Worker: consume
Worker ->> autopilot: 201 Created
```

## Astuces

- Les thèmes Mermaid (`--mermaid-theme`) et le fond (`--mermaid-background`) peuvent être ajustés via la CLI.
- Utilisez des identifiants simples (ASCII) pour éviter les surprises lors de la génération.
- Le format par défaut est PNG avec une mise à l'échelle ×2 pour un rendu net dans LaTeX.
