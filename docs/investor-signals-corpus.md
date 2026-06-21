# Corpus de signaux investisseurs — Méthodologie et gouvernance

> **Périmètre open-core.** Ce document décrit la *méthodologie* du corpus.
> Les données réelles (enregistrements JSONL, paires d'évaluation, citations
> primaires) vivent dans `datasets/` — dossier **gitignored** et réservé à
> l'édition enterprise privée. Aucune donnée de marché réelle, aucun chiffre
> propriétaire ne figure ici. Voir [`OPEN-CORE.md`](../OPEN-CORE.md) pour la
> règle de frontière public / privé.

---

## 1. Objectif : des décisions historiques DOCUMENTÉES comme cas « gold »

Le corpus `datasets/investor-signals/` rassemble des **décisions d'investissement
historiques** de deux profils d'acteurs institutionnels — **Berkshire Hathaway**
et **BlackRock** — dont les rationels sont massivement publics et sourcables.

Ces décisions servent de **cas d'évaluation de référence** pour un LLM finance :
non pas pour lui apprendre à reproduire ces décisions, mais pour vérifier qu'il
peut en **reconnaître les structures**, en **citer les sources primaires** sans
les inventer, et en **dater les contextes** sans look-ahead.

### Pourquoi ces deux acteurs

| Acteur | Axe de signal | Nature du corpus |
|---|---|---|
| **Berkshire Hathaway** | Valorisation micro, moat, capital allocation | Décisions d'achat / vente concentrées sur titres individuels ; rationnel Buffett/Munger documenté dans les lettres annuelles, les 13F SEC et les transcripts d'AGM |
| **BlackRock** | Macro séculaire, M&A stratégique, sentiment institutionnel | Acquisitions d'entités entières, appels de marché Larry Fink (lettres CEO/actionnaires), posture de stewardship |

Les deux acteurs couvrent des **axes orthogonaux** du raisonnement financier :
la valorisation ligne-à-ligne (Berkshire) et la lecture de régimes macro / flux
institutionnels (BlackRock). Ensemble ils forment un corpus pédagogique équilibré
pour un modèle généraliste finance.

---

## 2. Doctrine anti-fabrication (FR-049 — non négociable)

Chaque record du corpus est soumis à la même doctrine que le harnais de
recevabilité de ce dépôt : **jamais inventer un chiffre, une citation ou une
date**. Un champ manquant vaut toujours mieux qu'un champ fabriqué.

Les quatre règles opérationnelles :

1. **Sources primaires en priorité** — lettres annuelles, dépôts SEC 13F / 8-K,
   transcripts AGM officiels, communiqués de presse. Les sources secondaires
   (presse de référence) sont acceptables avec attribution explicite mais ne
   peuvent pas fonder un `confidence: "high"`.

2. **Verbatim ou paraphrase explicite** — toute citation est soit un extrait
   littéral (`"stated_rationale": "citation verbatim…"`), soit clairement
   marquée approximée (`"~paraphrase"`). Il est interdit de présenter une
   reformulation comme une citation directe.

3. **Séparation rationnel déclaré / signaux de marché** — le champ
   `stated_rationale` contient ce que l'investisseur a *dit* ; le champ
   `market_signals` contient des conditions observables (valorisation,
   dislocation, taux, sentiment) *sans interpolation* entre les deux.

