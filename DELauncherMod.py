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

if st.button("Automatic game path search"):
    with st.spinner("Automatic game path search"):
        executable_path = DELM.find_executable()
        if executable_path:
            folder_path = os.path.dirname(executable_path)
            st.success(f"File found : {executable_path}")

            config["game_folder"] = folder_path
            with open(config_file, "w") as f:
                json.dump(config, f)

            if not os.path.exists(f"{folder_path}\\Mods"):
                os.makedirs(f"{folder_path}\\Mods")
            st.success("Saved path.")
        else:
            st.error("DUNGEON ENCOUNTERS.exe cannot be found in the default paths.")

fpcol1, fpcol2 = st.columns([3, 1])
if folder_path != "":
    fpcol2.markdown("")
    fpcol2.markdown("")
    change_folder_path = fpcol2.toggle("Edit folder path", False)
else:
    change_folder_path = True
folder_path = fpcol1.text_input("Path to game folder:", folder_path if folder_path != "" else "",
                            placeholder="Path to game folder", disabled=True if change_folder_path is False else False)

if st.button("Save path"):
    config["game_folder"] = folder_path
    with open(config_file, "w") as f:
        json.dump(config, f)

    if not os.path.exists(f"{folder_path}\\Mods"):
        os.makedirs(f"{folder_path}\\Mods")
    st.success("Saved path.")

if st.button("Start analysis"):
    if not os.path.isdir(folder_path):
        st.error("The path specified is not a valid folder.")
    else:
        DELM.backup_folder(folder_path)

        new_analysis = DELM.analyze_folder(folder_path)

        if os.path.exists(analysis_file):
            with open(analysis_file, "r") as f:
                old_analysis = json.load(f)
        else:
            old_analysis = {}

        with open(analysis_file, "w") as f:
            json.dump(new_analysis, f)
        st.success("Analysis completed and saved.")

if folder_path and os.path.exists(folder_path):
    mods_folder = os.path.join(folder_path, "Mods")
    st.session_state["mods_folder"] = mods_folder
    data_folder = os.path.join(folder_path, "DUNGEON ENCOUNTERS_Data")
    backup_folder = os.path.join(folder_path, "DUNGEON ENCOUNTERS_Data_backup")

    if not os.path.exists(mods_folder):
        os.makedirs(mods_folder)
        st.info("The Mods folder has been created.")
    if not os.path.exists(backup_folder):
        shutil.copytree(data_folder, backup_folder)
        st.info("The backup folder has been created.")

    mod_folders = DELM.list_mod_folders(mods_folder)
    print(mod_folders)


def load_mod_config(mod_path):
    mod_config_file = os.path.join(mod_path, "mod_config.json")

    if os.path.exists(mod_config_file):
        with open(mod_config_file, "r") as f:
            mod_config = json.load(f)
        return mod_config, mod_config_file
    return {}, None


