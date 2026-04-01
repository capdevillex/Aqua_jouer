# \# 🌊 Aqua\_jouer

# 

# > \*\*Gestionnaire de playlist Steam intelligent\*\* — fini l'heure perdue à choisir à quoi jouer.

# 

# Aqua\_jouer importe votre bibliothèque Steam et vous propose le jeu suivant selon vos envies du moment, grâce à un système de priorité dynamique.

# 

# \---

# 

# \## Fonctionnalités

# 

# \- \*\*Import Steam automatique\*\* au démarrage via l'API Steam

# \- \*\*Système de priorité\*\* (heap) — chaque jeu a un score qui évolue selon vos sessions

# \- \*\*Humeur du soir\*\* — un slider pour choisir entre mode confort (favoris) et mode exploration (découverte)

# \- \*\*Accepter / Refuser\*\* une suggestion avec impact sur les scores

# \- \*\*Lancement direct\*\* via `steam://run/` en un clic

# \- \*\*Notes de session\*\* — écrivez où vous en êtes dans chaque jeu

# \- \*\*Archivage\*\* — marquez un jeu comme Terminé ou Abandonné

# \- \*\*Historique complet\*\* des sessions avec durées prévues

# \- \*\*Bilingue\*\* Français / English

# \- \*\*Dark mode\*\* inspiré de l'interface Steam

# 

# \---

# 

# \## Installation

# 

# \### Prérequis

# \- Python 3.10 ou supérieur → \[python.org](https://www.python.org/downloads/)

# 

# \### Étapes

# 

# ```bash

# \# 1. Cloner le repo

# git clone https://github.com/VOTRE\_PSEUDO/aqua\_jouer.git

# cd aqua\_jouer

# 

# \# 2. Installer les dépendances

# pip install -r requirements.txt

# 

# \# 3. Lancer l'application

# python aqua\_jouer.pyw

# ```

# 

# Ou double-cliquez sur \*\*launch.bat\*\* sous Windows.

# 

# \---

# 

# \## Configuration Steam

# 

# Au premier lancement, cliquez sur \*\*Paramètres\*\* et renseignez :

# 

# \*\*Clé API Steam\*\*

# 1\. Rendez-vous sur \[steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey)

# 2\. Enregistrez un domaine (ex: `localhost`)

# 3\. Copiez la clé générée

# 

# \*\*SteamID64\*\*

# 1\. Rendez-vous sur \[steamid.io](https://steamid.io)

# 2\. Entrez votre pseudo Steam

# 3\. Copiez le champ \*\*steamID64\*\*

# 

# > ⚠️ Votre profil Steam doit être en \*\*public\*\* pour que l'import fonctionne.

# 

# \---

# 

# \## Dépendances

# 

# ```

# PyQt6

# requests

# ```

# 

# \---

# 

# \## Licence

# 

# MIT — libre d'utilisation et de modification.



