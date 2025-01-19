import json
import os
import random
from collections import deque
from random import shuffle
import re
from tqdm import tqdm
import numpy as np
from PIL import Image
from scipy.spatial import Voronoi
from utils.bcolors import bcolors, color_settings
import hashlib


# Note for a tile x, y:
#   x - 1, y - 1 | x, y - 1 | x + 1, y - 1
#   --------------------------------------
#   x - 1,   y   |   x, y   | x + 1,   y
#   --------------------------------------
#   x - 1, y + 1 | x, y + 1 | x + 1, y + 1


# Generate .bin file from image 100x100
def reconstruct_bin(lvl, image_path, output_directories, special_tiles):
    for output_directory in output_directories:
        if output_directory is None:
            continue

        output_bin_path = os.path.join(output_directory, f"Map_m{lvl}.bin")

        image = Image.open(image_path)
        pixels = image.load()

        with open(special_tiles, "r") as f:
            special_cases = json.load(f)

        width, height = image.size
        if width != 100 or height != 100:
            raise ValueError(color_settings("Image size must be 100x100 pixels.", bcolors.FAIL))

        with open(output_bin_path, "wb") as f:
            for y in range(100):
                for x in range(100):
                    r, g, b = pixels[x, y]

                    hex_value = None
                    for key, tile in special_cases.items():
                        if tile["color"] == [r, g, b]:
                            hex_value = int(key, 16)
                            break

                    if hex_value is None:
                        raise ValueError(color_settings(
                            f"No value found for color {r, g, b} at position ({x}, {y})", bcolors.FAIL))

                    f.write(hex_value.to_bytes(3, 'big'))

        print(color_settings(f"Generated .bin: {output_bin_path}", bcolors.OKGREEN))


# Map generator (maze, road, voronoi)
# Maze
def generate_maze(grid, start_x, start_y, max_depth=50, seed=None, grid_size=100, special_tiles=None):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)

    def is_valid_move(grid, start_x, start_y, dx, dy):
        for i in range(1, 5):
            nx, ny = start_x + dx * i, start_y + dy * i
            if not (0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] == EMPTY):
                return False
        return True

    if max_depth <= 0:
        return

    random.seed(seed)

    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    random.shuffle(directions)

    for dx, dy in directions:
        if is_valid_move(grid, start_x, start_y, dx, dy):
            for i in range(1, 3):
                nx, ny = start_x + dx * i, start_y + dy * i
                if 0 <= nx < grid_size and 0 <= ny < grid_size:
                    grid[nx][ny] = PATH

            generate_maze(grid, nx, ny, max_depth - 1, seed=seed, special_tiles=special_tiles)


# Road
def generate_road(grid, start_x, start_y, route_width=15, grid_size=100, seed=None, special_tiles=None):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)

    def neighbors(start_x, start_y):
        return [(start_x + dx, start_y + dy) for dx, dy in
                [(0, route_width), (route_width, 0), (0, -route_width), (-route_width, 0)]
                if 0 <= start_x + dx < grid_size and 0 <= start_y + dy < grid_size]

    random.seed(seed)

    frontier = neighbors(start_x, start_y)
    random.shuffle(frontier)

    while frontier:
        nx, ny = frontier.pop()
        if grid[nx][ny] == EMPTY:
            for i in range(route_width):
                if 0 <= nx - i < grid_size:
                    grid[nx - i][ny] = PATH
                if 0 <= ny - i < grid_size:
                    grid[nx][ny - i] = PATH

            for neighbor in neighbors(nx, ny):
                if grid[neighbor[0]][neighbor[1]] == EMPTY:
                    frontier.append(neighbor)
            random.shuffle(frontier)

    print(color_settings(f"Maze (type: road) generated.", bcolors.OKGREEN))


# Voronoi
def generate_voronoi(grid, start_x, start_y, num_sites=25, grid_size=100, seed=None, special_tiles=None):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)

    random.seed(seed)

    def bresenham_line(x1, y1, x2, y2):
        points = []
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        while True:
            points.append((x1, y1))
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

        return points

    half_grid_size = grid_size // 2

    min_x = max(0, start_x - half_grid_size)
    max_x = min(len(grid), start_x + half_grid_size + max(0, - (start_x - half_grid_size)))

    min_y = max(0, start_y - half_grid_size)
    max_y = min(len(grid[0]), start_y + half_grid_size + max(0, - (start_y - half_grid_size)))

    sites = np.array([[start_x, start_y]] + [[
        random.randint(min_x, max_x - 1),
        random.randint(min_y, max_y - 1)
    ] for _ in range(num_sites - 1)])

    vor = Voronoi(sites)

    for ridge in vor.ridge_vertices:
        if -1 in ridge:
            continue
        start, end = vor.vertices[ridge]
        start = np.round(start).astype(int)
        end = np.round(end).astype(int)

        if (0 <= start[0] < len(grid) and 0 <= start[1] < len(grid[0]) and
                0 <= end[0] < len(grid) and 0 <= end[1] < len(grid[0])):
            for x, y in bresenham_line(start[0], start[1], end[0], end[1]):
                if 0 <= x < len(grid) and 0 <= y < len(grid[0]):
                    grid[x][y] = PATH

    print(color_settings(f"Maze (type: voronoi) generated.", bcolors.OKGREEN))


