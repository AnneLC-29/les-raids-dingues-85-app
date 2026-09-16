import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import calendar
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

# Nettoyage et conversion des dates pour le tri et le calendrier
df_courses['Date_dt'] = pd.to_datetime(df_courses['Date'], format='%d/%m/%Y', errors='coerce')
df_courses = df_courses.sort_values(by='Date_dt')

# Dictionnaire des mois en français
MOIS_FR = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
    7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
}

# 3. Géolocalisation mise en cache pour la carte
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
tab_fiche, tab_cal, tab_carte = st.tabs(["📋 Fiche & Inscription", "📅 Calendrier Visuel", "🗺️ Carte des courses"])

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

# --- TAB 2 : CALENDRIER VISUEL GRILLE ---
with tab_cal:
    st.subheader("📅 Vue Calendrier Mensuel 2026")
    
    col_m, _ = st.columns([2, 3])
    with col_m:
        mois_selectionne = st.selectbox(
            "Choisir le mois :",
            range(1, 13),
            index=0,
            format_func=lambda m: f"{MOIS_FR[m]} 2026"
        )

    # Matrice des jours du mois
    cal = calendar.Calendar(firstweekday=0)  # Lundi = 0
    month_days = cal.monthdayscalendar(2026, mois_selectionne)

    # Style HTML/CSS du calendrier
    html_code = """
    <style>
        .cal-container { overflow-x: auto; width: 100%; }
        .cal-table { width: 100%; min-width: 700px; border-collapse: collapse; font-family: sans-serif; table-layout: fixed; }
        .cal-th { background-color: #0066cc; color: white; text-align: center; padding: 10px; font-weight: bold; border: 1px solid #0055b3; }
        .cal-td { border: 1px solid #ddd; vertical-align: top; height: 110px; padding: 6px; background-color: #ffffff; }
        .cal-empty { background-color: #f8f9fa; border: 1px solid #eee; }
        .day-num { font-weight: bold; font-size: 13px; color: #333; margin-bottom: 6px; }
        .event-red { background-color: #ffe6e6; color: #cc0000; border-left: 4px solid #cc0000; padding: 4px 6px; margin-bottom: 4px; border-radius: 4px; font-size: 11px; font-weight: bold; word-wrap: break-word; }
        .event-normal { background-color: #e6f0ff; color: #004085; border-left: 4px solid #0066cc; padding: 4px 6px; margin-bottom: 4px; border-radius: 4px; font-size: 11px; word-wrap: break-word; }
    </style>
    <div class="cal-container">
    <table class="cal-table">
        <thead>
            <tr>
                <th class="cal-th">LUNDI</th>
                <th class="cal-th">MARDI</th>
                <th class="cal-th">MERCREDI</th>
                <th class="cal-th">JEUDI</th>
                <th class="cal-th">VENDREDI</th>
                <th class="cal-th">SAMEDI</th>
                <th class="cal-th">DIMANCHE</th>
            </tr>
        </thead>
        <tbody>
    """

    for week in month_days:
        html_code += "<tr>"
        for day in week:
            if day == 0:
                html_code += '<td class="cal-td cal-empty"></td>'
            else:
                date_target = pd.Timestamp(year=2026, month=mois_selectionne, day=day)
                courses_jour = df_courses[df_courses['Date_dt'] == date_target]
                
                cell_content = f'<div class="day-num">{day}</div>'
                
                for _, row in courses_jour.iterrows():
                    nom_c = row['Nom de la course']
                    # Nombre d'inscrits dans l'onglet PARTICIPATIONS
                    inscrits_c = df_participations[df_participations['Nom_Course'] == nom_c]
                    nb_inscrits = len(inscrits_c)
                    
                    if nb_inscrits > 0:
                        cell_content += f'<div class="event-red">🔴 {nom_c} ({nb_inscrits})</div>'
                    else:
                        cell_content += f'<div class="event-normal">🏃 {nom_c}</div>'
                        
                html_code += f'<td class="cal-td">{cell_content}</td>'
        html_code += "</tr>"

    html_code += "</tbody></table></div>"

    st.markdown(html_code, unsafe_allow_html=True)
    st.write("")
    st.caption("🔴 **Légende :** Fond rouge = au moins 1 Raid Dingue inscrit (nombre d'inscrits entre parenthèses). Fond bleu = course libre.")

# --- TAB 3 : CARTE INTERACTIVE ---
with tab_carte:
    st.subheader("🗺️ Localisation des courses")
    st.caption("Passe la souris ou clique sur un marqueur pour afficher le nom de l'événement.")
    
    m = folium.Map(location=[46.67, -1.42], zoom_start=8, tiles="OpenStreetMap")
    
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