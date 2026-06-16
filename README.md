# finance-research-eval

> **Un harnais qui décide si une analyse financière produite par un LLM est _recevable_ —
> sourcée, recalculable, datée — _avant_ de regarder si elle est « bonne ».**
> Cœur open-core public ; la donnée réelle, les connecteurs et la stack opérationnelle
> vivent dans une édition privée séparée.

Un modèle de langage peut produire une thèse d'investissement convaincante, bien écrite
— et **fausse**. Le vrai risque n'est pas qu'il se trompe : c'est qu'il se trompe de façon
crédible, avec un chiffre inventé glissé dans un raisonnement par ailleurs solide.

`finance-research-eval` ne cherche pas à produire de meilleures recommandations. Il définit
et applique une **mesure** : un jeu de **gates déterministes** qui vérifient, indépendamment
du modèle, qu'une recommandation est **traçable, recalculable et datée** — et qui la
**bloquent** sinon. La question posée _avant_ toute technique :

> **« Qu'est-ce qu'une recommandation financière justifiable, traçable et vérifiable ? »**

On ne commence pas par « quel modèle choisir ? ». On commence par la mesure. Le modèle
devient alors **interchangeable et benchmarkable** derrière le standard.

## L'idée clé : recevabilité avant exactitude

Le vérificateur est **séparé du modèle jugé** et **purement déterministe**. Il ne fait pas
confiance à la prose : il **re-calcule chaque chiffre** à partir des données fournies et
**refuse** ce qui ne tient pas — plutôt que d'« adoucir » en avertissement.

Conséquence, prouvée par les tests : une analyse peut être **« juste mais irrecevable »**.
Un candidat qui donne la bonne réponse mais sans la sourcer ni la dater est **bloqué** sur
la lane client ; un candidat qui source et recalcule proprement passe.

### Exemple (cas synthétique MEDISYN SA)

Une note d'analyse affiche un multiple « pas cher » de **EV/EBITDA = 6,5×**.
Le vérificateur recalcule, indépendamment, à partir des données de la note :

```
EV / EBITDA = 2160 / 240 = 9,0×   ≠   6,5× annoncé
→ G-3 (recalcul indépendant) : FAIL
→ lane client-mifid : G-5 propage le blocage
→ verdict : BLOCKED
```

La note « avait l'air » correcte. Elle est **refusée** parce que le chiffre mis en avant
n'est pas soutenu par les données. La même note avec un multiple cohérent passe `ADMISSIBLE`.
Voir [`harness/fixtures/cases_patrimoine.py`](harness/fixtures/cases_patrimoine.py) +
[`docs/usage-patrimoine-dossier-client.md`](docs/usage-patrimoine-dossier-client.md).

## Démarrage rapide

**Python stdlib pur — zéro dépendance, zéro réseau, zéro GPU.**

```bash
# Suite de conformité (le cœur : la table de gates verrouillée)
python3 -m unittest discover -s tests -t .        # 163 tests, 0 réseau

# Rapport local sur fixtures synthétiques (RR → gates → verdict)
python3 -m harness.runner

# Bout-en-bout : EvalItem → candidat (mock) → RR → gates  (offline, 0 VRAM)
python3 -m harness.eval_run

# Loaders publics sur échantillons synthétiques (offline, jamais les vraies données)
python3 -m harness.sources.demo

# Batch runner + rapport Markdown/CSV agrégé
python3 -m harness.report
```

Toutes les données embarquées sont des **fixtures synthétiques** (sociétés fictives,
ISIN préfixés `XX`). Aucune donnée réelle, aucune clé, aucun appel réseau.

## Le Recommendation Record (RR) et les gates

L'unité de sortie est le **Recommendation Record** : un objet où **chaque fait porte sa
source et sa date**, et **chaque ratio porte à la fois la valeur affirmée par le modèle et
la valeur recalculée**. C'est ce qui rend la vérification possible. Schéma machine-readable :
[`harness/schema/recommendation_record.schema.json`](harness/schema/recommendation_record.schema.json).

Six gates déterministes, avec une **sévérité par lane** :

| Gate | Vérifie |
|---|---|
| **G-1** Sourcing | chaque chiffre cite une source + un locator |
| **G-2** Audit | le RR est reproductible (hachage canonique du contenu) |
| **G-3** Recalcul | les ratios recalculés correspondent aux valeurs affirmées (tolérance bornée) |
| **G-4** Point-in-time | chaque donnée est datée (anti look-ahead / survivorship) |
| **G-5** Blocage client | sur la lane `client-mifid`, un échec G-1/G-3 **bloque** (ne signale pas) |
| **G-6** Cloisonnement | non-promotion entre lane perso et lane client |

