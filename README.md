# YouTube Downloader

Outil desktop pour telecharger des videos, playlists et chaines YouTube completes.

---

## Fonctionnalites

- **3 modes de telechargement** : video(s) unique(s), playlist(s), chaine complete
- **Import automatique** des playlists depuis un lien de chaine YouTube
- **Choix de la qualite** : 4K, 1080p, 720p, 480p, 360p
- **Audio uniquement** : extraction en MP3, WAV, FLAC ou AAC
- **Sous-titres** : telechargement automatique avec choix de la langue
- **Plage de videos** : telecharger uniquement une partie d'une playlist (ex: videos 10 a 50)
- **Telechargement accelere** : aria2c (16 connexions par fichier)
- **Telechargement parallele** : plusieurs playlists en meme temps
- **Reprise automatique** : arretez et reprenez sans rien perdre
- **Interface graphique** sombre et intuitive

---

## Installation

### Methode 1 : Installateur automatique (recommande)

1. Double-cliquer sur **`installer.bat`**
2. Attendre la fin de l'installation
3. Double-cliquer sur **`YouTube Playlist Downloader.exe`**

### Methode 2 : Installation manuelle

#### Prerequis

| Logiciel | Installation |
|----------|-------------|
| [Python 3.10+](https://www.python.org/downloads/) | `winget install Python.Python.3.12` |
| [Node.js](https://nodejs.org/) | `winget install OpenJS.NodeJS` |
| [FFmpeg](https://ffmpeg.org/) | `winget install Gyan.FFmpeg` |
| [aria2c](https://aria2.github.io/) | `winget install aria2.aria2` |

#### Bibliotheque Python

```bash
pip install yt-dlp
```

#### Lancement

```bash
python download_playlist.py
```

---

## Guide d'utilisation

### 1. Configurer l'authentification (obligatoire)

YouTube bloque les telechargements sans authentification. Vous devez fournir un fichier **cookies.txt**.

#### Exporter les cookies depuis votre navigateur

1. Installer l'extension **[Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)** sur Chrome/Edge
2. Aller sur [youtube.com](https://www.youtube.com) et verifier que vous etes **connecte**
3. Cliquer sur l'extension > **Export**
4. Un fichier `cookies.txt` est telecharge

#### Charger dans l'application

1. Selectionner **"Fichier cookies.txt (recommande)"**
2. Cliquer **"Choisir le fichier"**
3. Selectionner le `cookies.txt` telecharge

> **Note** : Le fichier cookies.txt expire apres quelques jours/semaines. Si les telechargements echouent, re-exportez un nouveau fichier.

> **Securite** : Ne partagez JAMAIS votre fichier cookies.txt. Il donne acces a votre compte Google.

---

### 2. Telecharger des videos

**Mode : Video(s)**

1. Selectionner le mode **"Video(s)"**
2. Coller un ou plusieurs liens de videos YouTube (un par ligne) :
   ```
   https://www.youtube.com/watch?v=xxxxxxxxxx
   https://www.youtube.com/watch?v=yyyyyyyyyy
   ```
3. Choisir la qualite
4. Cliquer **"Telecharger"**

Les videos sont enregistrees dans le dossier de destination.

---

### 3. Telecharger des playlists

**Mode : Playlist(s)**

1. Selectionner le mode **"Playlist(s)"**
2. Coller un ou plusieurs liens de playlists :
   ```
   https://www.youtube.com/playlist?list=PLxxxxxxxxxx
   https://www.youtube.com/playlist?list=PLyyyyyyyyyy
   ```
3. *(Optionnel)* Definir une **plage de videos** pour ne telecharger qu'une partie :
   - **De** : numero de la premiere video (ex: `10`)
   - **A** : numero de la derniere video (ex: `50`)
   - Laisser vide = telecharger tout
4. Cliquer **"Telecharger"**

Chaque playlist cree un dossier portant son nom. Les videos sont numerotees :
```
PHILOSOPHY LSA/
  001 - Introduction.mp4
  002 - Chapitre 1.mp4
  003 - Chapitre 2.mp4
```

#### Importer depuis une chaine

Au lieu de copier les liens manuellement :
1. Coller le lien de la chaine dans le champ dedie :
   ```
   https://www.youtube.com/@NomDeLaChaine
   ```
2. Cliquer **"Recuperer les playlists"**
3. Tous les liens sont remplis automatiquement
4. Supprimer ceux que vous ne voulez pas, puis telecharger

---

### 4. Telecharger une chaine complete

**Mode : Chaine complete**

1. Selectionner le mode **"Chaine complete"**
2. Coller le lien de la chaine :
   ```
   https://www.youtube.com/@NomDeLaChaine
   ```
3. Cliquer **"Tout telecharger"** puis **"Telecharger"**

Toutes les videos publiques de la chaine seront telechargees.

---

### 5. Options audio

Pour extraire uniquement l'audio :

1. Dans **Qualite**, selectionner **"Audio uniquement"**
2. Un selecteur de **format** apparait : **MP3**, WAV, FLAC, AAC
3. Telecharger normalement

---

### 6. Sous-titres

1. Cocher **"Telecharger les sous-titres"**
2. Choisir la **langue** (fr, en, es, de, etc.)
3. Les sous-titres sont telecharges en fichier `.srt` a cote de chaque video

> Les sous-titres automatiques (generes par YouTube) sont inclus si aucun sous-titre manuel n'existe.

---

## Reglages de vitesse

| Parametre | Description | Recommande |
|-----------|-------------|------------|
| **Parallele** | Nombre de playlists telechargees en meme temps | 3 |
| **Fragments** | Connexions simultanees par video | 4 |

### Conseils selon votre connexion

| Connexion | Parallele | Fragments |
|-----------|-----------|-----------|
| Lente (< 10 Mbps) | 1 | 2 |
| Moyenne (10-50 Mbps) | 2 | 4 |
| Rapide (50-100 Mbps) | 3 | 8 |
| Fibre (> 100 Mbps) | 5 | 16 |

**aria2c** est utilise automatiquement s'il est installe. Il ouvre 16 connexions par fichier pour contourner le bridage de YouTube.

---

## Reprise apres interruption

Vous pouvez **arreter le telechargement a tout moment** (fermer la fenetre ou Ctrl+C).

Pour reprendre :
1. Relancer l'application
2. Remettre les memes liens
3. Cliquer **"Telecharger"**

Les videos deja terminees sont **sautees automatiquement** grace au fichier `.downloaded.txt` dans chaque dossier. Rien n'est re-telecharge.

---

## Problemes courants

| Probleme | Solution |
|----------|----------|
| *"Sign in to confirm you're not a bot"* | Fichier cookies.txt invalide ou expire. Re-exportez-en un nouveau. |
| *"Could not copy Chrome cookie database"* | Le navigateur est ouvert. Fermez-le, ou utilisez un fichier cookies.txt. |
| *"Requested format is not available"* | La qualite choisie n'existe pas pour cette video. Essayez une qualite inferieure. |
| *"ffmpeg not found"* | Installez FFmpeg : `winget install Gyan.FFmpeg` puis redemarrez le terminal. |
| Telechargement lent (< 500 KB/s) | Verifiez que aria2c est installe. Augmentez les Fragments (8 ou 16). |
| Certaines videos ignorees | Normal : les videos privees, supprimees ou geo-bloquees sont ignorees automatiquement. |
| L'exe ne se lance pas | Installez les prerequis via `installer.bat` ou manuellement. |

---

## Structure des fichiers

```
YouTube Downloader/
  download_playlist.py              # Script principal
  YouTube Playlist Downloader.exe   # Executable
  installer.bat                     # Installateur automatique
  README.md                         # Cette documentation
```
