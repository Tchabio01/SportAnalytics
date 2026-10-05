# ⚽ SportAnalytics Pro

Moteur d'analyse sportive pour Termux + Telegram.

## Installation

```bash
pkg update
pkg install python git
cd SportAnalytics
python -m pip install -r requirements.txt
cp .env.example .env
```

Éditer `.env` et renseigner le token du bot Telegram.

## Test local

```bash
python main.py --demo
```

Le mode `--demo` est volontairement identifié comme DEMO. Il ne représente pas des matchs réels.

## Telegram

```bash
python main.py --telegram
```

Commandes :

- `/start`
- `/help`
- `/today`
- `/analyse`

## Données réelles

Le projet sépare volontairement le moteur d'analyse des fournisseurs de données. Avant d'utiliser des données réelles, renseigner une API sportive autorisée et implémenter son connecteur dans `sources/`.

Ne pas scraper des sites en contournant leurs protections ou leurs conditions d'utilisation.

## Sécurité

- Ne jamais publier `.env`.
- Ne jamais mettre le token Telegram dans Git.
- Les prédictions sont statistiques et ne constituent pas des garanties.