if os.path.exists(folder_path):
    st.write("### Mods management :")
    for mod in mod_folders:
        mod_path = os.path.join(mods_folder, mod)
        toggle_key = f"toggle_mod_{mod}"

        mod_config, mod_config_file = load_mod_config(mod_path)

        activable = mod_config.get("activable", True)
        current_state = mod_config.get("enabled", False)
        replacement_folder = mod_config.get(f"replacement_folder", None)
        replacement_folder = f"{mod_path}\\{replacement_folder}" if replacement_folder else mod_path
        compatible_items = mod_config.get("compatible_items", None)

        if f"{toggle_key}_prev" not in st.session_state:
            st.session_state[f"{toggle_key}_prev"] = current_state

        col1, col2 = st.columns(2)

        if col2.button(f"Delete mod {mod}"):
            DELM.restore_mod_files(mod, mods_folder, data_folder, backup_folder, config)
            shutil.rmtree(os.path.join(mods_folder, mod))
            st.success(f"The {mod} mod has been removed.")
            st.rerun()

        if activable:
            new_state = col1.toggle(f"Activate Mod : {mod}", value=current_state, key=toggle_key)

            if new_state != st.session_state[f"{toggle_key}_prev"]:
                st.session_state[f"{toggle_key}_prev"] = new_state

                if new_state:
                    st.toast(f"Mod activation : {mod}")
                    if replacement_folder:
                        st.write(f"Using the specified folder for replacements : {replacement_folder}")
                        subfolders = [f for f in os.listdir(replacement_folder) if
                                      os.path.isdir(os.path.join(replacement_folder, f))]

                        if compatible_items is True:
                            selected_subfolders = []
                            for subfolder in subfolders:
                                if st.checkbox(f"Activate mod {subfolder}", key=f"{mod}_{subfolder}",
                                               value=False):
                                    selected_subfolders.append(subfolder)

                            for subfolder in selected_subfolders:
                                replaced_files = DELM.replace_files_and_track(
                                    os.path.join(replacement_folder, subfolder), data_folder, mod, config)
                                st.toast(
                                    f"**Files replaced for {mod} from subfolder {subfolder} : {len(replaced_files)}**")
                        elif compatible_items is False:
                            selected_subfolder = st.radio(
                                "Select a mod",
                                ["None"] + subfolders
                            )

                            if selected_subfolder == "None":
                                restored_files = DELM.restore_files_from_backup(backup_folder, data_folder, mod,
                                                                                config)
                                st.toast(f"**Restored files for {mod} : {len(restored_files)}**")
                            elif selected_subfolder:
                                restored_files = DELM.restore_files_from_backup(backup_folder, data_folder, mod,
                                                                                config)
                                st.toast(f"**Restored files for {mod} : {len(restored_files)}**")

                                replaced_files = DELM.replace_files_and_track(
                                    os.path.join(replacement_folder, selected_subfolder), data_folder, mod, config)
                                st.toast(
                                    f"**Files replaced for {mod} from subfolder {selected_subfolder} : {len(replaced_files)}**")

                        elif replacement_folder == mod_path:
                                    replaced_files = DELM.replace_files_and_track(
                                        os.path.join(replacement_folder, mod_path), data_folder, mod, config)
                                    st.toast(
                                        f"**Files replaced for {mod} from subfolder {mod_path} : {len(replaced_files)}**")

                else:
                    st.toast(f"Mod deactivation :{mod}")
                    restored_files = DELM.restore_files_from_backup(backup_folder, data_folder, mod, config)
                    st.toast(f"**Files restored for {mod} : {len(restored_files)}**")

        else:
            new_state = col1.toggle(f"Activate Mod : {mod}", value=current_state, key=toggle_key, disabled=True)
            if replacement_folder:
                st.write(f"Using the specified folder for replacements : {replacement_folder}")
                subfolders = [f for f in os.listdir(replacement_folder) if
                              os.path.isdir(os.path.join(replacement_folder, f))]

                if compatible_items is True:
                    selected_subfolders = []
                    for subfolder in subfolders:
                        if st.checkbox(f"Activate mod {subfolder}", key=f"{mod}_{subfolder}", value=False):
                            selected_subfolders.append(subfolder)

                    for subfolder in selected_subfolders:
                        replaced_files = DELM.replace_files_and_track(os.path.join(replacement_folder, subfolder),
                                                                      data_folder, mod, config)
                        st.toast(
                            f"**Files replaced for {mod} from subfolder{subfolder} : {len(replaced_files)}**")

                    # Restauration des fichiers pour les sous-dossiers non sélectionnés
                    for subfolder in subfolders:
                        if subfolder not in selected_subfolders:
                            restored_files = DELM.restore_files_from_backup(backup_folder, data_folder, mod, config)
                            st.toast(f"**Files restored for {mod} since {subfolder} : {len(restored_files)}**")

                elif compatible_items is False:
                    selected_subfolder = st.radio(
                        "Select a mod for replacement",
                        ["None"] + subfolders
                    )

                    if selected_subfolder == "None":
                        restored_files = DELM.restore_files_from_backup(backup_folder, data_folder, mod, config)
                        st.toast(f"**Restored files for {mod} : {len(restored_files)}**")
                    elif selected_subfolder:
                        restored_files = DELM.restore_files_from_backup(backup_folder, data_folder, mod, config)
                        st.toast(f"**Restored files for {mod} : {len(restored_files)}**")

                        replaced_files = DELM.replace_files_and_track(
                            os.path.join(replacement_folder, selected_subfolder), data_folder, mod, config)
                        st.toast(
                            f"**Files replaced for {mod} from subfolder {selected_subfolder} : {len(replaced_files)}**")

                elif replacement_folder == mod_path:
                        replaced_files = DELM.replace_files_and_track(
                            os.path.join(replacement_folder, mod_path), data_folder, mod, config)
                        st.toast(
                            f"**Files replaced for {mod} from subfolder {mod_path} : {len(replaced_files)}**")

        if activable and current_state != st.session_state[f"{toggle_key}_prev"]:
            mod_config["enabled"] = st.session_state[f"{toggle_key}_prev"]
            if mod_config_file:
                with open(mod_config_file, "w") as f:
                    json.dump(mod_config, f, indent=4)

        config[toggle_key] = st.session_state[f"{toggle_key}_prev"]
        with open(config_file, "w") as f:
            json.dump(config, f, indent=4)

    pages_mods(st.session_state["mods_folder"])
else:
    st.info("No Mods available in the Mods folder.")

if st.button("Scan Mods"):
    st.rerun()

if st.button("Open the Mods folder"):
    DELM.open_mods_folder(mods_folder)

if st.button("Lancer DUNGEON ENCOUNTERS.exe"):
    DELM.launch_game()