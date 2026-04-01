"""
AquaPlay / Aqua_jouer — Steam Playlist Manager with Priority Heap
PyQt6 · SQLite · Dark Mode · FR/EN

Features:
  • Auto Steam sync on startup
  • Priority heap with mood-weighted pick
  • Completion status + archive (Finished / Dropped)
  • Estimated session duration
  • Full history log
  • Per-game session notes
  • French / English UI
"""

import sys
import sqlite3
import heapq
import random
import math
import requests
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QTabWidget, QMessageBox, QDialog, QDialogButtonBox, QFormLayout,
    QHeaderView, QFrame, QStatusBar, QProgressBar,
    QGraphicsOpacityEffect, QTextEdit, QScrollArea, QSlider,
    QComboBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QTimer
from PyQt6.QtGui import QColor, QPalette, QDesktopServices

# ─────────────────────────────────────────────
#  INTERNATIONALISATION
# ─────────────────────────────────────────────
_STRINGS = {
    # app
    "app_title":            {"fr": "Aqua_jouer",                     "en": "AquaPlay"},
    "app_subtitle":         {"fr": "Gestionnaire de Playlist Steam",  "en": "Steam Playlist Manager"},
    "app_welcome":          {"fr": "Bienvenue dans Aqua_jouer !",     "en": "Welcome to AquaPlay!"},
    "app_no_creds":         {"fr": "Configurez votre API Steam pour commencer (bouton Paramètres).",
                             "en": "Configure your Steam API to get started (Settings button)."},
    # header buttons
    "btn_sync":             {"fr": "Synchroniser Steam",   "en": "Sync Steam"},
    "btn_settings":         {"fr": "Paramètres",           "en": "Settings"},
    "btn_syncing":          {"fr": "Synchronisation…",     "en": "Syncing…"},
    "btn_sync_start":       {"fr": "Sync au démarrage…",   "en": "Startup sync…"},
    # tabs
    "tab_library":          {"fr": "Bibliothèque",  "en": "Library"},
    "tab_playlist":         {"fr": "Playlist",      "en": "Playlist"},
    "tab_notes":            {"fr": "Journal",       "en": "Journal"},
    "tab_archive":          {"fr": "Archives",      "en": "Archive"},
    "tab_history":          {"fr": "Historique",    "en": "History"},
    # stats
    "stat_total":           {"fr": "Total jeux",      "en": "Total games"},
    "stat_library":         {"fr": "Bibliothèque",    "en": "Library"},
    "stat_playlist":        {"fr": "Playlist",        "en": "Playlist"},
    "stat_archive":         {"fr": "Archivés",        "en": "Archived"},
    # library
    "search_placeholder":   {"fr": "Rechercher un jeu…",   "en": "Search for a game…"},
    "search_label":         {"fr": "Recherche :",           "en": "Search:"},
    "col_appid":            {"fr": "AppID",         "en": "AppID"},
    "col_name":             {"fr": "Nom du jeu",    "en": "Game name"},
    "col_time":             {"fr": "Temps joué",    "en": "Time played"},
    "col_score":            {"fr": "Score",         "en": "Score"},
    "col_actions":          {"fr": "Actions",       "en": "Actions"},
    "col_status":           {"fr": "Statut",        "en": "Status"},
    "col_archived":         {"fr": "Archivé le",    "en": "Archived on"},
    "col_datetime":         {"fr": "Date / Heure",  "en": "Date / Time"},
    "col_action":           {"fr": "Action",        "en": "Action"},
    "col_duration":         {"fr": "Durée prévue",  "en": "Planned duration"},
    "btn_add_playlist":     {"fr": "+ Playlist",    "en": "+ Playlist"},
    # playlist
    "pl_count":             {"fr": "{n} / 10 jeux",         "en": "{n} / 10 games"},
    "btn_freeze":           {"fr": "Geler",                 "en": "Freeze"},
    "btn_unfreeze":         {"fr": "Dégeler",               "en": "Unfreeze"},
    "freeze_msg":           {"fr": "Application gelée — suggestions suspendues.",
                             "en": "Frozen — suggestions paused."},
    "btn_note_has":         {"fr": "Note",    "en": "Note"},
    "btn_note_empty":       {"fr": "Note",    "en": "Note"},
    "btn_archive":          {"fr": "Archiver",  "en": "Archive"},
    "btn_remove":           {"fr": "Retirer",   "en": "Remove"},
    "btn_restore":          {"fr": "Restaurer", "en": "Restore"},
    # mood slider
    "mood_label":           {"fr": "Humeur du soir :",          "en": "Tonight's mood:"},
    "mood_safe":            {"fr": "Valeur sûre",               "en": "Safe pick"},
    "mood_explore":         {"fr": "Exploration",               "en": "Explore"},
    "mood_tooltip":         {"fr": "Bas = valeur sûre (haute priorité) · Haut = exploration (basse priorité)",
                             "en": "Low = safe pick (high priority) · High = exploration (low priority)"},
    # pick frame
    "btn_pick":             {"fr": "À quoi on joue ?",  "en": "What do we play?"},
    "pick_suggestion":      {"fr": "Suggestion : {name}",   "en": "Suggestion: {name}"},
    "pick_score":           {"fr": "Score de priorité : {score} / 100",
                             "en": "Priority score: {score} / 100"},
    "btn_accept":           {"fr": "Accepter",          "en": "Accept"},
    "btn_refuse":           {"fr": "Refuser / Reroll",  "en": "Refuse / Reroll"},
    # launch frame
    "launch_title":         {"fr": "On joue à : {name}",  "en": "Playing: {name}"},
    "launch_dur":           {"fr": " — {n} min prévues",  "en": " — {n} min planned"},
    "note_hdr":             {"fr": "Vos notes pour cette session :",  "en": "Your notes for this session:"},
    "btn_launch":           {"fr": "Lancer dans Steam",  "en": "Launch in Steam"},
    "btn_cancel":           {"fr": "Annuler",            "en": "Cancel"},
    # status messages
    "sync_progress":        {"fr": "Mise à jour : {c}/{t} jeux…",  "en": "Updating: {c}/{t} games…"},
    "sync_done":            {"fr": "Bibliothèque à jour — {n} jeux.",  "en": "Library up to date — {n} games."},
    "sync_manual_done":     {"fr": "{n} jeux importés.",              "en": "{n} games imported."},
    "sync_fail":            {"fr": "Échec de la synchronisation.",    "en": "Sync failed."},
    "added_pl":             {"fr": "«{name}» ajouté avec un score de {prio}.",
                             "en": "«{name}» added with score {prio}."},
    "removed_pl":           {"fr": "Jeu retiré de la playlist.",  "en": "Game removed from playlist."},
    "pl_full":              {"fr": "La playlist est pleine (max 10 jeux).",
                             "en": "Playlist is full (max 10 games)."},
    "pick_status":          {"fr": "Suggestion : {name}  (score {score})",
                             "en": "Suggestion: {name}  (score {score})"},
    "accepted_status":      {"fr": "«{name}» sélectionné{dur}. Prêt à jouer !",
                             "en": "«{name}» selected{dur}. Ready to play!"},
    "launched_status":      {"fr": "Lancement de «{name}»{dur}. Bonne session !",
                             "en": "Launching «{name}»{dur}. Have fun!"},
    "archived_done_t":      {"fr": "Félicitations ! «{name}» archivé comme terminé.",
                             "en": "Congrats! «{name}» archived as finished."},
    "archived_done_a":      {"fr": "Dommage ! «{name}» archivé comme abandonné.",
                             "en": "«{name}» archived as dropped."},
    "restored":             {"fr": "«{name}» restauré en bibliothèque.",  "en": "«{name}» restored to library."},
    "note_saved":           {"fr": "Note enregistrée pour «{name}».",  "en": "Note saved for «{name}»."},
    "note_deleted":         {"fr": "Note supprimée pour «{name}».",    "en": "Note deleted for «{name}»."},
    # settings dialog
    "settings_title":       {"fr": "Paramètres",             "en": "Settings"},
    "settings_steam":       {"fr": "Connexion Steam API",    "en": "Steam API Connection"},
    "apikey_label":         {"fr": "API Key :",              "en": "API Key:"},
    "steamid_label":        {"fr": "SteamID64 :",            "en": "SteamID64:"},
    "apikey_ph":            {"fr": "Clé API Steam (32 caractères)",    "en": "Steam API key (32 chars)"},
    "steamid_ph":           {"fr": "SteamID64 (ex: 76561198XXXXXXXXX)", "en": "SteamID64 (e.g. 76561198XXXXXXXXX)"},
    "lang_label":           {"fr": "Langue / Language :",   "en": "Language / Langue:"},
    "lang_restart":         {"fr": "Redémarrez l'application pour appliquer la langue.",
                             "en": "Restart the application to apply the language change."},
    "settings_help":        {"fr": (
        "<b>Obtenir l'API Key :</b><br>"
        "1. <a href='https://steamcommunity.com/dev/apikey' style='color:#1a9fff;'>steamcommunity.com/dev/apikey</a><br>"
        "2. Enregistrez un domaine (ex: localhost) et copiez la clé.<br><br>"
        "<b>Trouver le SteamID64 :</b> "
        "<a href='https://steamid.io' style='color:#1a9fff;'>steamid.io</a>"
    ), "en": (
        "<b>Get your API Key:</b><br>"
        "1. <a href='https://steamcommunity.com/dev/apikey' style='color:#1a9fff;'>steamcommunity.com/dev/apikey</a><br>"
        "2. Register any domain (e.g. localhost) and copy the key.<br><br>"
        "<b>Find your SteamID64:</b> "
        "<a href='https://steamid.io' style='color:#1a9fff;'>steamid.io</a>"
    )},
    "btn_save":             {"fr": "Enregistrer",  "en": "Save"},
    "btn_close_ok":         {"fr": "OK",           "en": "OK"},
    "missing_fields":       {"fr": "Renseignez l'API Key et le SteamID64.",
                             "en": "Please fill in the API Key and SteamID64."},
    # motivation dialog
    "motiv_title":          {"fr": "Priorité de jeu",               "en": "Game Priority"},
    "motiv_sub":            {"fr": "Ajouter à la playlist :",       "en": "Add to playlist:"},
    "motiv_question":       {"fr": "Quelle est votre motivation pour ce jeu ? (1 – 100)",
                             "en": "How motivated are you for this game? (1 – 100)"},
    "motiv_lo":             {"fr": "Peu motivé",    "en": "Not excited"},
    "motiv_hi":             {"fr": "Très motivé !", "en": "Very excited!"},
    "btn_add":              {"fr": "Ajouter",       "en": "Add"},
    # session dialog
    "session_title":        {"fr": "Durée de session",                  "en": "Session Duration"},
    "session_question":     {"fr": "Combien de temps prévoyez-vous jouer ?",
                             "en": "How long do you plan to play?"},
    "session_lo":           {"fr": "15 min",  "en": "15 min"},
    "session_hi":           {"fr": "4h00",    "en": "4h00"},
    "btn_skip":             {"fr": "Passer (sans durée)",  "en": "Skip (no duration)"},
    "btn_confirm":          {"fr": "Confirmer",            "en": "Confirm"},
    # archive dialog
    "archive_title":        {"fr": "Archiver le jeu",             "en": "Archive Game"},
    "archive_question":     {"fr": "Que faites-vous avec ce jeu ?", "en": "What are you doing with this game?"},
    "archive_finished":     {"fr": "Terminé",    "en": "Finished"},
    "archive_dropped":      {"fr": "Abandonné",  "en": "Dropped"},
    # note dialog
    "note_title":           {"fr": "Note — {name}",  "en": "Note — {name}"},
    "note_hint":            {"fr": "Où en êtes-vous ? Que faire cette session ?",
                             "en": "Where are you? What to do this session?"},
    "note_ph":              {"fr": "Ex: Chapitre 3 terminé.\nCette session : explorer la zone nord…",
                             "en": "E.g.: Chapter 3 done.\nThis session: explore the north area…"},
    "note_last":            {"fr": "Dernière maj : {dt}",  "en": "Last updated: {dt}"},
    "note_new":             {"fr": "Nouvelle note",        "en": "New note"},
    "note_too_long":        {"fr": "Maximum 1000 caractères.",  "en": "Maximum 1000 characters."},
    "note_delete_confirm":  {"fr": "Supprimer cette note ?",    "en": "Delete this note?"},
    "btn_erase":            {"fr": "Effacer",       "en": "Erase"},
    "btn_save_note":        {"fr": "Enregistrer",   "en": "Save"},
    # notes view
    "notes_section":        {"fr": "Journal de progression",   "en": "Progress Journal"},
    "notes_empty":          {"fr": "Aucune note pour l'instant.\n\nDans l'onglet Playlist, cliquez sur « Note »\npour écrire où vous en êtes dans un jeu.",
                             "en": "No notes yet.\n\nIn the Playlist tab, click « Note »\nto write where you are in a game."},
    "btn_edit":             {"fr": "Modifier",  "en": "Edit"},
    "modified_on":          {"fr": "Modifié le {dt}",  "en": "Modified on {dt}"},
    # archive view
    "archive_section":      {"fr": "Jeux archivés",   "en": "Archived Games"},
    "archive_empty":        {"fr": "Aucun jeu archivé.\n\nDans la Playlist, cliquez « Archiver »\npour marquer un jeu comme Terminé ou Abandonné.",
                             "en": "No archived games.\n\nIn Playlist, click «Archive»\nto mark a game as Finished or Dropped."},
    "status_finished":      {"fr": "Terminé",    "en": "Finished"},
    "status_dropped":       {"fr": "Abandonné",  "en": "Dropped"},
    "status_playing":       {"fr": "En cours",   "en": "Playing"},
    # history view
    "history_section":      {"fr": "Historique des sessions",  "en": "Session History"},
    "history_empty":        {"fr": "Aucune activité enregistrée.\n\nLancez votre premier jeu pour démarrer le journal !",
                             "en": "No activity recorded yet.\n\nLaunch your first game to start the log!"},
    "stat_sessions":        {"fr": "Sessions lancées",  "en": "Sessions launched"},
    "stat_hours":           {"fr": "Heures prévues",    "en": "Planned hours"},
    "stat_games_touched":   {"fr": "Jeux touchés",      "en": "Games played"},
    "action_picked":        {"fr": "Suggéré",    "en": "Suggested"},
    "action_accepted":      {"fr": "Accepté",    "en": "Accepted"},
    "action_refused":       {"fr": "Refusé",     "en": "Refused"},
    "action_launched":      {"fr": "Lancé",      "en": "Launched"},
    "action_archived_t":    {"fr": "Terminé",    "en": "Finished"},
    "action_archived_a":    {"fr": "Abandonné",  "en": "Dropped"},
    # inflation popup
    "inflation_title":      {"fr": "Conseil — Rééquilibrage des priorités",
                             "en": "Tip — Rebalance Priorities"},
    "inflation_body":       {"fr": "Plus de 75 % de vos jeux ont un score supérieur à 80.\n\nPour une meilleure précision des suggestions, n'hésitez pas\nà revoir votre motivation pour ces jeux : retirez-les de la\nplaylist puis rajoutez-les avec un nouveau score.",
                             "en": "More than 75% of your games have a score above 80.\n\nFor better suggestion accuracy, consider reviewing your\nmotivation for those games: remove them from the playlist\nthen add them back with a fresh score."},
    # empty / no cred
    "playlist_empty_title": {"fr": "Playlist vide",  "en": "Empty Playlist"},
    "playlist_empty_body":  {"fr": "Ajoutez des jeux à votre playlist d'abord !",
                             "en": "Add games to your playlist first!"},
    # errors
    "err_sync_title":       {"fr": "Erreur de synchronisation",  "en": "Sync Error"},
    "err_connection":       {"fr": "Impossible de contacter l'API Steam. Vérifiez votre connexion.",
                             "en": "Cannot reach Steam API. Check your connection."},
    "err_http":             {"fr": "Erreur HTTP Steam API : {e}",  "en": "Steam API HTTP error: {e}"},
    "err_unexpected":       {"fr": "Erreur inattendue : {e}",      "en": "Unexpected error: {e}"},
    "err_no_games":         {"fr": "Aucun jeu trouvé. Vérifiez vos paramètres et la visibilité de votre profil Steam.",
                             "en": "No games found. Check your settings and Steam profile visibility."},
    "err_missing_fields":   {"fr": "Champs manquants",  "en": "Missing fields"},
}

