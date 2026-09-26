# ANTMUX / BRUTUS LIVE — mode d'emploi

Prototype local de vitrine temps réel pour le pipeline Z-stereo ninefold.

## Lancer

Depuis la racine `brutus-control-plane` :

```powershell
python live\live_server.py
```

Ouvrir ensuite :

`http://127.0.0.1:8872`

## Commandes

- **RUN** : déroule automatiquement les 7 étages.
- **PAUSE** : arrête l'animation sans perdre l'état.
- **STEP** : avance exactement d'un étage.
- **RESET** : revient à l'entrée.
- **IDENTITY / CROSS** : compare routage propre et croisé.
- **Test F1 — k** : calcule la vraie relation Pell F1 épinglée.

Le tableau interroge `/api/state` toutes les 250 ms.
Le prototype reste local et n'expose aucun secret ni token.

## Voir Astra travailler

Le wrapper `trace_command.py` envoie les étapes d'une vraie commande au panneau
`ACTIVITÉ ASTRA / COMMANDES RÉELLES`.

Exemple :

```powershell
python live\trace_command.py --label "ASTRA - tests Z-stereo" -- python -m unittest discover -s tests -p test_z_stereo_ninefold.py -v
```

Les événements `COMMAND_START`, `OUTPUT` et `COMMAND_END` apparaissent dans la
vitrine pendant l'exécution. Les motifs évidents de token/mot de passe sont masqués,
mais cette version reste **locale seulement**. Ne pas l'exposer publiquement avant
l'audit de filtrage et la séparation explicite du flux public.

## Mode PUBLIC SAFE

Le mode public est séparé du panneau interne.

- Interne : `http://127.0.0.1:8872`
- Public lecture seule : `http://127.0.0.1:8873`

Lancer le panneau public :

```powershell
python live\public_server.py
```

Le serveur public ne transmet que `/api/public-state`, filtré par le serveur interne.
Il ne publie pas l'entrée brute, le routage interne, les commandes brutes, les chemins
locaux, les URLs, les adresses IP, les courriels, les secrets évidents ni les identifiants
hexadécimaux longs. Les sorties de tests sont résumées en événements publics.

Les méthodes POST/PUT/DELETE du serveur public retournent `405`.
Pour un futur déploiement nginx, n'exposer que le port public `8873`; garder `8872`
sur loopback et inaccessible depuis Internet.
