import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 1. Configuration de la page (Design)
st.set_page_config(page_title="Raids Dingues - Courses", page_icon="🏃‍♂️", layout="centered")
st.title("🏃‍♂️ Application Raids Dingues")
st.write("Saison 2026 - Calendrier et Inscriptions")

# 2. Connexion au Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Lecture des onglets
# On commence à la ligne 3 (header=2) pour la BDD 2026
df_courses = conn.read(worksheet="BDD 2026", header=2, ttl=10) 
df_participations = conn.read(worksheet="PARTICIPATIONS", ttl=10)

# 3. Interface : Choix de la course
st.subheader("📅 Sélectionner une course")
liste_courses = df_courses["Nom de la course"].dropna().unique()
course_choisie = st.selectbox("Quelle course t'intéresse ?", liste_courses)

# 4. Affichage des détails de la course
if course_choisie:
    # On récupère la ligne de la course sélectionnée
    infos = df_courses[df_courses["Nom de la course"] == course_choisie].iloc[0]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write(f"📍 **Lieu :** {infos['Lieu']}")
        st.write(f"🗓 **Date :** {infos['Date']}")
        st.write(f"🏃 **Type :** {infos['Type de course']} ({infos['Détail']})")
        if pd.notna(infos['Lien']) and infos['Lien'] != "Clos":
            st.write(f"🔗 [Lien d'inscription]({infos['Lien']})")
            
    with col2:
        # Affichage de l'image si tu as créé une colonne 'Lien_Image' et qu'elle n'est pas vide
        if 'Lien_Image' in infos and pd.notna(infos['Lien_Image']):
            st.image(infos['Lien_Image'], use_column_width=True)

    st.divider()

    # 5. Affichage des membres déjà inscrits
    st.subheader("👥 Déjà inscrits :")
    inscrits = df_participations[df_participations["Nom_Course"] == course_choisie]
    
    if inscrits.empty:
        st.info("Aucun Raid Dingue n'est encore inscrit pour cette course. Sois le premier !")
    else:
        # Affiche un joli tableau avec les participants et leur distance
        st.dataframe(inscrits[["Nom_Membre", "Distance", "Statut"]], hide_index=True, use_container_width=True)
        
    st.divider()

    # 6. Formulaire pour s'inscrire
    st.subheader("✍️ M'inscrire à cette course")
    with st.form("form_inscription"):
        # Dans la version finale, on lira l'onglet MEMBRES pour la selectbox
        nom = st.text_input("Ton Prénom et Nom")
        distance = st.text_input("Distance choisie (ex: 12 km)")
        
        submit = st.form_submit_button("Je participe !")
        
        if submit and nom:
            # Création de la nouvelle ligne de donnée
            nouvelle_inscription = pd.DataFrame([{
                "Horodatage": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Nom_Membre": nom,
                "Nom_Course": course_choisie,
                "Distance": distance,
                "Statut": "Inscrit",
                "Resultat": ""
            }])
            
            # Ajout à la base de données existante
            df_updated = pd.concat([df_participations, nouvelle_inscription], ignore_index=True)
            
            # Mise à jour du Google Sheets
            conn.update(worksheet="PARTICIPATIONS", data=df_updated)
            
            st.success(f"Bravo {nom} ! Ton inscription a bien été enregistrée.")
            st.rerun() # Rafraichit la page pour voir le nom apparaitre