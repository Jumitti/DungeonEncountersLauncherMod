class bcolors:

    # Standard text colors
    MAGENTA = '\033[95m'  # Light magenta
    PINK = '\033[38;5;205m'  # Pink
    ORANGE = '\033[38;5;208m'  # Orange
    BROWN = '\033[38;5;94m'  # Brown
    OKBLUE = '\033[94m'  # Blue
    OKCYAN = '\033[96m'  # Cyan
    OKGREEN = '\033[92m'  # Green
    WARNING = '\033[93m'  # Yellow
    FAIL = '\033[91m'  # Red

    # Advanced text colors
    LIGHTPINK = '\033[38;5;218m'  # Light pink
    LIGHTORANGE = '\033[38;5;214m'  # Light orange (peach tone)
    BLACK = '\033[30m'  # Black
    WHITE = '\033[97m'  # White
    GRAY = '\033[90m'  # Gray

    # Background colors
    BG_RED = '\033[41m'  # Red background
    BG_PINK = '\033[48;5;205m'  # Pink background
    BG_ORANGE = '\033[48;5;208m'  # Orange background
    BG_BROWN = '\033[48;5;94m'  # Brown background
    BG_GREEN = '\033[42m'  # Green background
    BG_YELLOW = '\033[43m'  # Yellow background
    BG_BLUE = '\033[44m'  # Blue background
    BG_MAGENTA = '\033[45m'  # Magenta background
    BG_CYAN = '\033[46m'  # Cyan background
    BG_BLACK = '\033[40m'  # Black background
    BG_WHITE = '\033[47m'  # White background
    BG_GRAY = '\033[100m'  # Gray background

    # Effect
    BOLD = '\033[1m'  # Bold
    UNDERLINE = '\033[4m'  # Underline
    ITALIC = '\033[3m'  # Italic (may not work everywhere)
    BLINK = '\033[5m'  # Blinking text (may not work everywhere)
    REVERSE = '\033[7m'  # Reverses background/text colors
    ENDC = '\033[0m'  # Resets the style


def display_colored_text():
    print(f"{bcolors.MAGENTA}MAGENTA: This is a magenta.{bcolors.ENDC}")
    print(f"{bcolors.OKBLUE}OKBLUE: This is blue text.{bcolors.ENDC}")
    print(f"{bcolors.OKCYAN}OKCYAN: This is cyan text.{bcolors.ENDC}")
    print(f"{bcolors.OKGREEN}OKGREEN: This is green text.{bcolors.ENDC}")
    print(f"{bcolors.WARNING}WARNING: This is yellow warning text.{bcolors.ENDC}")
    print(f"{bcolors.FAIL}FAIL: This is red error text.{bcolors.ENDC}")
    print(f"{bcolors.BOLD}BOLD: This is bold text.{bcolors.ENDC}")
    print(f"{bcolors.UNDERLINE}UNDERLINE: This is underlined text.{bcolors.ENDC}")
    print(f"{bcolors.ITALIC}ITALIC: This is italic text (may not work everywhere).{bcolors.ENDC}")
    print(f"{bcolors.BLINK}BLINK: This is blinking text (may not work everywhere).{bcolors.ENDC}")
    print(f"{bcolors.REVERSE}REVERSE: This text has reversed colors.{bcolors.ENDC}")
    print(f"{bcolors.BG_RED}BG_RED: This has a red background.{bcolors.ENDC}")
    print(f"{bcolors.BG_GREEN}{bcolors.WHITE}BG_GREEN: Green background with white text.{bcolors.ENDC}")
    print(f"{bcolors.BG_YELLOW}{bcolors.GRAY}BG_YELLOW: Yellow background with gray text.{bcolors.ENDC}")
    print(f"{bcolors.BG_BLUE}{bcolors.LIGHTMAGENTA}BG_BLUE: Blue background with magenta text.{bcolors.ENDC}")


def color_settings(value, settings_1=None, settings_2=None, settings_3=None, settings_4=None):
    styles = []
    if settings_1:
        styles.append(settings_1)
    if settings_2:
        styles.append(settings_2)
    if settings_3:
        styles.append(settings_3)
    if settings_4:
        styles.append(settings_4)

    return f"{''.join(styles)}{value}{bcolors.ENDC}"
