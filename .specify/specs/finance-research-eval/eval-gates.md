# Gates d'évaluation — jour 0 (G-1 .. G-6)

> **Design-only.** Spécifie les gates ; aucun n'est implémenté en Phase 0.
> Tous sont **déterministes** et **indépendants du LLM** (P-1, P-3). Ils sont
> appliqués à un *Recommendation Record* (RR, cf. spec §4).

## Vue d'ensemble

| Gate | Nom | FR | Principe | Sévérité Lane A | Sévérité Lane B |
|---|---|---|---|---|---|
| **G-1** | Sourcing obligatoire | FR-002 | tout chiffre cite un span résolvable | signalé | **BLOCK** |
| **G-2** | Audit-trail | FR-005 | RR immuable, reproductible | requis | requis |
| **G-3** | Calcul vérifiable | FR-003 | recalcul indépendant du LLM | signalé | **BLOCK** |
| **G-4** | Conscience point-in-time | FR-004 | aucune preuve post-cutoff | requis | **BLOCK** |
| **G-5** | Refus reco non sourcée | FR-007 | bloque, ne dégrade pas | n/a | **BLOCK** |
| **G-6** | Cloisonnement | FR-006/008 | lane déclaré, non-promotion | requis | requis |

« BLOCK » = la sortie **ne peut pas** être émise comme recommandation client.

---

## G-1 — Sourcing obligatoire

**Invariant.** Toute `claim` de type `quantitative` ou `valuation` porte ≥1
`evidence` dont le `locator` est **résolvable** (pointe vers un emplacement réel
d'un `source_doc` réel) et qui porte un `as_of`.

**Entrée.** `claims[].evidence[]` du RR.
**PASS.** Chaque affirmation chiffrée a au moins un localisateur résolvable + `as_of`.
**FAIL.** Au moins un chiffre sans source / avec localisateur non résolvable.

**Mesure (design).** Le moteur vérifie l'existence et la cohérence formelle du
localisateur (structure + correspondance au document déclaré). _La résolution
réelle contre un document n'a lieu qu'en phase données (P2+), jamais en P0._

**Rationale.** Un chiffre non sourçable = hallucination potentielle. C'est le
risque n°1 (le LLM invente un EPS, on achète sur du vent). → P-2.

**Exemple.**
- ✅ « CA 2024 = 1,2 Md€ » → `{source_doc: URD-2024, locator: §4.1/table 3/ligne CA, as_of: 2025-03-31}`
- ❌ « CA 2024 = 1,2 Md€ » → aucune `evidence` → **FAIL**.

---

## G-2 — Audit-trail

**Invariant.** Le RR est **immuable, horodaté, reproductible** : hash des entrées,
journal des transformations, identifiants stables. On peut **rejouer** l'analyse
et retrouver chaque chiffre.

**PASS.** `audit_trail` présent, hash d'entrée stable, transformations journalisées.
**FAIL.** Trail manquant, non reproductible, ou RR muté sans nouvelle version.

**Rationale.** Exigible en cas de contrôle (surtout Lane B) ; condition de
confiance pour tout le reste. → P-5.

---

## G-3 — Calcul vérifiable (le « vérificateur financier »)

**Invariant.** Chaque `computation` (ratio, valorisation) est **recalculée par le
moteur déterministe `compute/`**, indépendamment du LLM. `llm_value` est comparée
à `recomputed_value` ; au-delà de la tolérance → divergence.

**Entrée.** `claims[].computations[]` + `evidence[]` (les inputs).
**PASS.** Pour chaque computation, `agree == true` (dans la tolérance).
**FAIL.** Au moins une divergence hors tolérance — ou une computation que le moteur
ne peut **pas** reproduire à partir des inputs déclarés.

**Mesure (design).** Le moteur applique la `formula` aux `inputs[]` (référencés
dans `evidence[]`) et compare. Le LLM **ne valide jamais son propre nombre** — c'est
le cœur du gate. Analogue direct d'un vérificateur déterministe (séparation juge/jugé).

**Tolérance.** Question ouverte (spec §10) : bande relative paramétrable (ex.
±0,5 %) pour absorber les arrondis de présentation. À figer en P1.

**Rationale.** Le LLM **raisonne**, il ne **calcule pas** le verdict. → P-1, P-3.

**Exemple.**
- LLM : EV/EBITDA = 8,0. Moteur recalcule depuis EV et EBITDA sourcés = 8,02 → **PASS** (tolérance).
- LLM : EV/EBITDA = 6,0. Moteur = 9,1 → **FAIL** → Lane B : **BLOCKED**.

---

## G-4 — Conscience point-in-time

**Invariant.** Le RR déclare `information_cutoff`. Aucune `evidence.as_of` n'est
postérieure au cutoff (anti look-ahead). Toute `evidence` sans `as_of` est
inadmissible.

**PASS.** `∀ evidence : as_of ≤ information_cutoff` et `as_of` présent partout.
**FAIL.** Une preuve postérieure au cutoff, ou un `as_of` manquant.

**Rationale.** Horizon 1–5 ans ⇒ une thèse ne doit utiliser **que** ce qu'on
savait à la date de coupure. Sans cela, tout futur backtest est biaisé (look-ahead)
et toute « performance » affichée est fictive. → P-4.

**Note.** En P0–P1 (sans données), G-4 vérifie la **présence et la cohérence
formelle** des dates. La vérification contre des sources réelles arrive avec
l'ingestion point-in-time (P5).

---

## G-5 — Refus de recommandation client non sourcée

**Invariant (Lane B uniquement).** Un RR `client-mifid` qui échoue **G-1** ou
**G-3** est **BLOCKED** : il ne peut pas être émis comme recommandation. On
**bloque**, on ne **dégrade pas** en « avis prudent ».

**PASS.** Lane B + G-1 PASS + G-3 PASS (+ G-4).
**FAIL → BLOCKED.** Lane B + (G-1 FAIL ∨ G-3 FAIL).

**Rationale.** Une reco client doit être justifiable et vérifiable, sinon elle
n'existe pas. C'est la traduction opérationnelle de l'exigence d'adéquation /
présentation objective. → P-6, FR-007.

> Ce gate ne s'applique pas à Lane A (perso), où le founder reste seul juge — mais
> G-1/G-3 y restent **signalés**.

---

## G-6 — Cloisonnement personnel / MIF II

**Invariant.**
1. `lane` est **déclaré** sur tout RR.
2. `client-mifid` exige les `lane_fields` (cf. contrat dual-use).
3. **Aucune promotion automatique** `personal-research` → `client-mifid` :
   changer `lane` **invalide** `gate_results`/`verdict` et force un re-run complet
   en mode client + validation humaine tracée.

**PASS.** Lane déclaré + (si Lane B) `lane_fields` complets + pas de promotion
implicite.
**FAIL.** Lane absent, champs MIF II manquants en Lane B, ou RR perso ré-étiqueté
client sans re-évaluation.

**Rationale.** Le payeur n'est pas l'observateur ; l'usage perso et l'usage
réglementé ne se mélangent jamais. → P-6, FR-006/008.

---

## Lecture agrégée (rappel de hiérarchie)

```
Recevabilité (G-1..G-6)  PRIME SUR  Exactitude (vs gold)  PRIME SUR  Utilité (thèse)
```

Un candidat **exact mais peu recevable** (devine juste, ne sait pas le justifier)
est **mauvais** pour cet usage. Le rôle du harnais est précisément de **rendre ce
défaut mesurable**, là où un score d'exactitude seul le masquerait.

> Aucun gate n'est exécuté en Phase 0. Ce fichier en fige la **définition**.
