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
    "(from the settings)": "(aus den Einstellungen)",
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
    "not found – run get_legendary.py or choose legendary.exe":
        "nicht gefunden – get_legendary.py ausführen oder legendary.exe wählen",
    "Update Fog Launch…": "Fog Launch aktualisieren…",
    "Version {version}": "Version {version}",
    "Updating Fog Launch": "Fog Launch wird aktualisiert",
    "Fetch the newest Fog Launch from github.com/{repository} and replace the program files in "
    "'{folder}'? Your profiles and settings are not touched.":
        "Den neuesten Stand von Fog Launch von github.com/{repository} holen und die Programmdateien in "
        "«{folder}» ersetzen? Deine Profile und Einstellungen bleiben unberührt.",
    "Fog Launch is already up to date.": "Fog Launch ist bereits aktuell.",
    "{count} files were updated. Restart Fog Launch now to use the new version?":
        "{count} Dateien wurden aktualisiert. Fog Launch jetzt neu starten, um die neue Version zu verwenden?",
    "git could not update Fog Launch: {error}": "git konnte Fog Launch nicht aktualisieren: {error}",
    "The update could not be downloaded: {error}": "Das Update liess sich nicht herunterladen: {error}",
    "The downloaded update is not a valid ZIP file.": "Das heruntergeladene Update ist keine gültige ZIP-Datei.",
    "The downloaded update contains an unexpected path: {name}":
        "Das heruntergeladene Update enthält einen unerwarteten Pfad: {name}",
    "The downloaded update does not look like Fog Launch.":
        "Das heruntergeladene Update sieht nicht nach Fog Launch aus.",
    "The update could not be written: {error}": "Das Update liess sich nicht schreiben: {error}",
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