# Create diversity in the map by removing certain tiles
def remove_random_paths(grid, percentage_to_remove, grid_size=100, special_tiles=None):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)

    def dfs(grid, x, y, visited):
        stack = [(x, y)]
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) not in visited:
                visited.add((cx, cy))
                directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
                for dx, dy in directions:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] == PATH:
                        stack.append((nx, ny))

    paths = [(x, y) for x in range(grid_size) for y in range(grid_size) if grid[x][y] in {PATH, HIDDEN}]
    random.shuffle(paths)

    num_to_remove = int(len(paths) * percentage_to_remove)
    start_x, start_y = next((x, y) for x in range(grid_size) for y in range(grid_size) if grid[x][y] == PATH)

    for i in range(num_to_remove):
        x, y = paths[i]
        to_remove = [(x, y)]
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]

        random.shuffle(directions)
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] == PATH:
                to_remove.append((nx, ny))
                if len(to_remove) == 5:
                    break

        removed_cases = []
        for rx, ry in to_remove:
            grid[rx][ry] = EMPTY
            removed_cases.append((rx, ry))

        visited = set()
        dfs(grid, start_x, start_y, visited)

        if len(visited) != sum(1 for px, py in paths if grid[px][py] == PATH):
            for rx, ry in removed_cases:
                grid[rx][ry] = PATH

    print(color_settings(f"Some paths removed and refined", bcolors.OKGREEN))


# Attach a tile to the map
def complete_path(grid, x, y, case_type="RANDOM", grid_size=100, special_tiles=None):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)

    visited = set()
    queue = deque([(x, y, [])])
    visited.add((x, y))

    if case_type == "RANDOM":
        target_case = random.choice([PATH, HIDDEN])
    elif case_type == "PATH":
        target_case = PATH
    elif case_type == "HIDDEN":
        target_case = HIDDEN
    else:
        raise ValueError(color_settings(
            f'case_type invalid: {case_type}. Must be "RANDOM", "PATH", "HIDDEN"', bcolors.FAIL))

    while queue:
        cx, cy, path = queue.popleft()

        if grid[cx][cy] == PATH:
            for px, py in path:
                if grid[px][py] == EMPTY:
                    grid[px][py] = target_case
            return path

        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0),
                       (1, -1), (-1, 1), (1, 1), (-1, -1)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] in [EMPTY, PATH] and (
                    nx, ny) not in visited:
                visited.add((nx, ny))
                queue.append((nx, ny, path + [(nx, ny)]))


# Used especially when CROSS is added
def connect_disconnected_groups(grid, nb_groups=3, grid_size=100, special_tiles=None):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)
    CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)

    visited = [[False for _ in range(grid_size)] for _ in range(grid_size)]
    groups = []

    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    for x in range(grid_size):
        for y in range(grid_size):
            if grid[x][y] not in [EMPTY, CROSS] and not visited[x][y]:
                group = []
                stack = [(x, y)]
                visited[x][y] = True

                while stack:
                    cx, cy = stack.pop()
                    group.append((cx, cy))

                    for dx, dy in directions:
                        nx, ny = cx + dx, cy + dy

                        if (0 <= nx < grid_size and 0 <= ny < grid_size and
                                not visited[nx][ny] and grid[nx][ny] not in [EMPTY, CROSS]):
                            visited[nx][ny] = True
                            stack.append((nx, ny))

                groups.append(group)

    if len(groups) > nb_groups:
        paired_groups = []
        for i in range(0, len(groups) - 1, 2):
            paired_groups.append((groups[i], groups[i + 1]))

        if len(groups) % 2 == 1:
            paired_groups.append((groups[0], groups[-1]))

        for group1, group2 in tqdm(paired_groups,
                                   desc=color_settings(f"Connecting {len(groups)} groups...",
                                                       bcolors.GRAY, bcolors.BG_BLACK), colour="black"):
            start_x, start_y = random.choice(group1)
            end_x, end_y = random.choice(group2)

            path = []
            x, y = start_x, start_y

            dx = 1 if end_x > x else -1
            dy = 1 if end_y > y else -1

            while (x, y) != (end_x, end_y):
                if grid[x][y] in [EMPTY, HIDDEN, PATH]:
                    path.append((x, y))

                if x != end_x:
                    x += dx
                if y != end_y:
                    y += dy

            if grid[end_x][end_y] in [EMPTY, HIDDEN, PATH]:
                path.append((end_x, end_y))

            for (px, py) in path:
                grid[px][py] = HIDDEN

            print(color_settings(
                f"Connected group1 ({len(group1)} cells) and group2 ({len(group2)} cells) with a path.",
                bcolors.GRAY, bcolors.BG_BLACK))

        refine_map(grid, case_type="HIDDEN", special_tiles=special_tiles)


# Checks whether all tiles (PATH, HIDDEN and hidden tiles) are connected to each other
def is_connected(grid, start_x, start_y, iteration, grid_size=100, special_tiles=None):

    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)

    visited = [[False for _ in range(grid_size)] for _ in range(grid_size)]
    stack = [(start_x, start_y)]
    total_non_empty_count = sum(cell not in [EMPTY, CROSS] for row in grid for cell in row)

    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    visited[start_x][start_y] = True
    visited_count = 1

    while stack:
        x, y = stack.pop()

        for dx, dy in directions:
            nx, ny = x + dx, y + dy

            if 0 <= nx < grid_size and 0 <= ny < grid_size and not visited[nx][ny] and grid[nx][ny] not in [EMPTY,
                                                                                                            CROSS]:
                visited[nx][ny] = True
                stack.append((nx, ny))
                visited_count += 1

    if visited_count == total_non_empty_count:
        print(color_settings(f"Maze connected on iteration {iteration}.", bcolors.OKGREEN))
        return True
    else:
        print(color_settings(f"Maze not connected. Refining... (Iteration {iteration + 1})",
                             bcolors.WARNING))

        return False


