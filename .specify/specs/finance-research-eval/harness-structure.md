# Structure du harnais d'évaluation

> Référence d'architecture. Le harnais est **implémenté** (cœur public). Les
> composants ci-dessous existent sauf mention explicite « enterprise » (données
> réelles, corpus FR/EU premium). Pattern eval-first : mesurer avant de choisir le modèle.

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
abstraite) et **mesure**. Les candidats réels (modèle local ou distant) sont
configurables via `candidates/http_openai.py` ; les services d'inférence de
production restent hors-périmètre de l'évaluation.

## Layout (état réel)

```
finance-research-eval/
├── harness/
│   ├── rr.py             # hachage canonique + validation RR (G-2)
│   ├── schema/           # schéma RR — JSON Schema 2020-12
│   ├── compute/metrics.py# moteur de recalcul indépendant — G-3
│   ├── gates/gates.py    # moteur déterministe G-1..G-6 + sévérité par lane
│   ├── fixtures/         # RR synthétiques + cas worked (FICTEX, MEDISYN)
│   ├── sources/          # loaders publics en pointeurs (offline) + samples synthétiques
│   │   ├── registry.py   #   FinanceBench / FinQA / ConvFinQA / TAT-QA / EDGAR
│   │   ├── loaders.py    #   parsers offline (lecture locale, jamais de fetch)
│   │   └── samples/      #   échantillons SYNTHÉTIQUES uniquement
│   ├── candidates/       # adaptateurs model-agnostic (mock + endpoint OpenAI-compat)
│   ├── connectors/       # Protocols Connector/ConstituentsSource + MockConnector
│   ├── eval_run.py       # EvalItem → candidat → RR → gates → rapport
│   ├── report.py         # batch runner + rapport Markdown/CSV
│   └── export.py         # exporteur RR (JSONL + manifest + thesis-card)
├── tests/                # unittest stdlib (suite verte, 0 réseau)
└── runs/                 # sorties d'éval locales (gitignored)
```

> **Enterprise (privé)** : le corpus FR/EU premium, les vrais connecteurs de
> données (`EdgarConnector`, `TiingoConnector`) et le `corpora/` de données réelles
> vivent dans le dépôt enterprise privé qui *importe* ce cœur public.

## Composants (rôle, entrée, sortie, phase)

| Composant | Rôle | Déterministe ? | Statut |
|---|---|---|---|
| **schema/** + **rr.py** | Définit + valide le RR (l'unité de sortie) | n/a | ✅ public |
| **sources/** | Charge (question, gold) en pointeurs ; samples synthétiques | oui | ✅ public |
| **compute/** | Recalcule chaque ratio/valorisation **sans LLM** | **oui** | ✅ public |
| **gates/** | Applique G-1..G-6, émet pass/fail + raison | **oui** | ✅ public |
| **candidates/** | Interface abstraite vers un candidat (LLM/pipeline) | non | ✅ public |
| **eval_run/report/export** | Boucle d'éval + reporting + export RR | oui | ✅ public |
| corpus FR/EU + connecteurs réels | Corpus URD/AMF premium, ingestion réelle | oui | 🔒 enterprise |

**Invariant d'architecture (P-1, P-3)** : `compute/` et `gates/` sont
**totalement déterministes** et **n'appellent aucun LLM**. C'est la séparation qui
rend la mesure crédible — le juge (gates + recalcul) est indépendant du jugé (LLM).
Identique au principe d'un juge déterministe séparé du jugé.

## Le moteur de recalcul (`compute/`, le cœur de G-3)

- Reçoit les `evidence` (valeurs brutes extraites + localisateurs).
- Recalcule **lui-même** chaque métrique à partir de formules explicites.
- Compare à `llm_value`. Divergence hors tolérance → flag → `BLOCKED`.
- Ne « fait pas confiance » au nombre du LLM ; il le **re-dérive**.

Exemples de métriques (implémentées dans `compute/metrics.py`) : marges, EV/EBITDA,
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

## Garde-fous d'exécution

- Cœur public : **zéro dépendance, zéro réseau** dans la suite de tests (pur stdlib).
- Aucune clé API dans le dépôt ; les candidats distants (`candidates/http_openai.py`)
  sont configurables mais désactivés par défaut.
- Les services d'inférence de production sont strictement hors-périmètre de l'évaluation.
- Hygiène anti-fuite appliquée par `tools/check_public_hygiene.sh` (CI + hook pre-commit).
