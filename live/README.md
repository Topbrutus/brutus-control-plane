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
