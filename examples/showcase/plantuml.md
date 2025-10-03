# Diagrammes PlantUML

Les blocs ```plantuml``` sont rendus via le CLI `plantuml` en sortie PDF vectorielle. Les fichiers générés restent nets quel que soit le niveau de zoom.

## Diagramme de composants

```plantuml
@startuml
skinparam componentStyle rectangle
skinparam shadowing false

package "Ingestion" {
  [MQTT Broker]
  [Ingestion Worker]
}

package "Plateforme" {
  [API]
  [Backoffice]
  [Base de données]
}

[MQTT Broker] --> [Ingestion Worker]
[Ingestion Worker] --> [API]
[API] --> [Backoffice]
[API] --> [Base de données]
@enduml
```

## Diagramme de séquence

```plantuml
@startuml
skinparam ArrowColor #1A6FB3
skinparam participantPadding 15

participant Client
participant API
participant Worker
participant "DB" as Database

Client -> API: POST /reports
API -> Worker: enqueue(job)
Worker -> Database: INSERT job
Worker --> API: ack
API --> Client: 202 Accepted
@enduml
```

## Conseils

- Changez le format avec `--plantuml-format svg` si vous préférez du SVG.
- Les diagrammes sont generés depuis l'entrée standard (`-pipe`), les includes externes ne sont donc pas nécessaires.
- Un encodage UTF-8 est appliqué par défaut (`--plantuml-charset`).
