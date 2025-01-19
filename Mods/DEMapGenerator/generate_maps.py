import hashlib
import json
import os
import random
import string

from PIL import Image

from Mods.DEMapGenerator import DEMG as DE
from utils.bcolors import bcolors, color_settings


def validate_seed(seed):
    if not isinstance(seed, str):
        raise TypeError("Seed must be a string.")

    if len(seed) != 10:
        raise ValueError("Seed must be exactly 10 characters long.")
    if not seed.isdigit():
        raise ValueError("Seed must contain only numeric characters (digits).")
    return seed


def increment_seed(seed):
    incremented_seed = str(int(seed) + 1).zfill(10)
    if len(incremented_seed) > 10:
        incremented_seed = "0000000000"
        print("Incrementing the seed results in a value exceeding 10 digits.")
    return incremented_seed


debug_dir = "Mods/DEMapGenerator/debug"
if not os.path.exists(debug_dir):
    os.makedirs(debug_dir)

grid_size = 100

json_file = "Mods/DEMapGenerator/special_tiles.json"
wanderers_file = "Mods/DEMapGenerator/wanderers.json"

if not os.path.exists(json_file):
    raise FileNotFoundError(color_settings(f"{json_file} cannot be found.", bcolors.FAIL))
if not os.path.exists(wanderers_file):
    raise FileNotFoundError(color_settings(f"{wanderers_file} cannot be found.", bcolors.FAIL))

with open(json_file, "r") as f:
    special_tiles = json.load(f)

with open(wanderers_file, "r") as f:
    wanderers = json.load(f)

color_to_value = {
    tuple(tile["color"]): int(key, 16) for key, tile in special_tiles.items()
}

value_to_color = {
    int(key, 16): tuple(tile["color"]) for key, tile in special_tiles.items()
}

EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)
CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)
START_FLOOR_0 = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "00"), None)
two_way_positions = {}
one_way_positions = {}

if EMPTY is None or PATH is None or HIDDEN is None or START_FLOOR_0 is None:
    raise ValueError(color_settings("The necessary values are not present in the JSON file.", bcolors.FAIL))