# Complete the missing sections to have all tiles accessible
def refine_map(grid, case_type="RANDOM", grid_size=100, special_tiles=None):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)
    CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)

    if case_type == "RANDOM":
        target_case = random.choice([PATH, HIDDEN])
    elif case_type == "PATH":
        target_case = PATH
    elif case_type == "HIDDEN":
        target_case = HIDDEN
    else:
        raise ValueError(color_settings(
            f'case_type invalid: {case_type}. Must be "RANDOM", "PATH", "HIDDEN"', bcolors.FAIL))

    for x in tqdm(range(0, grid_size),
                  desc=color_settings("Refining map...", bcolors.WARNING), colour="yellow"):
        for y in range(0, grid_size):
            if grid[x][y] not in [EMPTY, CROSS]:

                special_cases = {int(key, 16): tile["name"]
                                 for key, tile in special_tiles.items()}

                target_case = HIDDEN if special_cases.get(
                    grid[x][y], "UNKNOWN") not in ['PATH', "HIDDEN"] else grid[x][y]

                if x == 0 or x == grid_size - 1 or y == 0 or y == grid_size - 1:
                    if (x == 0 or x == grid_size - 1) and (y == 0 or y == grid_size - 1):
                        complete_path(grid, x, y, case_type, special_tiles=special_tiles)
                    elif x == 0 or x == grid_size - 1:
                        if 0 < y < grid_size - 1 and (grid[x][y - 1] == EMPTY or grid[x][y + 1] == EMPTY):
                            complete_path(grid, x, y, case_type, special_tiles=special_tiles)
                    elif y == 0 or y == grid_size - 1:
                        if 0 < x < grid_size - 1 and (grid[x - 1][y] == EMPTY or grid[x + 1][y] == EMPTY):
                            complete_path(grid, x, y, case_type, special_tiles=special_tiles)

                else:
                    if (grid[x - 1][y] == EMPTY and grid[x + 1][y] == EMPTY and
                            grid[x][y - 1] == EMPTY and grid[x][y + 1] == EMPTY and
                            grid[x - 1][y - 1] == EMPTY and grid[x - 1][y + 1] == EMPTY and
                            grid[x + 1][y - 1] == EMPTY and grid[x + 1][y + 1] == EMPTY):

                        complete_path(grid, x, y, case_type, special_tiles=special_tiles)

                    elif (grid[x - 1][y] == EMPTY and grid[x + 1][y] == EMPTY and
                          grid[x][y - 1] == EMPTY and grid[x][y + 1] == EMPTY):

                        if grid[x - 1][y - 1] not in [EMPTY, CROSS]:
                            grid[x - 1][y] = target_case
                        elif grid[x - 1][y + 1] not in [EMPTY, CROSS]:
                            grid[x - 1][y] = target_case
                        elif grid[x + 1][y - 1] not in [EMPTY, CROSS]:
                            grid[x + 1][y] = target_case
                        elif grid[x + 1][y + 1] not in [EMPTY, CROSS]:
                            grid[x + 1][y] = target_case

                    elif ((grid[x - 1][y] not in [EMPTY, CROSS] and
                           grid[x + 1][y] == EMPTY and grid[x][y - 1] == EMPTY and grid[x][y + 1] == EMPTY) or
                          (grid[x + 1][y] not in [EMPTY, CROSS] and
                           grid[x - 1][y] == EMPTY and grid[x][y - 1] == EMPTY and grid[x][y + 1] == EMPTY) or
                          (grid[x][y - 1] not in [EMPTY, CROSS] and
                           grid[x - 1][y] == EMPTY and grid[x + 1][y] == EMPTY and grid[x][y + 1] == EMPTY) or
                          (grid[x][y + 1] not in [EMPTY, CROSS] and
                           grid[x - 1][y] == EMPTY and grid[x + 1][y] == EMPTY and grid[x][y - 1] == EMPTY)):

                        if grid[x - 1][y] not in [EMPTY, CROSS]:
                            if grid[x + 1][y - 1] not in [EMPTY, CROSS]:
                                grid[x][y - 1] = target_case
                            elif grid[x + 1][y + 1] not in [EMPTY, CROSS]:
                                grid[x][y + 1] = target_case

                        elif grid[x + 1][y] not in [EMPTY, CROSS]:
                            if grid[x - 1][y - 1] not in [EMPTY, CROSS]:
                                grid[x][y - 1] = target_case
                            elif grid[x - 1][y + 1] not in [EMPTY, CROSS]:
                                grid[x][y + 1] = target_case

                        elif grid[x][y - 1] not in [EMPTY, CROSS]:
                            if grid[x - 1][y + 1] not in [EMPTY, CROSS]:
                                grid[x - 1][y] = target_case
                            elif grid[x + 1][y + 1] not in [EMPTY, CROSS]:
                                grid[x + 1][y] = target_case

                        elif grid[x][y + 1] not in [EMPTY, CROSS]:
                            if grid[x - 1][y - 1] not in [EMPTY, CROSS]:
                                grid[x - 1][y] = target_case
                            elif grid[x + 1][y - 1] not in [EMPTY, CROSS]:
                                grid[x + 1][y] = target_case


