import json
import os
import shutil
import subprocess
import hashlib

import streamlit as st
from stqdm import stqdm  # Importer stqdm pour afficher la progression dans Streamlit


def find_executable(filename="DUNGEON ENCOUNTERS.exe", search_paths=None):
    if search_paths is None:
        search_paths = [
            os.getcwd(),
            "C:\\Program Files (x86)\\Steam\\steamapps\\common",
            "C:\\Program Files\\Steam\\steamapps\\common"
        ]

    found_path = None

    for root_path in search_paths:
        for root, dirs, files in os.walk(root_path):
            if filename in files:
                found_path = os.path.join(root, filename)
                return found_path

    return None


def backup_folder(folder_path):
    with st.spinner("Backing up folder..."):
        src_folder = os.path.join(folder_path, "DUNGEON ENCOUNTERS_Data")
        dest_folder = os.path.join(folder_path, "DUNGEON ENCOUNTERS_Data_backup")

        if not os.path.exists(src_folder):
            st.error(f"Source folder '{src_folder}' does not exist. Unable to create a backup.")
            return False

        try:
            if os.path.exists(dest_folder):
                return False
                # shutil.rmtree(dest_folder)
            shutil.copytree(src_folder, dest_folder)
            st.success(f"Backup created : {dest_folder}")
            return True
        except Exception as e:
            st.error(f"Backup error : {e}")
            return False


def hash_file(filepath):
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def analyze_folder(folder_path):
    analysis = {}
    all_files = []

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            all_files.append(os.path.join(root, file))

    for file_path in stqdm(all_files, desc="File analysis"):
        analysis[file_path] = {
            "size": os.path.getsize(file_path),
            "modified": os.path.getmtime(file_path),
            "hash": hash_file(file_path),
        }

    return analysis


def list_mod_folders(mods_folder):
    if os.path.exists(mods_folder):
        return [name for name in os.listdir(mods_folder) if os.path.isdir(os.path.join(mods_folder, name))]
    return []


def file_exists_in_dest(filename, dest_folder):
    for root, dirs, files in os.walk(dest_folder):
        if filename in files:
            return os.path.join(root, filename)
    return None


def replace_files_and_track(src_folder, dest_folder, mod_name, config):
    replaced_files = []
    for root, dirs, files in os.walk(src_folder):
        for file in files:
            src_path = os.path.join(root, file)

            existing_file_path = file_exists_in_dest(file, dest_folder)

            if existing_file_path:
                shutil.copy2(src_path, existing_file_path)
                replaced_files.append(existing_file_path)

                relative_path = os.path.relpath(existing_file_path, dest_folder)

                if mod_name not in config["mod_files"]:
                    config["mod_files"][mod_name] = []

                if relative_path not in config["mod_files"][mod_name]:
                    config["mod_files"][mod_name].append(relative_path)

    return replaced_files


def restore_files_from_backup(backup_folder, dest_folder, mod_name, config):
    restored_files = []
    if mod_name in config["mod_files"]:
        for relative_path in config["mod_files"][mod_name]:
            backup_path = os.path.join(backup_folder, relative_path)
            dest_path = os.path.join(dest_folder, relative_path)

            if os.path.exists(backup_path):
                shutil.copy2(backup_path, dest_path)
                restored_files.append(dest_path)

        del config["mod_files"][mod_name]

    return restored_files


def restore_mod_files(mod_name, mods_folder, data_folder, backup_folder, config):
    mod_folder_path = os.path.join(mods_folder, mod_name)
    if not os.path.exists(mod_folder_path):
        st.error(f"The mod {mod_name} does not exist in the Mods folder.")
        return

    restored_files = restore_files_from_backup(backup_folder, data_folder, mod_name, config)
    st.toast(f"**Restored files for {mod_name} : {len(restored_files)}**")
    return restored_files


def copy_mod_file_to_pages(mod_path, file, pages_folder):
    if not os.path.exists(pages_folder):
        os.makedirs(pages_folder)

    shutil.copy2(os.path.join(mod_path, file), os.path.join(pages_folder, file))


def open_mods_folder(mods_folder):
    try:
        if os.name == 'nt':
            os.startfile(mods_folder)
        elif os.name == 'posix':
            subprocess.run(['open', mods_folder], check=True)
        st.success(f"Opening the Mods folder : {mods_folder}")
    except Exception as e:
        st.error(f"Error opening file : {e}")


def launch_game():
    try:
        with open("analysis.json", "r") as f:
            analysis = json.load(f)

        exe_path = None
        for file_path in analysis:
            if file_path.endswith("DUNGEON ENCOUNTERS.exe"):
                exe_path = file_path
                break

        if exe_path and os.path.exists(exe_path):
            subprocess.Popen([exe_path], shell=True)
            st.success(f"The game was successfully launched: {exe_path}")
        else:
            st.error("DUNGEON ENCOUNTERS.exe' cannot be found. Check your folder or run the scan again.")

    except Exception as e:
        st.error(f"Game launch error: {e}")
