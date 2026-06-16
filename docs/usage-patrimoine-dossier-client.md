# Utiliser le harnais pour un dossier client fictif (cas patrimoine)

> **Cas 100 % synthétique.** Aucune donnée réelle, aucun ISIN réel, aucun
> appel réseau, aucun modèle branché. Ce guide montre *comment un conseiller en
> gestion de patrimoine (CGP) raisonnerait avec le harnais* — pas comment
> produire un conseil réel. Voir [`SECURITY.md`](../SECURITY.md) (usage
> responsable) et [`OPEN-CORE.md`](../OPEN-CORE.md) (frontière public/privé).

## À quelle question ce cas répond

Un CGP veut joindre à un dossier client une **note de recherche générale**
(`reco_nature = general-research`) sur une société cotée. La question n'est pas
« le modèle a-t-il l'air convaincant ? » mais :

> **« Cette note est-elle *recevable* — sourcée, recalculable, datée,
> cloisonnée — avant même qu'on la lise ? »**

Le harnais répond par un **verdict déterministe** (`ADMISSIBLE` / `BLOCKED`),
indépendant du modèle qui a rédigé la note (constitution P-1/P-3 : le juge ne
fait jamais confiance au chiffre de la partie jugée).

## Le cas : MEDISYN SA (synthétique)

`harness/fixtures/cases_patrimoine.py` fabrique une société pharma mid-cap
fictive (ticker `MDSY`, ISIN `XX0000000001`) et **deux notes** sur la lane
`client-mifid` :

| Note | EV/EBITDA annoncé par le modèle | EV/EBITDA recalculé | Verdict |
|---|---|---|---|
| `build_patrimoine_admissible()` | 9.0× | 9.0× (2160/240) | **ADMISSIBLE** |
| `build_patrimoine_rejected()`  | 6.5× | 9.0× (2160/240) | **BLOCKED** |

Les deux notes sont **identiques** sauf le multiple de tête. La note rejetée
gonfle la décote (« 6.5× = vraie affaire ») alors que les chiffres sourcés
donnent 9.0×. C'est exactement le faux-positif qu'un dossier client doit ne
**jamais** laisser passer.

## Étape par étape

### 1. Produire et évaluer les deux notes

```bash
python3 -c "
from harness.fixtures.cases_patrimoine import run_patrimoine_cases
for label, ev, aug in run_patrimoine_cases():
    print(f'{label:11s} -> {ev.verdict}')
    for g in ev.gate_results:
        flag = '' if g.status == 'PASS' else f'  <-- {g.reason}'
        print(f'    {g.gate_id} {g.status}{flag}')
"
```

Sortie attendue :

```
admissible  -> ADMISSIBLE
    G-1 PASS
    G-2 PASS
    G-3 PASS
    G-4 PASS
    G-5 PASS
    G-6 PASS
rejected    -> BLOCKED
    G-1 PASS
    G-2 PASS
    G-3 FAIL  <-- ev_ebitda: model=6.5 vs recomputed=9.0
    G-4 PASS
    G-5 FAIL  <-- client record fails sourcing/verification -> blocked, not degraded
    G-6 PASS
```

### 2. Lire le verdict

- **`ADMISSIBLE`** ≠ « bon investissement ». Cela veut dire : la note est
  *recevable* (tout est sourcé, recalculable, daté, cloisonné). Le jugement
  d'opportunité reste celui du CGP — le harnais ne donne **pas** de signal
  d'achat.
- **`BLOCKED`** = la note **ne doit pas être émise** au client en l'état. Sur la
  lane `client-mifid`, un échec G-3 (recalcul) est bloquant (`BLOCK`) et G-5
  propage le blocage : on **refuse**, on ne « dégrade » pas en avertissement.

### 3. Comprendre pourquoi la note est bloquée

Le moteur de recalcul (`harness/compute/metrics.py`) recompose chaque ratio à
partir des **evidence sourcées**, puis compare au chiffre proposé par le modèle
avec une tolérance relative de 0,5 %. Ici :

```
ev_ebitda = ev / ebitda = 2160 / 240 = 9.0   (recalcul déterministe)
modèle    = 6.5                              (annoncé dans la note)
9.0 vs 6.5  ->  écart > tolérance  ->  G-3 FAIL
```

La note rejetée échoue **uniquement** sur G-3/G-5 : les autres gates passent.
La défaillance est *isolée et nommée* — le CGP sait précisément quel chiffre
corriger (ou quel document re-sourcer) avant de re-soumettre.

## Adapter à votre propre dossier fictif

1. Copiez `cases_patrimoine.py` et remplacez les constantes `_EVIDENCE` par vos
   chiffres synthétiques (gardez un ISIN `XX…`, un filing fabriqué, des dates
   `as_of <= information_cutoff`).
2. Déclarez `reco_nature = "general-research"` pour une note de recherche
   générale (pas de bloc *suitability* requis), ou `"personalised-advice"` pour
   un conseil personnalisé (le bloc *suitability* devient alors obligatoire,
   gate G-6 — voir `harness/fixtures/cases_worked.py` pour la lane personnelle).
3. Lancez `gates.evaluate(rr)` et lisez le verdict + les raisons par gate.

> **Rappel de périmètre.** Brancher une vraie source (EDGAR, Euronext, un
> fournisseur de données) ou un vrai modèle reste **interdit** tant qu'un GO de
> phase distinct n'est pas donné (voir la liste « Périmètre encore verrouillé »
> du `README.md`). Ce guide est purement local et synthétique.

## Vérifier que le cas tient

```bash
python3 -m pytest tests/test_cases_patrimoine.py -q
```