# Place DOWNSTAIRS (need to investigate why there are 0x10101 and 0x20101)
def place_descending(grid, start_x, start_y, lvl, special_tiles, grid_size=100):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)
    CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)

    tile_positions = [(x, y) for x in range(grid_size) for y in range(grid_size) if grid[x][y] in {PATH, HIDDEN}]

    farthest_positions = sorted(
        [(cx, cy) for cx, cy in tile_positions],
        key=lambda pos: (pos[0] - start_x) ** 2 + (pos[1] - start_y) ** 2,
        reverse=True
    )

    placed = False

    for downstairs_key, downstairs_data in special_tiles.items():
        if downstairs_data["name"] == "01":
            coords = downstairs_data["coord"]
            for coord in coords:
                if lvl == coord[0]:
                    for farthest_position in farthest_positions:
                        cx, cy = farthest_position
                        dx, dy = random.randint(-4, 4), random.randint(-4, 4)
                        nx, ny = cx + dx, cy + dy

                        nx = max(0, min(nx, grid_size - 1))
                        ny = max(0, min(ny, grid_size - 1))
                        if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] in {EMPTY, PATH, HIDDEN}:
                            complete_path(grid, nx, ny, "RANDOM", special_tiles=special_tiles)
                            grid[nx][ny] = next(
                                (int(key, 16) for key, tile in special_tiles.items() if
                                 key == downstairs_key), None)
                            print(color_settings(f"01 Downstairs: z={lvl}, x={nx}, y={ny}", bcolors.OKBLUE))
                            placed = True
                            break
                        if placed:
                            break
                    if placed:
                        break
            if placed:
                break

    if not placed:
        for downstairs_key, downstairs_data in special_tiles.items():
            if downstairs_data["name"] == "01":
                for farthest_position in farthest_positions:
                    cx, cy = farthest_position
                    dx, dy = random.randint(-4, 4), random.randint(-4, 4)
                    nx, ny = cx + dx, cy + dy

                    nx = max(0, min(nx, grid_size - 1))
                    ny = max(0, min(ny, grid_size - 1))

                    if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] in {EMPTY, PATH, HIDDEN}:
                        complete_path(grid, nx, ny, "RANDOM", special_tiles=special_tiles)
                        grid[nx][ny] = next(
                            (int(key, 16) for key, tile in special_tiles.items() if
                             key == downstairs_key), None)
                        print(color_settings(f"01 Downstairs: z={lvl}, x={nx}, y={ny}", bcolors.OKBLUE))
                        placed = True
                        break
                    if placed:
                        break
                if placed:
                    break


# Place ASCENDING
def place_ascending(grid, start_x, start_y, lvl, special_tiles, grid_size=100):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)
    CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)

    placed = False

    for upstairs_key, upstairs_data in special_tiles.items():
        if upstairs_data["name"] == "02":
            coords = upstairs_data["coord"]
            for coord in coords:
                if lvl == coord[0]:
                    complete_path(grid, start_x, start_y, "RANDOM", special_tiles=special_tiles)
                    grid[start_x][start_y] = next(
                        (int(key, 16) for key, tile in special_tiles.items() if
                         key == upstairs_key), None)
                    print(color_settings(f"02 Upstairs: z={lvl}, x={start_x}, y={start_y}", bcolors.OKCYAN))
                    placed = True
                    break
                if placed:
                    break

    if not placed:
        for upstairs_key, upstairs_data in special_tiles.items():
            if upstairs_data["name"] == "02":
                complete_path(grid, start_x, start_y, "RANDOM", special_tiles=special_tiles)
                grid[start_x][start_y] = next(
                    (int(key, 16) for key, tile in special_tiles.items() if
                     key == upstairs_key), None)
                print(color_settings(f"02 Upstairs: z={lvl}, x={start_x}, y={start_y}", bcolors.OKCYAN))
                break


def place_wanderers(grid, lvl, wanderers, special_tiles):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)

    for wanderer_key, wanderer_data in wanderers.items():
        coords = wanderer_data["coord"]
        for coord in coords:
            wy, wx = coord[1], coord[2]

            if lvl == coord[0]:
                complete_path(grid, wx, wy, "HIDDEN", special_tiles=special_tiles)
                grid[wx][wy] = PATH
                print(color_settings(
                    f"Wanderer {wanderer_data['name']}: z={lvl}, x={wx}, y={wy}", bcolors.MAGENTA))


def place_riddles(grid, lvl, special_tiles):
    for riddle in ["Map Riddle", "Math Riddle"]:
        for riddle_key, riddle_data in special_tiles.items():
            if "other_name" in riddle_data:
                other_name = riddle_data["other_name"]
                if isinstance(other_name, list):
                    other_name = " ".join(other_name)
                if re.search(riddle, other_name):
                    coords = riddle_data["coord"]
                    for coord in coords:
                        wy, wx = coord[1], coord[2]

                        if lvl == coord[0]:
                            complete_path(grid, wx, wy, "RANDOM", special_tiles=special_tiles)
                            grid[wx][wy] = next(
                                (int(key, 16) for key, tile in special_tiles.items() if key == riddle_key), None)
                            print(color_settings(
                                f"{riddle_data['name']} {riddle}: z={lvl}, x={wx}, y={wy}",
                                bcolors.ORANGE if riddle == "Map Riddle" else bcolors.LIGHTORANGE))


def place_riddles_hints(grid, lvl, special_tiles, grid_size=100):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)
    CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)

    tile_positions = [(x, y) for x in range(grid_size) for y in range(grid_size) if grid[x][y] in {PATH, HIDDEN}]

    for riddle_hint_key, riddle_hint_data in special_tiles.items():
        if "other_name" in riddle_hint_data:
            other_name = riddle_hint_data["other_name"]
            if isinstance(other_name, list):
                other_name = " ".join(other_name)
            if re.search("Riddles", other_name) and riddle_hint_data["type_event"] == "Market/Other":
                coords = riddle_hint_data["coord"]
                for coord in coords:
                    if lvl == coord[0]:
                        cx, cy = random.choice(tile_positions)
                        dx, dy = random.randint(-4, 4), random.randint(-4, 4)
                        nx, ny = cx + dx, cy + dy

                        nx = max(0, min(nx, grid_size - 1))
                        ny = max(0, min(ny, grid_size - 1))
                        if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] in [EMPTY, PATH,
                                                                                            HIDDEN]:
                            complete_path(grid, nx, ny, "RANDOM", special_tiles=special_tiles)
                            grid[nx][ny] = next(
                                (int(key, 16) for key, tile in special_tiles.items() if key == riddle_hint_key), None)
                            print(color_settings(
                                f"{riddle_hint_data['name']} Riddle hint: z={lvl}, x={nx}, y={ny}",
                                bcolors.BLACK, bcolors.BG_ORANGE))