4. **Champs de traçabilité obligatoires** — chaque record porte :
   - `confidence` : `"high"` / `"medium"` / `"low"` (auto-déclaré, vérifié
     par validation adversariale)
   - `caveats` : tout ce qui est non-vérifié, contesté ou approximé
   - `outcome_known_as_of` : la date à laquelle le dénouement est décrit
     (anti-lookahead — un modèle évalué sur un contexte 2008 ne doit pas
     avoir accès aux faits postérieurs à 2008 au moment de l'évaluation)

Cette doctrine est le **miroir exact** de la philosophie du harnais : une analyse
peut être « plausible » et « juste dans les grandes lignes » tout en étant
**irrecevable** si elle n'est pas sourcée, datée et recalculable. Les mêmes
gates (G-1 sourcing, G-4 point-in-time) s'appliquent aux records du corpus
qu'aux outputs du LLM qu'ils servent à évaluer.

---

## 3. Pourquoi ce corpus reste hors du cœur public

Le framework de recevabilité (`harness/`, `tests/`, `harness/schema/`) est
**100 % public**. Les données réelles du corpus ne le sont pas — par choix
délibéré, pour trois raisons :

- **Redistribution** : les sources primaires (13F, lettres Berkshire, filing SEC,
  transcripts payants) appartiennent à leurs émetteurs ; les agréger dans un
  dataset public distribué soulève des questions de droits.
- **Qualité garantissable** : la confiance d'un record (`high` / `medium` / `low`)
  n'est valide que si la passe de validation adversariale est menée. Publier sans
  garantir la provenance équivaudrait à distribuer le défaut même qu'on cherche
  à détecter.
- **Modèle open-core** : conformément à [`OPEN-CORE.md`](../OPEN-CORE.md), *la
  mesure est publique, la réalité est privée*. Le harnais est un actif de
  légitimité fait pour être cité et audité ; les données d'entraînement et
  d'évaluation sont un actif opérationnel.

Ce document constitue la **spec publique** du corpus : structure, doctrine,
contraintes, mapping vers les gates. Les enregistrements réels vivent dans
`datasets/investor-signals/` (gitignored) et sont accessibles dans l'édition
enterprise.

---

## 4. Mapping vers les gates du harnais

Chaque record du corpus est conçu pour être directement exploitable dans les
gates G-1, G-2 et G-4.

### G-4 — Point-in-time (anti look-ahead)

C'est le gate le plus directement mobilisé. Chaque record a un `period` (la
période de la décision) et un `outcome_known_as_of` (la date jusqu'à laquelle
le dénouement est documenté). Un cas d'évaluation bien formé pose la question au
LLM **dans le contexte de l'époque** : les preuves disponibles sont celles qui
existaient à la date de la décision, sans information postérieure.

```
EvalItem:
  information_cutoff: "1990-12-31"    ← contexte de marché visible
  question: "Quelle décision BRK a-t-elle prise sur [secteur bancaire] en 1990
             et sur la base de quels signaux ?"
  attendu: rationnel daté + signaux de l'époque — JAMAIS données 1991+
```

Un modèle qui cite des faits postérieurs à `information_cutoff` **échoue G-4**,
exactement comme un RR qui présente une donnée datée après sa propre
`information_cutoff` est bloqué.

### G-1 — Sourcing

Chaque fait quantitatif cité dans un record porte une `rationale_sources` (liste
de documents primaires). Quand un LLM génère une analyse à partir d'un cas du
corpus, le harnais vérifie que chaque chiffre mis en avant cite une source
résolvable — pas seulement que la réponse « semble correcte ».

**Illustration de la distinction « juste mais irrecevable »** : un LLM qui
reproduit le bon ordre de grandeur d'une transaction historique *sans citer le
filing SEC ou la lettre primaire correspondante* est **bloqué sur G-1**, même si
le chiffre est exact. C'est la thèse centrale de ce dépôt : la recevabilité
précède l'exactitude.

### G-2 — Audit (reproductibilité)

Les paires d'évaluation générées à partir du corpus (`*-eval-pairs.jsonl`) sont
hachées canoniquement : le couple (question, réponse de référence) est stable et
reproductible. Un re-run doit produire le même verdict — pas de dérive aléatoire
introduite par le corpus lui-même.

---

## 5. Validation indépendante — la recevabilité se vérifie, elle ne se présume pas

La collecte des records est menée par des sous-agents (Sonnet, parallèle) dont
le mandat est la recherche sourcée avec doctrine anti-fabrication. Mais
l'**auto-certification est exclue** : le corpus produit est ensuite soumis à une
**passe de validation adversariale indépendante** (Antigravity / Codex selon
disponibilité).

Ce validateur :
- re-fetche les sources primaires citées (lettres annuelles, 13F, 8-K)
- vérifie la correspondance entre le record et la source
- **corrige les erreurs** détectées : attributions erronées, dates décalées,
  chiffres non conformes à la source primaire
- **confirme les drapeaux** auto-déclarés (`confidence: "medium"`) lorsque la
  source est secondaire ou le verbatim non vérifiable