# Active language — loaded from DB at startup
LANG = "fr"


def t(key, **kwargs):
    """Return translated string for the current LANG, with optional format kwargs."""
    entry = _STRINGS.get(key, {})
    s = entry.get(LANG, entry.get("fr", key))
    if kwargs:
        try:
            s = s.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return s


# ─────────────────────────────────────────────
#  PRIORITY CONSTANTS
# ─────────────────────────────────────────────
PRIORITY_DEFAULT = 50.0
DECAY_ACCEPT     = 14.0
DECAY_LAUNCH     =  7.0
DECAY_REFUSE     =  5.0
BOOST_ACCEPT     =  2.8
BOOST_REFUSE     =  1.0
SCORE_MIN        =  1.0
SCORE_MAX        = 100.0
INFLATION_THRESH =  0.75
INFLATION_SCORE  = 80.0


def recency_factor(last_launched_iso):
    if last_launched_iso is None:
        return 1.0
    try:
        days = (datetime.now() - datetime.fromisoformat(last_launched_iso)).total_seconds() / 86400.0
        return max(0.1, min(1.0, 1.0 - 0.9 * math.exp(-days / 5.0)))
    except Exception:
        return 1.0


def soft_cap_factor(score):
    if score <= 70.0:
        return 1.0
    return max(0.08, 1.0 - (score - 70.0) / 33.0)


