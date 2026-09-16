import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import calendar
import html
import folium
from streamlit_folium import st_folium
import streamlit.components.v1 as components
from geopy.geocoders import Nominatim

# 1. Configuration de la page
st.set_page_config(page_title="Raids Dingues 85", page_icon="🏃‍♂️", layout="wide")
st.title("🏃‍♂️ Raids Dingues 85")
st.write("Saison 2026 — Calendrier, Carte & Inscriptions")

# 2. Connexion au Google Sheet
conn = st.connection("gsheets", type=GSheetsConnection)

df_courses = conn.read(worksheet="BDD 2026", header=5, ttl=10)
df_participations = conn.read(worksheet="PARTICIPATIONS", ttl=10)

# Nettoyage et conversion des dates
df_courses['Date_dt'] = pd.to_datetime(df_courses['Date'], format='%d/%m/%Y', errors='coerce')
df_courses = df_courses.sort_values(by='Date_dt')

MOIS_FR = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
    7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
}

# 3. Géolocalisation pour la carte
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

# 4. Gestion de la sélection automatique via l'URL (si clic depuis le calendrier)
liste_courses = df_courses["Nom de la course"].dropna().unique()
course_url = st.query_params.get("course", None)

default_idx = 0
if course_url and course_url in liste_courses:
    default_idx = list(liste_courses).index(course_url)

# 5. Organisation en onglets
tab_fiche, tab_cal, tab_carte = st.tabs(["📋 Fiche & Inscription", "📅 Calendrier Visuel", "🗺️ Carte des courses"])

# --- TAB 1 : FICHE & INSCRIPTION ---
with tab_fiche:
    st.subheader("📅 Sélectionner une course")
    course_choisie = st.selectbox("Quelle course t'intéresse ?", liste_courses, index=default_idx)

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
                st.image(infos['Lien_Image'], width=300)

        st.divider()

        st.subheader("👥 Déjà inscrits :")
        inscrits = df_participations[df_participations["Nom_Course"] == course_choisie]
        
        if inscrits.empty:
            st.info("Aucun Raid Dingue n'est encore inscrit. Sois le premier !")
        else:
            st.dataframe(inscrits[["Nom_Membre", "Distance", "Statut"]], hide_index=True)
            
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

# --- TAB 2 : CALENDRIER VISUEL CORRIGÉ ---
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

    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(2026, mois_selectionne)

    html_code = f"""<!DOCTYPE html>
<html>
<head>
<style>
    body {{ margin: 0; padding-top: 40px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    .cal-table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
    .cal-th {{ background-color: #0066cc; color: white; text-align: center; padding: 10px; font-size: 13px; font-weight: bold; border: 1px solid #0055b3; }}
    .cal-td {{ border: 1px solid #ddd; vertical-align: top; height: 110px; padding: 5px; background-color: #ffffff; position: relative; }}
    .cal-empty {{ background-color: #f8f9fa; }}
    .day-num {{ font-weight: bold; font-size: 12px; color: #444; margin-bottom: 4px; }}
    
    .event-card {{
        position: relative;
        padding: 4px 6px;
        margin-bottom: 4px;
        border-radius: 4px;
        font-size: 11px;
        cursor: pointer;
    }}
    .event-red {{ background-color: #ffe6e6; color: #cc0000; border-left: 3px solid #cc0000; font-weight: bold; }}
    .event-blue {{ background-color: #e6f0ff; color: #004085; border-left: 3px solid #0066cc; }}
    
    /* Bulle d'information */
    .tooltip-content {{
        visibility: hidden;
        width: 210px;
        background-color: #1e293b;
        color: #ffffff;
        text-align: left;
        border-radius: 6px;
        padding: 8px 10px;
        position: absolute;
        z-index: 999;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        box-shadow: 0px 4px 12px rgba(0,0,0,0.3);
        font-size: 11px;
        line-height: 1.4;
        white-space: normal;
        opacity: 0;
        transition: opacity 0.15s ease-in-out;
        margin-bottom: 6px;
        pointer-events: auto;
    }}
    
    /* Flèche du bas */
    .tooltip-content::after {{
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: #1e293b transparent transparent transparent;
    }}
    
    /* Pont invisible pour combler le vide entre la carte et la bulle */
    .tooltip-content::before {{
        content: "";
        position: absolute;
        top: 100%;
        left: 0;
        width: 100%;
        height: 10px;
    }}
    
    .event-card:hover .tooltip-content {{
        visibility: visible;
        opacity: 1;
    }}
</style>
</head>
<body>
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
    <tbody>"""

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
                    nom_raw = str(row['Nom de la course'])
                    nom_c = html.escape(nom_raw)
                    lieu_c = html.escape(str(row['Lieu']))
                    type_c = html.escape(str(row['Type de course']))
                    detail_c = html.escape(str(row['Détail']))
                    
                    inscrits_df = df_participations[df_participations['Nom_Course'] == nom_raw]
                    inscrits_liste = inscrits_df['Nom_Membre'].tolist()
                    nb_inscrits = len(inscrits_liste)
                    
                    inscrits_html = ""
                    if nb_inscrits > 0:
                        membres_str = ", ".join([html.escape(m) for m in inscrits_liste])
                        inscrits_html = f"<br><b>👥 Inscrits ({nb_inscrits}) :</b><br>{membres_str}"
                    else:
                        inscrits_html = "<br><i>Aucun membre inscrit</i>"
                    
                    tooltip_body = f"""<b>{nom_c}</b><br>📍 {lieu_c}<br>🏃 {type_c} ({detail_c}){inscrits_html}<br><br><span style='color: #38bdf8; font-weight: bold;'>👉 Clic pour m'inscrire</span>"""
                    
                    nom_encoded = html.escape(nom_raw).replace("'", "\\'")
                    click_action = f"window.top.location.href='?course=' + encodeURIComponent('{nom_encoded}');"
                    
                    if nb_inscrits > 0:
                        cell_content += f"""
                        <div class="event-card event-red" onclick="{click_action}">
                            🔴 {nom_c} ({nb_inscrits})
                            <div class="tooltip-content">{tooltip_body}</div>
                        </div>"""
                    else:
                        cell_content += f"""
                        <div class="event-card event-blue" onclick="{click_action}">
                            🏃 {nom_c}
                            <div class="tooltip-content">{tooltip_body}</div>
                        </div>"""
                        
                html_code += f'<td class="cal-td">{cell_content}</td>'
        html_code += "</tr>"

    html_code += "</tbody></table></body></html>"

    components.html(html_code, height=680, scrolling=True)
    st.caption("💡 **Astuce :** Survole une course pour voir les détails. Clique directement sur la case ou sur la bulle pour ouvrir le formulaire d'inscription.")

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
                <b>{html.escape(str(row['Nom de la course']))}</b><br>
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
            
    st_folium(m, width=1100, height=500)