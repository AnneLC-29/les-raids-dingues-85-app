import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# 1. Configuration de la page
st.set_page_config(page_title="Raids Dingues 85", page_icon="🏃‍♂️", layout="wide")
st.title("🏃‍♂️ Raids Dingues 85")
st.write("Saison 2026 — Calendrier, Carte & Inscriptions")

# 2. Connexion au Google Sheet
conn = st.connection("gsheets", type=GSheetsConnection)

df_courses = conn.read(worksheet="BDD 2026", header=5, ttl=10)
df_participations = conn.read(worksheet="PARTICIPATIONS", ttl=10)

# Nettoyage et conversion des dates pour le tri
df_courses['Date_dt'] = pd.to_datetime(df_courses['Date'], format='%d/%m/%Y', errors='coerce')
df_courses = df_courses.sort_values(by='Date_dt')

# 3. Fonction de géolocalisation mise en cache
geolocator = Nominatim(user_agent="raids_dingues_app_85")

@st.cache_data
def get_lat_lon(lieu_str):
    if not lieu_str or pd.isna(lieu_str):
        return None, None
    try:
        ville = str(lieu_str).split('(')[0].strip()
        loc = geolocator.geocode(f"{ville}, France", timeout=5)
        if loc:
            return loc.latitude, loc.longitude
    except Exception:
        return None, None
    return None, None

# 4. Organisation en onglets
tab_fiche, tab_cal, tab_carte = st.tabs(["📋 Fiche & Inscription", "📅 Calendrier", "🗺️ Carte des courses"])

# --- TAB 1 : FICHE & INSCRIPTION ---
with tab_fiche:
    st.subheader("📅 Sélectionner une course")
    liste_courses = df_courses["Nom de la course"].dropna().unique()
    course_choisie = st.selectbox("Quelle course t'intéresse ?", liste_courses)

    if course_choisie:
        infos = df_courses[df_courses["Nom de la course"] == course_choisie].iloc[0]
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"📍 **Lieu :** {infos['Lieu']}")
            st.write(f"🗓 **Date :** {infos['Date']}")
            st.write(f"🏃 **Type :** {infos['Type de course']} ({infos['Détail']})")
            if pd.notna(infos['Lien']) and infos['Lien'] != "Clos":
                st.write(f"🔗 [Lien d'inscription]({infos['Lien']})")
                
        with col2:
            if 'Lien_Image' in infos and pd.notna(infos['Lien_Image']):
                st.image(infos['Lien_Image'], use_container_width=True)

        st.divider()

        st.subheader("👥 Déjà inscrits :")
        inscrits = df_participations[df_participations["Nom_Course"] == course_choisie]
        
        if inscrits.empty:
            st.info("Aucun Raid Dingue n'est encore inscrit. Sois le premier !")
        else:
            st.dataframe(inscrits[["Nom_Membre", "Distance", "Statut"]], hide_index=True, use_container_width=True)
            
        st.divider()

        st.subheader("✍️ M'inscrire à cette course")
        with st.form("form_inscription"):
            nom = st.text_input("Ton Prénom et Nom")
            distance = st.text_input("Distance choisie (ex : 12 km)")
            submit = st.form_submit_button("Je participe !")
            
            if submit and nom:
                nouvelle_inscription = pd.DataFrame([{
                    "Horodatage": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Nom_Membre": nom,
                    "Nom_Course": course_choisie,
                    "Distance": distance,
                    "Statut": "Inscrit",
                    "Resultat": ""
                }])
                df_updated = pd.concat([df_participations, nouvelle_inscription], ignore_index=True)
                conn.update(worksheet="PARTICIPATIONS", data=df_updated)
                st.success(f"Bravo {nom} ! Ton inscription a été enregistrée.")
                st.rerun()

# --- TAB 2 : CALENDRIER ---
with tab_cal:
    st.subheader("📅 Programme de la saison 2026")
    
    # Filtre par mois
    df_courses['Mois_Nom'] = df_courses['Date_dt'].dt.strftime('%m - %B')
    mois_dispos = ["Tous"] + list(df_courses['Mois_Nom'].dropna().unique())
    mois_filtre = st.selectbox("Filtrer par mois :", mois_dispos)
    
    df_affiche = df_courses.copy()
    if mois_filtre != "Tous":
        df_affiche = df_affiche[df_affiche['Mois_Nom'] == mois_filtre]
        
    for _, row in df_affiche.iterrows():
        with st.expander(f"🗓 {row['Date']} — **{row['Nom de la course']}** ({row['Lieu']})"):
            st.write(f"**Type :** {row['Type de course']} | **Format :** {row['Détail']}")
            if pd.notna(row['Lien']) and row['Lien'] != "Clos":
                st.write(f"🔗 [Site officiel / Inscription]({row['Lien']})")

# --- TAB 3 : CARTE INTERACTIVE ---
with tab_carte:
    st.subheader("🗺️ Localisation des courses")
    st.caption("Passe la souris ou clique sur un marqueur pour afficher le nom de l'événement.")
    
    # Centre de la carte (Vendée / Grand Ouest)
    m = folium.Map(location=[46.67, -1.42], zoom_start=8, tiles="OpenStreetMap")
    
    # Ajout des marqueurs
    for _, row in df_courses.iterrows():
        lieu = row['Lieu']
        lat, lon = get_lat_lon(lieu)
        if lat and lon:
            popup_html = f"""
            <div style='font-family: sans-serif; width: 180px;'>
                <b>{row['Nom de la course']}</b><br>
                📅 {row['Date']}<br>
                📍 {row['Lieu']}<br>
                🏃 {row['Type de course']}<br>
                <small>{row['Détail']}</small>
            </div>
            """
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=220),
                tooltip=f"{row['Nom de la course']} ({row['Date']})",
                icon=folium.Icon(color="red", icon="flag")
            ).add_to(m)
            
    st_folium(m, width="100%", height=500)