def place_treasure(grid, lvl, special_tiles, grid_size=100):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)
    CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)

    tile_positions = [(x, y) for x in range(grid_size) for y in range(grid_size) if grid[x][y] in {PATH, HIDDEN}]

    for treasure_key, treasure_data in special_tiles.items():
        if "other_name" in treasure_data:
            other_name = treasure_data["other_name"]
            if isinstance(other_name, list):
                other_name = " ".join(other_name)
            if re.search("Treasure", other_name) and treasure_data["type_event"] == "Market/Other":
                coords = treasure_data["coord"]
                for coord in coords:
                    if lvl == coord[0]:
                        cx, cy = random.choice(tile_positions)
                        dx, dy = random.randint(-4, 4), random.randint(-4, 4)
                        nx, ny = cx + dx, cy + dy

                        nx = max(0, min(nx, grid_size - 1))
                        ny = max(0, min(ny, grid_size - 1))
                        if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] in [EMPTY, PATH,
                                                                                            HIDDEN]:
                            complete_path(grid, nx, ny, "HIDDEN", special_tiles=special_tiles)
                            grid[nx][ny] = next(
                                (int(key, 16) for key, tile in special_tiles.items() if key == treasure_key), None)
                            print(color_settings(
                                f"{treasure_data['name']} {other_name}: z={lvl}, x={nx}, y={ny}",
                                bcolors.BLACK, bcolors.BG_YELLOW))


def place_shop(grid, lvl, special_tiles, grid_size=100):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)
    CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)

    tile_positions = [(x, y) for x in range(grid_size) for y in range(grid_size) if grid[x][y] in {PATH, HIDDEN}]

    for shop_key, shop_data in special_tiles.items():
        if "other_name" in shop_data and shop_data["type_event"] == "Market/Other":
            other_name = shop_data["other_name"]
            if isinstance(other_name, list):
                other_name = " ".join(other_name)
            if not re.search(r"hint|Treasure|Shrine|Spring|Fountain|Station|Start|Idol|Adventurer", other_name):
                coords = shop_data["coord"]
                for coord in coords:
                    if lvl == coord[0]:
                        cx, cy = random.choice(tile_positions)
                        dx, dy = random.randint(-4, 4), random.randint(-4, 4)
                        nx, ny = cx + dx, cy + dy

                        nx = max(0, min(nx, grid_size - 1))
                        ny = max(0, min(ny, grid_size - 1))
                        if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] in [EMPTY, PATH,
                                                                                            HIDDEN]:
                            complete_path(grid, nx, ny, "RANDOM", special_tiles=special_tiles)
                            grid[nx][ny] = next(
                                (int(key, 16) for key, tile in special_tiles.items() if key == shop_key), None)
                            print(color_settings(
                                f"{shop_data['name']} {other_name}: z={lvl}, x={nx}, y={ny}",
                                bcolors.LIGHTORANGE, bcolors.BG_MAGENTA))


def place_teleporter(grid, lvl, two_way_positions, one_way_positions, special_tiles, grid_size=100):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)
    CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)

    tile_positions = [(x, y) for x in range(grid_size) for y in range(grid_size) if grid[x][y] in {PATH, HIDDEN}]
    for k in range(1, 11):
        for two_way_key, two_way_data in special_tiles.items():
            if "other_name" in two_way_data:
                name, other_name = two_way_data["name"], two_way_data["other_name"]
                if re.search(rf"\bTwo-way Teleporter {k}\b", " ".join(other_name)):
                    coords = two_way_data["coord"]

                    if name in two_way_positions and len(two_way_positions[name]) >= 2:
                        continue

                    for coord in coords:
                        if lvl == coord[0]:
                            while True:
                                cx, cy = random.choice(tile_positions)
                                dx, dy = random.randint(-4, 4), random.randint(-4, 4)
                                nx, ny = cx + dx, cy + dy

                                nx = max(0, min(nx, grid_size - 1))
                                ny = max(0, min(ny, grid_size - 1))

                                if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] in [EMPTY, PATH,
                                                                                                    HIDDEN]:
                                    grid[nx][ny] = next(
                                        (int(key, 16) for key, tile in special_tiles.items() if key == two_way_key),
                                        None)
                                    complete_path(grid, nx, ny, "RANDOM", special_tiles=special_tiles)

                                    if name not in two_way_positions:
                                        two_way_positions[name] = []
                                    two_way_positions[name].append((lvl, nx, ny))
                                    print(color_settings(
                                        f"{two_way_data['name']} Two-way Teleporter {k}: z={lvl}, x={nx}, y={ny}",
                                        bcolors.BROWN))
                                    break

    for k in range(1, 4):
        for one_way_key, one_way_data in special_tiles.items():
            if "other_name" in one_way_data:
                name, other_name = one_way_data["name"], one_way_data["other_name"]
                if re.search(rf"One-way Teleporter {k}", " ".join(other_name)):
                    coords = one_way_data["coord"]

                    for coord in coords:
                        if lvl == coord[0]:
                            while True:
                                cx, cy = random.choice(tile_positions)
                                dx, dy = random.randint(-4, 4), random.randint(-4, 4)
                                nx, ny = cx + dx, cy + dy

                                nx = max(0, min(nx, grid_size - 1))
                                ny = max(0, min(ny, grid_size - 1))
                                if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] in [EMPTY, PATH,
                                                                                                    HIDDEN]:
                                    grid[nx][ny] = next(
                                        (int(key, 16) for key, tile in special_tiles.items() if key == one_way_key),
                                        None)
                                    complete_path(grid, nx, ny, "RANDOM", special_tiles=special_tiles)

                                    if name not in one_way_positions:
                                        one_way_positions[name] = []
                                    one_way_positions[name].append((lvl, nx, ny))
                                    print(color_settings(
                                        f"{one_way_data['name']} One-way Teleporter {k}: z={lvl}, x={nx}, y={ny}",
                                        bcolors.WHITE, bcolors.BG_BROWN))
                                    break


