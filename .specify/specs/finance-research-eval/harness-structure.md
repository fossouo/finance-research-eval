# /specify — Structure du futur harnais (décrite, non bâtie)

> **Design-only.** Chaque composant ci-dessous est **décrit**, jamais implémenté
> en Phase 0. Aucun fichier `.py` / `.sh` / `requirements.txt` n'existe.
> Décalque conceptuel de `edu-eval-harness`.

## Vue d'ensemble

```
                  ┌──────────────────────────────────────────────┐
   question  ───► │  CANDIDATE (model-agnostic, FR-009)          │ ───► RR brut
   (+ docs)       │  LLM local | distant | pipeline RAG         │
                  └──────────────────────────────────────────────┘
                                      │
                                      ▼
                  ┌──────────────────────────────────────────────┐
                  │  GATE ENGINE (déterministe)                  │
                  │  G-1 sourcing · G-2 audit · G-3 recalcul ·   │
                  │  G-4 point-in-time · G-5 blocage client ·    │
                  │  G-6 cloisonnement                           │
                  └──────────────────────────────────────────────┘
                                      │
                  ┌───────────────────┴────────────────────┐
                  ▼                                         ▼
        recevabilité (gates)                      exactitude (vs gold)
                  └───────────────────┬────────────────────┘
                                      ▼
                              RAPPORT (scores + verdicts)
```

Le **harnais ne contient pas de modèle**. Il branche un *candidat* (interface
abstraite) et **mesure**. Le candidat par défaut, en phase ultérieure, sera un
LLM local servi en **GPU local idle, CPU-safe, idle-guard** — tout service
d'inférence de production **jamais touché**.

## Layout cible (futur — NON créé)

```
finance-research-eval/                      [P1+ — n'existe pas encore]
├── harness/
│   ├── schema/            # schéma RR (§4 spec) — JSON Schema, design d'abord
│   ├── corpus/            # loaders benchmarks publics (P2) — lecture seule
│   │   ├── financebench/  #   (décrit ; aucun téléchargement en P0–P1)
│   │   ├── finqa/
│   │   ├── convfinqa/
│   │   └── tatqa/
│   ├── extension_fr/      # corpus URD/AMF (P3)
│   ├── gates/             # moteur déterministe G-1..G-6 (P1)
│   ├── compute/           # moteur de recalcul indépendant (P1) — G-3
│   │   └── ratios/        #   EV/EBITDA, P/E, FCF yield, ROIC, dette/EBITDA...
│   ├── runner/            # orchestration éval (P1) — idle-guard, CPU-safe
│   ├── candidates/        # adaptateurs model-agnostic (P6) — aucun modèle figé
│   └── report/            # scoring recevabilité + exactitude (P1)
├── corpora/               # données (P2+) — vide, gitignored, jamais en P0
└── runs/                  # sorties d'éval (P1+) — vide en P0
```

> Tous les dossiers ci-dessus sont **futurs**. En Phase 0, seuls existent ce
> fichier et ses voisins Markdown.

## Composants (rôle, entrée, sortie, phase)

| Composant | Rôle | Déterministe ? | Phase |
|---|---|---|---|
| **schema/** | Définit le RR (l'unité de sortie) | n/a | P1 (design) |
| **corpus/** | Charge (question, gold) des benchmarks publics | oui | P2 |
| **extension_fr/** | Corpus QA FR/EU sur URD/AMF | oui | P3 |
| **compute/** | Recalcule chaque ratio/valorisation **sans LLM** | **oui** | P1 |
| **gates/** | Applique G-1..G-6, émet pass/fail + raison | **oui** | P1 |
| **candidates/** | Interface abstraite vers un candidat (LLM/pipeline) | non | P6 |
| **runner/** | Boucle d'éval, idle-guard, bornes de temps | oui | P1 |
| **report/** | Deux scores : recevabilité + exactitude | oui | P1 |

**Invariant d'architecture (P-1, P-3)** : `compute/` et `gates/` sont
**totalement déterministes** et **n'appellent aucun LLM**. C'est la séparation qui
rend la mesure crédible — le juge (gates + recalcul) est indépendant du jugé (LLM).
Identique au principe d'un juge déterministe séparé du jugé.

## Le moteur de recalcul (`compute/`, le cœur de G-3)

- Reçoit les `evidence` (valeurs brutes extraites + localisateurs).
- Recalcule **lui-même** chaque métrique à partir de formules explicites.
- Compare à `llm_value`. Divergence hors tolérance → flag → `BLOCKED`.
- Ne « fait pas confiance » au nombre du LLM ; il le **re-dérive**.

Exemples de métriques (catalogue à figer en P1, design-only) : marges, EV/EBITDA,
P/E, P/B, FCF yield, ROIC, dette nette/EBITDA, croissance CA/EPS, ratios de
liquidité. Une valorisation type **DCF simplifié** ou **comparables** est elle
aussi recalculée pas-à-pas, jamais « sortie » par le LLM.

## Sortie du harnais (rapport)

Pour chaque item du corpus :
- `gate_results` : G-1..G-6 (pass/fail + raison).
- `verdict` : `ADMISSIBLE` / `BLOCKED`.
- `accuracy` (si gold) : exact-match / numérique tolérancé.
- agrégats : taux de recevabilité, taux de blocage par gate, exactitude
  **conditionnée à l'admissibilité**.

> Principe de lecture (P-récap) : un candidat « exact » mais à fort taux de
> blocage G-1/G-3 est **mauvais** pour notre usage — il devine juste sans pouvoir
> le justifier. Le harnais rend ce défaut visible, là où un benchmark d'exactitude
> seul le masquerait.

## Garde-fous d'exécution (pour P1+, rappel)

- GPU local idle uniquement, idle-guard, CPU-safe.
- Bornes de temps sur tout sous-processus (timeouts bornés).
- Aucune clé API — endpoint local uniquement le moment venu.
- tout service d'inférence de production strictement hors-périmètre.
- Rien de tout cela en Phase 0.