# ─────────────────────────────────────────────
#  STYLE
# ─────────────────────────────────────────────
DARK_STYLE = """
QMainWindow, QDialog { background-color: #0e1117; }
QWidget {
    background-color: #0e1117; color: #c7d5e0;
    font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px;
}
QTabWidget::pane { border: 1px solid #2a3f5f; background-color: #0e1117; border-radius: 4px; }
QTabBar::tab {
    background-color: #1b2838; color: #8ba0b4; padding: 8px 16px;
    border: 1px solid #2a3f5f; border-bottom: none;
    border-top-left-radius: 4px; border-top-right-radius: 4px;
    font-weight: 500; min-width: 85px;
}
QTabBar::tab:selected { background-color: #1a9fff; color: #ffffff; border-color: #1a9fff; }
QTabBar::tab:hover:!selected { background-color: #2a475e; color: #c7d5e0; }
QTableWidget {
    background-color: #131a21; alternate-background-color: #1b2838;
    gridline-color: #2a3f5f; border: 1px solid #2a3f5f; border-radius: 4px;
    selection-background-color: #1a9fff33; selection-color: #ffffff;
}
QTableWidget::item { padding: 2px 6px; border: none; }
QTableWidget::item:selected { background-color: #1a9fff44; color: #ffffff; }
QHeaderView::section {
    background-color: #1b2838; color: #8ba0b4; padding: 5px 6px; border: none;
    border-right: 1px solid #2a3f5f; border-bottom: 2px solid #1a9fff;
    font-weight: 600; font-size: 11px;
}
QPushButton {
    background-color: #1a9fff; color: #ffffff; border: none;
    padding: 6px 14px; border-radius: 4px; font-weight: 600;
    font-size: 12px; min-height: 28px; max-height: 28px;
}
QPushButton:hover { background-color: #2daeff; }
QPushButton:pressed { background-color: #0f8ae8; }
QPushButton:disabled { background-color: #2a3f5f; color: #4a6a8a; }
QPushButton#btn_secondary { background-color: #2a475e; color: #c7d5e0; border: 1px solid #3d6680; }
QPushButton#btn_secondary:hover { background-color: #3d6680; }
QPushButton#btn_freeze {
    background-color: #2a475e; color: #c7d5e0; border: 2px solid #4a90d9;
    font-size: 12px; padding: 5px 12px; min-height: 28px; max-height: 28px;
}
QPushButton#btn_freeze:checked { background-color: #1c3a5a; border-color: #5aade0; color: #7ec8ff; }
QPushButton#btn_pick {
    background-color: #4c6b22; color: #a4d007; border: 2px solid #a4d007;
    font-size: 13px; font-weight: 700;
    padding: 8px 24px; min-height: 38px; max-height: 38px; border-radius: 5px;
}
QPushButton#btn_pick:hover { background-color: #5c8029; border-color: #c7e84c; color: #c7e84c; }
QPushButton#btn_pick:disabled { background-color: #1e2d0f; border-color: #3a4a1a; color: #4a6020; }
QPushButton#btn_accept {
    background-color: #1a5e1a; color: #7ddb7d; border: 1px solid #4a9a4a;
    font-size: 12px; font-weight: 700;
    padding: 5px 16px; min-height: 30px; max-height: 30px; border-radius: 4px;
}
QPushButton#btn_accept:hover { background-color: #226622; }
QPushButton#btn_launch {
    background-color: #1a4a7a; color: #5bc8ff; border: 2px solid #1a9fff;
    font-size: 13px; font-weight: 700;
    padding: 7px 20px; min-height: 36px; max-height: 36px; border-radius: 5px;
}
QPushButton#btn_launch:hover { background-color: #1f5a94; border-color: #5bc8ff; }
QPushButton#btn_reroll {
    background-color: #2a3a50; color: #8ba0b4; border: 1px solid #3a5a7a;
    font-size: 12px; padding: 5px 16px; min-height: 30px; max-height: 30px; border-radius: 4px;
}
QPushButton#btn_reroll:hover { background-color: #3a5270; }
QPushButton#btn_danger_inline {
    background-color: transparent; color: #c9302c; border: 1px solid #c9302c;
    font-size: 11px; padding: 2px 6px; min-height: 22px; max-height: 22px; border-radius: 3px;
}
QPushButton#btn_danger_inline:hover { background-color: #c9302c22; }
QPushButton#btn_note_has {
    background-color: #1a3a1a; color: #7db840; border: 1px solid #4c6b22;
    font-size: 11px; padding: 2px 6px; min-height: 22px; max-height: 22px; border-radius: 3px;
}
QPushButton#btn_note_has:hover { background-color: #2a4a20; }
QPushButton#btn_note_empty {
    background-color: transparent; color: #4a6a8a; border: 1px solid #2a3f5f;
    font-size: 11px; padding: 2px 6px; min-height: 22px; max-height: 22px; border-radius: 3px;
}
QPushButton#btn_note_empty:hover { background-color: #1a9fff11; color: #8ba0b4; }
QPushButton#btn_add_lib {
    background-color: transparent; color: #7db840; border: 1px solid #4c6b22;
    font-size: 11px; padding: 2px 6px; min-height: 22px; max-height: 22px; border-radius: 3px;
}
QPushButton#btn_add_lib:hover { background-color: #2a4a20; }
QPushButton#btn_archive {
    background-color: transparent; color: #d4851a; border: 1px solid #d4851a;
    font-size: 11px; padding: 2px 6px; min-height: 22px; max-height: 22px; border-radius: 3px;
}
QPushButton#btn_archive:hover { background-color: #d4851a22; }
QPushButton#btn_restore {
    background-color: transparent; color: #4a9a9a; border: 1px solid #4a9a9a;
    font-size: 11px; padding: 2px 6px; min-height: 22px; max-height: 22px; border-radius: 3px;
}
QPushButton#btn_restore:hover { background-color: #4a9a9a22; }
QLineEdit {
    background-color: #131a21; color: #c7d5e0; border: 1px solid #2a3f5f;
    border-radius: 4px; padding: 6px 10px; font-size: 13px; min-height: 28px;
}
QLineEdit:focus { border-color: #1a9fff; background-color: #1b2838; }
QComboBox {
    background-color: #131a21; color: #c7d5e0; border: 1px solid #2a3f5f;
    border-radius: 4px; padding: 4px 10px; min-height: 28px;
}
QComboBox:focus { border-color: #1a9fff; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background-color: #1b2838; color: #c7d5e0; selection-background-color: #1a9fff; }
QSlider::groove:horizontal { background: #2a3f5f; height: 6px; border-radius: 3px; }
QSlider::handle:horizontal {
    background: #1a9fff; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px;
}
QSlider::sub-page:horizontal { background: #1a9fff; border-radius: 3px; }
QLabel { color: #c7d5e0; background: transparent; }
QLabel#title { font-size: 20px; font-weight: 700; color: #ffffff; letter-spacing: 1px; }
QLabel#subtitle { font-size: 11px; color: #8ba0b4; }
QLabel#section_title { font-size: 14px; font-weight: 600; color: #c7d5e0; }
QLabel#stat { font-size: 18px; font-weight: 700; color: #1a9fff; }
QLabel#stat_label { font-size: 10px; color: #8ba0b4; }
QLabel#mood_value { font-size: 14px; font-weight: 700; color: #1a9fff; min-width: 30px; }
QStatusBar { background-color: #1b2838; color: #8ba0b4; border-top: 1px solid #2a3f5f; font-size: 12px; }
QFrame#separator { background-color: #2a3f5f; max-height: 1px; }
QFrame#card { background-color: #1b2838; border: 1px solid #2a3f5f; border-radius: 6px; }
QFrame#freeze_banner { background-color: #0d1e2e; border: 2px solid #5aade0; border-radius: 6px; }
QFrame#mood_frame { background-color: #131a21; border: 1px solid #2a3f5f; border-radius: 5px; }
QFrame#pick_frame { background-color: #111d2b; border: 1px solid #1a9fff55; border-left: 3px solid #1a9fff; border-radius: 5px; }
QFrame#launch_frame { background-color: #0d1a10; border: 1px solid #4a9a4a55; border-left: 3px solid #4a9a4a; border-radius: 5px; }
QFrame#note_display { background-color: #131a21; border: 1px solid #2a3f5f; border-radius: 4px; }
QFrame#note_card { background-color: #1b2838; border: 1px solid #2a3f5f; border-left: 3px solid #1a9fff; border-radius: 4px; }
QFrame#stat_banner { background-color: #1b2838; border: 1px solid #2a3f5f; border-radius: 6px; }
QProgressBar { background-color: #131a21; border: 1px solid #2a3f5f; border-radius: 3px; height: 6px; }
QProgressBar::chunk { background-color: #1a9fff; border-radius: 3px; }
QScrollBar:vertical { background-color: #131a21; width: 8px; border: none; }
QScrollBar::handle:vertical { background-color: #2a475e; border-radius: 4px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background-color: #3d6680; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background-color: #131a21; height: 8px; border: none; }
QScrollBar::handle:horizontal { background-color: #2a475e; border-radius: 4px; }
QTextEdit {
    background-color: #131a21; color: #c7d5e0; border: 1px solid #2a3f5f;
    border-radius: 4px; padding: 8px; font-size: 13px;
}
QTextEdit:focus { border-color: #1a9fff; background-color: #1b2838; }
"""


