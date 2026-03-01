import os

# ==============================
# CONFIGURE AQUI
# ==============================

ROOT_PATH = r"C:\IC"  # <-- altere aqui
MAX_DEPTH = None  # None = sem limite | ou coloque um número ex: 5

# Pastas para ignorar completamente
IGNORE_DIRS = {
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build"
}

# Extensões de arquivos para ignorar (sempre em minúsculo)
IGNORE_EXTENSIONS = {
    ".xlsx",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg"
}

# ==============================
# FUNÇÃO
# ==============================

def print_tree(start_path, prefix="", level=0):
    if MAX_DEPTH is not None and level > MAX_DEPTH:
        return

    try:
        items = sorted(os.listdir(start_path))
    except PermissionError:
        return

    filtered_items = []

    for item in items:
        path = os.path.join(start_path, item)

        # Ignorar pastas específicas
        if item in IGNORE_DIRS:
            continue

        # Ignorar extensões específicas
        if os.path.isfile(path):
            _, ext = os.path.splitext(item)
            if ext.lower() in IGNORE_EXTENSIONS:
                continue

        filtered_items.append(item)

    for index, item in enumerate(filtered_items):
        path = os.path.join(start_path, item)
        is_last = index == len(filtered_items) - 1

        connector = "└── " if is_last else "├── "
        print(prefix + connector + item)

        if os.path.isdir(path):
            extension = "    " if is_last else "│   "
            print_tree(path, prefix + extension, level + 1)


if __name__ == "__main__":
    print(f"\nEstrutura de pastas: {ROOT_PATH}\n")
    print_tree(ROOT_PATH)