import shutil
import streamlit as st
import os
import DELM

def page_config(logo=None, mods_folder=None):
    if st.get_option("client.showSidebarNavigation") is True:
        st.set_option("client.showSidebarNavigation", False)
        st.rerun()

    img_path = os.path.join(os.path.dirname(__file__), '../.streamlit', 'DE_icon.jpg')

    st.set_page_config(page_title='Dungeon Encounters Map Generator', page_icon=img_path,
                       initial_sidebar_state="expanded", layout="wide")

    st.logo(img_path)
    if logo is True:
        st.sidebar.image(img_path)
    st.sidebar.title('🧱 DE Launcher Mod')
    st.sidebar.write("Created by [Minniti Julien](https://github.com/Jumitti)")

    # Ajouter un lien vers la page principale
    st.sidebar.page_link("DELauncherMod.py", label="**Home / Generator**", icon="🏠")

    st.sidebar.subheader("Mods settings")


def pages_mods(mods_folder=None):
    pages_folder = "pages"

    if mods_folder is not None:
        mod_folders = [f for f in os.listdir(mods_folder) if os.path.isdir(os.path.join(mods_folder, f))]

        for mod in mod_folders:
            mod_path = os.path.join(mods_folder, mod)
            mod_files = os.listdir(mod_path)

            for file in mod_files:
                if file.endswith("_streamlit.py"):
                    # Copier le fichier .py dans le dossier pages
                    DELM.copy_mod_file_to_pages(mod_path, file, pages_folder)

                    # Calculer le chemin relatif du fichier pour la sidebar
                    relative_path = os.path.relpath(os.path.join(pages_folder, file), os.getcwd())

                    # Si un fichier .py est trouvé, ajouter un lien dans la sidebar
                    st.sidebar.page_link(relative_path, label=f"Run {mod}", icon="📜")
