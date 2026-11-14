"""The window's texts in German. The English text is the key.

`tests/test_texts.py` fails when a text in the source has no entry here.
"""

from __future__ import annotations

import os

_language = "en"


def system_language() -> str:
    if os.name == "nt":
        try:
            import ctypes

            primary = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF  # type: ignore[attr-defined]
            return "de" if primary == 0x07 else "en"
        except (AttributeError, OSError):
            return "en"
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(name)
        if value:
            return "de" if value.lower().startswith("de") else "en"
    return "en"


def set_language(code: str) -> None:
    global _language
    _language = code if code in ("de", "en") else system_language()


def t(text: str, **values: object) -> str:
    """The text in the chosen language, with `{placeholders}` filled in."""
    if _language == "de":
        text = GERMAN.get(text, text)
    return text.format(**values) if values else text


GERMAN = {
    # tabs and common words
    "Profiles": "Profile",
    "Launch sequences": "Startfolgen",
    "Graphics": "Grafik",
    "Input": "Eingabe",
    "Settings": "Einstellungen",
    "OK": "OK",
    "Cancel": "Abbrechen",
    "Cancelled": "Abgebrochen",
    "Ready": "Bereit",
    "Done: {what}": "Fertig: {what}",
    "Clear log": "Protokoll leeren",
    "Browse…": "Wählen…",
    "New…": "Neu…",
    "Rename…": "Umbenennen…",
    "Delete": "Löschen",
    "Add…": "Hinzufügen…",
    "Edit…": "Bearbeiten…",
    "Remove": "Entfernen",
    "Save": "Speichern",
    # profiles
    "Profile": "Profil",
    "Epic account": "Epic-Konto",
    "Game folder": "Spielordner",
    "not signed in": "nicht angemeldet",
    "Sign in…": "Anmelden…",
    "Sign out": "Abmelden",
    "Launch": "Starten",
    "New profile": "Neues Profil",
    "Rename profile": "Profil umbenennen",
    "Name of the profile": "Name des Profils",
    "Select a profile first.": "Wähle zuerst ein Profil aus.",
    "Start in the settings: choose a profile folder, or take over Better Together.":
        "Beginne in den Einstellungen: Wähle einen Profilordner oder übernimm Better Together.",
    "No profiles yet. Create one, then sign it in to Epic.":
        "Noch keine Profile. Lege eines an und melde es dann bei Epic an.",
    "Double-click a profile to launch it. Each profile keeps its own Epic sign-in.":
        "Ein Doppelklick startet ein Profil. Jedes Profil hat seine eigene Epic-Anmeldung.",
    "Delete the profile '{name}' and its Epic sign-in? This cannot be undone.":
        "Das Profil «{name}» samt Epic-Anmeldung löschen? Das lässt sich nicht rückgängig machen.",
    "Sign the profile '{name}' out of Epic?": "Das Profil «{name}» bei Epic abmelden?",
    "Signing in {name}": "{name} wird angemeldet",
    "Signing out {name}": "{name} wird abgemeldet",
    "Launching {name}": "{name} wird gestartet",
    # sign-in window
    "Sign in: {name}": "Anmelden: {name}",
    "Sign in with this code": "Mit diesem Code anmelden",
    "Way 1: Legendary's own sign-in window": "Weg 1: Anmeldefenster von Legendary",
    "Legendary opens a window with Epic's sign-in page. You type your password there, not into Fog Launch.":
        "Legendary öffnet ein Fenster mit der Anmeldeseite von Epic. Dein Passwort gibst du dort ein, "
        "nicht in Fog Launch.",
    "Open sign-in window": "Anmeldefenster öffnen",
    "Way 2: your browser and a code": "Weg 2: dein Browser und ein Code",
    'Sign in to Epic in your browser with the account for this profile. The page then shows a short text '
    'containing "authorizationCode". Paste that text or just the code here. Use a private browser window '
    "if the browser is signed in to a different Epic account.":
        "Melde dich im Browser mit dem Konto für dieses Profil bei Epic an. Die Seite zeigt danach einen "
        "kurzen Text mit «authorizationCode». Füge diesen Text oder nur den Code hier ein. Nimm ein "
        "privates Browserfenster, wenn der Browser mit einem anderen Epic-Konto angemeldet ist.",
    "Open Epic's page in the browser": "Epic-Seite im Browser öffnen",
    'That does not look like an authorization code. Copy the value of "authorizationCode".':
        "Das sieht nicht nach einem Anmeldecode aus. Kopiere den Wert von «authorizationCode».",
    "{name} started, checking for {seconds} s": "{name} gestartet, Kontrolle noch {seconds} s",
    "Next: {name} in {seconds} s": "Als Nächstes: {name} in {seconds} s",
    "{name}: registering the game folder": "{name}: Spielordner wird eingetragen",
    "{name}: loading game data from Epic": "{name}: Spieldaten werden von Epic geladen",
    # launch sequences
    "Graphics preset": "Grafik-Preset",
    "Input preset": "Eingabe-Preset",
    "(current settings)": "(aktuelle Einstellungen)",
    "–: current settings, the folder from the settings, the game decides.":
        "–: aktuelle Einstellungen, Ordner aus den Einstellungen, das Spiel entscheidet.",
    "Launch sequence": "Folge starten",
    "Seconds between two launches": "Sekunden zwischen zwei Starts",
    "With a preset, Fog Launch waits at least 30 seconds so the game can read it.":
        "Mit Preset wartet Fog Launch mindestens 30 Sekunden, damit das Spiel es einlesen kann.",
    "New sequence": "Neue Folge",
    "Rename sequence": "Folge umbenennen",
    "Name of the sequence": "Name der Folge",
    "Profile in the sequence": "Profil in der Folge",
    "Empty: the folder from the settings.": "Leer: der Ordner aus den Einstellungen.",
    "Select or create a sequence first.": "Wähle zuerst eine Folge aus oder lege eine an.",
    "Select an entry first.": "Wähle zuerst einen Eintrag aus.",
    "Delete the sequence '{name}'?": "Die Folge «{name}» löschen?",
    "Sequence {name}": "Folge {name}",
    # presets
    "Editing": "Bearbeitet wird",
    "Current game settings": "Aktuelle Spieleinstellungen",
    "Save as new preset…": "Als neues Preset speichern…",
    "Delete preset": "Preset löschen",
    "Use in the game now": "Jetzt im Spiel verwenden",
    "New preset": "Neues Preset",
    "Name of the preset": "Name des Presets",
    "Saved: {file}": "Gespeichert: {file}",
    "Replace the preset '{name}'?": "Das Preset «{name}» ersetzen?",
    "Delete the preset '{name}'?": "Das Preset «{name}» löschen?",
    "Choose a preset first.": "Wähle zuerst ein Preset.",
    "Choose a preset first. The current game settings cannot be deleted.":
        "Wähle zuerst ein Preset. Die aktuellen Spieleinstellungen lassen sich nicht löschen.",
    "There is nothing loaded to save.": "Es ist nichts geladen, das gespeichert werden könnte.",
    "The preset '{name}' is now the game's setting. The previous file is in the backups.":
        "Das Preset «{name}» ist jetzt die Einstellung des Spiels. Die vorherige Datei liegt bei den Sicherungen.",
    # graphics
    "Display and sound": "Anzeige und Ton",
    "Quality": "Qualität",
    "Width": "Breite",
    "Height": "Höhe",
    "Display mode": "Anzeigemodus",
    "Fullscreen": "Vollbild",
    "Borderless window": "Rahmenloses Fenster",
    "Window": "Fenster",
    "FPS limit (0 = none)": "FPS-Grenze (0 = keine)",
    "Render scale in %": "Renderauflösung in %",
    "VSync": "VSync",
    "Dynamic resolution": "Dynamische Auflösung",
    "Main volume": "Gesamtlautstärke",
    "Menu music volume": "Lautstärke der Menümusik",
    "Low": "Niedrig",
    "Medium": "Mittel",
    "High": "Hoch",
    "Ultra": "Ultra",
    "View distance": "Sichtweite",
    "Anti-aliasing": "Kantenglättung",
    "Shadows": "Schatten",
    "Global illumination": "Globale Beleuchtung",
    "Reflections": "Spiegelungen",
    "Post-processing": "Nachbearbeitung",
    "Textures": "Texturen",
    "Effects": "Effekte",
    "Foliage": "Vegetation",
    "Shading": "Schattierung",
    "Landscape": "Landschaft",
    "Animation": "Animation",
    "Greyed-out fields are not in this file and stay untouched.":
        "Ausgegraute Felder gibt es in dieser Datei nicht; sie bleiben unberührt.",
    "'{value}' is not a whole number.": "«{value}» ist keine ganze Zahl.",
    "{value} is outside the range {low} to {high}.": "{value} liegt ausserhalb von {low} bis {high}.",
    # input
    "Type": "Art",
    "Action": "Aktion",
    "Axis": "Achse",
    "Name in the game": "Name im Spiel",
    "Key": "Taste",
    "Key binding": "Tastenbelegung",
    "Held with it": "Dazu gehalten",
    "Held with it (actions)": "Dazu gehalten (Aktionen)",
    "Scale": "Faktor",
    "Scale (axes)": "Faktor (Achsen)",
    "Key names are Unreal Engine's, for example E, SpaceBar or LeftMouseButton.":
        "Die Tastennamen sind die der Unreal Engine, zum Beispiel E, SpaceBar oder LeftMouseButton.",
    "Changes take effect once you press Save.": "Änderungen gelten erst nach «Speichern».",
    "Names and keys must not contain quotation marks, commas, brackets or '='.":
        "Namen und Tasten dürfen keine Anführungszeichen, Kommas, Klammern oder «=» enthalten.",
    "The scale must be a number, for example 1 or -1.": "Der Faktor muss eine Zahl sein, zum Beispiel 1 oder -1.",
    "This file has no key bindings.": "Diese Datei enthält keine Tastenbelegungen.",
    # settings
    "Profile folder": "Profilordner",
    "Dead by Daylight folder": "Ordner von Dead by Daylight",
    "Extra game arguments": "Zusätzliche Startparameter",
    "Skip Legendary's version check when launching (needed for shared installations)":
        "Versionsprüfung von Legendary beim Start überspringen (nötig bei gemeinsamer Installation)",
    "Language": "Sprache",
    "Automatic": "Automatisch",
    "The language changes the next time Fog Launch starts.":
        "Die Sprache wechselt beim nächsten Start von Fog Launch.",
    "Open Fog Launch's data folder": "Datenordner von Fog Launch öffnen",
    "The profile folder holds one subfolder per profile with that profile's Epic sign-in. "
    "Treat it like a password: do not share it or put it in a synced folder.":
        "Im Profilordner liegt pro Profil ein Unterordner mit dessen Epic-Anmeldung. Behandle ihn wie ein "
        "Passwort: nicht weitergeben und nicht in einen synchronisierten Ordner legen.",
    "Update Fog Launch…": "Fog Launch aktualisieren…",
    "Version {version}": "Version {version}",
    "Updating Fog Launch": "Fog Launch wird aktualisiert",
    "Fog Launch is already up to date.": "Fog Launch ist bereits aktuell.",
    "{count} files were updated. Restart Fog Launch now to use the new version?":
        "{count} Dateien wurden aktualisiert. Fog Launch jetzt neu starten, um die neue Version zu verwenden?",
    "git could not update Fog Launch: {error}": "git konnte Fog Launch nicht aktualisieren: {error}",
    "The downloaded update is not a valid ZIP file.": "Das heruntergeladene Update ist keine gültige ZIP-Datei.",
    "The downloaded update contains an unexpected path: {name}":
        "Das heruntergeladene Update enthält einen unerwarteten Pfad: {name}",
    "The downloaded update does not look like Fog Launch.":
        "Das heruntergeladene Update sieht nicht nach Fog Launch aus.",
    "The update could not be written: {error}": "Das Update liess sich nicht schreiben: {error}",
    # game windows
    "Game": "Spiel",
    "running": "läuft",
    "Close game": "Spiel beenden",
    "Close all games": "Alle Spiele beenden",
    "Close every open Dead by Daylight window?": "Alle offenen Fenster von Dead by Daylight schliessen?",
    "Asked the game of '{name}' to close.": "Das Spiel von «{name}» wurde gebeten, sich zu schliessen.",
    "Asked {count} game windows to close.": "{count} Spielfenster wurden gebeten, sich zu schliessen.",
    "No Dead by Daylight window is open.": "Es ist kein Fenster von Dead by Daylight offen.",
    "No window of '{name}' that Fog Launch launched is open.":
        "Es ist kein von Fog Launch gestartetes Fenster von «{name}» offen.",
    "No window of '{name}' that Fog Launch launched is open. Launch the profile, move its window where you "
    "want it, then press this button again.":
        "Es ist kein von Fog Launch gestartetes Fenster von «{name}» offen. Starte das Profil, schiebe sein "
        "Fenster an die gewünschte Stelle und drücke diesen Knopf dann noch einmal.",
    "Game windows can only be found and arranged on Windows.":
        "Spielfenster lassen sich nur unter Windows finden und anordnen.",
    "Window position": "Fensterposition",
    "Take from the running window": "Vom laufenden Fenster übernehmen",
    "Clear": "Leeren",
    'Empty: the game decides. Works best with the display mode "Window" or "Borderless window" in the '
    "graphics preset.":
        "Leer: Das Spiel entscheidet. Klappt am besten mit dem Anzeigemodus «Fenster» oder «Rahmenloses "
        "Fenster» im Grafik-Preset.",
    "The window position needs four whole numbers: X, Y, width and height.":
        "Die Fensterposition braucht vier ganze Zahlen: X, Y, Breite und Höhe.",
    "The window position is outside the possible range.": "Die Fensterposition liegt ausserhalb des Möglichen.",
    # arranging windows
    "Arrange windows…": "Fenster anordnen…",
    "Arrange windows": "Fenster anordnen",
    "Apply": "Übernehmen",
    "Add profiles to the sequence first.": "Füge der Folge zuerst Profile hinzu.",
    "Layout": "Anordnung",
    "All monitors": "Alle Monitore",
    "Monitor {number}": "Monitor {number}",
    "main": "Hauptmonitor",
    "Side by side": "Nebeneinander",
    "Stacked": "Untereinander",
    "Grid": "Raster",
    "One per monitor": "Je ein Monitor",
    "Keep 16:9": "16:9 beibehalten",
    "Windows": "Fenster",
    "not arranged": "nicht angeordnet",
    "Same size as": "Gleiche Grösse wie",
    "Standard size": "Standardgrösse",
    "Place": "Platzieren",
    "Take over size": "Grösse übernehmen",
    "Do not arrange": "Nicht anordnen",
    "Take from running windows": "Von laufenden Fenstern übernehmen",
    "Snap to edges": "An Kanten einrasten",
    'Drag a window to move it, drag a corner to resize it. Arranging works with the display mode "Window" or '
    '"Borderless window".':
        "Ein Fenster ziehen verschiebt es, eine Ecke ziehen ändert die Grösse. Das Anordnen klappt mit dem "
        "Anzeigemodus «Fenster» oder «Rahmenloses Fenster».",
    "The monitors could not be read; this shows only the main screen.":
        "Die Monitore liessen sich nicht auslesen; zu sehen ist nur der Hauptbildschirm.",
    "None of these profiles has a game window open that Fog Launch launched.":
        "Keines dieser Profile hat ein von Fog Launch gestartetes Spielfenster offen.",
    # shortcuts
    "Desktop shortcut": "Desktop-Verknüpfung",
    "Creating a shortcut": "Verknüpfung wird angelegt",
    "Shortcut created: {file}": "Verknüpfung angelegt: {file}",
    "Desktop shortcuts can only be created on Windows.": "Desktop-Verknüpfungen gibt es nur unter Windows.",
    "The shortcut could not be created: {error}": "Die Verknüpfung liess sich nicht anlegen: {error}",
    # encrypted sign-ins
    "Encrypt the Epic sign-ins with Windows (DPAPI)": "Epic-Anmeldungen mit Windows verschlüsseln (DPAPI)",
    "Encrypt the sign-ins of all profiles? They can then only be used by this Windows user on this PC, and "
    "Better Together can no longer use profiles in the same folder. A profile folder copied to another PC "
    "has to be signed in again.":
        "Die Anmeldungen aller Profile verschlüsseln? Sie sind dann nur noch für diesen Windows-Benutzer auf "
        "diesem PC nutzbar, und Better Together kann Profile im selben Ordner nicht mehr verwenden. Ein auf "
        "einen anderen PC kopierter Profilordner muss neu angemeldet werden.",
    "Store the sign-ins of all profiles unencrypted again?":
        "Die Anmeldungen aller Profile wieder unverschlüsselt speichern?",
    "Sign-ins encrypted: {count}": "Anmeldungen verschlüsselt: {count}",
    "Sign-ins decrypted: {count}": "Anmeldungen entschlüsselt: {count}",
    "Encrypting the sign-ins is only possible on Windows.":
        "Die Anmeldungen lassen sich nur unter Windows verschlüsseln.",
    "Windows could not encrypt or decrypt a sign-in (error {code}).":
        "Windows konnte eine Anmeldung nicht ver- oder entschlüsseln (Fehler {code}).",
    "The sign-in of '{name}' could not be changed: {error}":
        "Die Anmeldung von «{name}» liess sich nicht ändern: {error}",
    "Encrypted sign-ins are on, so these profiles are now encrypted and Better Together can no longer use them.":
        "Die Verschlüsselung der Anmeldungen ist an, deshalb sind diese Profile jetzt verschlüsselt, und "
        "Better Together kann sie nicht mehr verwenden.",
    # Legendary
    "Download Legendary": "Legendary herunterladen",
    "Downloading Legendary": "Legendary wird heruntergeladen",
    "Download Legendary {version} from its official GitHub releases? Fog Launch keeps the file only if its "
    "checksum is right.":
        "Legendary {version} von den offiziellen GitHub-Releases herunterladen? Fog Launch behält die Datei "
        "nur, wenn die Prüfsumme stimmt.",
    "Legendary saved: {file}": "Legendary gespeichert: {file}",
    "not found – download it or choose legendary.exe": "nicht gefunden – herunterladen oder legendary.exe wählen",
    "The downloaded Legendary does not match its checksum. Nothing was saved.":
        "Das heruntergeladene Legendary passt nicht zur Prüfsumme. Es wurde nichts gespeichert.",
    "'{file}' is not a known official Legendary build (SHA-256 {sha256}). It may have been replaced.":
        "«{file}» ist kein bekannter offizieller Build von Legendary (SHA-256 {sha256}). Die Datei wurde "
        "vielleicht ausgetauscht.",
    "Only continue if you downloaded this file yourself from Legendary's official releases. Trust it from "
    "now on?":
        "Fahre nur fort, wenn du diese Datei selbst von den offiziellen Releases von Legendary geladen hast. "
        "Ihr ab jetzt vertrauen?",
    # updates
    "Looking for a new version": "Suche nach einer neuen Version",
    "Fog Launch {version} is the newest version.": "Fog Launch {version} ist die neueste Version.",
    "Version {new} is available (you have {old}). Install it now? Your profiles and settings are not touched.":
        "Version {new} ist verfügbar (du hast {old}). Jetzt installieren? Deine Profile und Einstellungen "
        "bleiben unberührt.",
    "No version of Fog Launch has been published yet.": "Es wurde noch keine Version von Fog Launch veröffentlicht.",
    "GitHub's answer about the newest version could not be read.":
        "Die Antwort von GitHub zur neuesten Version liess sich nicht lesen.",
    "The download failed: {error}": "Der Download ist fehlgeschlagen: {error}",
    "The program file of version {tag} is still being built. Try again in a few minutes.":
        "Die Programmdatei von Version {tag} wird noch gebaut. Versuche es in ein paar Minuten noch einmal.",
    "The downloaded program does not match its checksum. Nothing was changed.":
        "Das heruntergeladene Programm passt nicht zur Prüfsumme. Es wurde nichts geändert.",
    "The downloaded update does not match its checksum. Nothing was changed.":
        "Das heruntergeladene Update passt nicht zur Prüfsumme. Es wurde nichts geändert.",
    "{name} is not listed in {sums}.": "{name} steht nicht in {sums}.",
    # Better Together
    "Take over from Better Together": "Aus Better Together übernehmen",
    "Take over from Better Together…": "Aus Better Together übernehmen…",
    "Take over": "Übernehmen",
    "Better Together's settings folder": "Einstellungsordner von Better Together",
    "No Better Together settings here.": "Hier liegen keine Einstellungen von Better Together.",
    "Found – profiles: {profiles}, launch presets: {sequences}, profile folder: {library}":
        "Gefunden – Profile: {profiles}, Start-Presets: {sequences}, Profilordner: {library}",
    "Use Better Together's profile folder as it is (recommended)":
        "Den Profilordner von Better Together direkt verwenden (empfohlen)",
    "Nothing is copied or changed. Both programs then share the same sign-ins, and you can keep using either.":
        "Nichts wird kopiert oder verändert. Beide Programme teilen sich dann dieselben Anmeldungen, "
        "und du kannst beide weiter benutzen.",
    "Copy the profiles to a new folder": "Die Profile in einen neuen Ordner kopieren",
    "The originals stay untouched. Epic may sign a copy out as soon as the other copy is used, "
    "so stop using Better Together afterwards.":
        "Die Originale bleiben unberührt. Epic kann eine Kopie abmelden, sobald die andere benutzt wird; "
        "verwende Better Together danach also nicht mehr.",
    "Choose the folder the profiles are copied to.": "Wähle den Ordner, in den die Profile kopiert werden.",
    "Taken over: {count} profiles.": "Übernommen: {count} Profile.",
    "Better Together was used on this PC. Take over its profiles and launch presets now?":
        "Auf diesem PC wurde Better Together benutzt. Dessen Profile und Start-Presets jetzt übernehmen?",
    "Better Together has no profile folder set, or it no longer exists.":
        "In Better Together ist kein Profilordner eingestellt, oder es gibt ihn nicht mehr.",
    "Choose a folder outside Better Together's profile folder for the copy.":
        "Wähle für die Kopie einen Ordner ausserhalb des Profilordners von Better Together.",
    "No Better Together settings were found in '{folder}'.":
        "In «{folder}» liegen keine Einstellungen von Better Together.",
    "The profile '{name}' already exists in the target and was not copied.":
        "Das Profil «{name}» gibt es im Ziel schon; es wurde nicht kopiert.",
    "The profile '{name}' could not be copied: {error}": "Das Profil «{name}» liess sich nicht kopieren: {error}",
    "The game folder '{folder}' no longer contains {exe}.": "Im Spielordner «{folder}» liegt {exe} nicht mehr.",
    "The sequence '{name}' already exists and was kept as it is.":
        "Die Folge «{name}» gibt es schon; sie blieb unverändert.",
    # errors
    "Fog Launch is still busy. Wait for it, or press Cancel.":
        "Fog Launch ist noch beschäftigt. Warte ab oder drücke «Abbrechen».",
    "Names may contain letters, digits, spaces, '-', '_' and '.', and must not start or end with a dot.":
        "Namen dürfen Buchstaben, Ziffern, Leerzeichen, «-», «_» und «.» enthalten und nicht mit einem "
        "Punkt beginnen oder enden.",
    "The launch arguments have an unclosed quotation mark.":
        "In den Startparametern fehlt ein schliessendes Anführungszeichen.",
    "The profile folder could not be created: {error}": "Der Profilordner liess sich nicht anlegen: {error}",
    "'{exe}' is not in '{folder}'. Choose the folder the game is installed in.":
        "«{exe}» liegt nicht in «{folder}». Wähle den Ordner, in dem das Spiel installiert ist.",
    "'{file}' does not exist.": "«{file}» gibt es nicht.",
    "'{file}' does not exist. Start the game once, or set the path in the settings.":
        "«{file}» gibt es nicht. Starte das Spiel einmal oder setze den Pfad in den Einstellungen.",
    "'{file}' could not be read: {error}": "«{file}» liess sich nicht lesen: {error}",
    "'{file}' could not be written: {error}": "«{file}» liess sich nicht schreiben: {error}",
    "Legendary was not found. Run get_legendary.py, or choose legendary.exe in the settings.":
        "Legendary wurde nicht gefunden. Führe get_legendary.py aus oder wähle legendary.exe in den Einstellungen.",
    "Choose a profile folder in the settings first.": "Wähle zuerst in den Einstellungen einen Profilordner.",
    "Choose the Dead by Daylight folder in the settings first.":
        "Wähle zuerst in den Einstellungen den Ordner von Dead by Daylight.",
    "The profile '{name}' does not exist.": "Das Profil «{name}» gibt es nicht.",
    "The profile '{name}' already exists.": "Das Profil «{name}» gibt es schon.",
    "The profile '{name}' is not signed in.": "Das Profil «{name}» ist nicht angemeldet.",
    "The profile could not be renamed: {error}": "Das Profil liess sich nicht umbenennen: {error}",
    "The profile could not be deleted: {error}": "Das Profil liess sich nicht löschen: {error}",
    "'{folder}' also contains {extra}. Fog Launch only deletes folders that hold nothing but the sign-in data; "
    "delete this one yourself.":
        "«{folder}» enthält auch {extra}. Fog Launch löscht nur Ordner, in denen nichts als die "
        "Anmeldedaten liegt; lösche diesen selbst.",
    "No profile knows the game yet. Sign in to one profile and choose the game folder again.":
        "Noch kein Profil kennt das Spiel. Melde ein Profil an und wähle den Spielordner erneut.",
    "The preset could not be deleted: {error}": "Das Preset liess sich nicht löschen: {error}",
    "The preset '{name}' could not be applied: {error}": "Das Preset «{name}» liess sich nicht anwenden: {error}",
    "The delay must be a whole number of seconds.": "Die Wartezeit muss eine ganze Zahl in Sekunden sein.",
    "The delay must be between 0 and 3600 seconds.": "Die Wartezeit muss zwischen 0 und 3600 Sekunden liegen.",
    "The sequence '{name}' already exists.": "Die Folge «{name}» gibt es schon.",
    "The sequence '{name}' has no entries.": "Die Folge «{name}» hat keine Einträge.",
    "These profiles no longer exist: {names}": "Diese Profile gibt es nicht mehr: {names}",
    "Legendary could not be started: {error}": "Legendary liess sich nicht starten: {error}",
    "Legendary stopped with an error (code {code}). See the log.":
        "Legendary hat mit einem Fehler beendet (Code {code}). Siehe Protokoll.",
    "Legendary could not register the game folder. See the log.":
        "Legendary konnte den Spielordner nicht eintragen. Siehe Protokoll.",
    "Signing in to '{name}' did not work. See the log.":
        "Die Anmeldung von «{name}» hat nicht geklappt. Siehe Protokoll.",
    "The game data for '{name}' could not be loaded. See the log.":
        "Die Spieldaten für «{name}» liessen sich nicht laden. Siehe Protokoll.",
    "Dead by Daylight is not in the Epic library of '{name}'.":
        "Dead by Daylight ist nicht in der Epic-Bibliothek von «{name}».",
}
