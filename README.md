# finance-research-eval

> **Framework de recevabilité pour l'analyse financière assistée par LLM.** Cœur
> public open-core ; la donnée réelle, les connecteurs et la stack opérationnelle
> vivent dans une édition privée séparée.

## État : Phase 1 — harnais sec local

Il répond à **une seule question**, posée _avant_ toute technique :

> **« Qu'est-ce qu'une recommandation financière justifiable, traçable et vérifiable ? »**

On ne commence pas par « quel modèle choisir ? ». On commence par définir la
**mesure** : un harnais qui décide si une analyse est _recevable_ (sourcée,
recalculable, datée, cloisonnée) — **avant** qu'un modèle, une ingestion ou un
backtest n'existe.

**P1 (livré) = harnais sec local** : `RR synthétique → gates déterministes → rapport`.
Python **stdlib pur, zéro dépendance**. Voir [« Lancer le harnais »](#lancer-le-harnais-sec).

### Périmètre encore verrouillé (interdits tant qu'un GO de phase distinct n'est pas donné)

- ❌ pas d'ingestion de données réelles
- ❌ pas d'appel réseau à un fournisseur (EODHD / FMP / Tiingo / Sharadar / EDGAR)
- ❌ pas d'appel à une API payante
- ❌ pas de modèle / LLM branché (arrive en **P3**, en local)
- ❌ pas de job GPU
- ❌ pas de backtest
- ❌ pas de conseil client généré
- ❌ aucun impact sur un service d'inférence de production
- ❌ pas de `git init` / `git push` (phase **Ouverture**)
- ❌ pas de CI / hook (phase **Ouverture**)

Ce que P1 **contient** : du code **local, déterministe, sans données ni réseau ni
modèle** — exactement la « substance technique avant publication » prévue. Les
seules données sont des **fixtures synthétiques** fabriquées dans le repo.

### Lancer le harnais sec

```bash
# tests de conformité (stdlib unittest — aucune install, aucun réseau)
python3 -m unittest discover -s tests -t .
# rapport local (écrit runs/p1_dry_report.json, gitignored)
python3 -m harness.runner
# P2 : loaders publics sur échantillons synthétiques (offline, aucune vraie donnée)
python3 -m harness.sources.demo
# P3 : end-to-end EvalItem → candidat → RR → gates (mocks, offline, 0 VRAM)
python3 -m harness.eval_run
```

## Ce que ce dépôt est / n'est pas

| C'est | Ce n'est pas |
|---|---|
| Une spec SDD du futur harnais d'évaluation | Un screener / stock-picker |
| Un contrat d'usage dual (perso / client MIF II) | Un robot de trading |
| Un jeu de gates de recevabilité (jour 0) | Un fournisseur de signaux d'achat |
| Une définition de « recommandation justifiable » | Un conseil en investissement |
| Model-agnostic par construction | Un choix de modèle |

> **Avertissement.** Ce dépôt décrit un cadre d'ingénierie et d'évaluation.
> Il ne constitue **ni un conseil en investissement, ni un conseil juridique**.
> Le contrat « client-mifid » (cf. `dual-use-contract.md`) doit être **validé
> par la conformité / un juriste** avant tout usage réel relevant de MiFID II / AMF.

## Licence & modèle open-core

Dépôt **public** sous approche **open-core** : le *framework de recevabilité* est
ouvert ; la stack réelle (données, connecteurs, scoring, conformité opérationnelle)
reste dans un **dépôt privé séparé** `finance-research-eval-enterprise`.

| Périmètre | Licence |
|---|---|
| **Code** (gates, schémas, moteurs de référence, mocks, tests) | **Apache-2.0** (`LICENSE`) |
| **Spec & docs** (RR, gates, contrat dual-use) | **CC-BY-4.0** (`LICENSE-docs`) |
| **Contributions** | **DCO** (`DCO`, `git commit -s`) — pas de CLA |
| **Nom du projet** | politique de marque (`TRADEMARK.md`) |

La frontière public/privé est définie dans **[`OPEN-CORE.md`](OPEN-CORE.md)** —
à lire avant d'ajouter quoi que ce soit. Règle : *public = la mesure + interfaces +
mocks + fixtures synthétiques ; privé = la réalité (impl. réelles) + données + ops*.
Les gates et le Recommendation Record sont **100 % publics, volontairement** (actif
de légitimité, fait pour être cité).

## Structure

```
finance-research-eval/
├── README.md                                  ← vous êtes ici
├── pyproject.toml                             ← métadonnées (zéro dépendance runtime)
├── harness/                                    ← P1 : harnais sec (stdlib pur)
│   ├── rr.py                                   ←   hachage canonique + validation RR
│   ├── schema/recommendation_record.schema.json ← le standard RR (machine-readable)
│   ├── compute/metrics.py                      ←   moteur de recalcul déterministe (G-3)
│   ├── gates/gates.py                          ←   G-1..G-6 + sévérité par lane + verdict
│   ├── fixtures/{synthetic,cases}.py           ←   RR synthétiques + catalogue de conformité
│   ├── fixtures/cases_worked.py                 ←   cas E2E complet : FICTEX SA (analyste)
│   ├── fixtures/cases_patrimoine.py             ←   cas patrimoine/CGP : MEDISYN SA (note OK + note refusée)
│   ├── runner.py                               ←   fixtures → gates → rapport local
│   ├── sources/                                ← P2 : loaders publics (pointeurs, offline)
│   │   ├── registry.py                         ←   pointeurs : URL, licence, no-redistribution
│   │   ├── evalitem.py                         ←   item d'éval normalisé (question+contexte+gold)
│   │   ├── loaders.py                          ←   parsers offline FinanceBench/FinQA/EDGAR
│   │   ├── samples/*.{jsonl,json}              ←   échantillons SYNTHÉTIQUES (jamais les vraies données)
│   │   └── demo.py                             ←   démo offline (samples → EvalItems)
│   ├── candidates/                             ← P3 : adaptateurs candidat (model-agnostic)
│   │   ├── mock.py                             ←   faithful/sloppy mocks (0 VRAM, tests)
│   │   └── http_openai.py                      ←   modèle réel via endpoint OpenAI-compatible
│   ├── eval_run.py                             ←   EvalItem → candidat → RR → gates → rapport
│   ├── report.py                               ← P4 : batch runner + rapport Markdown/CSV (stdlib, offline)
│   └── export.py                               ← P5 : exporteur RR (JSONL + manifest + thesis-card Markdown)
├── tests/                                      ← unittest stdlib (163 tests, 0 réseau)
│   ├── test_gates_conformity.py               ←   table de conformité verrouillée (vérificateur déterministe)
│   ├── test_compute.py
│   └── test_schema.py
├── LICENSE                                     ← Apache-2.0 (code)
├── LICENSE-docs                               ← CC-BY-4.0 (spec & docs)
├── NOTICE                                      ← attributions + périmètre open-core
├── DCO                                         ← Developer Certificate of Origin
├── OPEN-CORE.md                                ← contrat de frontière public/privé
├── GOVERNANCE.md                               ← qui décide, évolution du standard
├── CONTRIBUTING.md                             ← scope + DCO + standard high-scrutiny
├── SECURITY.md                                 ← divulgation responsable + usage responsable
├── CODE_OF_CONDUCT.md                          ← Contributor Covenant 2.1
├── TRADEMARK.md                                ← politique de nom / source canonique
├── CHANGELOG.md                                ← versionnage du standard (SemVer)
├── .gitignore                                  ← anti-fuite (deny-by-default)
└── .specify/
    ├── memory/
    │   └── constitution.md                    ← principes directeurs + question centrale
    └── specs/
        └── finance-research-eval/
            ├── spec.md                         ← spec SDD (FR-001..FR-012)
            ├── harness-structure.md            ← /specify : layout du futur harnais (décrit, non bâti)
            ├── dual-use-contract.md            ← lanes personal-research / client-mifid
            └── eval-gates.md                   ← gates jour 0 : G-1..G-6
```

> ⚠️ `.github/` (templates issue/PR + CI) et le hook anti-fuite pre-commit sont
> **différés à la phase _ouverture_** (pas à P1) : une CI ne tourne qu'au push et un
> hook pre-commit n'a pas de sens avant `git init`. Les inclure en P1 reviendrait à
> « transformer le repo en produit actif », ce que P1 doit éviter. P1 = substance
> technique locale (schéma + gates + tests synthétiques), sans `git`, sans réseau.

## Données — décision confirmée

**On ne paie rien maintenant.** V1 = **benchmarks publics** (FinanceBench, FinQA,
ConvFinQA, TAT-QA) + **SEC EDGAR** (gratuit). Les fournisseurs **EODHD / FMP /
Tiingo / Sharadar** sont **repoussés** à une phase ingestion/backtest ultérieure,
après un **test de couverture FR/EU** explicite. Aucun de ces fournisseurs n'est
appelé en Phase 0. Voir `spec.md` §Données.

## Phases (chacune nécessite un GO distinct)

| Phase | Contenu | Repo | Statut |
|---|---|---|---|
| **P0** | Doctrine + open-core + gouvernance | public | ✅ fait |
| **P1** | Harnais sec **local** : `RR synthétique → gates déterministes → rapport`. Schéma RR, gates, compute, fixtures, tests. **Pas de git, données, LLM, réseau, GPU.** | public | ✅ fait (12 tests verts, 10 cas) |
| **P2** | Loaders publics : benchmarks + EDGAR (**pointeurs**, pas de redistribution). **Aucune donnée privée.** | public | ✅ fait (loaders offline FinanceBench/FinQA/EDGAR + pointeurs ConvFinQA/TAT-QA, 19 tests verts) |
| **P3** | Candidate/**modèle branché localement** (GPU local idle), sur public/synthétique. Le modèle devient benchmarkable + interchangeable. | public | ✅ fait (e2e mocks 23 tests + live vs endpoint OpenAI-compatible, 0 VRAM nouvelle) |
| **P4** | Batch runner + reporting : N candidats × M lanes × K item-sets → stats de gates agrégées, rapport Markdown + export CSV, `run_id` déterministe. **stdlib pur, offline, fixtures synthétiques.** | public | ✅ fait (`harness/report.py`, 41 tests verts) |
| **P5** | Exporteur RR : bundle JSONL durable par RR + manifest `index.json` + thesis-card Markdown (provenance, claims, recalcul indépendant, synthèse de gates). Cas E2E **FICTEX SA synthétique** sur les deux lanes. **stdlib pur, offline, aucune donnée réelle.** | public | ✅ fait (`harness/export.py` + `fixtures/cases_worked.py`, 69 tests verts) |
| **Ouverture** | **Seulement quand le standard est clair** : `git init`, emails placeholder, CI, hooks anti-fuite, repo `-enterprise`, push. | public | ⏸ GO requis |
| **Enterprise** | Ingestion réelle, FR/EU premium, point-in-time, fournisseurs payants, intégration MARBO, conformité, workflows, backtest. | **privé** | différé |

**Principe directeur — ne pas ouvrir trop tôt.** L'ouverture vient **après P3**, pas
après P0 : on n'ouvre que lorsque le dépôt *prouve* la méthode (RR vérifiable +
gates + fixtures + tests), pas lorsqu'il la *promet*. Gouvernance seule = intention ;
gates exécutables = standard.

> Cette table est la **source de vérité de la roadmap**. Les marqueurs de phase
> inline dans `spec.md` / `harness-structure.md` (anciens P1..P6) sont **supersédés**
> par cette séquence et seront resynchronisés quand ces fichiers seront édités en P1.

Rien au-delà de P0 ne démarre sans validation explicite, phase par phase.
