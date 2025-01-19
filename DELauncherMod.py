import streamlit as st
from stqdm import stqdm  # Importer stqdm pour afficher la progression dans Streamlit
import os
import hashlib
import json
import subprocess
import shutil
import DELM
import zipfile
from pathlib import Path
from utils.page_config_DELM import page_config, pages_mods

# Charger ou demander le chemin d'accès au dossier du jeu
if "mods_folder" not in st.session_state:
    st.session_state["mods_folder"] = None

page_config(logo=True)

st.title("DE Launcher Mod")

config_file = "config.json"
analysis_file = "analysis.json"

if not os.path.exists(config_file):
    with open(config_file, "w") as f:
        json.dump({"game_folder": "", "mod_files": {}}, f)

with open(config_file, "r") as f:
    config = json.load(f)

folder_path = config.get("game_folder", "")

if st.button("Rechercher automatiquement le jeu"):
    with st.spinner("Rechercher automatiquement le jeu"):
        executable_path = DELM.find_executable()
        if executable_path:
            folder_path = os.path.dirname(executable_path)
            st.success(f"Fichier trouvé : {executable_path}")

            config["game_folder"] = folder_path
            with open(config_file, "w") as f:
                json.dump(config, f)

            if not os.path.exists(f"{folder_path}\\Mods"):
                os.makedirs(f"{folder_path}\\Mods")
            st.success("Chemin sauvegardé.")
        else:
            st.error("Impossible de trouver 'DUNGEON ENCOUNTERS.exe' dans les chemins par défaut.")

fpcol1, fpcol2 = st.columns([3, 1])
if folder_path != "":
    fpcol2.markdown("")
    fpcol2.markdown("")
    change_folder_path = fpcol2.toggle("Edit folder path", False)
else:
    change_folder_path = True
folder_path = fpcol1.text_input("Chemin vers le dossier du jeu :", folder_path if folder_path != "" else "",
                            placeholder="Chemin vers le dossier du jeu :", disabled=True if change_folder_path is False else False)

if st.button("Sauvegarder le chemin"):
    config["game_folder"] = folder_path
    with open(config_file, "w") as f:
        json.dump(config, f)

    if not os.path.exists(f"{folder_path}\\Mods"):
        os.makedirs(f"{folder_path}\\Mods")
    st.success("Chemin sauvegardé.")

# Bouton pour lancer l'analyse
if st.button("Lancer l'analyse"):
    if not os.path.isdir(folder_path):
        st.error("Le chemin spécifié n'est pas un dossier valide.")
    else:
        # Créer une sauvegarde avant l'analyse
        DELM.backup_folder(folder_path)

        # Analyser les fichiers
        new_analysis = DELM.analyze_folder(folder_path)

        # Charger l'analyse précédente si elle existe
        if os.path.exists(analysis_file):
            with open(analysis_file, "r") as f:
                old_analysis = json.load(f)
        else:
            old_analysis = {}

        with open(analysis_file, "w") as f:
            json.dump(new_analysis, f)
        st.success("Analyse terminée et sauvegardée.")

if folder_path and os.path.exists(folder_path):
    mods_folder = os.path.join(folder_path, "Mods")
    st.session_state["mods_folder"] = mods_folder
    data_folder = os.path.join(folder_path, "DUNGEON ENCOUNTERS_Data")
    backup_folder = os.path.join(folder_path, "DUNGEON ENCOUNTERS_Data_backup")

    # Créer les dossiers Mods et Backup si nécessaires
    if not os.path.exists(mods_folder):
        os.makedirs(mods_folder)
        st.info("Le dossier Mods a été créé.")
    if not os.path.exists(backup_folder):
        shutil.copytree(data_folder, backup_folder)
        st.info("Le dossier de sauvegarde a été créé.")

    mod_folders = DELM.list_mod_folders(mods_folder)
    print(mod_folders)


def load_mod_config(mod_path):
    mod_config_file = os.path.join(mod_path, "mod_config.json")

    if os.path.exists(mod_config_file):
        with open(mod_config_file, "r") as f:
            mod_config = json.load(f)
        return mod_config, mod_config_file
    return {}, None  # Retourner un dictionnaire vide si le fichier n'existe pas


