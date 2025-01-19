import json
import os
import shutil
import subprocess
import hashlib

import streamlit as st
from stqdm import stqdm  # Importer stqdm pour afficher la progression dans Streamlit


def find_executable(filename="DUNGEON ENCOUNTERS.exe", search_paths=None):
    if search_paths is None:
        # Chemins courants où Steam installe les jeux
        search_paths = [
            os.getcwd(),  # Dossier courant où tourne le script Python
            "C:\\Program Files (x86)\\Steam\\steamapps\\common",
            "C:\\Program Files\\Steam\\steamapps\\common"
        ]

    found_path = None

    for root_path in search_paths:
        for root, dirs, files in os.walk(root_path):
            if filename in files:
                found_path = os.path.join(root, filename)
                return found_path  # Retourner le premier résultat trouvé

    return None  # Retourne None si le fichier n'est pas trouvé

def backup_folder(folder_path):
    with st.spinner("Backing up folder..."):
        src_folder = os.path.join(folder_path, "DUNGEON ENCOUNTERS_Data")
        dest_folder = os.path.join(folder_path, "DUNGEON ENCOUNTERS_Data_backup")

        if not os.path.exists(src_folder):
            st.error(f"Le dossier source '{src_folder}' n'existe pas. Impossible de créer une sauvegarde.")
            return False

        try:
            if os.path.exists(dest_folder):
                return False
                # shutil.rmtree(dest_folder)  # Supprimer l'ancienne sauvegarde si elle existe
            shutil.copytree(src_folder, dest_folder)  # Copier le dossier
            st.success(f"Sauvegarde créée : {dest_folder}")
            return True
        except Exception as e:
            st.error(f"Erreur lors de la sauvegarde : {e}")
            return False


def hash_file(filepath):
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


# Fonction pour analyser un dossier avec un indicateur de progression
def analyze_folder(folder_path):
    analysis = {}
    all_files = []

    # Récupérer tous les fichiers pour suivre la progression
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            all_files.append(os.path.join(root, file))

    # Analyse des fichiers avec barre de progression
    for file_path in stqdm(all_files, desc="Analyse des fichiers"):
        analysis[file_path] = {
            "size": os.path.getsize(file_path),
            "modified": os.path.getmtime(file_path),
            "hash": hash_file(file_path),
        }

    return analysis


# Fonction pour lister les sous-dossiers de Mods
def list_mod_folders(mods_folder):
    if os.path.exists(mods_folder):
        return [name for name in os.listdir(mods_folder) if os.path.isdir(os.path.join(mods_folder, name))]
    return []


# Fonction pour vérifier si un fichier existe dans dest_folder (y compris ses sous-dossiers)
def file_exists_in_dest(filename, dest_folder):
    for root, dirs, files in os.walk(dest_folder):
        if filename in files:
            return os.path.join(root, filename)
    return None


# Fonction pour remplacer uniquement les fichiers existants
def replace_files_and_track(src_folder, dest_folder, mod_name, config):
    replaced_files = []
    for root, dirs, files in os.walk(src_folder):
        for file in files:
            src_path = os.path.join(root, file)

            # Chercher si le fichier existe dans les sous-dossiers de dest_folder
            existing_file_path = file_exists_in_dest(file, dest_folder)

            if existing_file_path:
                # Remplacer le fichier
                shutil.copy2(src_path, existing_file_path)
                replaced_files.append(existing_file_path)

                relative_path = os.path.relpath(existing_file_path, dest_folder)

                if mod_name not in config["mod_files"]:
                    config["mod_files"][mod_name] = []

                if relative_path not in config["mod_files"][mod_name]:
                    config["mod_files"][mod_name].append(relative_path)

    return replaced_files


# Fonction pour restaurer uniquement les fichiers modifiés
def restore_files_from_backup(backup_folder, dest_folder, mod_name, config):
    restored_files = []
    if mod_name in config["mod_files"]:
        for relative_path in config["mod_files"][mod_name]:
            backup_path = os.path.join(backup_folder, relative_path)
            dest_path = os.path.join(dest_folder, relative_path)

            # Restaurer le fichier uniquement s'il existe dans le backup
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, dest_path)
                restored_files.append(dest_path)

        # Supprimer les fichiers de ce mod de la config
        del config["mod_files"][mod_name]

    return restored_files


def restore_mod_files(mod_name, mods_folder, data_folder, backup_folder, config):
    mod_folder_path = os.path.join(mods_folder, mod_name)
    if not os.path.exists(mod_folder_path):
        st.error(f"Le mod {mod_name} n'existe pas dans le dossier Mods.")
        return

    restored_files = restore_files_from_backup(backup_folder, data_folder, mod_name, config)
    st.toast(f"**Fichiers restaurés pour {mod_name} : {len(restored_files)}**")
    return restored_files


def copy_mod_file_to_pages(mod_path, file, pages_folder):
    """Copie le fichier .py du mod dans le dossier pages."""
    if not os.path.exists(pages_folder):
        os.makedirs(pages_folder)  # Crée le dossier pages s'il n'existe pas

    # Copie du fichier mod .py dans le dossier pages
    shutil.copy2(os.path.join(mod_path, file), os.path.join(pages_folder, file))


# Fonction pour ouvrir le dossier des mods dans l'explorateur
def open_mods_folder(mods_folder):
    try:
        if os.name == 'nt':  # Windows
            os.startfile(mods_folder)
        elif os.name == 'posix':  # macOS ou Linux
            subprocess.run(['open', mods_folder], check=True)
        st.success(f"Ouverture du dossier Mods : {mods_folder}")
    except Exception as e:
        st.error(f"Erreur lors de l'ouverture du dossier : {e}")


def launch_game():
    try:
        # Charger l'analyse pour trouver l'exécutable
        with open("analysis.json", "r") as f:
            analysis = json.load(f)

        # Trouver "DUNGEON ENCOUNTERS.exe" dans les fichiers analysés
        exe_path = None
        for file_path in analysis:
            if file_path.endswith("DUNGEON ENCOUNTERS.exe"):
                exe_path = file_path
                break

        if exe_path and os.path.exists(exe_path):
            # Lancer l'exécutable
            subprocess.Popen([exe_path], shell=True)
            st.success(f"Le jeu a été lancé avec succès : {exe_path}")
        else:
            st.error("Impossible de trouver 'DUNGEON ENCOUNTERS.exe'. Vérifiez votre dossier ou relancez l'analyse.")

    except Exception as e:
        st.error(f"Erreur lors du lancement du jeu : {e}")