Le résultat de cette passe figure dans `datasets/…/report/` (non public). Sa
valeur n'est pas seulement la correction des erreurs : c'est la **démonstration
empirique** que des agents bien outillés et bien instruits *produisent quand même
des erreurs*, et que la détection adversariale est nécessaire. Le corpus lui-même
est la preuve de la thèse du dépôt.

---

## 6. Schéma d'un record — structure et exemple fictif

### 6.1 Champs du schéma (version simplifiée)

```json
{
  "id": "string — identifiant unique du record (ex. ACTEUR-CIBLE-ANNEE)",
  "company": "string — société ou entité visée",
  "ticker": "string — ticker boursier si applicable",
  "action": "enum — BUY | ADD | TRIM | SELL | EXIT | ACQUIRE | HOLD_NOTABLE | STRATEGIC_PIVOT | MARKET_CALL | STEWARDSHIP_STANCE",
  "period": "string — période de la décision (ex. '1999-2001')",
  "approx_position": "string — exposition approximative, avec 'environ' si estimée",
  "decision_summary": "string — résumé neutre en 1-3 phrases",
  "stated_rationale": ["array — rationnel déclaré par l'investisseur, sourcé"],
  "rationale_sources": ["array — documents primaires correspondants"],
  "market_signals": [
    {
      "type": "string — voir vocabulaire signal_types ci-dessous",
      "signal": "string — description courte du signal observable",
      "evidence": "string — ce qui l'étaye"
    }
  ],
  "signal_types": ["array — tags du vocabulaire normalisé"],
  "outcome": "string — dénouement descriptif (pas de jugement prospectif)",
  "outcome_known_as_of": "string — date ISO (YYYY-MM)",
  "confidence": "enum — high | medium | low",
  "lessons_for_llm": "string — le pattern transférable que ce cas enseigne",
  "caveats": "string — tout ce qui est non-vérifié, approximé ou contesté"
}
```

**Vocabulaire `signal_types`** (tags normalisés, combinables) :

| Tag | Signification |
|---|---|
| `valuation` | Décote par rapport à la valeur intrinsèque |
| `crisis_dislocation` | Panique, vente forcée, scandale, récession |
| `moat` | Avantage concurrentiel durable / pricing power |
| `management` | Qualité / intégrité des dirigeants |
| `macro` | Taux, inflation, devise, cycle matière première |
| `sentiment` | Cycle de peur/avidité, biais comportemental |
| `capital_allocation` | Rachat, float, cash, coût d'opportunité |
| `mistake` | Erreur documentée — signal d'entraînement négatif |

### 6.2 Exemple entièrement fictif

L'exemple ci-dessous est **synthétique** : société, chiffres et citations sont
inventés pour illustrer le format. Toute ressemblance avec un record réel du
corpus est fortuite.

```json
{
  "id": "ACME-FICTEX-2003",
  "company": "FICTEX Industries SA",
  "ticker": "FIC",
  "action": "BUY",
  "period": "2003-2004",
  "approx_position": "environ 5 % du capital ; coût d'entrée estimé ~800 M€",
  "decision_summary": "ACME Capital a pris une position significative dans FICTEX après l'effondrement sectoriel de 2002-03, estimant que la société était la seule à disposer d'un actif de distribution impossible à répliquer à court terme.",
  "stated_rationale": [
    "« Le marché a vendu l'ensemble du secteur sans distinguer les acteurs qui avaient une franchise réelle de ceux qui n'en avaient pas » (Lettre annuelle ACME 2003, p. 4 — fictif).",
    "« La valeur de l'actif de distribution ne s'affiche pas au bilan ; c'est précisément ce que le marché a ignoré. »"
  ],
  "rationale_sources": [
    "Lettre annuelle ACME Capital 2003 (fictif)",
    "Interview fictive, Revue Finance Hebdo, mars 2004"
  ],
  "market_signals": [
    {
      "type": "crisis_dislocation",
      "signal": "Effondrement sectoriel indiscriminé 2002-03",
      "evidence": "Le secteur a perdu environ 60 % de sa capitalisation en 18 mois ; FICTEX a reculé autant que ses concurrents sans moat."
    },
    {
      "type": "valuation",
      "signal": "Décote extrême sur actif net réévalué",
      "evidence": "Cours à environ 0,4× la valeur estimée de l'actif de distribution — ratio non observable depuis la crise de 1992."
    },
    {
      "type": "moat",
      "signal": "Réseau de distribution exclusif sur 14 régions",
      "evidence": "FICTEX SA, rapport annuel 2002, p. 12 — réseau agréé par autorité sectorielle, renouvellement automatique 20 ans."
    }
  ],
  "signal_types": ["crisis_dislocation", "valuation", "moat"],
  "outcome": "Position cédée en 2007 après revalorisation complète. Retour total estimé ~3× sur la période (non confirmé par source primaire).",
  "outcome_known_as_of": "2026-06",
  "confidence": "low",
  "lessons_for_llm": "Distinguer une dislocation sectorielle indiscriminée d'une dégradation fondamentale réelle : l'actif immatériel (réseau, agrément) peut ne pas apparaître dans la vente forcée. Ce cas illustre le tag crisis_dislocation + moat combinés.",
  "caveats": "EXEMPLE ENTIÈREMENT FICTIF. Ne pas utiliser comme donnée. Société, chiffres et citations sont synthétiques."
}
```