def place_ability(grid, lvl, special_tiles, grid_size=100):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)
    CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)

    tile_positions = [(x, y) for x in range(grid_size) for y in range(grid_size) if grid[x][y] in {PATH, HIDDEN}]

    for ability_key, ability_data in special_tiles.items():
        if "other_name" in ability_data:
            other_name = ability_data["other_name"]
            if isinstance(other_name, list):
                other_name = " ".join(other_name)
            if re.search("Ability Station", other_name):
                for coord in ability_data["coord"]:
                    if lvl == coord[0]:
                        while True:
                            cx, cy = random.choice(tile_positions)
                            dx, dy = random.randint(-2, 2), random.randint(-2, 2)
                            nx, ny = cx + dx, cy + dy

                            nx = max(0, min(nx, grid_size - 1))
                            ny = max(0, min(ny, grid_size - 1))

                            if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] in [EMPTY, PATH, HIDDEN]:
                                complete_path(grid, nx, ny, "RANDOM", special_tiles=special_tiles)
                                grid[nx][ny] = next(
                                    (int(key, 16) for key, tile in special_tiles.items() if
                                     key == ability_key), None)

                                print(color_settings(
                                    f"{ability_data['name']} Ability station: z={lvl}, x={nx}, y={ny}", bcolors.PINK))
                                break


def place_adventures(grid, lvl, special_tiles, grid_size=100):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)
    CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)

    tile_positions = [(x, y) for x in range(grid_size) for y in range(grid_size) if grid[x][y] in {PATH, HIDDEN}]

    for adventures_key, adventures_data in special_tiles.items():
        if "other_name" in adventures_data:
            other_name = adventures_data["other_name"]
            if isinstance(other_name, list):
                other_name = " ".join(other_name)
            if re.search("Adventurer's Rest", other_name):
                for coord in adventures_data["coord"]:
                    if lvl == coord[0]:
                        while True:
                            cx, cy = random.choice(tile_positions)
                            dx, dy = random.randint(-2, 2), random.randint(-2, 2)
                            nx, ny = cx + dx, cy + dy

                            nx = max(0, min(nx, grid_size - 1))
                            ny = max(0, min(ny, grid_size - 1))

                            if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] in [EMPTY, PATH, HIDDEN]:
                                complete_path(grid, nx, ny, "RANDOM", special_tiles=special_tiles)
                                grid[nx][ny] = next(
                                    (int(key, 16) for key, tile in special_tiles.items() if
                                     key == adventures_key), None)

                                print(color_settings(
                                    f"{adventures_data['name']} Adventure's Rest: z={lvl}, x={nx}, y={ny}",
                                    bcolors.LIGHTPINK))
                                break


def place_resurrection(grid, lvl, special_tiles, grid_size=100):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)
    CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)

    tile_positions = [(x, y) for x in range(grid_size) for y in range(grid_size) if grid[x][y] in {PATH, HIDDEN}]

    for resurrection_key, resurrection_data in special_tiles.items():
        if "other_name" in resurrection_data:
            other_name = resurrection_data["other_name"]
            if isinstance(other_name, list):
                other_name = " ".join(other_name)
            if re.search("Resurrection Shrine", other_name):
                for coord in resurrection_data["coord"]:
                    if lvl == coord[0]:
                        while True:
                            cx, cy = random.choice(tile_positions)
                            dx, dy = random.randint(-2, 2), random.randint(-2, 2)
                            nx, ny = cx + dx, cy + dy

                            nx = max(0, min(nx, grid_size - 1))
                            ny = max(0, min(ny, grid_size - 1))

                            if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] in [EMPTY, PATH, HIDDEN]:
                                complete_path(grid, nx, ny, "RANDOM", special_tiles=special_tiles)
                                grid[nx][ny] = next(
                                    (int(key, 16) for key, tile in special_tiles.items() if
                                     key == resurrection_key), None)

                                print(color_settings(
                                    f"{resurrection_data['name']} Resurrection Shrine: z={lvl}, x={nx}, y={ny}",
                                    bcolors.BLACK, bcolors.BG_PINK))
                                break