## Usage dual — et avertissement

Le framework distingue deux **lanes** par un contrat explicite
([`dual-use-contract.md`](.specify/specs/finance-research-eval/dual-use-contract.md)) :

- **`personal-research`** — recherche personnelle ; G-1/G-3 *signalent* (FLAG).
- **`client-mifid`** — contexte conseil ; G-1/G-3 *bloquent* (un défaut de sourcing ou de
  recalcul rend la recommandation irrecevable).

> **Avertissement.** Ce dépôt décrit un cadre d'ingénierie et d'évaluation. Il ne constitue
> **ni un conseil en investissement, ni un conseil juridique**. La lane `client-mifid` doit
> être **validée par la conformité / un juriste** avant tout usage réel relevant de MiFID II / AMF.

## Ce que c'est / ce que ce n'est pas

| C'est | Ce n'est pas |
|---|---|
| Une mesure de recevabilité (gates déterministes) | Un screener / stock-picker |
| Un standard de traçabilité (le RR) | Un robot de trading |
| Un vérificateur model-agnostic | Un fournisseur de signaux d'achat |
| Une définition de « recommandation justifiable » | Un conseil en investissement |

## Open-core & licence

Approche **open-core** : le *framework de recevabilité* est public ; la stack réelle
(données, connecteurs, scoring propriétaire, conformité opérationnelle) vit dans un dépôt
**privé séparé** `finance-research-eval-enterprise`. Règle de frontière (voir
[`OPEN-CORE.md`](OPEN-CORE.md)) : *public = la mesure + interfaces + mocks + fixtures
synthétiques ; privé = la réalité + données + ops*. Les gates et le RR sont **100 % publics,
volontairement** — un actif de légitimité fait pour être cité.

| Périmètre | Licence |
|---|---|
| **Code** (gates, schémas, moteurs de référence, mocks, tests) | **Apache-2.0** ([`LICENSE`](LICENSE)) |
| **Spec & docs** (RR, gates, contrat dual-use) | **CC-BY-4.0** ([`LICENSE-docs`](LICENSE-docs)) |
| **Contributions** | **DCO** ([`DCO`](DCO), `git commit -s`) — pas de CLA |
| **Nom du projet** | politique de marque ([`TRADEMARK.md`](TRADEMARK.md)) |

Mainteneur : **Donald FOSSOUO / MARBO FINANCE** — `contact@marbo-finance.fr`.
Sécurité & divulgation responsable : [`SECURITY.md`](SECURITY.md).
Contribuer : [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Structure

```
harness/
├── rr.py                     hachage canonique + validation RR (G-2)
├── schema/…schema.json       le standard RR (machine-readable)
├── compute/metrics.py        moteur de recalcul déterministe (G-3)
├── gates/gates.py            G-1..G-6 + sévérité par lane + verdict
├── fixtures/                 RR synthétiques + catalogue de conformité
│   ├── cases_worked.py       cas E2E analyste : FICTEX SA
│   └── cases_patrimoine.py   cas CGP : MEDISYN SA (note OK + note refusée)
├── sources/                  loaders publics (pointeurs, offline) + échantillons synthétiques
├── candidates/               adaptateurs candidat model-agnostic (mock + endpoint OpenAI-compat)
├── eval_run.py               EvalItem → candidat → RR → gates → rapport
├── report.py                 batch runner + rapport Markdown/CSV
└── export.py                 exporteur RR (JSONL + manifest + thesis-card Markdown)
tests/                        unittest stdlib (163 tests, 0 réseau)
.specify/specs/…              spec SDD, contrat dual-use, définition des gates
```

## Statut & feuille de route

| Étape | Contenu | Statut |
|---|---|---|
| Doctrine + gouvernance open-core | principes, licences, frontière public/privé | ✅ public |
| Harnais de recevabilité | RR + gates G-1..G-6 + recalcul déterministe + fixtures + tests | ✅ public |
| Loaders publics | benchmarks (FinanceBench/FinQA/…) + EDGAR en **pointeurs**, jamais de redistribution | ✅ public |
| Candidat model-agnostic | mocks + endpoint OpenAI-compatible ; le modèle devient benchmarkable | ✅ public |
| Batch + export | reporting agrégé Markdown/CSV + bundle RR + thesis-card | ✅ public |
| Enterprise | ingestion réelle, point-in-time, fournisseurs, conformité, backtest | 🔒 privé, planifié |

> **Données — décision assumée :** on ne paie rien pour démarrer. Le cœur public s'appuie sur
> des **benchmarks publics** et **SEC EDGAR** (gratuit), uniquement en **pointeurs** (aucune
> donnée redistribuée). Les fournisseurs payants relèvent de l'édition Enterprise.
