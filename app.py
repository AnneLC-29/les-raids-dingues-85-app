import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import calendar
import html
import folium
from streamlit_folium import st_folium
import streamlit.components.v1 as components

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

# 3. Base de coordonnées instantanée (GPS Villes)
COORDS_VILLES = {
    "FOURAS": (45.9875, -1.0936),
    "MAILLEZAIS": (46.3725, -0.7383),
    "LA ROCHELLE": (46.1603, -1.1511),
    "LES MATHES": (45.7183, -1.1472),
    "BRESSUIRE": (46.8406, -0.4939),
    "POUFFONDS": (46.1736, -0.1558),
    "ST LAURENT SUR SEVRE": (46.9583, -0.8931),
    "PARIS": (48.8566, 2.3522),
    "LUCS SUR BOULOGNE": (46.8439, -1.4939),
    "LES LUCS SUR BOULOGNE": (46.8439, -1.4939),
    "NUEIL LES AUBIERS": (46.9372, -0.5897),
    "LA CHAPELLE DES POTS": (45.7608, -0.5408),
    "AIGONNAY": (46.3411, -0.2447),
    "FONTENAY LE COMTE": (46.4667, -0.8000),
    "SAIVRES": (46.4250, -0.2319),
    "SAINTE SOULLE": (46.1856, -1.0117),
    "CUGAND": (47.0628, -1.2542),
    "ST MAIXENT L'ECOLE": (46.4117, -0.2078),
    "CHAPELLE ST LAURENT": (46.8147, -0.4786),
    "ARCHINGEAY": (45.9328, -0.6558),
    "MERVENT": (46.5228, -0.7553),
    "VALLET": (47.1611, -1.2658),
    "AIGONDIGNE": (46.3486, -0.2883),
    "BOURNEZEAU": (46.6358, -1.1689),
    "VINCENNES": (48.8475, 2.4392),
    "ISSY LES MOULINEAUX": (48.8239, 2.2703),
    "CHAMPDENIERS": (46.4842, -0.4028),
    "CHAUCHE": (46.8308, -1.2694),
    "CHARENTON LE PONT": (48.8222, 2.4144),
    "AIGREFEUILLE D'AUNIS": (46.1181, -0.9328),
    "BOISSIERE DE MONTAIGU": (46.9806, -1.1917),
    "VOLVIC": (45.8711, 3.0372),
    "ST JEAN DE MONTS": (46.7922, -2.0603),
    "MORTAGNE / SEVRE": (46.9931, -0.9542),
    "MORTAGNE SUR SEVRE": (46.9931, -0.9542),
    "ROCHEFORT": (45.9428, -0.9631),
    "ST MARTIN DES NOYERS": (46.7239, -1.1783),
    "LONGEVILLE SUR MER": (46.4239, -1.4889),
    "LA GAUBRETIERE": (46.9458, -1.0664),
    "BEAULIEU SOUS LA ROCHE": (46.6764, -1.6094),
    "SAUMUR": (47.2603, -0.0769),
    "L'OIE": (46.7981, -1.1325),
    "ST HILAIRE DE RIEZ": (46.7214, -1.9453),
    "POUZAUGES": (46.7833, -0.8333),
    "VENAUSAULT": (46.6858, -1.5125),
    "NIORT": (46.3237, -0.4648),
    "LUCON": (46.4550, -1.1664),
    "LA TRANCHE / MER": (46.3439, -1.4389),
    "LA TRANCHE SUR MER": (46.3439, -1.4389),
    "NOIRMOUTIER": (47.0003, -2.2417),
    "LES SABLES D'OLONNES": (46.4972, -1.7833),
    "LES SABLES D'OLONNE": (46.4972, -1.7833),
    "PARTHENAY": (46.6486, -0.2483),
    "LA ROCHE SUR YON": (46.6705, -1.4265),
    "BRESSUIRE": (46.8406, -0.4939),
    "CHATELAILLON-PLAGE": (46.0728, -1.0881),
    "CHATELAILLON": (46.0728, -1.0881),
    "LES HERBIERS": (46.8681, -1.0094),
    "NANTES": (47.2181, -1.5536),
    "CHANTONNAY": (46.6881, -1.0506),
    "MONTAIGU": (46.9739, -1.3125),
    "AIRVAULT": (46.8267, -0.1389),
    "TALMONT ST HILAIRE": (46.4683, -1.6186),
    "SAINTE NEOMAYE": (46.3719, -0.2589),
    "MAGNÉ": (46.3153, -0.5461)
}

def get_coords_fast(lieu_str):
    if not lieu_str or pd.isna(lieu_str):
        return None, None
    ville = str(lieu_str).split('(')[0].strip().upper()
    return COORDS_VILLES.get(ville, (46.67, -1.42))  # Coordonnées par défaut si ville inconnue

# 4. Gestion de la sélection automatique via l'URL
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

# --- TAB 2 : CALENDRIER VISUEL ---
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

# --- TAB 3 : CARTE INTERACTIVE RAPIDE ---
with tab_carte:
    st.subheader("🗺️ Localisation des courses")
    st.caption("Passe la souris ou clique sur un marqueur pour afficher l'événement.")
    
    m = folium.Map(location=[46.67, -1.42], zoom_start=8, tiles="OpenStreetMap")
    
    for _, row in df_courses.iterrows():
        lat, lon = get_coords_fast(row['Lieu'])
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