def generate_floor_data(lvl, maps_data=None, maze_type="voronoi", param_1=None, seed=None, cheat_mode=False, debug=False):
    max_iterations = 5
    map_attempts = 0

    # Determine ascending coordinates
    if lvl == 0 or len(maps_data) == 0:
        ascending_coords = (50, 50)
    else:
        descending_types = [int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "01"]
        previous_grid = maps_data[-1]["grid"]
        ascending_coords = None
        for DESCENDING in descending_types:
            ascending_coords = next(
                ((x, y) for x in range(grid_size) for y in range(grid_size) if previous_grid[x][y] == DESCENDING),
                None)
            if ascending_coords is not None:
                break

        if ascending_coords is None:
            raise ValueError("No DESCENDING tile found in the previous grid.")

    start_x, start_y = ascending_coords

    print(seed)
    hashed_seed = hashlib.sha256(seed.encode()).hexdigest()
    map_attempts += 1

    grid = [[EMPTY for _ in range(grid_size)] for _ in range(grid_size)]

    if maze_type == "shuffle":
        maze_type = random.choice(["maze", "road", "voronoi"])
    if maze_type == "maze":
        DE.generate_maze(grid, start_x, start_y, max_depth=param_1 if param_1 is not None else 50, seed=hashed_seed,
                         special_tiles=special_tiles)
        print(color_settings(f"Maze (type: maze) generated.", bcolors.OKGREEN))
    elif maze_type == "road":
        DE.generate_road(grid, start_x, start_y, route_width=param_1 if param_1 is not None else 15, seed=hashed_seed,
                         special_tiles=special_tiles)
    elif maze_type == "voronoi":
        DE.generate_voronoi(grid, start_x, start_y, num_sites=param_1 if param_1 is not None else 25,
                            special_tiles=special_tiles,
                            seed=hashed_seed)
    DE.remove_random_paths(grid, 0.50, special_tiles=special_tiles)

    if cheat_mode is True and lvl == 0:
        DE.cheat_mode(grid, lvl, special_tiles)

    if lvl == 0:
        grid[start_x][start_y] = START_FLOOR_0
        print(color_settings(
            f"00 Start: z={lvl}, x={start_x}, y={start_y}", bcolors.OKCYAN))
        DE.complete_path(grid, start_x, start_y, "PATH", special_tiles=special_tiles)
    else:
        DE.place_ascending(grid, start_x, start_y, lvl, special_tiles)

    DE.place_wanderers(grid, lvl, wanderers, special_tiles)

    DE.place_riddles(grid, lvl, special_tiles)

    DE.place_descending(grid, start_x, start_y, lvl, special_tiles)

    DE.place_riddles_hints(grid, lvl, special_tiles)

    DE.place_treasure(grid, lvl, special_tiles)

    DE.place_shop(grid, lvl, special_tiles)

    DE.place_teleporter(grid, lvl, two_way_positions, one_way_positions, special_tiles)

    DE.place_ability(grid, lvl, special_tiles)

    DE.place_adventures(grid, lvl, special_tiles)

    DE.place_resurrection(grid, lvl, special_tiles)

    DE.place_healing(grid, lvl, special_tiles)

    DE.place_purification(grid, lvl, special_tiles)

    DE.place_gorgon(grid, lvl, special_tiles)

    DE.place_cavy(grid, lvl, special_tiles)

    DE.place_note(grid, lvl, special_tiles)

    DE.place_movement(grid, lvl, special_tiles)

    DE.place_battle(grid, lvl, special_tiles)

    nb_special_tiles = [
        (x, y) for x in range(grid_size) for y in range(grid_size)
        if grid[x][y] not in [EMPTY, PATH, HIDDEN, CROSS]
    ]

    iteration = 0
    refine_failures = 0
    max_refine_failures = 3

    while iteration < max_iterations:
        if DE.is_connected(grid, start_x, start_y, iteration, special_tiles=special_tiles):
            if 49 < lvl < 59:
                DE.place_cross(grid, lvl, special_tiles)
                DE.connect_disconnected_groups(grid, special_tiles=special_tiles)

            if len(nb_special_tiles) == len([(x, y) for x in range(len(grid)) for y in range(len(grid[0])) if
                                             grid[x][y] not in [EMPTY, PATH, HIDDEN, CROSS]]):
                return grid
            else:
                print(color_settings("Refinement of the map has broken special tiles. Generating a new map...",
                                     bcolors.FAIL))
                if debug:
                    save_floor_image(grid, f"Mods/DEMapGenerator/debug/Map_m{lvl}_{iteration}_broken.png")
                break

        try:
            if debug:
                save_floor_image(grid, f"Mods/DEMapGenerator/debug/Map_m{lvl}_{iteration}_br.png")
            DE.refine_map(grid, special_tiles=special_tiles)
            if debug:
                save_floor_image(grid, f"Mods/DEMapGenerator/debug/Map_m{lvl}_{iteration}_ar.png")

            refine_failures = 0
            iteration += 1

        except Exception as e:
            print(color_settings(f"Refine failed: {e}. Attempting to reconnect groups...", bcolors.WARNING))
            DE.connect_disconnected_groups(grid, special_tiles=special_tiles)

            refine_failures += 1
            if refine_failures >= max_refine_failures:
                print(color_settings("Too many refine failures. Aborting map generation...", bcolors.FAIL))
                break

    if iteration >= max_iterations:
        print(color_settings("Max iterations reached. Attempting final connection...", bcolors.WARNING))
        while DE.is_connected(grid, start_x, start_y, iteration, special_tiles=special_tiles) is False:
            DE.connect_disconnected_groups(grid, nb_groups=1, special_tiles=special_tiles)
        DE.refine_map(grid, special_tiles=special_tiles)
        if DE.is_connected(grid, start_x, start_y, iteration, special_tiles=special_tiles):
            return grid
        else:
            if debug:
                save_floor_image(grid, f"Mods/DEMapGenerator/debug/Map_m{lvl}_{iteration}_rf.png")
            print(color_settings("Final connection failed. Map generation aborted.", bcolors.FAIL))
            return None


def save_floor_image(grid, output_image_path, output_image_path_720p=None, saved_seed=None, saved_seed_720p=None):
    image = Image.new("RGB", (grid_size, grid_size), value_to_color[EMPTY])
    pixels = image.load()

    for x in range(grid_size):
        for y in range(grid_size):
            pixels[x, y] = value_to_color[grid[x][y]]

    image.save(output_image_path)
    print(color_settings(f"Generated image: {output_image_path}", bcolors.OKGREEN))
    if saved_seed is not None:
        image.save(saved_seed)

    if output_image_path_720p is not None:
        image_720p = Image.new("RGB", (700, 700), value_to_color[EMPTY])
        pixels_720p = image_720p.load()

        scale_factor = 700 // grid_size

        for x in range(grid_size):
            for y in range(grid_size):
                color = value_to_color[grid[x][y]]
                for dx in range(scale_factor):
                    for dy in range(scale_factor):
                        pixels_720p[x * scale_factor + dx, y * scale_factor + dy] = color

        image_720p.save(output_image_path_720p)
        print(color_settings(f"Generated 720x720 image: {output_image_path_720p}", bcolors.OKGREEN))
        if saved_seed_720p is not None:
            image_720p.save(saved_seed_720p)


