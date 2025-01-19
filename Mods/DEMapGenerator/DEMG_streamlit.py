import json
import os
import shutil
import zipfile
import random
import string

import pandas as pd
import streamlit as st
from PIL import Image

from Mods.DEMapGenerator import generate_maps
from utils.page_config_DELM import page_config


def highlight_color(val):
    if isinstance(val, tuple):
        r, g, b = val
        return f"background-color: rgb({r}, {g}, {b});"
    return ""


with open("Mods/DEMapGenerator/special_tiles.json", "r") as file:
    special_tiles = json.load(file)

data = []
for value, tile in special_tiles.items():
    data.append({
        "Name": tile["name"],
        "Color": tuple(tile["color"]),
        "Other Name": ", ".join(tile.get("other_name", [])) if "other_name" in tile else "",
        "Description": ", ".join(tile.get("description", [])) if "description" in tile else "",
        "Value": value,
    })

df = pd.DataFrame(data)
styled_df = df.style.map(highlight_color, subset=["Color"])


if "output_files_720p" not in st.session_state:
    st.session_state["output_files_720p"] = []
if "zip_path" not in st.session_state:
    st.session_state["zip_path"] = None
if "generated" not in st.session_state:
    st.session_state["generated"] = False
if "generated_seed" not in st.session_state:
    st.session_state["generated_seed"] = ''.join(random.choices(string.digits, k=10))
if 'seed' not in st.session_state:
    st.session_state["seed"] = ""
if 'maze_type_save' not in st.session_state:
    st.session_state["maze_type_save"] = ""

page_config(logo=True)

st.title("Dungeon Encounters Map Generator 🧱")

with st.expander("👋🏽 **Welcome to the Dungeon Encounters Map Generator! / ❓ How to Use the Generator**"):
    st.success(r"""
            This generator creates dungeon maps for the game *[Dungeon Encounters](https://fr.store.square-enix-games.com/dungeon-encounters---digital) from Square Enix*. It allows you to create mazes, roads, or random maps with customizable options.

            **Generation Parameters:**
            - **Generation Type**: Choose the type of map to generate:
                - *Maze*: A classic maze with narrow paths.
                - *Road*: A map with open roads and intersections.
                - *Voronoi*: A generation type based on Voronoi diagrams, creating irregular zones.
                - *Shuffle*: A mixed map type, with varied generation elements.
            - **Depth, Empty Width, Node Number**: These parameters adjust the map generation characteristics based on the selected type.

            **Cheat Mode:**
            - By enabling *cheat_mode*, all treasures, combat abilities, and movement skills will be placed on level 0, providing immediate access to all resources in the game.

            **After Generation:**
            - Once the maps are generated, the `.bin` files should be placed in the following directory:
              - `C:\Program Files (x86)\Steam\steamapps\common\DUNGEON ENCOUNTERS\DUNGEON ENCOUNTERS_Data\StreamingAssets\xlsx`
              - Note: The directory path may vary depending on where your game is installed.

            **Important Reminder:**
            - I do not take responsibility for any issues that may arise. I strongly recommend making a backup of your maps before replacing any files in the game directory.

            **Generation Delays and Errors:**
            - Sometimes, map generation can be slow, especially for larger maps. If you encounter a `max_attempts` error, don’t be alarmed—it’s simply due to the time taken for the generation process. Just restart the generation, and it should work fine.
            - Over time, I will continue to fix and improve any bugs, so please be patient and feel free to report any issues you encounter.

            This generator is perfect for creating custom maps for your Dungeon Encounters adventures. You can choose the map type, adjust parameters, and see the results in real time!

            **GitHub Repository**: [Dungeon Encounters Map Generator](https://github.com/Jumitti/DungeonEncountersMapGenerator)
        """)

with st.expander("🎨 **Color legend**"):
    st.dataframe(styled_df, hide_index=True, use_container_width=True)

st.sidebar.header("⚙️ Generation settings")
nb_levels = st.sidebar.number_input("🔢 Number of levels", min_value=1, max_value=100, value=5)
maze_type = st.sidebar.selectbox("🗺️ Type of maze", ["Maze", "Road", "Voronoi", "Shuffle"], index=2)

if maze_type == "Maze":
    param_label = "Depth"
    param_min = 1
    param_max = 1000
    param_value = 50
elif maze_type == "Road":
    param_label = "Empty Width"
    param_min = 1
    param_max = 40
    param_value = 15
elif maze_type == "Voronoi":
    param_label = "Node Number"
    param_min = 5
    param_max = 250
    param_value = 25

if maze_type in ["Maze", "Road", "Voronoi"]:
    param_value = st.sidebar.slider(param_label, min_value=param_min, max_value=param_max, value=param_value, step=1)
else:
    param_value = None

if st.sidebar.checkbox("🎲 Random Seed", value=True):
    st.sidebar.text(f"Seed: {st.session_state['generated_seed']}")

    if st.sidebar.button("🌱 Generate New Seed"):
        st.session_state["generated_seed"] = ''.join(random.choices(string.digits, k=10))

    seed_input = st.session_state["generated_seed"]

    valid_seed = False

