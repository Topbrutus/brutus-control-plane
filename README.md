# Brutus Control Plane

Control plane de traçabilité, reproductibilité et promotion pour les systèmes de recherche Brutus.

## Principe

Le dépôt n'absorbe pas les moteurs scientifiques. Pell reste Pell, ASTRAEUM reste ASTRAEUM et Antmux reste Antmux. Ce dépôt orchestre les contrats entre eux.

> Aucun résultat ne monte d'un étage sans trace.

Chaîne canonique :

INGEST -> NORMALIZE -> COMPUTE -> MIRROR -> COUNTERTEST
       -> PRECISION -> PROOF -> TRACE -> RELEASE

## Cinq postes indépendants

1. PRIMARY — calcul principal.
2. MIRROR — implémentation indépendante.
3. COUNTERTEST — recherche active de rupture.
4. PRECISION — recalcul des zones sensibles.
5. ARBITER — vérifie les preuves de promotion; ne recalcule pas le résultat.

**Redondance != indépendance.** Deux workers utilisant le même algorithme ne constituent pas deux preuves indépendantes.

## Statuts

OBSERVATION -> CANDIDATE -> VERIFIED -> PROVEN -> RELEASED

Chaque transition exige les éléments déclarés dans `policies/promotion.json`.

## Identité d'un run

Un run conserve au minimum le dépôt et commit source, les paramètres, la précision, les algorithmes, les empreintes SHA-256, les invariants, les contre-tests et les traces.

Les erreurs reproductibles portent l'événement public `TRACE_CRITIQUE_REPRODUCTIBLE`.

Alias interne historique : `LA_MACHINE_TE_FAIT_CHIER`.

## Démarrage

`python -m unittest discover -s tests -v`
`python src/brutus_control_plane.py validate examples/job.example.json`
`python src/brutus_control_plane.py fingerprint examples/job.example.json`

Version initiale : **0.1.0**.

## Premier run ASTRAEUM vérifié

`BRUTUS-RUN://PELL/2026-09-25/000001` est le premier run Brutus-Pell exécuté via l'adaptateur ASTRAEUM à cinq postes.

- X = 2,000,000; Q = 199; précision = 70 chiffres.
- PRIMARY : agrégation de motifs + polynômes élémentaires.
- MIRROR : parcours ligne par ligne + identités de Newton + récurrence logarithmique.
- COUNTERTEST : certificat entier/rationnel de B(4)<1 et des facteurs pairwise.
- PRECISION : comparaison Decimal / float64.
- ARBITER : comparaison des traces sans recalcul du résultat principal.

Statut final du control plane : `VERIFIED`.
Le statut `PROVEN` reste réservé à une preuve dont la portée et les limitations sont explicitement déclarées.