# ─────────────────────────────────────────────
#  DATABASE
# ─────────────────────────────────────────────
class Database:
    def __init__(self, db_path="aqua_jouer.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
        self._migrate()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY, value TEXT
            );
            CREATE TABLE IF NOT EXISTS games (
                appid             INTEGER PRIMARY KEY,
                name              TEXT    NOT NULL,
                playtime_min      INTEGER DEFAULT 0,
                in_playlist       INTEGER DEFAULT 0,
                in_archive        INTEGER DEFAULT 0,
                completion_status TEXT    DEFAULT 'en_cours',
                archived_at       TEXT    DEFAULT NULL,
                added_at          TEXT
            );
            CREATE TABLE IF NOT EXISTS playlist_meta (
                appid         INTEGER PRIMARY KEY,
                priority      REAL    DEFAULT 50.0,
                last_launched TEXT    DEFAULT NULL,
                FOREIGN KEY (appid) REFERENCES games(appid)
            );
            CREATE TABLE IF NOT EXISTS notes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                appid      INTEGER NOT NULL,
                content    TEXT    NOT NULL,
                created_at TEXT    NOT NULL,
                updated_at TEXT    NOT NULL,
                FOREIGN KEY (appid) REFERENCES games(appid)
            );
            CREATE TABLE IF NOT EXISTS history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                appid           INTEGER NOT NULL,
                name_snapshot   TEXT    NOT NULL,
                action          TEXT    NOT NULL,
                planned_minutes INTEGER DEFAULT NULL,
                happened_at     TEXT    NOT NULL
            );
        """)
        self.conn.commit()

    def _migrate(self):
        for sql in [
            "ALTER TABLE playlist_meta ADD COLUMN last_launched TEXT DEFAULT NULL",
            "ALTER TABLE games ADD COLUMN in_archive INTEGER DEFAULT 0",
            "ALTER TABLE games ADD COLUMN completion_status TEXT DEFAULT 'en_cours'",
            "ALTER TABLE games ADD COLUMN archived_at TEXT DEFAULT NULL",
        ]:
            try:
                self.conn.execute(sql); self.conn.commit()
            except Exception:
                pass
        # De-duplicate notes (old schemas without UNIQUE)
        try:
            self.conn.execute(
                "DELETE FROM notes WHERE id NOT IN "
                "(SELECT MAX(id) FROM notes GROUP BY appid)"
            )
            self.conn.commit()
        except Exception:
            pass

    # ── Settings ──────────────────────────────
    def get_setting(self, key, default=""):
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        self.conn.execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)", (key, value))
        self.conn.commit()

    # ── Games ─────────────────────────────────
    def upsert_game(self, appid, name, playtime_min):
        now = datetime.now().isoformat()
        self.conn.execute("""
            INSERT INTO games (appid, name, playtime_min, added_at) VALUES (?,?,?,?)
            ON CONFLICT(appid) DO UPDATE SET
                name=excluded.name, playtime_min=excluded.playtime_min
        """, (appid, name, playtime_min, now))
        self.conn.commit()

    def get_library(self, search=""):
        return self.conn.execute(
            "SELECT * FROM games WHERE in_playlist=0 AND in_archive=0 AND name LIKE ? ORDER BY name",
            (f"%{search}%",)
        ).fetchall()

    def get_playlist(self):
        return self.conn.execute("""
            SELECT g.*, COALESCE(pm.priority, 50.0) AS priority,
                   pm.last_launched AS last_launched
            FROM games g
            LEFT JOIN playlist_meta pm ON pm.appid = g.appid
            WHERE g.in_playlist = 1
            ORDER BY priority DESC
        """).fetchall()

    def add_to_playlist(self, appid, priority=PRIORITY_DEFAULT):
        count = self.conn.execute(
            "SELECT COUNT(*) FROM games WHERE in_playlist=1"
        ).fetchone()[0]
        if count >= 10:
            return False, t("pl_full")
        self.conn.execute(
            "UPDATE games SET in_playlist=1, completion_status='en_cours' WHERE appid=?",
            (appid,)
        )
        self.conn.execute(
            "INSERT OR REPLACE INTO playlist_meta (appid, priority) VALUES (?,?)",
            (appid, float(priority))
        )
        self.conn.commit()
        return True, ""

    def remove_from_playlist(self, appid):
        self.conn.execute("UPDATE games SET in_playlist=0 WHERE appid=?", (appid,))
        self.conn.execute("DELETE FROM playlist_meta WHERE appid=?", (appid,))
        self.conn.commit()

    def archive_game(self, appid, completion_status):
        now = datetime.now().isoformat()
        self.conn.execute("""
            UPDATE games
            SET in_playlist=0, in_archive=1, completion_status=?, archived_at=?
            WHERE appid=?
        """, (completion_status, now, appid))
        self.conn.execute("DELETE FROM playlist_meta WHERE appid=?", (appid,))
        self.conn.commit()

    def restore_from_archive(self, appid):
        self.conn.execute("""
            UPDATE games
            SET in_archive=0, completion_status='en_cours', archived_at=NULL
            WHERE appid=?
        """, (appid,))
        self.conn.commit()

    def get_archive(self):
        return self.conn.execute(
            "SELECT * FROM games WHERE in_archive=1 ORDER BY archived_at DESC"
        ).fetchall()

    def get_priority(self, appid):
        row = self.conn.execute(
            "SELECT priority FROM playlist_meta WHERE appid=?", (appid,)
        ).fetchone()
        return row["priority"] if row else PRIORITY_DEFAULT

    def set_priority(self, appid, value):
        value = max(SCORE_MIN, min(SCORE_MAX, float(value)))
        self.conn.execute(
            "UPDATE playlist_meta SET priority=? WHERE appid=?", (value, appid)
        )
        self.conn.commit()

    def record_launch(self, appid):
        now  = datetime.now().isoformat()
        prio = self.get_priority(appid)
        new  = max(SCORE_MIN, prio - DECAY_LAUNCH)
        self.conn.execute(
            "UPDATE playlist_meta SET last_launched=?, priority=? WHERE appid=?",
            (now, new, appid)
        )
        self.conn.commit()

    # ── Notes ─────────────────────────────────
    def save_note(self, appid, content):
        now      = datetime.now().isoformat()
        existing = self.conn.execute("SELECT id FROM notes WHERE appid=?", (appid,)).fetchone()
        if existing:
            self.conn.execute(
                "UPDATE notes SET content=?, updated_at=? WHERE appid=?",
                (content, now, appid)
            )
        else:
            self.conn.execute(
                "INSERT INTO notes (appid, content, created_at, updated_at) VALUES (?,?,?,?)",
                (appid, content, now, now)
            )
        self.conn.commit()

    def get_note(self, appid):
        return self.conn.execute("SELECT * FROM notes WHERE appid=?", (appid,)).fetchone()

    def delete_note(self, appid):
        self.conn.execute("DELETE FROM notes WHERE appid=?", (appid,))
        self.conn.commit()

    def get_all_notes(self):
        return self.conn.execute("""
            SELECT n.*, g.name AS game_name
            FROM notes n JOIN games g ON g.appid = n.appid
            ORDER BY n.updated_at DESC
        """).fetchall()

    # ── History ───────────────────────────────
    def log_history(self, appid, name_snapshot, action, planned_minutes=None):
        now = datetime.now().isoformat()
        self.conn.execute("""
            INSERT INTO history (appid, name_snapshot, action, planned_minutes, happened_at)
            VALUES (?,?,?,?,?)
        """, (appid, name_snapshot, action, planned_minutes, now))
        self.conn.commit()

    def get_history(self, limit=100):
        return self.conn.execute(
            "SELECT * FROM history ORDER BY happened_at DESC LIMIT ?", (limit,)
        ).fetchall()

    def get_history_summary(self):
        return self.conn.execute("""
            SELECT appid, name_snapshot,
                   COUNT(CASE WHEN action='launched' THEN 1 END) AS sessions,
                   SUM(CASE WHEN action='launched' THEN COALESCE(planned_minutes,0) END) AS total_minutes,
                   MAX(happened_at) AS last_session
            FROM history
            GROUP BY appid
            HAVING sessions > 0
            ORDER BY last_session DESC
        """).fetchall()

    # ── Counters ──────────────────────────────
    def count_total(self):
        return self.conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    def count_library(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM games WHERE in_playlist=0 AND in_archive=0"
        ).fetchone()[0]
    def count_playlist(self):
        return self.conn.execute("SELECT COUNT(*) FROM games WHERE in_playlist=1").fetchone()[0]
    def count_archive(self):
        return self.conn.execute("SELECT COUNT(*) FROM games WHERE in_archive=1").fetchone()[0]
    def close(self):
        self.conn.close()


# ─────────────────────────────────────────────
#  PRIORITY ENGINE
# ─────────────────────────────────────────────
class PriorityEngine:
    """
    Mood-aware weighted pick using a max-heap.

    The `mood` parameter (1–100) acts as an exponent on the selection weights:

        exponent = 2.0 - 4.0 * mood / 100.0

      • mood=0  → exponent= 2.0  → weight=score²  (very strong bias toward HIGH priority)
      • mood=50 → exponent= 0.0  → weight=score⁰=1 (uniform — pure random)
      • mood=25 → exponent= 1.0  → weight=score¹  (default / balanced)
      • mood=100→ exponent=-2.0  → weight=score⁻² (strong bias toward LOW priority)

    The default mood=25 reproduces the previous "score-weighted" behaviour exactly.
    """
    VARIABILITY_BAND = 20.0

    @staticmethod
    def build_heap(games):
        h = [(-g["priority"], g["appid"]) for g in games]
        heapq.heapify(h)
        return h

    @staticmethod
    def pick(db, mood=25):
        games = db.get_playlist()
        if not games:
            return None

        # Mood → exponent
        exponent = 2.0 - 4.0 * max(1, min(100, mood)) / 100.0

        # Build weights from mood-adjusted scores
        weights = []
        for g in games:
            score = max(0.01, g["priority"])  # avoid zero/negative
            w = score ** exponent if exponent >= 0 else (1.0 / score) ** (-exponent)
            weights.append(max(0.001, w))

        picked = random.choices(games, weights=weights, k=1)[0]
        return {"appid": picked["appid"], "name": picked["name"], "priority": picked["priority"]}

    @staticmethod
    def apply_accept(db, accepted_appid):
        for g in db.get_playlist():
            if g["appid"] == accepted_appid:
                db.set_priority(g["appid"], g["priority"] - DECAY_ACCEPT)
            else:
                last  = g["last_launched"] if "last_launched" in g.keys() else None
                boost = BOOST_ACCEPT * recency_factor(last) * soft_cap_factor(g["priority"])
                db.set_priority(g["appid"], g["priority"] + boost)

    @staticmethod
    def apply_refuse(db, refused_appid):
        for g in db.get_playlist():
            if g["appid"] == refused_appid:
                db.set_priority(g["appid"], g["priority"] - DECAY_REFUSE)
            else:
                last  = g["last_launched"] if "last_launched" in g.keys() else None
                boost = BOOST_REFUSE * recency_factor(last) * soft_cap_factor(g["priority"])
                db.set_priority(g["appid"], g["priority"] + boost)

    @staticmethod
    def check_inflation(db):
        games = db.get_playlist()
        if len(games) < 2:
            return False
        high = sum(1 for g in games if g["priority"] >= INFLATION_SCORE)
        return high / len(games) > INFLATION_THRESH


# ─────────────────────────────────────────────
#  STEAM SYNC THREAD
# ─────────────────────────────────────────────
class SteamSyncThread(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(int)
    error    = pyqtSignal(str)

    def __init__(self, api_key, steam_id, db):
        super().__init__()
        self.api_key  = api_key
        self.steam_id = steam_id
        self.db_path  = db.db_path

    def run(self):
        conn = sqlite3.connect(self.db_path)
        try:
            url = (
                "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
                f"?key={self.api_key}&steamid={self.steam_id}"
                "&format=json&include_appinfo=1&include_played_free_games=1"
            )
            resp  = requests.get(url, timeout=20)
            resp.raise_for_status()
            games = resp.json().get("response", {}).get("games", [])
            if not games:
                self.error.emit(t("err_no_games")); return
            total = len(games)
            now   = datetime.now().isoformat()
            for i, g in enumerate(games):
                conn.execute("""
                    INSERT INTO games (appid, name, playtime_min, added_at) VALUES (?,?,?,?)
                    ON CONFLICT(appid) DO UPDATE SET
                        name=excluded.name, playtime_min=excluded.playtime_min
                """, (g["appid"], g["name"], g.get("playtime_forever", 0), now))
                if i % 100 == 0:
                    conn.commit()
                self.progress.emit(i + 1, total)
            conn.commit()
            self.finished.emit(total)
        except requests.exceptions.ConnectionError:
            self.error.emit(t("err_connection"))
        except requests.exceptions.HTTPError as e:
            self.error.emit(t("err_http", e=e))
        except Exception as e:
            self.error.emit(t("err_unexpected", e=e))
        finally:
            conn.close()


# ─────────────────────────────────────────────
#  HELPER
# ─────────────────────────────────────────────
def _cell(widget, margins=(3, 0, 3, 0)):
    w = QWidget()
    l = QHBoxLayout(w)
    l.setContentsMargins(*margins)
    l.addWidget(widget)
    return w


# ─────────────────────────────────────────────
#  SETTINGS DIALOG (now with language selector)
# ─────────────────────────────────────────────
class SettingsDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle(t("settings_title"))
        self.setMinimumWidth(460)
        self.setStyleSheet(DARK_STYLE)
        lay = QVBoxLayout(self); lay.setSpacing(12); lay.setContentsMargins(20, 20, 20, 20)

        hdr = QLabel(t("settings_steam")); hdr.setObjectName("section_title"); lay.addWidget(hdr)
        sep = QFrame(); sep.setObjectName("separator"); sep.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(sep)

        form = QFormLayout(); form.setSpacing(10)
        self.api_key_edit = QLineEdit(db.get_setting("api_key"))
        self.api_key_edit.setPlaceholderText(t("apikey_ph"))
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.steam_id_edit = QLineEdit(db.get_setting("steam_id"))
        self.steam_id_edit.setPlaceholderText(t("steamid_ph"))
        form.addRow(t("apikey_label"),  self.api_key_edit)
        form.addRow(t("steamid_label"), self.steam_id_edit)
        lay.addLayout(form)

        # Language selector
        sep2 = QFrame(); sep2.setObjectName("separator"); sep2.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(sep2)
        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel(t("lang_label")))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Français", "fr")
        self.lang_combo.addItem("English",  "en")
        current = db.get_setting("lang", "fr")
        self.lang_combo.setCurrentIndex(0 if current == "fr" else 1)
        lang_row.addWidget(self.lang_combo); lang_row.addStretch()
        lay.addLayout(lang_row)

        # Steam help card
        info = QFrame(); info.setObjectName("card")
        il = QVBoxLayout(info); il.setContentsMargins(12, 10, 12, 10)
        t2 = QLabel(t("settings_help"))
        t2.setTextFormat(Qt.TextFormat.RichText)
        t2.setWordWrap(True)
        t2.setStyleSheet("color:#8ba0b4; font-size:12px;")
        il.addWidget(t2); lay.addWidget(info)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.button(QDialogButtonBox.StandardButton.Ok).setText(t("btn_save"))
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText(t("btn_cancel"))
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _save(self):
        k = self.api_key_edit.text().strip()
        s = self.steam_id_edit.text().strip()
        if not k or not s:
            QMessageBox.warning(self, t("err_missing_fields"), t("missing_fields"))
            return
        self.db.set_setting("api_key", k)
        self.db.set_setting("steam_id", s)
        new_lang = self.lang_combo.currentData()
        old_lang = self.db.get_setting("lang", "fr")
        self.db.set_setting("lang", new_lang)
        self.accept()
        if new_lang != old_lang:
            QMessageBox.information(
                self.parent(), t("settings_title"), t("lang_restart")
            )


# ─────────────────────────────────────────────
#  MOTIVATION DIALOG
# ─────────────────────────────────────────────
class MotivationDialog(QDialog):
    def __init__(self, game_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("motiv_title"))
        self.setMinimumWidth(390); self.setStyleSheet(DARK_STYLE)
        lay = QVBoxLayout(self); lay.setSpacing(12); lay.setContentsMargins(20, 20, 20, 20)
        sub = QLabel(t("motiv_sub")); sub.setObjectName("subtitle"); lay.addWidget(sub)
        gl = QLabel(game_name); gl.setStyleSheet("font-size:14px;font-weight:700;color:#ffffff;")
        gl.setWordWrap(True); lay.addWidget(gl)
        sep = QFrame(); sep.setObjectName("separator"); sep.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(sep)
        lay.addWidget(QLabel(t("motiv_question")))
        row = QHBoxLayout()
        self.slider = QSlider(Qt.Orientation.Horizontal); self.slider.setRange(1, 100)
        self.slider.setValue(50)
        self.val_lbl = QLabel("50")
        self.val_lbl.setStyleSheet("font-size:15px;font-weight:700;color:#1a9fff;min-width:30px;")
        self.val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slider.valueChanged.connect(lambda v: self.val_lbl.setText(str(v)))
        row.addWidget(self.slider); row.addWidget(self.val_lbl); lay.addLayout(row)
        mm = QHBoxLayout()
        lo = QLabel(t("motiv_lo")); lo.setStyleSheet("color:#4a6a8a;font-size:11px;")
        hi = QLabel(t("motiv_hi")); hi.setStyleSheet("color:#4a6a8a;font-size:11px;")
        hi.setAlignment(Qt.AlignmentFlag.AlignRight)
        mm.addWidget(lo); mm.addWidget(hi); lay.addLayout(mm)
        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.button(QDialogButtonBox.StandardButton.Ok).setText(t("btn_add"))
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText(t("btn_cancel"))
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def get_priority(self):
        return float(self.slider.value())


# ─────────────────────────────────────────────
#  SESSION DIALOG
# ─────────────────────────────────────────────
class SessionDialog(QDialog):
    def __init__(self, game_name, parent=None):
        super().__init__(parent)
        self._minutes = None
        self.setWindowTitle(t("session_title"))
        self.setMinimumWidth(400); self.setStyleSheet(DARK_STYLE)
        lay = QVBoxLayout(self); lay.setSpacing(12); lay.setContentsMargins(20, 20, 20, 20)
        gl = QLabel(game_name); gl.setStyleSheet("font-size:14px;font-weight:700;color:#7ddb7d;")
        gl.setWordWrap(True); lay.addWidget(gl)
        sep = QFrame(); sep.setObjectName("separator"); sep.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(sep)
        lay.addWidget(QLabel(t("session_question")))
        row = QHBoxLayout()
        self.slider = QSlider(Qt.Orientation.Horizontal); self.slider.setRange(1, 16)
        self.slider.setValue(4)
        self.val_lbl = QLabel("1h00")
        self.val_lbl.setStyleSheet("font-size:15px;font-weight:700;color:#1a9fff;min-width:42px;")
        self.val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slider.valueChanged.connect(self._on_slider)
        row.addWidget(self.slider); row.addWidget(self.val_lbl); lay.addLayout(row)
        mm = QHBoxLayout()
        lo = QLabel(t("session_lo")); lo.setStyleSheet("color:#4a6a8a;font-size:11px;")
        hi = QLabel(t("session_hi")); hi.setStyleSheet("color:#4a6a8a;font-size:11px;")
        hi.setAlignment(Qt.AlignmentFlag.AlignRight)
        mm.addWidget(lo); mm.addWidget(hi); lay.addLayout(mm)
        btn_row = QHBoxLayout()
        skip = QPushButton(t("btn_skip")); skip.setObjectName("btn_secondary")
        skip.clicked.connect(self._on_skip)
        ok   = QPushButton(t("btn_confirm"))
        ok.clicked.connect(self._on_confirm)
        btn_row.addWidget(skip); btn_row.addStretch(); btn_row.addWidget(ok)
        lay.addLayout(btn_row)
        self._on_slider(4)

    def _on_slider(self, v):
        mins = v * 15; h, m = divmod(mins, 60)
        self.val_lbl.setText(f"{h}h{m:02d}" if h else f"{m}m")

    def _on_confirm(self):
        self._minutes = self.slider.value() * 15; super().accept()

    def _on_skip(self):
        self._minutes = None; super().accept()

    def get_minutes(self):
        return self._minutes


# ─────────────────────────────────────────────
#  ARCHIVE DIALOG
# ─────────────────────────────────────────────
class ArchiveDialog(QDialog):
    def __init__(self, game_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("archive_title"))
        self.setMinimumWidth(360); self.setStyleSheet(DARK_STYLE)
        lay = QVBoxLayout(self); lay.setSpacing(14); lay.setContentsMargins(20, 20, 20, 20)
        lay.addWidget(QLabel(t("archive_question")))
        gl = QLabel(game_name); gl.setStyleSheet("font-size:14px;font-weight:700;color:#ffffff;")
        gl.setWordWrap(True); lay.addWidget(gl)
        sep = QFrame(); sep.setObjectName("separator"); sep.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(sep)
        row = QHBoxLayout(); row.setSpacing(10)
        t_btn = QPushButton(t("archive_finished"))
        t_btn.setStyleSheet("""
            QPushButton { background-color:#1a5e1a; color:#7ddb7d; border:1px solid #4a9a4a;
                border-radius:4px; padding:8px 16px; font-weight:700;
                min-height:32px; max-height:32px; }
            QPushButton:hover { background-color:#226622; }
        """)
        t_btn.clicked.connect(lambda: self.done(1))
        a_btn = QPushButton(t("archive_dropped"))
        a_btn.setStyleSheet("""
            QPushButton { background-color:#3a2008; color:#d4851a; border:1px solid #d4851a;
                border-radius:4px; padding:8px 16px; font-weight:700;
                min-height:32px; max-height:32px; }
            QPushButton:hover { background-color:#4a2a10; }
        """)
        a_btn.clicked.connect(lambda: self.done(2))
        c_btn = QPushButton(t("btn_cancel")); c_btn.setObjectName("btn_secondary")
        c_btn.clicked.connect(self.reject)
        row.addWidget(t_btn); row.addWidget(a_btn); row.addStretch(); row.addWidget(c_btn)
        lay.addLayout(row)


# ─────────────────────────────────────────────
#  NOTE DIALOG
# ─────────────────────────────────────────────
class NoteDialog(QDialog):
    def __init__(self, db, appid, game_name, parent=None):
        super().__init__(parent)
        self.db = db; self.appid = appid; self.game_name = game_name
        self.setWindowTitle(t("note_title", name=game_name))
        self.setMinimumSize(490, 360); self.setStyleSheet(DARK_STYLE)
        lay = QVBoxLayout(self); lay.setSpacing(10); lay.setContentsMargins(20, 18, 20, 18)
        gl = QLabel(game_name); gl.setStyleSheet("font-size:14px;font-weight:700;color:#ffffff;")
        gl.setWordWrap(True); lay.addWidget(gl)
        self.meta = QLabel(""); self.meta.setStyleSheet("color:#4a6a8a;font-size:11px;font-style:italic;")
        lay.addWidget(self.meta)
        sep = QFrame(); sep.setObjectName("separator"); sep.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(sep)
        hint = QLabel(t("note_hint")); hint.setStyleSheet("color:#4a6a8a;font-size:12px;font-style:italic;")
        lay.addWidget(hint)
        self.edit = QTextEdit(); self.edit.setPlaceholderText(t("note_ph"))
        self.edit.setMinimumHeight(150)
        self.edit.textChanged.connect(self._update_count)
        lay.addWidget(self.edit)
        self.counter = QLabel("0 / 1000")
        self.counter.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.counter.setStyleSheet("color:#4a6a8a;font-size:11px;")
        lay.addWidget(self.counter)
        row = QHBoxLayout()
        self.del_btn = QPushButton(t("btn_erase")); self.del_btn.setObjectName("btn_danger_inline")
        self.del_btn.clicked.connect(self._delete)
        save   = QPushButton(t("btn_save_note"))
        cancel = QPushButton(t("btn_cancel")); cancel.setObjectName("btn_secondary")
        save.clicked.connect(self.accept); cancel.clicked.connect(self.reject)
        row.addWidget(self.del_btn); row.addStretch(); row.addWidget(cancel); row.addWidget(save)
        lay.addLayout(row)
        self._load()

    def _load(self):
        note = self.db.get_note(self.appid)
        if note:
            self.edit.setPlainText(note["content"])
            dt = note["updated_at"][:16].replace("T", " à " if LANG == "fr" else " at ")
            self.meta.setText(t("note_last", dt=dt)); self.del_btn.setEnabled(True)
        else:
            self.meta.setText(t("note_new")); self.del_btn.setEnabled(False)

    def _update_count(self):
        n = len(self.edit.toPlainText()); self.counter.setText(f"{n} / 1000")
        self.counter.setStyleSheet(f"color:{'#c9302c' if n > 1000 else '#4a6a8a'};font-size:11px;")

    def _delete(self):
        if QMessageBox.question(
            self, t("settings_title"), t("note_delete_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self.db.delete_note(self.appid); self.done(2)

    def accept(self):
        content = self.edit.toPlainText().strip()
        if len(content) > 1000:
            QMessageBox.warning(self, t("settings_title"), t("note_too_long")); return
        if content:
            self.db.save_note(self.appid, content)
        super().accept()

    def get_content(self):
        return self.edit.toPlainText().strip()


# ─────────────────────────────────────────────
#  STATS WIDGET (4 counters)
# ─────────────────────────────────────────────
class StatsWidget(QFrame):
    def __init__(self):
        super().__init__(); self.setObjectName("card")
        lay = QHBoxLayout(self); lay.setSpacing(20); lay.setContentsMargins(16, 8, 16, 8)
        self._vals = {}
        entries = [("total", "stat_total"), ("library", "stat_library"),
                   ("playlist", "stat_playlist"), ("archive", "stat_archive")]
        for i, (key, lbl_key) in enumerate(entries):
            col = QVBoxLayout(); col.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v = QLabel("0"); v.setObjectName("stat"); v.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l = QLabel(t(lbl_key).upper()); l.setObjectName("stat_label")
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.addWidget(v); col.addWidget(l); lay.addLayout(col); self._vals[key] = v
            if i < len(entries) - 1:
                s = QFrame(); s.setFrameShape(QFrame.Shape.VLine)
                s.setStyleSheet("background-color:#2a3f5f;max-width:1px;")
                lay.addWidget(s)

    def update(self, total, library, playlist, archive):
        self._vals["total"].setText(str(total))
        self._vals["library"].setText(str(library))
        self._vals["playlist"].setText(str(playlist))
        self._vals["archive"].setText(str(archive))


# ─────────────────────────────────────────────
#  LIBRARY VIEW
# ─────────────────────────────────────────────
class LibraryView(QWidget):
    def __init__(self, db, on_add):
        super().__init__(); self.db = db; self.on_add = on_add; self._build()

    def _build(self):
        lay = QVBoxLayout(self); lay.setSpacing(10); lay.setContentsMargins(14, 14, 14, 14)
        row = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText(t("search_placeholder"))
        self.search.textChanged.connect(self.refresh)
        row.addWidget(QLabel(t("search_label"))); row.addWidget(self.search); lay.addLayout(row)
        self.table = QTableWidget(); self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            t("col_appid"), t("col_name"), t("col_time"), ""
        ])
        hh = self.table.horizontalHeader(); hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col, w in [(0, 78), (2, 105), (3, 108)]:
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, w)
        self.table.verticalHeader().setVisible(False); self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False); self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        lay.addWidget(self.table)

    def refresh(self):
        games = self.db.get_library(self.search.text())
        self.table.setRowCount(len(games))
        for r, g in enumerate(games):
            self.table.setRowHeight(r, 32)
            ai = QTableWidgetItem(str(g["appid"])); ai.setForeground(QColor("#4a6a8a"))
            self.table.setItem(r, 0, ai)
            self.table.setItem(r, 1, QTableWidgetItem(g["name"]))
            h, m = divmod(g["playtime_min"], 60)
            ti = QTableWidgetItem(f"{h}h {m:02d}m" if h else f"{m}m")
            ti.setForeground(QColor("#8ba0b4")); ti.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 2, ti)
            btn = QPushButton(t("btn_add_playlist")); btn.setObjectName("btn_add_lib")
            btn.setFixedHeight(22)
            btn.clicked.connect(lambda _, aid=g["appid"], nm=g["name"]: self.on_add(aid, nm))
            self.table.setCellWidget(r, 3, _cell(btn))


# ─────────────────────────────────────────────
#  PLAYLIST VIEW
# ─────────────────────────────────────────────
class PlaylistView(QWidget):
    def __init__(self, db, on_remove, on_pick, on_note, on_launch, on_archive):
        super().__init__()
        self.db = db; self.on_remove = on_remove; self.on_pick = on_pick
        self.on_note = on_note; self.on_launch = on_launch; self.on_archive = on_archive
        self.is_frozen = False; self._current_pick_appid = None
        self._build()

    def _build(self):
        lay = QVBoxLayout(self); lay.setSpacing(10); lay.setContentsMargins(14, 14, 14, 14)

        # Top bar
        top = QHBoxLayout()
        self.count_lbl = QLabel("0"); self.count_lbl.setObjectName("subtitle")
        self.freeze_btn = QPushButton(t("btn_freeze")); self.freeze_btn.setObjectName("btn_freeze")
        self.freeze_btn.setCheckable(True); self.freeze_btn.setFixedWidth(78)
        self.freeze_btn.toggled.connect(self._toggle_freeze)
        top.addWidget(self.count_lbl); top.addStretch(); top.addWidget(self.freeze_btn)
        lay.addLayout(top)

        # Freeze banner
        self.freeze_banner = QFrame(); self.freeze_banner.setObjectName("freeze_banner")
        fb = QHBoxLayout(self.freeze_banner); fb.setContentsMargins(12, 6, 12, 6)
        fb.addWidget(QLabel(t("freeze_msg"))); fb.addStretch()
        self.freeze_banner.hide(); lay.addWidget(self.freeze_banner)

        # Table — 6 cols
        self.table = QTableWidget(); self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            t("col_appid"), t("col_name"), t("col_time"),
            t("col_score"), t("col_actions"), ""
        ])
        hh = self.table.horizontalHeader(); hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col, w in [(0, 60), (2, 85), (3, 58), (4, 145), (5, 72)]:
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, w)
        self.table.verticalHeader().setVisible(False); self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False); self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        lay.addWidget(self.table)

        sep = QFrame(); sep.setObjectName("separator"); sep.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(sep)

        # ── Mood slider ──────────────────────────────────
        mood_frame = QFrame(); mood_frame.setObjectName("mood_frame")
        mf = QHBoxLayout(mood_frame); mf.setContentsMargins(10, 6, 10, 6); mf.setSpacing(10)
        mood_lbl = QLabel(t("mood_label")); mood_lbl.setStyleSheet("color:#8ba0b4;font-size:12px;")
        self.mood_slider = QSlider(Qt.Orientation.Horizontal)
        self.mood_slider.setRange(1, 100); self.mood_slider.setValue(25)
        self.mood_slider.setToolTip(t("mood_tooltip"))
        self.mood_val_lbl = QLabel("")
        self.mood_val_lbl.setObjectName("mood_value")
        self.mood_val_lbl.setMinimumWidth(86)
        self.mood_slider.valueChanged.connect(self._on_mood_change)
        lo = QLabel(t("mood_safe")); lo.setStyleSheet("color:#4a6a8a;font-size:11px;")
        hi = QLabel(t("mood_explore")); hi.setStyleSheet("color:#4a6a8a;font-size:11px;")
        mf.addWidget(mood_lbl)
        mf.addWidget(lo)
        mf.addWidget(self.mood_slider, 1)
        mf.addWidget(hi)
        mf.addWidget(self.mood_val_lbl)
        lay.addWidget(mood_frame)
        self._on_mood_change(25)   # init label

        # Pick button
        pick_row = QHBoxLayout(); pick_row.addStretch()
        self.pick_btn = QPushButton(t("btn_pick")); self.pick_btn.setObjectName("btn_pick")
        self.pick_btn.clicked.connect(self.on_pick)
        pick_row.addWidget(self.pick_btn); pick_row.addStretch()
        lay.addLayout(pick_row)

        # ── Pick frame (phase 1) ──
        self.pick_frame = QFrame(); self.pick_frame.setObjectName("pick_frame"); self.pick_frame.hide()
        pf = QVBoxLayout(self.pick_frame); pf.setContentsMargins(14, 10, 14, 10); pf.setSpacing(6)
        self.pick_name_lbl  = QLabel(""); self.pick_name_lbl.setStyleSheet("font-size:13px;font-weight:700;color:#ffffff;")
        self.pick_score_lbl = QLabel(""); self.pick_score_lbl.setStyleSheet("color:#8ba0b4;font-size:11px;")
        ar = QHBoxLayout(); ar.addStretch()
        self.accept_btn = QPushButton(t("btn_accept")); self.accept_btn.setObjectName("btn_accept")
        self.reroll_btn = QPushButton(t("btn_refuse")); self.reroll_btn.setObjectName("btn_reroll")
        ar.addWidget(self.accept_btn); ar.addWidget(self.reroll_btn); ar.addStretch()
        pf.addWidget(self.pick_name_lbl); pf.addWidget(self.pick_score_lbl); pf.addLayout(ar)
        lay.addWidget(self.pick_frame)

        # ── Launch frame (phase 2) ──
        self.launch_frame = QFrame(); self.launch_frame.setObjectName("launch_frame"); self.launch_frame.hide()
        lf = QVBoxLayout(self.launch_frame); lf.setContentsMargins(14, 10, 14, 10); lf.setSpacing(8)
        self.launch_game_lbl = QLabel("")
        self.launch_game_lbl.setStyleSheet("font-size:13px;font-weight:700;color:#7ddb7d;")
        lf.addWidget(self.launch_game_lbl)
        self.note_display_frame = QFrame(); self.note_display_frame.setObjectName("note_display")
        ndf = QVBoxLayout(self.note_display_frame); ndf.setContentsMargins(10, 8, 10, 8); ndf.setSpacing(4)
        note_hdr = QLabel(t("note_hdr")); note_hdr.setStyleSheet("color:#8ba0b4;font-size:11px;font-weight:600;")
        self.note_content_lbl = QLabel(""); self.note_content_lbl.setWordWrap(True)
        self.note_content_lbl.setStyleSheet("color:#c7d5e0;font-size:12px;")
        ndf.addWidget(note_hdr); ndf.addWidget(self.note_content_lbl)
        lf.addWidget(self.note_display_frame)
        lb_row = QHBoxLayout(); lb_row.addStretch()
        self.launch_btn = QPushButton(t("btn_launch")); self.launch_btn.setObjectName("btn_launch")
        self.cancel_launch_btn = QPushButton(t("btn_cancel")); self.cancel_launch_btn.setObjectName("btn_secondary")
        self.cancel_launch_btn.clicked.connect(self.reset_pick_ui)
        lb_row.addWidget(self.cancel_launch_btn); lb_row.addWidget(self.launch_btn); lb_row.addStretch()
        lf.addLayout(lb_row)
        lay.addWidget(self.launch_frame)

    def _on_mood_change(self, v):
        """Update mood label: semantic description based on value."""
        if v <= 20:
            desc = t("mood_safe")
            color = "#1a9fff"
        elif v <= 40:
            desc = f"{v}"
            color = "#5bc8ff"
        elif v <= 60:
            desc = f"{v}"
            color = "#c7d5e0"
        elif v <= 80:
            desc = f"{v}"
            color = "#f4a444"
        else:
            desc = t("mood_explore")
            color = "#a4d007"
        if 21 <= v <= 79:
            self.mood_val_lbl.setText(str(v))
        else:
            self.mood_val_lbl.setText(desc)
        self.mood_val_lbl.setStyleSheet(f"font-size:13px;font-weight:700;color:{color};min-width:86px;")

    def get_mood(self):
        return self.mood_slider.value()

    def _toggle_freeze(self, checked):
        self.is_frozen = checked
        self.freeze_btn.setText(t("btn_unfreeze") if checked else t("btn_freeze"))
        self.freeze_banner.setVisible(checked)
        self.pick_btn.setEnabled(not checked)
        eff = QGraphicsOpacityEffect(); eff.setOpacity(0.35)
        self.table.setGraphicsEffect(eff if checked else None)

    def refresh(self):
        games = self.db.get_playlist()
        n = len(games)
        self.count_lbl.setText(t("pl_count", n=n))
        self.table.setRowCount(n)
        for r, g in enumerate(games):
            self.table.setRowHeight(r, 32)
            ai = QTableWidgetItem(str(g["appid"])); ai.setForeground(QColor("#4a6a8a"))
            self.table.setItem(r, 0, ai)
            ni = QTableWidgetItem(g["name"])
            if g["appid"] == self._current_pick_appid:
                ni.setForeground(QColor("#a4d007"))
            self.table.setItem(r, 1, ni)
            h, m = divmod(g["playtime_min"], 60)
            ti = QTableWidgetItem(f"{h}h {m:02d}m" if h else f"{m}m")
            ti.setForeground(QColor("#8ba0b4")); ti.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 2, ti)
            prio = g["priority"]
            pi = QTableWidgetItem(f"{prio:.0f}")
            pi.setForeground(QColor("#a4d007" if prio >= 70 else "#1a9fff" if prio >= 40 else "#8ba0b4"))
            pi.setTextAlignment(Qt.AlignmentFlag.AlignCenter); self.table.setItem(r, 3, pi)
            has_note = self.db.get_note(g["appid"]) is not None
            note_btn = QPushButton(t("btn_note_has" if has_note else "btn_note_empty"))
            note_btn.setFixedHeight(22)
            note_btn.setObjectName("btn_note_has" if has_note else "btn_note_empty")
            note_btn.clicked.connect(lambda _, aid=g["appid"], nm=g["name"]: self.on_note(aid, nm))
            arch_btn = QPushButton(t("btn_archive")); arch_btn.setObjectName("btn_archive"); arch_btn.setFixedHeight(22)
            arch_btn.clicked.connect(lambda _, aid=g["appid"], nm=g["name"]: self.on_archive(aid, nm))
            aw = QWidget(); al = QHBoxLayout(aw); al.setContentsMargins(3, 0, 3, 0); al.setSpacing(4)
            al.addWidget(note_btn); al.addWidget(arch_btn)
            self.table.setCellWidget(r, 4, aw)
            rem_btn = QPushButton(t("btn_remove")); rem_btn.setObjectName("btn_danger_inline"); rem_btn.setFixedHeight(22)
            rem_btn.clicked.connect(lambda _, aid=g["appid"]: self.on_remove(aid))
            self.table.setCellWidget(r, 5, _cell(rem_btn))
        self.pick_btn.setEnabled(n >= 1 and not self.is_frozen)

    def show_pick(self, name, appid, score):
        self._current_pick_appid = appid
        self.pick_name_lbl.setText(t("pick_suggestion", name=name))
        self.pick_score_lbl.setText(t("pick_score", score=f"{score:.0f}"))
        self.pick_frame.show(); self.launch_frame.hide(); self.refresh()

    def show_launch(self, name, appid, note_content, planned_minutes):
        self._current_pick_appid = appid
        dur = t("launch_dur", n=planned_minutes) if planned_minutes else ""
        self.launch_game_lbl.setText(t("launch_title", name=name) + dur)
        if note_content:
            self.note_content_lbl.setText(note_content); self.note_display_frame.show()
        else:
            self.note_display_frame.hide()
        try:
            self.launch_btn.clicked.disconnect()
        except Exception:
            pass
        self.launch_btn.clicked.connect(lambda: self.on_launch(appid, name, planned_minutes))
        self.pick_frame.hide(); self.launch_frame.show(); self.refresh()

    def reset_pick_ui(self):
        self._current_pick_appid = None; self.pick_frame.hide(); self.launch_frame.hide(); self.refresh()


# ─────────────────────────────────────────────
#  ARCHIVE VIEW
# ─────────────────────────────────────────────
class ArchiveView(QWidget):
    def __init__(self, db, on_restore):
        super().__init__(); self.db = db; self.on_restore = on_restore; self._build()

    def _build(self):
        lay = QVBoxLayout(self); lay.setSpacing(10); lay.setContentsMargins(14, 14, 14, 14)
        hr = QHBoxLayout()
        lbl = QLabel(t("archive_section")); lbl.setObjectName("section_title")
        self.count_lbl = QLabel(""); self.count_lbl.setObjectName("subtitle")
        hr.addWidget(lbl); hr.addStretch(); hr.addWidget(self.count_lbl); lay.addLayout(hr)
        sep = QFrame(); sep.setObjectName("separator"); sep.setFrameShape(QFrame.Shape.HLine); lay.addWidget(sep)
        self.table = QTableWidget(); self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([t("col_name"), t("col_status"), t("col_archived"), ""])
        hh = self.table.horizontalHeader(); hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col, w in [(1, 90), (2, 130), (3, 90)]:
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(col, w)
        self.table.verticalHeader().setVisible(False); self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False); self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        lay.addWidget(self.table)
        self.empty_lbl = QLabel(t("archive_empty"))
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.setStyleSheet("color:#4a6a8a;font-size:13px;")
        lay.addWidget(self.empty_lbl)

    def refresh(self):
        games = self.db.get_archive(); n = len(games)
        self.count_lbl.setText(f"{n}")
        if not games:
            self.empty_lbl.show(); self.table.hide(); return
        self.empty_lbl.hide(); self.table.show(); self.table.setRowCount(n)
        status_map = {
            "termine":   (t("status_finished"), "#4a9a4a"),
            "abandonne": (t("status_dropped"),  "#d4851a"),
            "en_cours":  (t("status_playing"),  "#1a9fff"),
        }
        for r, g in enumerate(games):
            self.table.setRowHeight(r, 32)
            self.table.setItem(r, 0, QTableWidgetItem(g["name"]))
            status = g["completion_status"] or "en_cours"
            label, color = status_map.get(status, ("?", "#8ba0b4"))
            si = QTableWidgetItem(label); si.setForeground(QColor(color))
            si.setTextAlignment(Qt.AlignmentFlag.AlignCenter); self.table.setItem(r, 1, si)
            archived = (g["archived_at"] or "")[:10]
            ai = QTableWidgetItem(archived); ai.setForeground(QColor("#8ba0b4"))
            ai.setTextAlignment(Qt.AlignmentFlag.AlignCenter); self.table.setItem(r, 2, ai)
            rb = QPushButton(t("btn_restore")); rb.setObjectName("btn_restore"); rb.setFixedHeight(22)
            rb.clicked.connect(lambda _, aid=g["appid"], nm=g["name"]: self.on_restore(aid, nm))
            self.table.setCellWidget(r, 3, _cell(rb))


# ─────────────────────────────────────────────
#  HISTORY VIEW
# ─────────────────────────────────────────────
class HistoryView(QWidget):
    def __init__(self, db):
        super().__init__(); self.db = db; self._build()

    def _action_label(self, action):
        mapping = {
            "picked":             (t("action_picked"),   "#4a6a8a"),
            "accepted":           (t("action_accepted"), "#1a9fff"),
            "refused":            (t("action_refused"),  "#c9302c"),
            "launched":           (t("action_launched"), "#4a9a4a"),
            "archived_termine":   (t("action_archived_t"), "#4a9a4a"),
            "archived_abandonne": (t("action_archived_a"), "#d4851a"),
        }
        return mapping.get(action, (action, "#8ba0b4"))

    def _build(self):
        lay = QVBoxLayout(self); lay.setSpacing(10); lay.setContentsMargins(14, 14, 14, 14)
        hr = QHBoxLayout()
        lbl = QLabel(t("history_section")); lbl.setObjectName("section_title")
        hr.addWidget(lbl); hr.addStretch(); lay.addLayout(hr)
        sep = QFrame(); sep.setObjectName("separator"); sep.setFrameShape(QFrame.Shape.HLine); lay.addWidget(sep)
        self.stat_banner = QFrame(); self.stat_banner.setObjectName("stat_banner")
        sb = QHBoxLayout(self.stat_banner); sb.setContentsMargins(16, 8, 16, 8); sb.setSpacing(24)
        self._s_sessions = self._stat_col(sb, t("stat_sessions"))
        self._s_hours    = self._stat_col(sb, t("stat_hours"))
        self._s_games    = self._stat_col(sb, t("stat_games_touched"))
        lay.addWidget(self.stat_banner)
        self.table = QTableWidget(); self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            t("col_datetime"), t("col_name"), t("col_action"), t("col_duration")
        ])
        hh = self.table.horizontalHeader(); hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col, w in [(0, 122), (2, 90), (3, 95)]:
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(col, w)
        self.table.verticalHeader().setVisible(False); self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False); self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        lay.addWidget(self.table)
        self.empty_lbl = QLabel(t("history_empty"))
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.setStyleSheet("color:#4a6a8a;font-size:13px;")
        lay.addWidget(self.empty_lbl)

    @staticmethod
    def _stat_col(parent_lay, label):
        col = QVBoxLayout(); col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v = QLabel("0"); v.setObjectName("stat"); v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l = QLabel(label.upper()); l.setObjectName("stat_label"); l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.addWidget(v); col.addWidget(l); parent_lay.addLayout(col); return v

    def refresh(self):
        events  = self.db.get_history()
        summary = self.db.get_history_summary()
        total_sessions = sum(r["sessions"] for r in summary)
        total_mins     = sum(r["total_minutes"] or 0 for r in summary)
        h, m = divmod(int(total_mins), 60)
        self._s_sessions.setText(str(total_sessions))
        self._s_hours.setText(f"{h}h{m:02d}" if h else (f"{m}m" if m else "—"))
        self._s_games.setText(str(len(summary)))
        if not events:
            self.empty_lbl.show(); self.table.hide(); self.stat_banner.hide(); return
        self.empty_lbl.hide(); self.table.show(); self.stat_banner.show()
        self.table.setRowCount(len(events))
        for r, e in enumerate(events):
            self.table.setRowHeight(r, 32)
            dt = e["happened_at"][:16].replace("T", " ")
            di = QTableWidgetItem(dt); di.setForeground(QColor("#4a6a8a")); self.table.setItem(r, 0, di)
            self.table.setItem(r, 1, QTableWidgetItem(e["name_snapshot"]))
            label, color = self._action_label(e["action"])
            ai = QTableWidgetItem(label); ai.setForeground(QColor(color))
            ai.setTextAlignment(Qt.AlignmentFlag.AlignCenter); self.table.setItem(r, 2, ai)
            mins = e["planned_minutes"]
            if mins:
                hh, mm = divmod(int(mins), 60)
                dur_str = f"{hh}h{mm:02d}" if hh else f"{mm}m"
            else:
                dur_str = "—"
            di2 = QTableWidgetItem(dur_str); di2.setForeground(QColor("#8ba0b4"))
            di2.setTextAlignment(Qt.AlignmentFlag.AlignCenter); self.table.setItem(r, 3, di2)


# ─────────────────────────────────────────────
#  NOTES VIEW
# ─────────────────────────────────────────────
class NotesView(QWidget):
    def __init__(self, db, on_edit):
        super().__init__(); self.db = db; self.on_edit = on_edit; self._build()

    def _build(self):
        lay = QVBoxLayout(self); lay.setSpacing(10); lay.setContentsMargins(14, 14, 14, 14)
        hr = QHBoxLayout()
        lbl = QLabel(t("notes_section")); lbl.setObjectName("section_title")
        self.count_lbl = QLabel(""); self.count_lbl.setObjectName("subtitle")
        hr.addWidget(lbl); hr.addStretch(); hr.addWidget(self.count_lbl); lay.addLayout(hr)
        sep = QFrame(); sep.setObjectName("separator"); sep.setFrameShape(QFrame.Shape.HLine); lay.addWidget(sep)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        self.inner = QWidget(); self.inner_lay = QVBoxLayout(self.inner)
        self.inner_lay.setSpacing(8); self.inner_lay.setContentsMargins(0, 0, 6, 0)
        self.inner_lay.addStretch(); self.scroll.setWidget(self.inner); lay.addWidget(self.scroll)
        self.empty_lbl = QLabel(t("notes_empty"))
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.setStyleSheet("color:#4a6a8a;font-size:13px;")
        lay.addWidget(self.empty_lbl)

    def refresh(self):
        while self.inner_lay.count() > 1:
            item = self.inner_lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        notes = self.db.get_all_notes(); n = len(notes)
        self.count_lbl.setText(f"{n} note{'s' if n != 1 else ''}")
        if not notes:
            self.empty_lbl.show(); self.scroll.hide(); return
        self.empty_lbl.hide(); self.scroll.show()
        for note in notes:
            card = QFrame(); card.setObjectName("note_card")
            cl = QVBoxLayout(card); cl.setSpacing(4); cl.setContentsMargins(12, 8, 12, 8)
            tr = QHBoxLayout()
            gl = QLabel(note["game_name"]); gl.setStyleSheet("font-size:13px;font-weight:700;color:#ffffff;")
            eb = QPushButton(t("btn_edit"))
            eb.setStyleSheet("""
                QPushButton { background:transparent; color:#1a9fff; border:1px solid #1a9fff44;
                    border-radius:3px; padding:2px 8px; font-size:11px; min-height:20px; max-height:20px; }
                QPushButton:hover { background:#1a9fff22; }
            """)
            eb.clicked.connect(lambda _, aid=note["appid"], nm=note["game_name"]: self.on_edit(aid, nm))
            tr.addWidget(gl); tr.addStretch(); tr.addWidget(eb); cl.addLayout(tr)
            lines = note["content"].split("\n")
            preview = "\n".join(lines[:3]) + (" …" if len(lines) > 3 else "")
            pl = QLabel(preview); pl.setWordWrap(True); pl.setStyleSheet("color:#c7d5e0;font-size:12px;")
            cl.addWidget(pl)
            dt = note["updated_at"][:16].replace("T", " ")
            dl = QLabel(t("modified_on", dt=dt)); dl.setStyleSheet("color:#4a6a8a;font-size:11px;font-style:italic;")
            cl.addWidget(dl)
            self.inner_lay.insertWidget(self.inner_lay.count() - 1, card)


# ─────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────
class AquaJouer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db          = Database()
        self.sync_thread = None
        self._last_pick  = None

        self.setWindowTitle(t("app_title"))
        self.setMinimumSize(940, 650); self.resize(1120, 730)
        self.setStyleSheet(DARK_STYLE)
        self._build_ui(); self._refresh_all()
        QTimer.singleShot(300, self._auto_sync_on_start)

    def _build_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        root = QVBoxLayout(central); root.setSpacing(0); root.setContentsMargins(0, 0, 0, 0)

        header = QFrame()
        header.setStyleSheet("background-color:#1b2838;border-bottom:2px solid #2a3f5f;")
        header.setFixedHeight(60)
        hl = QHBoxLayout(header); hl.setContentsMargins(18, 0, 18, 0)
        logo = QLabel(t("app_title")); logo.setObjectName("title")
        sub  = QLabel(t("app_subtitle")); sub.setObjectName("subtitle")
        tcol = QVBoxLayout(); tcol.setSpacing(1); tcol.addWidget(logo); tcol.addWidget(sub)
        self.sync_btn = QPushButton(t("btn_sync")); self.sync_btn.clicked.connect(self._sync_steam)
        settings_btn  = QPushButton(t("btn_settings")); settings_btn.setObjectName("btn_secondary")
        settings_btn.clicked.connect(self._open_settings)
        hl.addLayout(tcol); hl.addStretch()
        hl.addWidget(self.sync_btn); hl.addSpacing(6); hl.addWidget(settings_btn)
        root.addWidget(header)

        self.progress_bar = QProgressBar(); self.progress_bar.setFixedHeight(3)
        self.progress_bar.setTextVisible(False); self.progress_bar.hide()
        root.addWidget(self.progress_bar)

        body = QWidget(); bl = QVBoxLayout(body); bl.setSpacing(10); bl.setContentsMargins(14, 10, 14, 10)
        self.stats = StatsWidget(); bl.addWidget(self.stats)

        self.tabs = QTabWidget()
        self.lib_view     = LibraryView(self.db, self._add_to_playlist)
        self.pl_view      = PlaylistView(
            self.db,
            on_remove  = self._remove_from_playlist,
            on_pick    = self._pick_game,
            on_note    = self._open_note,
            on_launch  = self._launch_game,
            on_archive = self._archive_game,
        )
        self.notes_view   = NotesView(self.db, self._open_note)
        self.archive_view = ArchiveView(self.db, self._restore_from_archive)
        self.history_view = HistoryView(self.db)

        self.pl_view.accept_btn.clicked.connect(self._accept_pick)
        self.pl_view.reroll_btn.clicked.connect(self._refuse_and_pick)

        self.tabs.addTab(self.lib_view,     t("tab_library"))
        self.tabs.addTab(self.pl_view,      t("tab_playlist"))
        self.tabs.addTab(self.notes_view,   t("tab_notes"))
        self.tabs.addTab(self.archive_view, t("tab_archive"))
        self.tabs.addTab(self.history_view, t("tab_history"))
        bl.addWidget(self.tabs); root.addWidget(body)

        self.status = QStatusBar(); self.setStatusBar(self.status)
        self.status.showMessage(t("app_welcome"))

    # ── Steam ─────────────────────────────────
    def _open_settings(self):
        SettingsDialog(self.db, self).exec()

    def _auto_sync_on_start(self):
        api_key  = self.db.get_setting("api_key")
        steam_id = self.db.get_setting("steam_id")
        if not api_key or not steam_id:
            self.status.showMessage(t("app_no_creds")); return
        self.sync_btn.setEnabled(False); self.sync_btn.setText(t("btn_sync_start"))
        self.progress_bar.setValue(0); self.progress_bar.show()
        self.sync_thread = SteamSyncThread(api_key, steam_id, self.db)
        self.sync_thread.progress.connect(lambda c, tt: (
            self.progress_bar.setValue(int(c / tt * 100)),
            self.status.showMessage(t("sync_progress", c=c, t=tt)),
        ))
        self.sync_thread.finished.connect(self._on_auto_sync_done)
        self.sync_thread.error.connect(self._on_sync_error)
        self.sync_thread.start()

    def _on_auto_sync_done(self, total):
        self.sync_btn.setEnabled(True); self.sync_btn.setText(t("btn_sync"))
        self.progress_bar.hide(); self._refresh_all()
        self.status.showMessage(t("sync_done", n=total))

    def _sync_steam(self):
        api_key  = self.db.get_setting("api_key")
        steam_id = self.db.get_setting("steam_id")
        if not api_key or not steam_id:
            dlg = SettingsDialog(self.db, self)
            if dlg.exec() != QDialog.DialogCode.Accepted: return
            api_key  = self.db.get_setting("api_key")
            steam_id = self.db.get_setting("steam_id")
        self.sync_btn.setEnabled(False); self.sync_btn.setText(t("btn_syncing"))
        self.progress_bar.setValue(0); self.progress_bar.show()
        self.sync_thread = SteamSyncThread(api_key, steam_id, self.db)
        self.sync_thread.progress.connect(lambda c, tt: (
            self.progress_bar.setValue(int(c / tt * 100)),
            self.status.showMessage(t("sync_progress", c=c, t=tt)),
        ))
        self.sync_thread.finished.connect(self._on_sync_done)
        self.sync_thread.error.connect(self._on_sync_error)
        self.sync_thread.start()

    def _on_sync_done(self, total):
        self.sync_btn.setEnabled(True); self.sync_btn.setText(t("btn_sync"))
        self.progress_bar.hide(); self._refresh_all()
        self.status.showMessage(t("sync_manual_done", n=total))

    def _on_sync_error(self, msg):
        self.sync_btn.setEnabled(True); self.sync_btn.setText(t("btn_sync"))
        self.progress_bar.hide()
        QMessageBox.critical(self, t("err_sync_title"), msg)
        self.status.showMessage(t("sync_fail"))

    # ── Playlist ──────────────────────────────
    def _add_to_playlist(self, appid, name):
        dlg = MotivationDialog(name, self)
        if dlg.exec() != QDialog.DialogCode.Accepted: return
        prio = dlg.get_priority()
        ok, err = self.db.add_to_playlist(appid, prio)
        if not ok:
            QMessageBox.warning(self, t("app_title"), err); return
        self._refresh_all(); self.tabs.setCurrentIndex(1)
        self.status.showMessage(t("added_pl", name=name, prio=f"{prio:.0f}"))

    def _remove_from_playlist(self, appid):
        self.db.remove_from_playlist(appid)
        if self._last_pick == appid:
            self._last_pick = None; self.pl_view.reset_pick_ui()
        self._refresh_all(); self.status.showMessage(t("removed_pl"))

    def _archive_game(self, appid, name):
        dlg = ArchiveDialog(name, self)
        result = dlg.exec()
        if result == 0: return
        status = "termine" if result == 1 else "abandonne"
        self.db.archive_game(appid, status)
        self.db.log_history(appid, name, f"archived_{status}")
        if self._last_pick == appid:
            self._last_pick = None; self.pl_view.reset_pick_ui()
        self._refresh_all(); self.tabs.setCurrentIndex(3)
        msg = t("archived_done_t", name=name) if status == "termine" else t("archived_done_a", name=name)
        self.status.showMessage(msg)

    def _restore_from_archive(self, appid, name):
        self.db.restore_from_archive(appid); self._refresh_all()
        self.status.showMessage(t("restored", name=name))

    # ── Pick system ───────────────────────────
    def _pick_game(self):
        mood   = self.pl_view.get_mood()
        picked = PriorityEngine.pick(self.db, mood=mood)
        if not picked:
            QMessageBox.information(self, t("playlist_empty_title"), t("playlist_empty_body"))
            return
        self._last_pick = picked["appid"]
        self.db.log_history(picked["appid"], picked["name"], "picked")
        self.pl_view.show_pick(picked["name"], picked["appid"], picked["priority"])
        self.status.showMessage(t("pick_status", name=picked["name"], score=f"{picked['priority']:.0f}"))

    def _accept_pick(self):
        if self._last_pick is None: return
        appid = self._last_pick
        name  = self.db.conn.execute(
            "SELECT name FROM games WHERE appid=?", (appid,)
        ).fetchone()["name"]
        session_dlg = SessionDialog(name, self)
        if session_dlg.exec() != QDialog.DialogCode.Accepted: return
        planned = session_dlg.get_minutes()
        self.db.log_history(appid, name, "accepted", planned)
        PriorityEngine.apply_accept(self.db, appid)
        self._refresh_all()
        note = self.db.get_note(appid)
        note_content = note["content"] if note else None
        self.pl_view.show_launch(name, appid, note_content, planned)
        dur = t("launch_dur", n=planned) if planned else ""
        self.status.showMessage(t("accepted_status", name=name, dur=dur))

    def _launch_game(self, appid, name, planned_minutes):
        self.db.log_history(appid, name, "launched", planned_minutes)
        QDesktopServices.openUrl(QUrl(f"steam://run/{appid}"))
        self.db.record_launch(appid)
        self._last_pick = None; self.pl_view.reset_pick_ui(); self._refresh_all()
        dur = t("launch_dur", n=planned_minutes) if planned_minutes else ""
        self.status.showMessage(t("launched_status", name=name, dur=dur))
        if PriorityEngine.check_inflation(self.db):
            QMessageBox.information(self, t("inflation_title"), t("inflation_body"))

    def _refuse_and_pick(self):
        if self._last_pick is not None:
            appid = self._last_pick
            name  = self.db.conn.execute(
                "SELECT name FROM games WHERE appid=?", (appid,)
            ).fetchone()["name"]
            self.db.log_history(appid, name, "refused")
            PriorityEngine.apply_refuse(self.db, appid)
            self._last_pick = None
        self._pick_game()

    # ── Notes ─────────────────────────────────
    def _open_note(self, appid, game_name):
        dlg = NoteDialog(self.db, appid, game_name, self)
        result = dlg.exec()
        if result != 0:
            self._refresh_all()
            if result == 2:
                self.status.showMessage(t("note_deleted", name=game_name))
            elif dlg.get_content():
                self.status.showMessage(t("note_saved", name=game_name))

    # ── Refresh ───────────────────────────────
    def _refresh_all(self):
        self.lib_view.refresh(); self.pl_view.refresh()
        self.notes_view.refresh(); self.archive_view.refresh(); self.history_view.refresh()
        self.stats.update(
            self.db.count_total(), self.db.count_library(),
            self.db.count_playlist(), self.db.count_archive()
        )

    def closeEvent(self, event):
        self.db.close(); event.accept()


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
def main():
    global LANG
    # Load language before building any UI
    _db_check = sqlite3.connect("aqua_jouer.db")
    try:
        row = _db_check.execute(
            "SELECT value FROM settings WHERE key='lang'"
        ).fetchone()
        if row:
            LANG = row[0]
    except Exception:
        pass
    finally:
        _db_check.close()

    app = QApplication(sys.argv); app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor("#0e1117"))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor("#c7d5e0"))
    pal.setColor(QPalette.ColorRole.Base,            QColor("#131a21"))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor("#1b2838"))
    pal.setColor(QPalette.ColorRole.ToolTipBase,     QColor("#1b2838"))
    pal.setColor(QPalette.ColorRole.ToolTipText,     QColor("#c7d5e0"))
    pal.setColor(QPalette.ColorRole.Text,            QColor("#c7d5e0"))
    pal.setColor(QPalette.ColorRole.Button,          QColor("#1b2838"))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor("#c7d5e0"))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor("#1a9fff"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(pal)
    w = AquaJouer(); w.show(); sys.exit(app.exec())


if __name__ == "__main__":
    main()