def run(nb_lvl, maze_type="voronoi", param_1=None, seed=None, generate_bin=False, one_lvl=None, cheat_mode=False,
        debug=False, type_progress="tqdm"):
    try:
        if maze_type not in ["maze", "road", "voronoi", "shuffle"]:
            raise ValueError(color_settings('maze_type must be "maze", "road", "voronoi", "shuffle"', bcolors.FAIL))

        if type_progress not in ["tqdm", "stqdm"]:
            raise ValueError(color_settings('type_progress must be "tqdm" (for CMD) or "stqdm" (for Streamlit)', bcolors.FAIL))

        if type_progress == "tqdm":
            from tqdm import tqdm
        elif type_progress == "stqdm":
            from stqdm import stqdm as tqdm

        maps_data = []

        if seed is None:
            seed = ''.join(random.choices(string.digits, k=10))
        else:
            try:
                seed = validate_seed(seed)
            except Exception as e:
                print(color_settings(f"Invalid seed: {e}"), bcolors.FAIL)
                return

        random.seed(seed)
        used_seed = seed

        if one_lvl is not None:
            for lvl in tqdm(one_lvl, desc=color_settings(
                    f"Generating maps...", bcolors.OKGREEN) if type_progress == "tqdm" else f"Generating maps...",
                            colour="green"):
                grid = generate_floor_data(lvl=lvl, maps_data=maps_data,
                                           maze_type=maze_type if maze_type in ["maze", "road", "voronoi"] else
                                           random.choice(["maze", "road", "voronoi"]), param_1=param_1,
                                           seed=used_seed, cheat_mode=cheat_mode, debug=debug)
                maps_data.append({"level": lvl, "grid": grid})
                used_seed = increment_seed(used_seed)
        else:
            for i in tqdm(range(nb_lvl), desc=color_settings(
                    f"Generating maps...", bcolors.OKGREEN) if type_progress == "tqdm" else f"Generating maps...",
                            colour="green"):
                grid = generate_floor_data(lvl=i, maps_data=maps_data,
                                           maze_type=maze_type if maze_type in ["maze", "road", "voronoi"] else
                                           random.choice(["maze", "road", "voronoi"]), param_1=param_1,
                                           seed=used_seed, cheat_mode=cheat_mode, debug=debug)
                maps_data.append({"level": i, "grid": grid})
                used_seed = increment_seed(used_seed)

        for data in tqdm(maps_data, desc=color_settings("Saving images and generating binaries", bcolors.WARNING),
                         colour="yellow"):
            lvl = data["level"]
            grid = data["grid"]

            tempo_dir, tempo_dir_720p = (f"Mods/DEMapGenerator/tempo/{maze_type}_{seed}_{param_1 if param_1 is not None else 'default'}_{'nocheat' if cheat_mode is False else 'cheat'}/100p",
                                         f"Mods/DEMapGenerator/tempo/{maze_type}_{seed}_{param_1 if param_1 is not None else 'default'}_{'nocheat' if cheat_mode is False else 'cheat'}/720p")
            if not os.path.exists(tempo_dir):
                os.makedirs(tempo_dir)
            if not os.path.exists(tempo_dir_720p):
                os.makedirs(tempo_dir_720p)

            if nb_lvl == 100 and one_lvl is None:
                saved_seed = f"Mods/DEMapGenerator/seed/{maze_type}_{seed}_{param_1 if param_1 is not None else 'default'}_{'nocheat' if cheat_mode is False else 'cheat'}/100p"
                saved_seed_720p = f"Mods/DEMapGenerator/seed/{maze_type}_{seed}_{param_1 if param_1 is not None else 'default'}_{'nocheat' if cheat_mode is False else 'cheat'}/720p"
                if not os.path.exists(saved_seed):
                    os.makedirs(saved_seed)
                if not os.path.exists(saved_seed_720p):
                    os.makedirs(saved_seed_720p)
                saved_seed_IP = os.path.join(saved_seed, f"Map_m{lvl}.png")
                saved_seed_IP_720p = os.path.join(saved_seed_720p, f"Map_m{lvl}_720p.png")
            else:
                saved_seed = None
                saved_seed_IP, saved_seed_IP_720p = None, None

            output_image_path = os.path.join(tempo_dir, f"Map_m{lvl}.png")
            output_image_path_720p = os.path.join(tempo_dir_720p, f"Map_m{lvl}_720p.png")
            save_floor_image(grid, output_image_path, output_image_path_720p, saved_seed_IP, saved_seed_IP_720p)

            if generate_bin is True and one_lvl is None:
                DE.reconstruct_bin(lvl=lvl, image_path=output_image_path, output_directories=[tempo_dir, saved_seed], special_tiles=special_tiles)
                print(color_settings(f"Binary and image files for level {lvl} saved in: {tempo_dir}", bcolors.OKGREEN))

        return seed
    except Exception as e:
        print(e)
        raise


if __name__ == "__main__":
    run(nb_lvl=100, maze_type="maze", seed="0000000028", generate_bin=False, one_lvl=[0], cheat_mode=False, debug=True)
