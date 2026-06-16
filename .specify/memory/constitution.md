# Constitution — finance-research-eval

> Document directeur. Toute spec, tout composant du dépôt doit s'y conformer.
> Statut : **cadre actif** — le harnais de recevabilité est implémenté et public.

## Question centrale (le point de départ, validé)

> **« Qu'est-ce qu'une recommandation financière justifiable, traçable et vérifiable ? »**

Le projet **n'optimise pas un modèle**. Il définit d'abord une **mesure de
recevabilité** d'une analyse financière, puis ne construit que ce qui passe cette
mesure. Le modèle est un détail d'implémentation tardif, **gated** par le harnais.

Corollaire : la valeur ne vient **pas** du modèle (l'efficience de marché érode
l'edge LLM sur les large caps couvertes) mais de **(a) la qualité/fraîcheur des
données** et **(b) la discipline de vérification**. Ce dépôt n'industrialise que (b).

## Principes (P-1 .. P-7)

### P-1 — Les faits ne vivent pas dans les poids
Tout chiffre provient d'un document source, pas de la mémoire d'un modèle. Le LLM
**raisonne et rédige** ; il ne **produit jamais** une valeur numérique faisant foi.
Les nombres sont extraits (avec localisateur source) ou recalculés (moteur
déterministe), jamais « générés ».

### P-2 — Toute affirmation quantitative est sourcée
Aucun chiffre sans localisateur résolvable (document + emplacement + date `as_of`).
Une affirmation non sourçable est **rejetée**, pas « atténuée ». → Gate **G-1**.

### P-3 — Tout calcul est indépendamment vérifiable
Chaque ratio / valorisation est recalculé par un moteur déterministe **indépendant
du LLM**. Si le nombre émis par le LLM diverge du recalcul → **échec**. C'est le
« vérificateur financier », analogue d'un vérificateur déterministe (le LLM ne valide jamais
son propre verdict). → Gate **G-3**.

### P-4 — Conscience point-in-time
Toute analyse déclare une **date de coupure d'information**. Aucune preuve datée
**après** la coupure n'est admise (anti look-ahead). Une preuve sans `as_of` est
inadmissible. La performance affirmée sans point-in-time honnête est de
l'astrologie. → Gate **G-4**.

### P-5 — Traçabilité immuable (audit-trail)
Toute analyse est un enregistrement **horodaté, reproductible et immuable**
(hash des entrées, journal des transformations). On doit pouvoir rejouer le
raisonnement et retrouver chaque chiffre. → Gate **G-2**.

### P-6 — Cloisonnement dual-use strict
Deux lanes, jamais mélangées : **personal-research** (capital propre, libre) et
**client-mifid** (relevant de MiFID II / AMF, encadré). Une analyse personnelle
**n'est jamais promue automatiquement** en recommandation client : re-validation
humaine explicite obligatoire. Le lane client exige des champs supplémentaires
(adéquation, risques, conflits) et **bloque** (ne dégrade pas) toute sortie non
sourcée ou non vérifiable. → Gates **G-5**, **G-6**.

### P-7 — Décision-support, jamais exécution
Le système produit une **thèse + un dossier sourcé**. La décision d'achat/vente
appartient à l'humain. Aucun ordre, aucun mouvement de fonds, jamais.

## Hiérarchie de blocage

```
Recevabilité (gates) ─► Exactitude (vs gold) ─► Utilité (thèse)
        │
        └─ si un gate de sécurité échoue (G-1, G-3, G-4, G-5), la sortie est
           BLOQUÉE — l'exactitude et l'utilité ne la rattrapent jamais.
```

## Avertissements

- **Pas un conseil juridique.** Le cadre `client-mifid` est une _proposition
  d'ingénierie_ ; il doit être validé par la conformité / un juriste avant tout
  usage réel relevant de MiFID II (Directive 2014/65/UE) ou du règlement AMF.
- **Pas un conseil en investissement.** Ce dépôt décrit une méthode de mesure.
- **Périmètre public.** Ces principes gouvernent le dépôt public (mesure + interfaces
  + fixtures synthétiques) ; la donnée réelle et les connecteurs vivent dans l'édition
  enterprise privée.