else:
    seed_input = st.sidebar.text_input("Enter Seed", placeholder="0123456789", value="", max_chars=10)

    try:
        generate_maps.validate_seed(seed_input)
        valid_seed = False
    except ValueError as e:
        valid_seed = True
        st.sidebar.error(e)

cheat_mode = st.sidebar.checkbox("🥷🏽 Cheat Mode", value=False)
generate_bin = st.sidebar.checkbox("📦 Generate .bin files", value=False)


def clean_output_dirs(directories):
    for directory in directories:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                st.error(f"Cleaning error {file_path}: {e}")


sd_col1, sd_col2 = st.sidebar.columns(2)

tempo_dir = f"Mods/DEMapGenerator/tempo/{maze_type.lower()}_{seed_input}_{param_value if param_value is not None else 'default'}_{'nocheat' if cheat_mode is False else 'cheat'}/100p"
tempo_dir_720p = f"Mods/DEMapGenerator/tempo/{maze_type.lower()}_{seed_input}_{param_value if param_value is not None else 'default'}_{'nocheat' if cheat_mode is False else 'cheat'}/720p"
if not os.path.exists(tempo_dir):
    os.makedirs(tempo_dir)
if not os.path.exists(tempo_dir_720p):
    os.makedirs(tempo_dir_720p)

st.divider()
if sd_col1.button(f"Preview Map_{nb_levels - 1}", disabled=valid_seed):
    clean_output_dirs([tempo_dir, tempo_dir_720p])
    try:
        seed = generate_maps.run(nb_lvl=None, maze_type=maze_type.lower(), generate_bin=generate_bin, seed=seed_input,
                                 param_1=param_value, cheat_mode=cheat_mode, one_lvl=[nb_levels - 1], type_progress="stqdm")
        st.session_state["seed"] = seed
        st.session_state["maze_type_save"] = maze_type.lower()

        st.session_state["output_files_720p"] = sorted(
            [os.path.join(tempo_dir_720p, f) for f in os.listdir(tempo_dir_720p) if f.endswith(".png")]
        )
        st.session_state["generated"] = True

    except Exception as e:
        st.error(e)

if sd_col2.button(f"Generate maps (0 to {nb_levels - 1})", disabled=valid_seed):
    zip_path = None
    clean_output_dirs([tempo_dir, tempo_dir_720p])
    try:
        seed = generate_maps.run(nb_lvl=nb_levels, maze_type=maze_type.lower(), param_1=param_value, seed=seed_input,
                                 generate_bin=generate_bin, cheat_mode=cheat_mode, type_progress="stqdm")
        st.session_state["seed"] = seed
        st.session_state["maze_type_save"] = maze_type.lower()

        st.session_state["output_files_720p"] = sorted(
            [os.path.join(tempo_dir_720p, f) for f in os.listdir(tempo_dir_720p) if f.endswith(".png")]
        )

        st.session_state["generated"] = True
        st.session_state["zip_path"] = os.path.join(
            f"Mods/DEMapGenerator/tempo/{maze_type.lower()}_{seed_input}_{param_value if param_value is not None else 'default'}_{'nocheat' if cheat_mode is False else 'cheat'}",
            f'{st.session_state["maze_type_save"]}_{st.session_state["seed"]}_{param_value if param_value is not None else 'default'}_{'nocheat' if cheat_mode is False else 'cheat'}.zip')
        with zipfile.ZipFile(st.session_state["zip_path"], "w") as zipf:
            for file in os.listdir(tempo_dir):
                file_path = os.path.join(tempo_dir, file)
                if os.path.isfile(file_path):
                    zipf.write(file_path, arcname=os.path.join(f"100p", file))

            for file in os.listdir(tempo_dir_720p):
                file_path = os.path.join(tempo_dir_720p, file)
                if os.path.isfile(file_path):
                    zipf.write(file_path, arcname=os.path.join(f"720p", file))

        st.success("Generation successfully completed! Seed: " + st.session_state["seed"])
    except Exception as e:
        st.error(e)

try:
    if st.session_state["generated"] and st.session_state["output_files_720p"]:
        tabs = st.tabs([os.path.basename(file_path) for file_path in st.session_state["output_files_720p"]])
        for i, file_path in enumerate(st.session_state["output_files_720p"]):
            with tabs[i]:
                image = Image.open(file_path)
                st.image(image, caption=f"{os.path.basename(file_path)}")

    if st.session_state["zip_path"] and os.path.exists(st.session_state["zip_path"]):
        with open(st.session_state["zip_path"], "rb") as f:
            st.sidebar.download_button(
                label="💾 Download maps and .bin files", data=f,
                file_name=f'{st.session_state["maze_type_save"]}_{st.session_state["seed"]}_{param_value if param_value is not None else 'default'}_{'nocheat' if cheat_mode is False else 'cheat'}.zip', mime="application/zip")
except Exception as e:
    st.warning("Maps not generated yet.")

