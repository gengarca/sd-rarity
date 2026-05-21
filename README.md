# BallsDex V3 Rarity Package

A rarity list package for **BallsDex V3**. Players can view the rarity list of collectibles and their tiers.

## Commands

| Command | Description |
|---|---|
| `/balls rarity` | Show the rarity list of the collectibles |
| `/balls rarity countryball` | Show the rarity tier for a specific countryball |
| `/balls rarity tier` | Show all collectibles in a specific rarity tier |
| `/balls rarity specials:True` | Show enabled specials and their spawn chances |
| `/balls rarity special` | Show the spawn chance for a specific special |

## Installation

### 1 — Configure extra.toml

**If the file doesn't exist:** Create a new file `extra.toml` in your `config` folder under the BallsDex directory.

**If you already have other packages installed:** Simply add the following configuration to your existing `extra.toml` file. Each package is defined by a `[[ballsdex.packages]]` section, so you can have multiple packages installed.

Add the following configuration:

```toml
[[ballsdex.packages]]
location = "git+https://github.com/hiboman/BallsDex-Rarity-Pack.git@0.0.3#master"
path = "rarity"
enabled = true
```

**Example of multiple packages:**

```toml
# First package
[[ballsdex.packages]]
location = "git+https://github.com/example/other-package.git@0.0.1#master"
path = "other"
enabled = true

# Rarity Package
[[ballsdex.packages]]
location = "git+https://github.com/hiboman/BallsDex-Rarity-Pack.git@0.0.3#master"
path = "rarity"
enabled = true
```

### 2 — Rebuild and start the bot

```bash
docker compose build
docker compose up -d
```

This will install the package and start the bot.