> **Note de lecture** : dans le corpus réel, un record `confidence: "high"` est
> celui dont le rationnel déclaré est vérifiable sur une source primaire (lettre
> annuelle disponible, 13F correspondant). Un record `confidence: "medium"` a un
> rationnel plausible mais non vérifiable sur PDF (transcript non accessible) ou
> reposant sur des sources secondaires concordantes. Un record `confidence: "low"`
> est explicitement conjectural (rationnel inféré, non déclaré par l'investisseur).
> Les trois classes sont **utiles** : les records `low` servent précisément à
> entraîner le modèle à déclarer l'incertitude plutôt qu'à combler les lacunes.

---

## 7. Usage dans le harnais — comment un record devient un cas d'éval

```
record JSONL (corpus privé)
    │
    ▼
EvalItem (harness/eval_run.py)
    │  information_cutoff = period.start
    │  lane = "personal-research"
    │
    ▼
Candidat LLM (harness/candidates/)
    │  → produit un Recommendation Record (RR)
    │
    ▼
Gates G-1..G-6 (harness/gates/gates.py)
    │  G-1 : chaque chiffre cité par le LLM porte-t-il une source ?
    │  G-4 : aucune information postérieure à information_cutoff ?
    │  G-3 : les ratios avancés sont-ils recalculables depuis les données fournies ?
    │
    ▼
Verdict : ADMISSIBLE ou BLOCKED
```

Un LLM qui produit le bon rationnel historique **sans sourcer** échoue G-1.
Un LLM qui cite correctement mais avec une date postérieure au contexte échoue G-4.
Un LLM qui affiche un multiple cohérent avec un calcul erroné échoue G-3.
**La bonne réponse non traçable est bloquée.** C'est la définition de la
recevabilité dans ce dépôt.

---

## 8. Limites et ce qui reste hors-périmètre

- **Ce document n'est pas un conseil en investissement.** Les patterns
  identifiés dans le corpus (§2-3 des rapports internes) sont des structures
  pédagogiques pour l'évaluation d'un LLM, pas des signaux d'achat ou de vente.
- **Les records ne sont pas exhaustifs.** Le corpus couvre un échantillon
  documenté, pas l'intégralité des décisions des acteurs concernés.
- **La validation adversariale est continue.** Des erreurs subsistent dans tout
  corpus de cette nature ; le champ `caveats` et le niveau `confidence` en
  tracent honnêtement les limites. Utiliser ces records sans lire les `caveats`
  est une violation de la doctrine FR-049.
- **Brancher une vraie source de données en temps réel** (Bloomberg, Euronext,
  fournisseur de 13F temps-réel) est **hors-périmètre du dépôt public** :
  cela relève de l'édition enterprise privée.

---

*Voir aussi :*
- [`docs/usage-patrimoine-dossier-client.md`](usage-patrimoine-dossier-client.md) — cas synthétique CGP (MEDISYN SA) illustrant les gates G-1/G-3/G-4 en action
- [`harness/schema/recommendation_record.schema.json`](../harness/schema/recommendation_record.schema.json) — schéma machine-readable du Recommendation Record
- [`OPEN-CORE.md`](../OPEN-CORE.md) — règle de frontière public / privé
