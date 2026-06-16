# Contrat dual-use — personal-research / client-mifid

> Définit deux lanes et leur cloisonnement (implémenté : G-6 + `lane_fields`). Le volet
> `client-mifid` est une **proposition d'ingénierie** : il doit être **validé par la
> conformité / un juriste** avant tout usage réel. **Ni conseil en investissement, ni
> conseil juridique.**

## Principe (P-6)

Un seul moteur, **deux lanes jamais mélangées**. Le cloisonnement se fait par
**gate d'évaluation** (G-6), pas par deux codebases. Le `lane` est un champ
**déclaré** du RR ; il conditionne les champs requis et la sévérité du blocage.

```
                 ┌─────────────────────────┐
                 │   Moteur d'analyse       │  (commun)
                 └───────────┬─────────────┘
            lane=personal    │    lane=client-mifid
                 ▼           │           ▼
   ┌───────────────────┐    │   ┌────────────────────────────┐
   │ personal-research │    │   │ client-mifid               │
   │ usage: capital     │   │   │ usage: relevant MiFID II   │
   │ propre (PEA/CTO)   │   │   │ / AMF                      │
   └─────────┬─────────┘    │   └─────────────┬──────────────┘
             │   ┌──────────┴──────────┐      │
             └──►│  BARRIÈRE DE         │◄─────┘
                 │  NON-PROMOTION (P-6) │
                 │  re-validation       │
                 │  humaine explicite   │
                 └──────────────────────┘
```

## Lane A — `personal-research`

| | |
|---|---|
| **Usage** | Analyse pour le **capital propre** de l'utilisateur (PEA / CTO). |
| **Cadre** | Hors champ du conseil réglementé (on n'analyse pas pour autrui). |
| **Champs requis** | RR standard (claims sourcées + computations recalculées + cutoff). |
| **Gates appliqués** | G-1..G-4, G-6 (déclaration de lane). |
| **Sévérité** | Un RR non recevable est **signalé** ; l'utilisateur reste seul juge et seul responsable de sa décision. |
| **Sortie** | Thèse + dossier sourcé. **Jamais un ordre** (P-7). |

> Lane A reste soumise à P-1..P-5 : même en usage perso, on ne tolère pas un chiffre
> halluciné ou un calcul non vérifié — c'est le but du dépôt.

## Lane B — `client-mifid`

| | |
|---|---|
| **Usage** | Analyse **susceptible de nourrir une recommandation à un client** (activité CGP). |
| **Cadre** | MiFID II (Dir. 2014/65/UE) + règlement AMF. ⚠️ à **valider conformité**. |
| **Champs requis (`lane_fields`)** | voir ci-dessous. |
| **Gates appliqués** | G-1..G-6, avec **blocage dur** (G-5). |
| **Sévérité** | Un RR échouant G-1 (sourcing) ou G-3 (recalcul) est **BLOCKED** : il **ne peut pas** être émis comme recommandation. Pas de dégradé. |
| **Sortie** | Aucune recommandation tant que le dossier n'est pas sourcé, recalculé, daté **et** complété des champs MIF II. |

### `lane_fields` (périmètre proposé — à valider)

Distinguer d'abord la nature de la sortie :

- **Recommandation personnalisée** (conseil réglementé) → exige une évaluation
  d'**adéquation** :
  - connaissance & expérience du client ;
  - situation financière, **capacité à subir des pertes** ;
  - objectifs d'investissement, **horizon**, tolérance au risque ;
  - **déclaration d'adéquation** (suitability report) justifiant que la reco
    convient au profil ;
  - **divulgation des conflits d'intérêts**.
- **Recommandation d'investissement générale / recherche** (non personnalisée) →
  relève plutôt de MAR (Rég. 596/2014) art. 20 + Rég. délégué 2016/958 :
  présentation **objective**, mention des sources, **disclosure** des intérêts,
  étiquetage clair « recherche, non personnalisée ».

> Le RR `client-mifid` doit porter un champ `reco_nature` ∈
> {`personalised-advice`, `general-research`} qui sélectionne le sous-ensemble de
> champs obligatoires. Le périmètre minimal viable est une **question ouverte**
> (cf. `spec.md` §10) à trancher avec la conformité.

### Champ commun obligatoire (toute Lane B)

- `disclaimers` : étiquetage de la nature, mention « ne constitue pas une
  garantie de performance », sources, conflits.
- `audit_trail` complet (G-2) — exigible en cas de contrôle.

## Barrière de non-promotion (P-6, FR-008)

- Un RR `personal-research` **n'est jamais converti automatiquement** en
  `client-mifid`.
- La promotion exige une **action humaine explicite** : ré-ouverture du dossier,
  complétion des `lane_fields`, **re-passage de tous les gates en mode client**
  (blocage dur), et validation humaine tracée.
- Techniquement : changer `lane` **invalide** `gate_results` et `verdict` ; le RR
  redevient `non évalué` jusqu'à un nouveau run complet en Lane B.

## Ce que le contrat **n'autorise pas** (rappel)

- ❌ Émettre une reco client non sourcée / non recalculée (G-5).
- ❌ Promouvoir du perso en client sans re-validation (P-6).
- ❌ Passer un ordre, mouvementer des fonds (P-7).
- ❌ Présenter une sortie comme « conseil » sans l'étiquetage et les champs requis.
- ❌ Tout usage avec des données client réelles sans la re-validation humaine décrite ci-dessus.