def place_healing(grid, lvl, special_tiles, grid_size=100):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)
    CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)

    tile_positions = [(x, y) for x in range(grid_size) for y in range(grid_size) if grid[x][y] in {PATH, HIDDEN}]

    for healing_key, healing_data in special_tiles.items():
        if "other_name" in healing_data:
            other_name = healing_data["other_name"]
            if isinstance(other_name, list):
                other_name = " ".join(other_name)
            if re.search("Healing Fountain", other_name):
                for coord in healing_data["coord"]:
                    if lvl == coord[0]:
                        while True:
                            cx, cy = random.choice(tile_positions)
                            dx, dy = random.randint(-2, 2), random.randint(-2, 2)
                            nx, ny = cx + dx, cy + dy

                            nx = max(0, min(nx, grid_size - 1))
                            ny = max(0, min(ny, grid_size - 1))

                            if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] in [EMPTY, PATH, HIDDEN]:
                                complete_path(grid, nx, ny, "RANDOM", special_tiles=special_tiles)
                                grid[nx][ny] = next(
                                    (int(key, 16) for key, tile in special_tiles.items() if
                                     key == healing_key), None)

                                print(color_settings(
                                    f"{healing_data['name']} Healing Fountain: z={lvl}, x={nx}, y={ny}",
                                    bcolors.BLACK, bcolors.BG_GREEN))
                                break


def place_purification(grid, lvl, special_tiles, grid_size=100):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)
    CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)

    tile_positions = [(x, y) for x in range(grid_size) for y in range(grid_size) if grid[x][y] in {PATH, HIDDEN}]

    for purification_key, purification_data in special_tiles.items():
        if "other_name" in purification_data:
            other_name = purification_data["other_name"]
            if isinstance(other_name, list):
                other_name = " ".join(other_name)
            if re.search("Purification Spring", other_name):
                for coord in purification_data["coord"]:
                    if lvl == coord[0]:
                        while True:
                            cx, cy = random.choice(tile_positions)
                            dx, dy = random.randint(-2, 2), random.randint(-2, 2)
                            nx, ny = cx + dx, cy + dy

                            nx = max(0, min(nx, grid_size - 1))
                            ny = max(0, min(ny, grid_size - 1))

                            if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] in [EMPTY, PATH, HIDDEN]:
                                complete_path(grid, nx, ny, "RANDOM", special_tiles=special_tiles)
                                grid[nx][ny] = next(
                                    (int(key, 16) for key, tile in special_tiles.items() if
                                     key == purification_key), None)

                                print(color_settings(
                                    f"{purification_data['name']} Purification Spring: z={lvl}, x={nx}, y={ny}",
                                    bcolors.WHITE, bcolors.BG_WHITE))
                                break


def place_gorgon(grid, lvl, special_tiles, grid_size=100):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)
    CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)

    tile_positions = [(x, y) for x in range(grid_size) for y in range(grid_size) if grid[x][y] in {PATH, HIDDEN}]

    for gorgon_key, gorgon_data in special_tiles.items():
        if "other_name" in gorgon_data:
            other_name = gorgon_data["other_name"]
            if isinstance(other_name, list):
                other_name = " ".join(other_name)
            if re.search("Gorgon Altar", other_name):
                for coord in gorgon_data["coord"]:
                    if lvl == coord[0]:
                        while True:
                            cx, cy = random.choice(tile_positions)
                            dx, dy = random.randint(-2, 2), random.randint(-2, 2)
                            nx, ny = cx + dx, cy + dy

                            nx = max(0, min(nx, grid_size - 1))
                            ny = max(0, min(ny, grid_size - 1))

                            if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] in [EMPTY, PATH, HIDDEN]:
                                complete_path(grid, nx, ny, "RANDOM", special_tiles=special_tiles)
                                grid[nx][ny] = next(
                                    (int(key, 16) for key, tile in special_tiles.items() if
                                     key == gorgon_key), None)

                                print(color_settings(
                                    f"{gorgon_data['name']} Gorgon Altar: z={lvl}, x={nx}, y={ny}",
                                    bcolors.BLACK, bcolors.BG_BLUE))
                                break


def place_cavy(grid, lvl, special_tiles, grid_size=100):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)
    CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)

    tile_positions = [(x, y) for x in range(grid_size) for y in range(grid_size) if grid[x][y] in {PATH, HIDDEN}]

    for cavy_key, cavy_data in special_tiles.items():
        if "other_name" in cavy_data:
            other_name = cavy_data["other_name"]
            if isinstance(other_name, list):
                other_name = " ".join(other_name)
            if re.search("Cavy Idol", other_name):
                for coord in cavy_data["coord"]:
                    if lvl == coord[0]:
                        while True:
                            cx, cy = random.choice(tile_positions)
                            dx, dy = random.randint(-2, 2), random.randint(-2, 2)
                            nx, ny = cx + dx, cy + dy

                            nx = max(0, min(nx, grid_size - 1))
                            ny = max(0, min(ny, grid_size - 1))

                            if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] in [EMPTY, PATH, HIDDEN]:
                                complete_path(grid, nx, ny, "HIDDEN", special_tiles=special_tiles)
                                grid[nx][ny] = next(
                                    (int(key, 16) for key, tile in special_tiles.items() if
                                     key == cavy_key), None)

                                print(color_settings(
                                    f"{cavy_data['name']} Cavy Idol: z={lvl}, x={nx}, y={ny}",
                                    bcolors.BLACK, bcolors.BG_CYAN))
                                break


def place_note(grid, lvl, special_tiles, grid_size=100):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)
    CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)

    tile_positions = [(x, y) for x in range(grid_size) for y in range(grid_size) if grid[x][y] in {PATH, HIDDEN}]

    for note_key, note_data in special_tiles.items():
        if note_data.get("type_event") == "Notes":
            for coord in note_data.get("coord", []):
                if lvl == coord[0]:
                    cx, cy = random.choice(tile_positions)
                    dx, dy = random.randint(-2, 2), random.randint(-2, 2)
                    nx, ny = cx + dx, cy + dy

                    nx = max(0, min(nx, grid_size - 1))
                    ny = max(0, min(ny, grid_size - 1))

                    if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] in [EMPTY, PATH, HIDDEN]:
                        complete_path(grid, nx, ny, "RANDOM", special_tiles=special_tiles)
                        grid[nx][ny] = next(
                            (int(key, 16) for key, tile in special_tiles.items() if
                             tile["name"] == note_data['name']), None)

                        print(color_settings(
                            f"{note_data['name']} Note: z={lvl}, x={nx}, y={ny}",
                            bcolors.BLACK, bcolors.BG_MAGENTA))


