# Spec SDD — finance-research-eval

| | |
|---|---|
| **Feature** | Harnais d'évaluation de recevabilité pour l'analyse fondamentale assistée par LLM |
| **Statut** | **Implémenté** — harnais public (gates G-1..G-6, RR, recalcul déterministe, loaders publics, candidats, reporting) |
| **Constitution** | `.specify/memory/constitution.md` (P-1..P-7) |
| **Auteur** | Donald FOSSOUO / MARBO FINANCE (rédaction assistée par IA) |
| **Date** | 2026-06-13 |

---

## 1. Contexte & problème

Objectif final (au-delà du cœur public) : détecter des sociétés **sous-valorisées
par le marché** pour un horizon d'achat/revente **1–5 ans**, à partir de rapports
financiers + données de marché/actualité, **sur infra locale**, à coût ≈ 0 €.

Problème réel : « détecter du sous-valorisé » n'est pas un problème de modèle.
C'est **un problème de discipline** — un LLM hallucine des chiffres, et une thèse
non sourcée/non recalculée n'a aucune valeur (pire : elle fait perdre de l'argent).
Avant de produire la moindre recommandation, il faut **une mesure** de ce qu'est
une analyse _recevable_.

**Décision méthodologique (validée).** On construit le **harnais d'évaluation
d'abord** (eval-first) : ancrage sur référentiel public + extension domaine + gate
de sécurité déterministe, avant tout choix de modèle.

## 2. Décomposition (où est le travail)

| # | Brique | Responsable | Hors cœur public |
|---|---|---|---|
| 1 | Ingestion (filings + marché + news) | pipeline data | oui (enterprise) |
| 2 | Extraction des fondamentaux **ancrée/citée** | LLM + localisateur | oui (enterprise) |
| 3 | Valorisation / ratios | **moteur déterministe** | oui (enterprise) |
| 4 | Thèse qualitative (moat, mgmt, risques) | LLM / RAG | oui (enterprise) |
| 0 | **Mesure de recevabilité de 1–4** | **harnais d'éval** | **← le cœur public (ce dépôt)** |

## 3. Objectifs / Non-objectifs

**Objectifs (cœur public — livrés)**
- L'**unité de sortie** : le *Recommendation Record* (RR).
- Les **gates de recevabilité** G-1..G-6 (cf. `eval-gates.md`), implémentés et testés.
- Le **contrat dual-use** (cf. `dual-use-contract.md`).
- La **structure du harnais** (cf. `harness-structure.md`).
- La **décision data** (gratuit only en V1).

**Hors cœur public (édition enterprise privée)**
- Servir un modèle de production / brancher une vraie ingestion.
- Appeler une donnée réelle (EDGAR live, fournisseurs payants, marché).
- Produire une recommandation client réelle (sans re-validation humaine).
- Backtester sur données réelles point-in-time.

## 4. Artefact central — le *Recommendation Record* (RR)

Toute sortie du futur système (les deux lanes) est un **RR structuré**, défini
ici comme **schéma conceptuel** (pas de code) :

```
RecommendationRecord:
  id                      # identifiant stable
  lane                    # personal-research | client-mifid
  subject                 # émetteur / instrument analysé
  information_cutoff      # date de coupure (P-4) — aucune preuve postérieure admise
  claims[]                # affirmations / thèse
    - statement           # texte
    - kind                # qualitative | quantitative | valuation
    - evidence[]          # ≥1 si quantitative/valuation (P-2)
        - figure          # ex. "chiffre d'affaires 2024"
        - value           # valeur extraite
        - source_doc      # document d'origine (ex. 10-K, URD)
        - locator         # emplacement résolvable (page/section/table/span)
        - as_of           # date de l'information (P-4)
    - computations[]      # si valuation/ratio (P-3)
        - metric          # ex. EV/EBITDA
        - formula         # formule explicite
        - inputs[]        # références aux evidence[]
        - llm_value       # valeur proposée par le LLM (pour comparaison)
        - recomputed_value# valeur du moteur déterministe indépendant
        - agree           # llm_value ≈ recomputed_value (tolérance définie)
  audit_trail             # hash des entrées + journal transformations (P-5)
  lane_fields             # voir dual-use-contract.md (client-mifid uniquement)
  gate_results            # G-1..G-6 : pass/fail + raison (rempli par le harnais)
  verdict                 # ADMISSIBLE | BLOCKED
```