if os.path.exists(folder_path):
    st.write("### Gestion des Mods :")
    for mod in mod_folders:
        mod_path = os.path.join(mods_folder, mod)
        toggle_key = f"toggle_mod_{mod}"

        # Charger la configuration du mod (si elle existe)
        mod_config, mod_config_file = load_mod_config(mod_path)

        activable = mod_config.get("activable", True)  # Si activable n'existe pas, on assume que le mod est activable
        current_state = mod_config.get("enabled", False)  # L'état du mod, ou False si non défini
        replacement_folder = mod_config.get(f"replacement_folder", None)  # Dossier de remplacement, ou None par défaut
        replacement_folder = f"{mod_path}\\{replacement_folder}" if replacement_folder else mod_path  # Si pas de folder, on prend mod_path
        compatible_items = mod_config.get("compatible_items", None)  # Paramètre pour savoir si les sous-dossiers sont compatibles entre eux

        # Initialiser l'état précédent si nécessaire
        if f"{toggle_key}_prev" not in st.session_state:
            st.session_state[f"{toggle_key}_prev"] = current_state

        col1, col2 = st.columns(2)

        # Bouton pour supprimer le mod
        if col2.button(f"Supprimer le mod {mod}"):
            DELM.restore_mod_files(mod, mods_folder, data_folder, backup_folder, config)
            shutil.rmtree(os.path.join(mods_folder, mod))
            st.success(f"Le mod {mod} a été supprimé.")
            st.rerun()

        # Toggle pour activer/désactiver le mod seulement si le mod est activable
        if activable:
            new_state = col1.toggle(f"Activer le Mod : {mod}", value=current_state, key=toggle_key)

            # Détecter si l'état a changé
            if new_state != st.session_state[f"{toggle_key}_prev"]:
                st.session_state[f"{toggle_key}_prev"] = new_state  # Mettre à jour l'état précédent

                if new_state:  # Activation du mod
                    st.toast(f"Activation du Mod : {mod}")
                    if replacement_folder:
                        # Si un dossier de remplacement spécifique est défini
                        st.write(f"Utilisation du dossier spécifié pour les remplacements : {replacement_folder}")
                        subfolders = [f for f in os.listdir(replacement_folder) if
                                      os.path.isdir(os.path.join(replacement_folder, f))]

                        if compatible_items is True:
                            # Si compatible_items est True, on permet de sélectionner plusieurs sous-dossiers
                            selected_subfolders = []
                            for subfolder in subfolders:
                                if st.checkbox(f"Activer le sous-dossier {subfolder}", key=f"{mod}_{subfolder}",
                                               value=False):
                                    selected_subfolders.append(subfolder)

                            # Effectuer les remplacements pour les sous-dossiers sélectionnés
                            for subfolder in selected_subfolders:
                                replaced_files = DELM.replace_files_and_track(
                                    os.path.join(replacement_folder, subfolder), data_folder, mod, config)
                                st.toast(
                                    f"**Fichiers remplacés pour {mod} depuis le sous-dossier {subfolder} : {len(replaced_files)}**")
                        elif compatible_items is False:
                            # Si compatible_items est False, on permet de choisir un seul sous-dossier ou l'option "vide"
                            selected_subfolder = st.radio(
                                "Sélectionner un sous-dossier pour le remplacement",
                                ["Aucun (vide)"] + subfolders  # Ajout de l'option "Aucun" en début de liste
                            )

                            # Effectuer le remplacement pour le sous-dossier sélectionné
                            if selected_subfolder == "Aucun (vide)":
                                # Si l'utilisateur choisit l'option "Aucun", on restaure les fichiers sans faire de remplacement
                                restored_files = DELM.restore_files_from_backup(backup_folder, data_folder, mod,
                                                                                config)
                                st.toast(f"**Fichiers restaurés pour {mod} : {len(restored_files)}**")
                            elif selected_subfolder:
                                # Si un sous-dossier est sélectionné, on effectue les remplacements
                                restored_files = DELM.restore_files_from_backup(backup_folder, data_folder, mod,
                                                                                config)
                                st.toast(f"**Fichiers restaurés pour {mod} : {len(restored_files)}**")

                                replaced_files = DELM.replace_files_and_track(
                                    os.path.join(replacement_folder, selected_subfolder), data_folder, mod, config)
                                st.toast(
                                    f"**Fichiers remplacés pour {mod} depuis le sous-dossier {selected_subfolder} : {len(replaced_files)}**")

                        elif replacement_folder == mod_path:
                                    replaced_files = DELM.replace_files_and_track(
                                        os.path.join(replacement_folder, mod_path), data_folder, mod, config)
                                    st.toast(
                                        f"**Fichiers remplacés pour {mod} depuis le sous-dossier {mod_path} : {len(replaced_files)}**")

                else:  # Désactivation du mod
                    st.toast(f"Désactivation du Mod : {mod}")
                    restored_files = DELM.restore_files_from_backup(backup_folder, data_folder, mod, config)
                    st.toast(f"**Fichiers restaurés pour {mod} : {len(restored_files)}**")

        else:
            new_state = col1.toggle(f"Activer le Mod : {mod}", value=current_state, key=toggle_key, disabled=True)
            if replacement_folder:
                # Si un dossier de remplacement spécifique est défini
                st.write(f"Utilisation du dossier spécifié pour les remplacements : {replacement_folder}")
                subfolders = [f for f in os.listdir(replacement_folder) if
                              os.path.isdir(os.path.join(replacement_folder, f))]

                if compatible_items is True:
                    # Si compatible_items est True, on permet de sélectionner plusieurs sous-dossiers
                    selected_subfolders = []
                    for subfolder in subfolders:
                        if st.checkbox(f"Activer le sous-dossier {subfolder}", key=f"{mod}_{subfolder}", value=False):
                            selected_subfolders.append(subfolder)

                    # Effectuer les remplacements pour les sous-dossiers sélectionnés
                    for subfolder in selected_subfolders:
                        replaced_files = DELM.replace_files_and_track(os.path.join(replacement_folder, subfolder),
                                                                      data_folder, mod, config)
                        st.toast(
                            f"**Fichiers remplacés pour {mod} depuis le sous-dossier {subfolder} : {len(replaced_files)}**")

                    # Restauration des fichiers pour les sous-dossiers non sélectionnés
                    for subfolder in subfolders:
                        if subfolder not in selected_subfolders:
                            restored_files = DELM.restore_files_from_backup(backup_folder, data_folder, mod, config)
                            st.toast(f"**Fichiers restaurés pour {mod} depuis {subfolder} : {len(restored_files)}**")

                elif compatible_items is False:
                    # Si compatible_items est False, on permet de choisir un seul sous-dossier ou l'option "vide"
                    selected_subfolder = st.radio(
                        "Sélectionner un sous-dossier pour le remplacement",
                        ["Aucun (vide)"] + subfolders  # Ajout de l'option "Aucun" en début de liste
                    )

                    # Effectuer le remplacement pour le sous-dossier sélectionné
                    if selected_subfolder == "Aucun (vide)":
                        # Si l'utilisateur choisit l'option "Aucun", on restaure les fichiers sans faire de remplacement
                        restored_files = DELM.restore_files_from_backup(backup_folder, data_folder, mod, config)
                        st.toast(f"**Fichiers restaurés pour {mod} : {len(restored_files)}**")
                    elif selected_subfolder:
                        # Si un sous-dossier est sélectionné, on effectue les remplacements
                        restored_files = DELM.restore_files_from_backup(backup_folder, data_folder, mod, config)
                        st.toast(f"**Fichiers restaurés pour {mod} : {len(restored_files)}**")

                        replaced_files = DELM.replace_files_and_track(
                            os.path.join(replacement_folder, selected_subfolder), data_folder, mod, config)
                        st.toast(
                            f"**Fichiers remplacés pour {mod} depuis le sous-dossier {selected_subfolder} : {len(replaced_files)}**")

                elif replacement_folder == mod_path:
                        replaced_files = DELM.replace_files_and_track(
                            os.path.join(replacement_folder, mod_path), data_folder, mod, config)
                        st.toast(
                            f"**Fichiers remplacés pour {mod} depuis le sous-dossier {mod_path} : {len(replaced_files)}**")

        # Sauvegarder l'état dans le fichier de configuration du mod si l'état change
        if activable and current_state != st.session_state[f"{toggle_key}_prev"]:
            # Sauvegarder l'état modifié dans le fichier de configuration du mod
            mod_config["enabled"] = st.session_state[f"{toggle_key}_prev"]
            if mod_config_file:  # Vérifier si le fichier mod_config_file est défini
                with open(mod_config_file, "w") as f:
                    json.dump(mod_config, f, indent=4)


        # Sauvegarder l'état dans le fichier de configuration global
        config[toggle_key] = st.session_state[f"{toggle_key}_prev"]
        with open(config_file, "w") as f:
            json.dump(config, f, indent=4)

    pages_mods(st.session_state["mods_folder"])
else:
    st.info("Aucun Mod disponible dans le dossier Mods.")

if st.button("Scan Mods"):
    st.rerun()

# Bouton pour ouvrir le dossier des mods
if st.button("Ouvrir le dossier Mods"):
    DELM.open_mods_folder(mods_folder)

# Ajouter un bouton dans l'application Streamlit
if st.button("Lancer DUNGEON ENCOUNTERS"):
    DELM.launch_game()