def place_movement(grid, lvl, special_tiles, grid_size=100):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)
    CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)

    tile_positions = [(x, y) for x in range(grid_size) for y in range(grid_size) if grid[x][y] in {PATH, HIDDEN}]

    for movement_key, movement_data in special_tiles.items():
        if movement_data.get("type_event") == "Movement":
            for coord in movement_data.get("coord", []):
                if lvl == coord[0]:
                    cx, cy = random.choice(tile_positions)
                    dx, dy = random.randint(-2, 2), random.randint(-2, 2)
                    nx, ny = cx + dx, cy + dy

                    nx = max(0, min(nx, grid_size - 1))
                    ny = max(0, min(ny, grid_size - 1))

                    if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] in [EMPTY, PATH, HIDDEN]:
                        complete_path(grid, nx, ny, "RANDOM", special_tiles=special_tiles)
                        grid[nx][ny] = next(
                            (int(key, 16) for key, tile in special_tiles.items() if
                             tile["name"] == movement_data['name']), None)

                        print(color_settings(
                            f"{movement_data['name']} Movement ability: z={lvl}, x={nx}, y={ny}",
                            bcolors.BLACK, bcolors.BG_YELLOW))


def place_battle(grid, lvl, special_tiles, grid_size=100):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)
    CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)

    tile_positions = [(x, y) for x in range(grid_size) for y in range(grid_size) if grid[x][y] in {PATH, HIDDEN}]

    for battle_key, battle_data in special_tiles.items():
        if battle_data.get("type_event") == "Battle":
            for coord in battle_data.get("coord", []):
                if lvl == coord[0]:
                    cx, cy = random.choice(tile_positions)
                    dx, dy = random.randint(-2, 2), random.randint(-2, 2)
                    nx, ny = cx + dx, cy + dy

                    nx = max(0, min(nx, grid_size - 1))
                    ny = max(0, min(ny, grid_size - 1))

                    if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] in [EMPTY, PATH, HIDDEN]:
                        complete_path(grid, nx, ny, "RANDOM", special_tiles=special_tiles)
                        grid[nx][ny] = next(
                            (int(key, 16) for key, tile in special_tiles.items() if
                             tile["name"] == battle_data['name']), None)

                        print(color_settings(
                            f"{battle_data['name']} Battle ability: z={lvl}, x={nx}, y={ny}",
                            bcolors.BLACK, bcolors.BG_GRAY))


def place_cross(grid, lvl, special_tiles, grid_size=100):

    PATH = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "PATH"), None)
    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "EMPTY"), None)
    HIDDEN = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "HIDDEN"), None)
    CROSS = next((int(key, 16) for key, tile in special_tiles.items() if tile["name"] == "CROSS"), None)

    tile_positions = [(x, y) for x in range(grid_size) for y in range(grid_size) if grid[x][y] == PATH]

    for cross_key, cross_data in special_tiles.items():
        if cross_data["name"] == "CROSS":
            for coord in cross_data["coord"]:
                if lvl == coord[0]:
                    while True:
                        cx, cy = random.choice(tile_positions)
                        if 0 <= cx < grid_size and 0 <= cy < grid_size and grid[cx][cy] == PATH:
                            directions = [
                                (-1, 0), (1, 0), (0, -1), (0, 1),
                                (-1, -1), (-1, 1), (1, -1), (1, 1)
                            ]
                            nb_empty = 0
                            for dx, dy in directions:
                                nx, ny = cx + dx, cy + dy
                                if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] in [EMPTY, CROSS]:
                                    nb_empty += 1

                            if 3 < nb_empty < 6:
                                grid[cx][cy] = CROSS
                                print(color_settings(
                                    f"{cross_data['name']} path: z={lvl}, x={cx}, y={cy} {nb_empty}",
                                    bcolors.GRAY, bcolors.BG_BLACK))
                                break


def cheat_mode(grid, lvl, special_tiles, grid_size=100):

    EMPTY = next((int(key, 16) for key, tile in special_tiles.items() if
                  tile["name"] == "EMPTY"), None)

    def find_next_empty(x, y):
        while True:
            if 0 <= x < grid_size and 0 <= y < grid_size and grid[x][y] == EMPTY:
                return x, y
            x += 1
            if x >= grid_size:
                x = 0
                y += 1
            if y >= grid_size:
                x, y = 0, 0

    x, y = 0, 0
    for cheat_key, cheat_data in special_tiles.items():
        if cheat_data.get("type_event") in ["Movement", "Battle", "Riddles"] or (
                "other_name" in cheat_data and re.search("Treasure", " ".join(cheat_data["other_name"]))):

            x, y = find_next_empty(x, y)
            tile_value = next(
                (int(key, 16) for key, tile in special_tiles.items() if key == cheat_key),
                None
            )
            if tile_value is not None:
                grid[x][y] = tile_value

                print(color_settings(
                    f"{cheat_data['name']} {cheat_data.get('other_name', '')}: z={lvl}, x={x}, y={y}",
                    bcolors.BLACK, bcolors.BG_WHITE, bcolors.BLINK))

    complete_path(grid, x // 2, y, "PATH", special_tiles=special_tiles)