Le **harnais** prend un RR (ou la question + la sortie d'un candidat) et calcule
`gate_results` + `verdict`, puis (en présence d'un gold) un score d'exactitude.

## 5. Exigences fonctionnelles (FR)

> FR-001 à FR-009 et FR-011 sont **implémentées** dans le cœur public (gates, RR,
> recalcul, candidats model-agnostic). FR-010 (ingestion de données réelles) relève
> de l'édition enterprise.

- **FR-001** — L'unité de sortie est le RR structuré (§4). Toute analyse non
  exprimable en RR est hors-système.
- **FR-002** *(→ G-1)* — Toute `claim` quantitative/valuation porte ≥1 `evidence`
  avec `locator` **résolvable** et `as_of`. Sinon : `BLOCKED`.
- **FR-003** *(→ G-3)* — Toute `computation` est recalculée par un **moteur
  déterministe indépendant du LLM**. Divergence `llm_value` vs `recomputed_value`
  hors tolérance → `BLOCKED`. Le LLM ne valide jamais son propre nombre.
- **FR-004** *(→ G-4)* — Chaque `evidence` porte `as_of` ; le RR déclare
  `information_cutoff` ; aucune `evidence.as_of > information_cutoff` (anti
  look-ahead). `as_of` manquant → inadmissible.
- **FR-005** *(→ G-2)* — Le RR est **immuable, horodaté, reproductible** : hash
  des entrées + journal des transformations. Rejouable à l'identique.
- **FR-006** *(→ G-6)* — `lane` est **déclaré**. `client-mifid` exige les champs
  `lane_fields` (adéquation, risques, conflits — cf. contrat).
- **FR-007** *(→ G-5)* — En `client-mifid`, un RR échouant G-1 ou G-3 est
  **bloqué** (jamais émis comme recommandation), pas dégradé en « avis prudent ».
- **FR-008** *(→ G-6)* — **Aucune promotion automatique** `personal-research`
  → `client-mifid`. Re-validation humaine explicite requise.
- **FR-009** — **Model-agnostic.** Le harnais mesure n'importe quel candidat
  (LLM local, distant, ou pipeline). Le choix du modèle est une **décision aval**,
  gated par le passage du harnais (P6). On ne part jamais de « quel modèle ? ».
- **FR-010** — **Données V1 = gratuit only** : benchmarks publics (FinanceBench,
  FinQA, ConvFinQA, TAT-QA) + SEC EDGAR. Fournisseurs payants (EODHD/FMP/Tiingo/
  Sharadar) **différés** à une phase ingestion/backtest, après test de couverture
  FR/EU. Aucun appel réseau dans le cœur public.
- **FR-011** — Le harnais produit **deux scores distincts** : (a) *recevabilité*
  (conformité aux gates) et (b) *exactitude* (vs gold quand disponible). La
  recevabilité prime (un RR exact mais non sourcé reste `BLOCKED`).
- **FR-012** — **Frontière open-core.** Tout usage avec des données réelles ou en
  production relève de l'édition enterprise privée (cf. `OPEN-CORE.md`).

## 6. Ancrage & extension (le harnais, vu de haut)

Pattern eval-first : ancrer sur un référentiel public, puis étendre au domaine.

**Ancrage (référentiel public, reproductible)** — en pointeurs, non redistribué :
- **FinanceBench** — ~10k QA vérifiées sur 10-K/10-Q réels (l'équivalent gsm8k/mmlu).
- **FinQA / ConvFinQA** — raisonnement numérique sur tables+texte (teste G-3).
- **TAT-QA** — hybride table+texte.

**Extension (l'edge, cloisonné)** :
- **Dimension SOURCING** (G-1) — chaque chiffre cite un span résolvable.
- **Dimension VERIF-CALCUL** (G-3) — recalcul indépendant = vérificateur financier.
- **Corpus FR/EU** — QA sur URD/AMF (terrain CGP, là où l'ancrage US ne va pas).
  Décrit ici. ⚠️ Frontière public/enterprise à trancher : les *questions* d'éval
  peuvent être publiques, mais la donnée FR/EU **premium / point-in-time** relève
  de l'Enterprise (cf. roadmap README + `OPEN-CORE.md`). Phase ultérieure.

Benchmarks plus avancés à considérer en v2 (cités, non requis) : SECQUE, Fin-RATE,
FinAuditing (multi-documents), `agent-finance-reasoning` (Snorkel, angle tool-use).

## 7. Données (décision figée)

- **V1 : ne rien payer.** Public benchmarks + SEC EDGAR (gratuit, intrinsèquement
  point-in-time car filings datés).
- **Tradeoff dur acté** : pas-cher + global/FR + point-in-time = **2 sur 3**.
  - EDGAR : gratuit / US / point-in-time ✅ — couverture FR ❌.
  - Tiingo, Sharadar : point-in-time ✅ — US-centré.
  - EODHD : couverture Euronext/FR ✅ — point-in-time partiel.
  - FMP : large couverture — point-in-time « as reported ».
- **Décision fournisseur différée** à la phase **Enterprise** (privée), après un
  **test de couverture sur 5–10 tickers FR de référence**. Un univers « mix global »
  pousserait probablement vers **EODHD** (seul à couvrir Euronext proprement),
  complété par EDGAR pour le point-in-time US.

## 8. Critères de succès

- [x] Le RR (§4) couvre les 6 gates sans trou.
- [x] Le contrat dual-use distingue sans ambiguïté les deux lanes + la barrière
      de non-promotion.
- [x] Gates G-1..G-6 implémentés, déterministes, testés (suite verte).
- [x] La décision data (gratuit only) est explicitement tracée.

**Invariant permanent du cœur public** : aucune donnée réelle, aucun appel réseau
en suite de tests, aucun secret. Garanti par `tools/check_public_hygiene.sh` (CI + hook).

## 9. Hors-scope / différé

Ingestion de données réelles, modèle de production, RAG, backtest, fournisseurs
payants, UI, déploiement, génération de recommandation client réelle : relèvent de
l'édition enterprise privée (cf. `OPEN-CORE.md` + la feuille de route du README).

## 10. Questions ouvertes

1. **Tolérance de recalcul** (G-3) : ✅ **résolu** — bande relative ±0,5 %
   (`DEFAULT_REL_TOL = 0.005` dans `compute/metrics.py`, paramétrable).
2. **Granularité du `locator`** : ✅ **résolu** — `locator` libre (page/section/
   table/span) ; le cœur public valide la forme, la résolution réelle est enterprise.
3. **Schéma `lane_fields` MIF II** : ⏳ **ouvert** — périmètre minimal viable de la
   déclaration d'adéquation, à valider avec la conformité.
4. **Format de persistance du RR** : ✅ **résolu** — JSON plat (cf.
   `harness/schema/recommendation_record.schema.json` + export JSONL).
