import streamlit as st
import pandas as pd
import re
import requests
import folium
import os
import time as time_lib
from datetime import datetime, time
import zoneinfo
from streamlit_folium import st_folium

# Configuration de la page
st.set_page_config(page_title="Outil Speaker Course", layout="wide")

st.title("🎙️ Samedi 03 Octobre 2026 - 3ème édition des Foulées des Raids Dingues")

# Dictionnaire des catégories FFA avec tranches d'âge
CATEGORIES_AGE = {
    'BB': 'Baby (3-5 ans)',
    'EA': 'Éveil Athlé (6-9 ans)',
    'PO': 'Poussins (10-11 ans)',
    'BE': 'Benjamins (12-13 ans)',
    'MI': 'Minimes (14-15 ans)',
    'CA': 'Cadets (16-17 ans)',
    'JU': 'Juniors (18-19 ans)',
    'ES': 'Espoirs (20-22 ans)',
    'SE': 'Séniors (23-34 ans)',
    'M0': 'Master 0 (35-39 ans)',
    'M1': 'Master 1 (40-44 ans)',
    'M2': 'Master 2 (45-49 ans)',
    'M3': 'Master 3 (50-54 ans)',
    'M4': 'Master 4 (55-59 ans)',
    'M5': 'Master 5 (60-64 ans)',
    'M6': 'Master 6 (65-69 ans)',
    'M7': 'Master 7 (70-74 ans)',
    'M8': 'Master 8 (75-79 ans)',
    'M9': 'Master 9 (80-84 ans)',
    'M10': 'Master 10 (85+ ans)'
}

ORDRE_CATEGORIES = list(CATEGORIES_AGE.keys())

# Liste officielle des adhérents / membres Raids Dingues
MEMBRES_RAIDS_DINGUES = [
    "BAUDRY Gaëtan", "BONNIN Gregory", "GUILLON Geoffroy", "PARADIS Caroline", "RENAUD Stéphane",
    "GUÉRY Médérick", "LE COZ Anne", "BOBIN Mathieu", "CHARRON Giovanni", "PUAUD Delphine",
    "BRIAND Mathieu", "RENAUD David", "DESLANDES Michael", "BLANCHET Lilian", "CHEVOLEAU Anne",
    "TRUTEAU Pierre", "FAUGER Axelle", "LE MOULLEC Kyllian", "COUÉ Jean-François", "MANTEAU Pierre",
    "RENOU Julien", "FOLIARD LE GAL Hélène", "RENAUD Jean-François", "JANVIER Ludovic", "DELALANDRE Cyril",
    "MANTEAU Aline", "CHAPELET Joachim", "MÉNARD Adeline", "BLANCHET Noël", "BAUDRY Julie",
    "GOUIN Fréderic", "FOLIARD LE GAL Sébastien", "GUÉRY Axel", "AUBRY Christophe", "HUMBERT-DROZ-LAURENT Emmanuelle",
    "BOUTEILLER François", "BONNIN Bérengère", "MATHIEU Sébastien", "BRIAND Charlotte", "BOUDAUD Amélie",
    "SOUCHARD Céline", "TOUMI Tony", "RENOU Mathieu", "BONNIN Elodie", "BONNIN Anthony",
    "GANTIER Aurélie", "BERNARD Johanne", "DOBIGNY Aurore", "JORET Isabelle", "BONNIN Aloïs",
    "TANGATCHY Stéphane", "RIVÉ Sébastien", "ROY Bernard", "BLANCHET Quentin", "GABORIAU Freddy",
    "BLUTEAU Simon", "BLANCHET Romain", "BIRONNEAU Stéphanie", "ROUSSEAU Cécile", "GUILLON Arnaud",
    "LE GOFF Yohan", "NEAU Gaëtan", "CHARRON Virginie", "GABORIT Maxime", "MORIN Raphaël",
    "PARADIS Thérèse", "PARADIS Jean-Michel", "BAUDRY Noël", "BAUDRY Thérèse", "BLANCHET Isabelle",
    "BONNIN Pascal", "GUILLON Yolaine"
]

def clean_name_str(s):
    if pd.isna(s): return ""
    return re.sub(r'[^A-Z]', '', str(s).upper())

MEMBRES_RAIDS_CLEAN = [clean_name_str(m) for m in MEMBRES_RAIDS_DINGUES]

def calc_vitesse(dist_km, time_str):
    try:
        parts = str(time_str).strip().split(':')
        if len(parts) == 3:
            h, m, s = map(int, parts)
            total_hours = h + m/60.0 + s/3600.0
        elif len(parts) == 2:
            m, s = map(int, parts)
            total_hours = m/60.0 + s/3600.0
        else:
            return ""
        if total_hours > 0:
            speed = dist_km / total_hours
            return f"⚡ **{speed:.1f} km/h**"
    except Exception:
        pass
    return ""

def add_medal_prefix(res_str):
    if pd.isna(res_str) or str(res_str).strip() in ["", "-", "NONE", "NAN"]:
        return "-"
    s = str(res_str).strip()
    match = re.search(r'^\s*(\d+)\s*([MF]?)', s, re.IGNORECASE)
    if match:
        rank = int(match.group(1))
        if rank == 1:
            return f"🥇 {s}"
        elif rank == 2:
            return f"🥈 {s}"
        elif rank == 3:
            return f"🥉 {s}"
    return s

def extract_rank_number(res_str):
    if pd.isna(res_str): return 9999
    match = re.search(r'(\d+)', str(res_str))
    if match:
        return int(match.group(1))
    return 9999

def extract_club(val):
    if pd.isna(val):
        return "Indépendant / Non renseigné"
    parts = str(val).split('/', 1)
    if len(parts) > 1 and parts[1].strip() != "":
        return parts[1].strip()
    return "Indépendant / Non renseigné"

def extract_ville_cp(val):
    if pd.isna(val):
        return "Inconnue", None
    ville_part = str(val).split('/')[0].strip()
    match = re.search(r'^(.*?)\s*\(\s*([\d\s]{5,6})\s*\)', ville_part)
    if match:
        nom_ville = match.group(1).strip()
        cp = re.sub(r'\s+', '', match.group(2).strip())
        return nom_ville, cp
    if "TAUGON" in ville_part.upper():
        return "TAUGON", "17170"
    return ville_part, None

@st.cache_data
def load_and_process_data():
    try:
        df = pd.read_csv("coureurs.csv", sep=None, engine='python')
    except Exception:
        df = pd.read_csv("coureurs.csv")
    
    df.columns = [str(c).strip() for c in df.columns]

    col_nom = None
    for c in df.columns:
        if c.upper().strip() in ['NOM', 'NOM_COUREUR', 'NOM COUREUR']:
            col_nom = c
            break
            
    if col_nom and col_nom != 'NOM':
        df.rename(columns={col_nom: 'NOM'}, inplace=True)

    if 'NOM' in df.columns:
        df = df[df['NOM'].notna() & (df['NOM'].astype(str).str.strip() != "") & (df['NOM'].astype(str).str.upper() != "NAN")]

    col_course = None
    for c in df.columns:
        if c.upper().strip() in ['COURSE', 'ÉPREUVE', 'EPREUVE', 'DISTANCE']:
            col_course = c
            break
            
    if col_course and col_course != 'COURSE':
        df.rename(columns={col_course: 'COURSE'}, inplace=True)
    elif not col_course:
        df['COURSE'] = "Non renseigné"

    col_dossard = None
    for c in df.columns:
        if c.upper() in ['DOSSARD', 'DOS', 'N° DOSSARD', 'N°DOSSARD']:
            col_dossard = c
            break

    if col_dossard:
        df['DOSSARD'] = pd.to_numeric(df[col_dossard], errors='coerce')
    else:
        df['DOSSARD'] = None

    if 'Indice BETRAIL' in df.columns:
        df['Indice BETRAIL'] = pd.to_numeric(df['Indice BETRAIL'], errors='coerce')
    else:
        df['Indice BETRAIL'] = None
    
    if 'SEXE' in df.columns:
        df['SEXE'] = df['SEXE'].astype(str).str.strip().str.upper()
    else:
        df['SEXE'] = ""

    ville_col = df['VILLE'] if 'VILLE' in df.columns else pd.Series([""] * len(df))
    df['CLUB'] = ville_col.apply(extract_club)
    res_villes = ville_col.apply(extract_ville_cp)
    df['NOM_VILLE'] = [r[0] for r in res_villes]
    df['CODE_POSTAL'] = [r[1] for r in res_villes]
    df['VILLE_CLEAN'] = df.apply(lambda r: f"{r['NOM_VILLE']} ({r['CODE_POSTAL']})" if pd.notna(r['CODE_POSTAL']) else r['NOM_VILLE'], axis=1)
    df['NOM_COMPLET'] = df.apply(lambda r: f"{str(r.get('NOM', '')).strip()} {str(r.get('PRENOM', '')).strip()}".upper(), axis=1)
    
    return df

@st.cache_data
def geolocaliser_communes(df_villes):
    coords = []
    for _, row in df_villes.iterrows():
        cp = str(row['CODE_POSTAL']).strip() if pd.notna(row['CODE_POSTAL']) else None
        ville = str(row['NOM_VILLE']).strip() if pd.notna(row['NOM_VILLE']) else ""
        
        if cp and cp != "None":
            try:
                url = f"https://geo.api.gouv.fr/communes?codePostal={cp}&fields=centre,nom&format=json"
                response = requests.get(url, timeout=3).json()
                
                if response:
                    commune_match = response[0]
                    for item in response:
                        if item.get('nom', '').lower() == ville.lower():
                            commune_match = item
                            break
                    
                    if 'centre' in commune_match:
                        lon, lat = commune_match['centre']['coordinates']
                        coords.append({
                            'NOM_VILLE': ville,
                            'CODE_POSTAL': cp,
                            'Ville_CP': f"{ville} ({cp})",
                            'latitude': lat,
                            'longitude': lon
                        })
            except Exception:
                pass
    return pd.DataFrame(coords)

try:
    df = load_and_process_data()

    has_2025 = 'FOULEES 2025' in df.columns
    has_2024 = 'FOULEES 2024' in df.columns

    col_boldair = None
    for c in df.columns:
        if "BOL" in c.upper():
            col_boldair = c
            break

    col_renaissance = None
    for c in df.columns:
        if "RENAISSANCE" in c.upper():
            col_renaissance = c
            break

    # -------------------------------------------------------------
    # ⏱️ BARRE DU HAUT : COMPTE À REBOURS SAMEDI 3 OCTOBRE 2026
    # -------------------------------------------------------------
    tz_france = zoneinfo.ZoneInfo("Europe/Paris")
    now = datetime.now(tz_france)
    
    date_course = datetime(2026, 10, 3, tzinfo=tz_france).date()
    h16 = datetime.combine(date_course, time(16, 0, 0), tzinfo=tz_france)
    h1645 = datetime.combine(date_course, time(16, 45, 0), tzinfo=tz_france)
    
    diff_16 = h16 - now
    diff_1645 = h1645 - now

    def format_td(td):
        if td.total_seconds() < 0:
            return "🏁 Épreuve lancée !"
        
        total_sec = int(td.total_seconds())
        days = total_sec // 86400
        hrs = (total_sec % 86400) // 3600
        mins = (total_sec % 3600) // 60
        secs = total_sec % 60
        
        if days > 0:
            return f"⏳ J-{days} ({hrs:02d}h {mins:02d}m {secs:02d}s)"
        else:
            return f"⏳ {hrs:02d}h {mins:02d}m {secs:02d}s"

    col_h1, col_h2, col_h3 = st.columns([1, 1, 1])
    
    with col_h1:
        st.metric("🕒 Heure Actuelle (France)", now.strftime("%d/%m/%Y - %H:%M:%S"))
    with col_h2:
        st.metric("🚩 15 KM & 25 KM (03/10 à 16h00)", format_td(diff_16))
    with col_h3:
        st.metric("🚩 8 KM & Marche (03/10 à 16h45)", format_td(diff_1645))

    # -------------------------------------------------------------
    # 📊 BARRES DE CHARGE / REMPLISSAGE COURSES (150 PLACES / COURSE)
    # -------------------------------------------------------------
    st.markdown("##### 🎯 Taux de Remplissage des Épreuves (Quota : 150 places / course)")
    
    MAX_PLACES = 150
    df_real_courses = df[df['COURSE'].notna() & (~df['COURSE'].astype(str).str.upper().str.contains("ADHERENT"))] if 'COURSE' in df.columns else pd.DataFrame()
    
    def get_count(pattern):
        if df_real_courses.empty: return 0
        return len(df_real_courses[df_real_courses['COURSE'].astype(str).str.contains(pattern, case=False, na=False)])

    nb_8k = get_count("8")
    nb_15k = get_count("15")
    nb_25k = get_count("25")

    c_c1, c_c2, c_c3 = st.columns(3)
    
    with c_c1:
        pct_8k = min(1.0, nb_8k / MAX_PLACES)
        st.write(f"🏃 **8 KM** : **{nb_8k} / {MAX_PLACES}** inscrits (**{pct_8k*100:.1f}%**)")
        st.progress(pct_8k)
        
    with c_c2:
        pct_15k = min(1.0, nb_15k / MAX_PLACES)
        st.write(f"🏃 **15 KM** : **{nb_15k} / {MAX_PLACES}** inscrits (**{pct_15k*100:.1f}%**)")
        st.progress(pct_15k)
        
    with c_c3:
        pct_25k = min(1.0, nb_25k / MAX_PLACES)
        st.write(f"🏃 **25 KM** : **{nb_25k} / {MAX_PLACES}** inscrits (**{pct_25k*100:.1f}%**)")
        st.progress(pct_25k)

    st.markdown("---")

    # -------------------------------------------------------------
    # ⚡ BARRE LATERALE : RECHERCHE & RECHARGEMENT CSV & DATE MAJ
    # -------------------------------------------------------------
    st.sidebar.header("⚡ Outils Rapides Speaker")
    
    if os.path.exists("coureurs.csv"):
        mtime = os.path.getmtime("coureurs.csv")
        last_mod_dt = datetime.fromtimestamp(mtime, tz=tz_france)
        st.sidebar.caption(f"📅 **Dernier import CSV :** {last_mod_dt.strftime('%d/%m/%Y à %H:%M:%S')}")
    else:
        st.sidebar.caption("📅 **Dernier import CSV :** Inconnu")

    if st.sidebar.button("🔄 Force Recharger CSV (GitHub)", use_container_width=True):
        st.cache_data.clear()
        st.sidebar.success("Données rechargées !")
        st.rerun()

    st.sidebar.markdown("---")
    quick_query = st.sidebar.text_input("🔍 N° Dossard ou Nom :", placeholder="Tapez ici...").strip()
    
    if quick_query:
        if quick_query.isdigit() and 'DOSSARD' in df.columns:
            res_q = df[df['DOSSARD'] == int(quick_query)]
        else:
            res_q = df[df['NOM_COMPLET'].str.contains(quick_query.upper(), na=False)]
            
        if not res_q.empty:
            if len(res_q) > 1:
                st.sidebar.info(f"{len(res_q)} trouvés :")
                opts_q = {f"#{int(r['DOSSARD']) if pd.notna(r.get('DOSSARD')) else 'N/A'} {r.get('NOM','')} {r.get('PRENOM','')}": idx for idx, r in res_q.iterrows()}
                sel_q = st.sidebar.selectbox("Choisir :", options=list(opts_q.keys()))
                c_q = res_q.loc[opts_q[sel_q]]
            else:
                c_q = res_q.iloc[0]
                
            st.sidebar.success(f"🏃 **{c_q.get('NOM','')} {c_q.get('PRENOM','')}**")
            dos_val = int(c_q['DOSSARD']) if pd.notna(c_q.get('DOSSARD')) else 'N/A'
            st.sidebar.write(f"• **Dossard :** #{dos_val}")
            st.sidebar.write(f"• **Course :** {c_q.get('COURSE','N/A')}")
            st.sidebar.write(f"• **Catégorie :** {c_q.get('Catégorie','N/A')}")
            st.sidebar.write(f"• **Ville/Club :** {c_q.get('VILLE_CLEAN','N/A')}")
            
            if col_boldair and pd.notna(c_q.get(col_boldair)) and str(c_q.get(col_boldair)).strip() not in ["", "-", "NONE", "NAN"]:
                st.sidebar.info(f"🌲 **Bol d'Air 2026 :** {c_q.get(col_boldair)}")

            if col_renaissance and pd.notna(c_q.get(col_renaissance)) and str(c_q.get(col_renaissance)).strip() not in ["", "-", "NONE", "NAN"]:
                st.sidebar.info(f"🏰 **Renaissance 2026 :** {c_q.get(col_renaissance)}")
                
            if pd.notna(c_q.get('Indice BETRAIL')):
                st.sidebar.write(f"• **Betrail :** {c_q['Indice BETRAIL']}")
            if pd.notna(c_q.get('COMMENTAIRES')):
                st.sidebar.warning(f"📝 {c_q['COMMENTAIRES']}")
        else:
            st.sidebar.error("Aucun participant trouvé.")

    # -------------------------------------------------------------
    # ONGLETS DE NAVIGATION PRINCIPAUX
    # -------------------------------------------------------------
    tab_general, tab_raids, tab_search, tab_favoris, tab_stats, tab_sponsors = st.tabs([
        "📈 Infos Générales & Stats",
        "🛡️ Résultats Raids Dingues",
        "🔎 Recherche Participant", 
        "🏆 Favoris & Cotes Betrail", 
        "📊 Origine & Clubs",
        "🤝 Sponsors & Partenaires"
    ])

    # -------------------------------------------------------------
    # ONGLET 1 : INFOS GÉNÉRALES & STATISTIQUES
    # -------------------------------------------------------------
    with tab_general:
        st.subheader("📈 Statistiques Générales & Fidélité")
        
        df_epreuves = df[df['COURSE'].notna() & (~df['COURSE'].astype(str).str.upper().str.contains("ADHERENT"))].copy() if 'COURSE' in df.columns else pd.DataFrame()
        
        if not df_epreuves.empty:
            courses_raw = df_epreuves['COURSE'].unique()
            
            def sort_courses_key(course_str):
                s = str(course_str).upper()
                if "MARCHE" in s:
                    return (0, 0)
                match = re.search(r'(\d+)', s)
                km = int(match.group(1)) if match else 999
                return (1, km)
                
            courses_sorted = sorted(courses_raw, key=sort_courses_key)
            matrix_data = []
            
            total_h = len(df_epreuves[df_epreuves['SEXE'] == 'H'])
            total_f = len(df_epreuves[df_epreuves['SEXE'] == 'F'])
            total_global = len(df_epreuves)
            
            tot_p2025 = len(df_epreuves[df_epreuves['FOULEES 2025'].notna() & (df_epreuves['FOULEES 2025'].astype(str).str.strip() != "")]) if has_2025 else 0
            tot_p2024 = len(df_epreuves[df_epreuves['FOULEES 2024'].notna() & (df_epreuves['FOULEES 2024'].astype(str).str.strip() != "")]) if has_2024 else 0

            for c in courses_sorted:
                df_c = df_epreuves[df_epreuves['COURSE'] == c]
                tot_c = len(df_c)
                if tot_c == 0: continue
                
                h_cnt = len(df_c[df_c['SEXE'] == 'H'])
                f_cnt = len(df_c[df_c['SEXE'] == 'F'])
                
                h_pct = (h_cnt / tot_c * 100)
                f_pct = (f_cnt / tot_c * 100)
                
                p2025_cnt = len(df_c[df_c['FOULEES 2025'].notna() & (df_c['FOULEES 2025'].astype(str).str.strip() != "")]) if has_2025 else 0
                p2024_cnt = len(df_c[df_c['FOULEES 2024'].notna() & (df_c['FOULEES 2024'].astype(str).str.strip() != "")]) if has_2024 else 0
                
                p2025_pct = (p2025_cnt / tot_c * 100)
                p2024_pct = (p2024_cnt / tot_c * 100)
                
                matrix_data.append({
                    "Épreuve": c,
                    "Hommes (H)": f"{h_cnt} ({h_pct:.1f}%)",
                    "Femmes (F)": f"{f_cnt} ({f_pct:.1f}%)",
                    "TOTAL": tot_c,
                    "Présent en 2025": f"{p2025_cnt} ({p2025_pct:.1f}%)",
                    "Présent en 2024": f"{p2024_cnt} ({p2024_pct:.1f}%)"
                })
                
            if total_global > 0:
                tot_h_pct = (total_h / total_global * 100)
                tot_f_pct = (total_f / total_global * 100)
                tot_p2025_pct = (tot_p2025 / total_global * 100)
                tot_p2024_pct = (tot_p2024 / total_global * 100)
                
                matrix_data.append({
                    "Épreuve": "TOTAL",
                    "Hommes (H)": f"{total_h} ({tot_h_pct:.1f}%)",
                    "Femmes (F)": f"{total_f} ({tot_f_pct:.1f}%)",
                    "TOTAL": total_global,
                    "Présent en 2025": f"{tot_p2025} ({tot_p2025_pct:.1f}%)",
                    "Présent en 2024": f"{tot_p2024} ({tot_p2024_pct:.1f}%)"
                })
                
            df_matrix = pd.DataFrame(matrix_data)
            
            def style_table(val_df):
                styles = pd.DataFrame('', index=val_df.index, columns=val_df.columns)
                styles['TOTAL'] = 'font-weight: 900; font-size: 16px; background-color: #f0f2f6; text-align: center;'
                
                for idx, row in val_df.iterrows():
                    ep = str(row['Épreuve']).upper()
                    bg_color = ""
                    text_color = "black"
                    
                    if "MARCHE" in ep:
                        bg_color = "#d4edda"
                        text_color = "#155724"
                    elif "8" in ep:
                        bg_color = "#cce5ff"
                        text_color = "#004085"
                    elif "15" in ep:
                        bg_color = "#fff3cd"
                        text_color = "#856404"
                    elif "25" in ep:
                        bg_color = "#f8d7da"
                        text_color = "#721c24"
                    elif ep == "TOTAL":
                        styles.loc[idx, :] = 'font-weight: bold; background-color: #e2e3e5;'
                        styles.loc[idx, 'TOTAL'] = 'font-weight: 900; font-size: 18px; background-color: #d6d8d9; color: #000;'
                        continue

                    if bg_color:
                        styles.loc[idx, 'Épreuve'] = f'background-color: {bg_color}; color: {text_color}; font-weight: bold; font-size: 15px;'
                        
                return styles

            st.markdown("### 📊 Récapitulatif Inscrits & Fidélité Éditions Précédentes")
            st.dataframe(
                df_matrix.style.apply(style_table, axis=None), 
                use_container_width=True, 
                hide_index=True
            )

        # -------------------------------------------------------------
        # FOCUS BOL D'AIR 2026
        # -------------------------------------------------------------
        if col_boldair:
            st.markdown("---")
            st.markdown("### 🌲 Performances & Podiums au Bol d'Air 2026")
            
            df_ba = df[df[col_boldair].notna() & (df[col_boldair].astype(str).str.strip().str.upper().isin(["", "-", "NONE", "NAN"]) == False)].copy()
            
            if not df_ba.empty:
                total_ba = len(df_ba)
                dist_counts_ba = df_ba['COURSE'].value_counts()
                
                cols_m_ba = st.columns(1 + len(dist_counts_ba))
                cols_m_ba[0].metric("🌲 Total Participants Bol d'Air", total_ba)
                
                for idx, (dist_name, count_val) in enumerate(dist_counts_ba.items()):
                    cols_m_ba[idx + 1].metric(f"🚩 Inscrits {dist_name}", count_val)

                st.markdown(" ")
                
                df_ba['RANK_NUM'] = df_ba[col_boldair].apply(extract_rank_number)
                df_ba['RÉSULTAT BOL D\'AIR'] = df_ba[col_boldair].apply(add_medal_prefix)
                
                df_ba_sorted = df_ba.sort_values(by=['RANK_NUM', 'NOM']).reset_index(drop=True)
                
                cols_ba = ['NOM', 'PRENOM', 'COURSE', 'RÉSULTAT BOL D\'AIR']
                if 'DOSSARD' in df_ba_sorted.columns and df_ba_sorted['DOSSARD'].notna().any():
                    cols_ba.insert(0, 'DOSSARD')
                
                st.dataframe(
                    df_ba_sorted[cols_ba],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "DOSSARD": "Dossard",
                        "NOM": "Nom",
                        "PRENOM": "Prénom",
                        "COURSE": "Épreuve 2026",
                        "RÉSULTAT BOL D'AIR": "Résultat Bol d'Air 2026 (Classé)"
                    }
                )
            else:
                st.write("Aucun participant identifié pour l'instant sur le Bol d'Air 2026.")

        # -------------------------------------------------------------
        # FOCUS TRAIL DE LA RENAISSANCE 2026
        # -------------------------------------------------------------
        if col_renaissance:
            st.markdown("---")
            st.markdown("### 🏰 Performances & Podiums au Trail de la Renaissance 2026")
            
            df_ren = df[df[col_renaissance].notna() & (df[col_renaissance].astype(str).str.strip().str.upper().isin(["", "-", "NONE", "NAN"]) == False)].copy()
            
            if not df_ren.empty:
                total_ren = len(df_ren)
                dist_counts_ren = df_ren['COURSE'].value_counts()
                
                cols_m_ren = st.columns(1 + len(dist_counts_ren))
                cols_m_ren[0].metric("🏰 Total Trail de la Renaissance", total_ren)
                
                for idx, (dist_name, count_val) in enumerate(dist_counts_ren.items()):
                    cols_m_ren[idx + 1].metric(f"🚩 Inscrits {dist_name}", count_val)

                st.markdown(" ")
                
                df_ren['RANK_NUM'] = df_ren[col_renaissance].apply(extract_rank_number)
                df_ren['RÉSULTAT RENAISSANCE'] = df_ren[col_renaissance].apply(add_medal_prefix)
                
                df_ren_sorted = df_ren.sort_values(by=['RANK_NUM', 'NOM']).reset_index(drop=True)
                
                cols_ren = ['NOM', 'PRENOM', 'COURSE', 'RÉSULTAT RENAISSANCE']
                if 'DOSSARD' in df_ren_sorted.columns and df_ren_sorted['DOSSARD'].notna().any():
                    cols_ren.insert(0, 'DOSSARD')
                
                st.dataframe(
                    df_ren_sorted[cols_ren],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "DOSSARD": "Dossard",
                        "NOM": "Nom",
                        "PRENOM": "Prénom",
                        "COURSE": "Épreuve 2026",
                        "RÉSULTAT RENAISSANCE": "Résultat Renaissance 2026 (Classé)"
                    }
                )
            else:
                st.write("Aucun participant identifié pour l'instant sur le Trail de la Renaissance 2026.")

        # -------------------------------------------------------------
        # SECTION PODIUMS, TEMPOS & STATISTIQUES HISTORIQUES
        # -------------------------------------------------------------
        st.markdown("---")
        st.markdown("### 🥇 Podiums, Affluence & Tracés Historiques (Strava)")
        
        tab_pod2025, tab_pod2024 = st.tabs(["🏆 Édition 2025 (7 / 14 / 24 KM)", "🏆 Édition 2024 (9 / 18 KM)"])
        
        with tab_pod2025:
            st.success("""
            📊 **Statistiques Édition 2025 (284 Inscrits au total) :**
            * 🏃 **7 KM :** **78** participants *(67 en ligne + 11 sur place)*
            * 🏃 **14 KM :** **76** participants *(71 en ligne + 5 sur place)*
            * 🏃 **24 KM :** **45** participants *(44 en ligne + 1 sur place)*
            * 🥾 **Rando :** **116** participants *(42 en ligne + 43 sur place)*
            """)
            
            st.info("""
            📐 **Tracés Réels Strava 2025 :**
            * **7 KM :** 7,0 km réels | **126 m D+**
            * **14 KM :** 14,6 km réels | **233 m D+**
            * **24 KM :** 24,4 km réels | **480 m D+**
            """)
            
            st.info("💡 **Note Speaker 2026 :** Axelle FAUGER (Vainqueure du 7 KM en 2025) a rejoint le club des **RAIDS DINGUES** cette année !")
            c7, c14, c21 = st.columns(3)
            
            with c7:
                st.markdown("#### 🏃 7 KM (2025)")
                st.markdown("**Podium Hommes :**")
                st.write(f"1. **DEPLANQUE Alexandre** - 00:31:14 {calc_vitesse(7, '00:31:14')} (Doix les Fontaines)")
                st.write("2. **BRETAUD Mateo** - 00:31:18 (Training Like Pro)")
                st.write("3. **HERAUD Mickael** - 00:31:41 (Vendée Running 85)")
                st.markdown("**Podium Femmes :**")
                st.write(f"1. 🥇 **FAUGER Axelle** - 00:34:09 {calc_vitesse(7, '00:34:09')} (Fors)")
                st.write("2. **PEROCHAIN Cecile** - 00:40:41 (Damvix)")
                st.write("3. **SAOUDIN Alexane** - 00:41:03 (Sainte Soulle)")
                
                st.caption("🏁 **Fin de course 2025 :**")
                st.caption(f"• Dernière F : **PECHINE Catherine** - 01:08:19 {calc_vitesse(7, '01:08:19')}")
                st.caption(f"• Dernier H : **GANNE Laurent** - 01:08:19 {calc_vitesse(7, '01:08:19')}")

            with c14:
                st.markdown("#### 🏃 14 KM (2025)")
                st.markdown("**Podium Hommes :**")
                st.write(f"1. **ALLARD Justin** - 01:04:53 {calc_vitesse(14, '01:04:53')} (Bournezeau)")
                st.write("2. **METAIS Teddy** - 01:06:56 (Saint-Pierre-le-Vieux)")
                st.write("3. **AIME Franck** - 01:07:01 (Longèves)")
                st.markdown("**Podium Femmes :**")
                st.write(f"1. **VIDOT Joelle** - 01:29:48 {calc_vitesse(14, '01:29:48')} (SA Fontenay le Comte)")
                st.write("2. **FOUR Camille** - 01:31:43 (Liez)")
                st.write("3. **TALON Clara** - 01:32:47 (Maillezais)")
                
                st.caption("🏁 **Fin de course 2025 :**")
                st.caption(f"• Dernier H : **LEMOINE Cyril** - 01:58:42 {calc_vitesse(14, '01:58:42')}")
                st.caption(f"• Dernière F : **BARRE Marianne** - 02:10:11 {calc_vitesse(14, '02:10:11')}")

            with c21:
                st.markdown("#### 🏃 24 KM (2025)")
                st.markdown("**Podium Hommes :**")
                st.write(f"1. **ROCHETEAU Benjamin** - 01:41:49 {calc_vitesse(24, '01:41:49')} (La Roche sur Yon)")
                st.write("2. **CHAILLOLEAU Antoine** - 01:51:33 (SAF Fontenay le Comte)")
                st.write("3. **LEFORT Freddy** - 01:51:37 (Sérigné)")
                st.markdown("**Podium Femmes :**")
                st.write(f"1. **BOUREAU Mathilde** - 02:24:31 {calc_vitesse(24, '02:24:31')} (Pouzauges)")
                st.write("2. **GREDELU Flavie** - 02:35:50 (Mernel)")
                st.write("3. **LUCAS Margaux** - 02:50:11 (Benet)")
                
                st.caption("🏁 **Fin de course 2025 :**")
                st.caption(f"• Dernier H : **CALVET Christophe** - 03:02:14 {calc_vitesse(24, '03:02:14')}")
                st.caption(f"• Dernière F : **FAUCHER RAYMOND Erika** - 03:18:59 {calc_vitesse(24, '03:18:59')}")

        with tab_pod2024:
            st.success("""
            📊 **Statistiques Édition 2024 (288 Inscrits au total) :**
            * 🏃 **9 KM :** **116** participants *(96 en ligne + 20 sur place)*
            * 🏃 **18 KM :** **88** participants *(81 en ligne + 7 sur place)*
            * 🥾 **Rando :** **84** participants *(28 en ligne + 56 sur place)*
            """)
            
            st.info("""
            📐 **Tracés Réels Strava 2024 :**
            * **9 KM :** 8,9 km réels | **41 m D+**
            * **18 KM :** 18,1 km réels | **289 m D+**
            """)
            
            st.info("💡 **Note Speaker 2026 :** Emmanuelle HUMBERT-DROZ-LAURENT (3e du 9 KM en 2024) & Hélène FOLIARD LE GAL (Fin de course 2024) ont rejoint les **RAIDS DINGUES** !")
            c9, c18 = st.columns(2)
            
            with c9:
                st.markdown("#### 🏃 9 KM (2024 - 1ère Édition)")
                st.markdown("**Podium Hommes :**")
                st.write(f"1. **GUIGNOUARD Cédric** - 00:32:25 {calc_vitesse(9, '00:32:25')} (Aventures Running Segonzac)")
                st.write("2. **CHABOT Mickael** - 00:34:39")
                st.write("3. **TEXIER Mathieu** - 00:34:51 (FC2 Sud Vendée)")
                st.markdown("**Podium Femmes :**")
                st.write(f"1. **ROY Léa** - 00:36:59 {calc_vitesse(9, '00:36:59')}")
                st.write("2. **SICLON JARRAU Théoline** - 00:38:49")
                st.write("3. 🥉 **HUMBERT-DROZ-LAURENT Emmanuelle** - 00:42:58")
                
                st.caption("🏁 **Fin de course 2024 :**")
                st.caption(f"• Dernier H : **GARRAUD Tony** - 01:01:30 {calc_vitesse(9, '01:01:30')}")
                st.caption(f"• Dernière F : **FOLIARD LE GAL Hélène** - 01:11:46 {calc_vitesse(9, '01:11:46')}")

            with c18:
                st.markdown("#### 🏃 18 KM (2024 - 1ère Édition)")
                st.markdown("**Podium Hommes :**")
                st.write(f"1. **CHAUSSEE Marc** - 01:16:03 {calc_vitesse(18, '01:16:03')} (UA Chateaubourg)")
                st.write("2. **MENARD Franck** - 01:16:09 (ABV La Chataigneraie)")
                st.write("3. **ETOURNEAU Charly** - 01:20:29")
                st.markdown("**Podium Femmes :**")
                st.write(f"1. **SCHVARTZ Amandine** - 01:45:34 {calc_vitesse(18, '01:45:34')}")
                st.write("2. **DOMENGER Camille** - 01:45:44")
                st.write("3. **GUIBERT Clémentine** - 01:46:34")
                
                st.caption("🏁 **Fin de course 2024 :**")
                st.caption(f"• Dernière F : **ROUART Camille** - 02:07:20 {calc_vitesse(18, '02:07:20')}")
                st.caption(f"• Dernier H : **PAIRAUD Guillaume** - 02:11:40 {calc_vitesse(18, '02:11:40')}")

        # -------------------------------------------------------------
        # SECTION LES PILIERS DE LA COURSE
        # -------------------------------------------------------------
        st.markdown("---")
        st.markdown("### 🌟 Les Piliers des Foulées (Fidélité & Historique)")
        
        if has_2025 and has_2024 and not df_epreuves.empty:
            cond_2025 = df_epreuves['FOULEES 2025'].notna() & (df_epreuves['FOULEES 2025'].astype(str).str.strip() != "")
            cond_2024 = df_epreuves['FOULEES 2024'].notna() & (df_epreuves['FOULEES 2024'].astype(str).str.strip() != "")
            
            df_fidele_3 = df_epreuves[cond_2025 & cond_2024].sort_values(by=['NOM', 'PRENOM']).reset_index(drop=True)
            df_fidele_at_least_1 = df_epreuves[cond_2025 | cond_2024].sort_values(by=['NOM', 'PRENOM']).reset_index(drop=True)
            
            col_f3, col_f1 = st.columns(2)
            
            with col_f3:
                st.markdown(f"#### 👑 3e Participation d'affilée ({len(df_fidele_3)} participants)")
                st.caption("A déjà participé aux éditions 2024 ET 2025 !")
                
                if not df_fidele_3.empty:
                    cols_f3 = ['NOM', 'PRENOM', 'COURSE', 'FOULEES 2025', 'FOULEES 2024']
                    if 'DOSSARD' in df_fidele_3.columns and df_fidele_3['DOSSARD'].notna().any():
                        cols_f3.insert(0, 'DOSSARD')
                    
                    disp_f3 = df_fidele_3[cols_f3]
                    st.dataframe(
                        disp_f3, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            "DOSSARD": "Dossard",
                            "NOM": "Nom",
                            "PRENOM": "Prénom",
                            "COURSE": "Course 2026",
                            "FOULEES 2025": "Résultat 2025",
                            "FOULEES 2024": "Résultat 2024"
                        }
                    )
                else:
                    st.write("Aucun participant dans cette catégorie.")
                    
            with col_f1:
                st.markdown(f"#### 🏅 Au moins 1 édition précédente ({len(df_fidele_at_least_1)} participants)")
                st.caption("A déjà participé en 2024 ou 2025 !")
                
                if not df_fidele_at_least_1.empty:
                    cols_f1 = ['NOM', 'PRENOM', 'COURSE', 'FOULEES 2025', 'FOULEES 2024']
                    if 'DOSSARD' in df_fidele_at_least_1.columns and df_fidele_at_least_1['DOSSARD'].notna().any():
                        cols_f1.insert(0, 'DOSSARD')
                        
                    disp_f1 = df_fidele_at_least_1[cols_f1]
                    st.dataframe(
                        disp_f1, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            "DOSSARD": "Dossard",
                            "NOM": "Nom",
                            "PRENOM": "Prénom",
                            "COURSE": "Course 2026",
                            "FOULEES 2025": "Résultat 2025",
                            "FOULEES 2024": "Résultat 2024"
                        }
                    )
                else:
                    st.write("Aucun participant dans cette catégorie.")

        st.markdown("---")
        c_left, c_right = st.columns(2)
        
        with c_left:
            st.markdown("### 🏃‍♂️ Inscrits par Épreuve / Distance")
            if not df_epreuves.empty and 'COURSE' in df_epreuves.columns:
                df_courses = df_epreuves.groupby(['COURSE', 'SEXE']).size().unstack(fill_value=0)
                if 'H' not in df_courses.columns: df_courses['H'] = 0
                if 'F' not in df_courses.columns: df_courses['F'] = 0
                df_courses['Total'] = df_courses['H'] + df_courses['F']
                st.bar_chart(df_courses[['Total']], color="#FF4B4B")

        with c_right:
            st.markdown("### 🏷️ Répartition par Catégorie (triée par âge)")
            if not df_epreuves.empty and 'Catégorie' in df_epreuves.columns:
                df_cat = df_epreuves['Catégorie'].value_counts().reset_index()
                df_cat.columns = ['Code_Cat', 'Nombre']
                df_cat['Code_clean'] = df_cat['Code_Cat'].astype(str).str.strip().str.upper()
                
                df_cat = df_cat[df_cat['Code_clean'].isin(ORDRE_CATEGORIES)].copy()
                df_cat['Code_clean'] = pd.Categorical(
                    df_cat['Code_clean'], 
                    categories=ORDRE_CATEGORIES, 
                    ordered=True
                )
                
                df_cat = df_cat.sort_values(by='Code_clean').reset_index(drop=True)
                df_cat['Catégorie & Plage d\'âge'] = df_cat['Code_clean'].apply(
                    lambda x: f"{x} - {CATEGORIES_AGE.get(str(x), 'Non spécifié')}"
                )
                
                chart_data = df_cat.set_index('Code_clean')[['Nombre']]
                st.bar_chart(chart_data)
                
                list_cats_dispo = list(df_cat['Code_clean'])
                dict_labels = {c_code: f"{c_code} - {CATEGORIES_AGE.get(str(c_code), '')} ({len(df_epreuves[df_epreuves['Catégorie'].astype(str).str.strip().str.upper() == c_code])} inscrits)" for c_code in list_cats_dispo}
                
                selected_cat_code = st.selectbox(
                    "🔎 Cliquez ici pour sélectionner une catégorie et voir la liste des coureurs :",
                    options=["-- Choisir une catégorie --"] + list_cats_dispo,
                    format_func=lambda x: dict_labels.get(x, x)
                )
                
                if selected_cat_code and selected_cat_code != "-- Choisir une catégorie --":
                    cols_cat = ['NOM', 'PRENOM', 'COURSE', 'SEXE', 'VILLE_CLEAN']
                    if 'DOSSARD' in df_epreuves.columns and df_epreuves['DOSSARD'].notna().any():
                        cols_cat.insert(0, 'DOSSARD')
                    df_cat_coureurs = df_epreuves[df_epreuves['Catégorie'].astype(str).str.strip().str.upper() == selected_cat_code][cols_cat].sort_values(by=['NOM', 'PRENOM']).reset_index(drop=True)
                    st.write(f"👥 **{len(df_cat_coureurs)} coureur(s)** dans la catégorie **{selected_cat_code}** ({CATEGORIES_AGE.get(selected_cat_code, '')}) :")
                    st.dataframe(df_cat_coureurs, use_container_width=True, hide_index=True)
                else:
                    st.dataframe(
                        df_cat[['Catégorie & Plage d\'âge', 'Nombre']], 
                        use_container_width=True, 
                        hide_index=True
                    )

    # -------------------------------------------------------------
    # ONGLET 2 : RÉSULTATS DES MEMBRES RAIDS DINGUES
    # -------------------------------------------------------------
    with tab_raids:
        st.subheader("🛡️ Historique & Performances des Membres Raids Dingues")
        st.write("Retrouvez la liste exclusive de nos membres ayant au moins une participation enregistrée en 2024 ou 2025 !")
        
        df['CLEAN_NOM'] = df['NOM_COMPLET'].apply(clean_name_str)
        is_in_official_list = df['CLEAN_NOM'].isin(MEMBRES_RAIDS_CLEAN)
        is_adherent_course = df['COURSE'].astype(str).str.upper().str.contains("ADHERENT")
        
        df_raids_all = df[is_in_official_list | is_adherent_course].copy()

        has_res_2025_r = df_raids_all['FOULEES 2025'].notna() & (df_raids_all['FOULEES 2025'].astype(str).str.strip() != "") & (df_raids_all['FOULEES 2025'].astype(str).str.upper() != "NONE") if has_2025 else pd.Series([False]*len(df_raids_all))
        has_res_2024_r = df_raids_all['FOULEES 2024'].notna() & (df_raids_all['FOULEES 2024'].astype(str).str.strip() != "") & (df_raids_all['FOULEES 2024'].astype(str).str.upper() != "NONE") if has_2024 else pd.Series([False]*len(df_raids_all))
        
        df_raids = df_raids_all[has_res_2025_r | has_res_2024_r].copy()

        if not df_raids.empty:
            if has_2025: df_raids['FOULEES 2025'] = df_raids['FOULEES 2025'].apply(add_medal_prefix)
            if has_2024: df_raids['FOULEES 2024'] = df_raids['FOULEES 2024'].apply(add_medal_prefix)
            
            df_raids_sorted = df_raids.sort_values(by=['NOM', 'PRENOM']).reset_index(drop=True)
            
            col_r1, col_r2 = st.columns([1, 2])
            with col_r1:
                st.metric("🏃 Membres ayant déjà couru (2024/2025)", len(df_raids_sorted))
            with col_r2:
                sel_membre = st.selectbox(
                    "🔍 Filtrer par membre du club :",
                    options=["-- Tous les membres --"] + list(df_raids_sorted['NOM_COMPLET'].unique())
                )

            if sel_membre != "-- Tous les membres --":
                df_raids_disp = df_raids_sorted[df_raids_sorted['NOM_COMPLET'] == sel_membre]
            else:
                df_raids_disp = df_raids_sorted

            cols_show = ['NOM', 'PRENOM']
            if has_2025: cols_show.append('FOULEES 2025')
            if has_2024: cols_show.append('FOULEES 2024')
            
            st.dataframe(
                df_raids_disp[cols_show], 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "NOM": "Nom",
                    "PRENOM": "Prénom",
                    "FOULEES 2025": "Édition 2025",
                    "FOULEES 2024": "Édition 2024"
                }
            )
        else:
            st.warning("Aucun membre de l'association n'a de résultat enregistré en 2024 ou 2025 dans le CSV actuel.")

    # -------------------------------------------------------------
    # ONGLET 3 : RECHERCHE PARTICIPANT
    # -------------------------------------------------------------
    with tab_search:
        st.subheader("🔍 Recherche de Participant")
        
        query_input = st.text_input(
            "Saisissez un N° de Dossard ou un Nom / Prénom :",
            placeholder="Exemples: 12, Giraudeau, Valérie..."
        ).strip()

        if query_input:
            if query_input.isdigit() and 'DOSSARD' in df.columns:
                dossard_num = int(query_input)
                resultats = df[df['DOSSARD'] == dossard_num]
            else:
                query_upper = query_input.upper()
                resultats = df[df['NOM_COMPLET'].str.contains(query_upper, na=False)]

            if not resultats.empty:
                if len(resultats) > 1:
                    st.info(f"💡 {len(resultats)} participants correspondent à votre recherche :")
                    options_dict = {
                        f"Dossard {int(r['DOSSARD']) if pd.notna(r.get('DOSSARD')) else 'N/A'} - {r.get('NOM','')} {r.get('PRENOM','')} ({r.get('COURSE','')})": idx 
                        for idx, r in resultats.iterrows()
                    }
                    selected_label = st.selectbox("Sélectionnez le participant :", options=list(options_dict.keys()))
                    coureur = resultats.loc[options_dict[selected_label]]
                else:
                    coureur = resultats.iloc[0]

                st.markdown("---")
                st.header(f"🏃 {coureur.get('NOM', '')} {coureur.get('PRENOM', '')}")
                
                club_name = coureur['CLUB']
                is_club_valid = club_name != "Indépendant / Non renseigné"
                
                cat_code = str(coureur.get('Catégorie', 'N/A')).strip().upper()
                cat_label = CATEGORIES_AGE.get(cat_code, cat_code)
                
                dossard_str = f"N° {int(coureur['DOSSARD'])}" if pd.notna(coureur.get('DOSSARD')) else "Non attribué"
                st.subheader(f"Dossard : **{dossard_str}** | Épreuve : **{coureur.get('COURSE', 'N/A')}** | Catégorie : **{cat_label}** ({coureur.get('SEXE', 'N/A')})")
                
                if is_club_valid:
                    st.success(f"🛡️ **Club / Association : {club_name}**")

                rang_str = "N/A"
                if pd.notna(coureur.get('Indice BETRAIL')) and pd.notna(coureur.get('DOSSARD')):
                    df_meme_course_sexe = df[
                        (df['COURSE'] == coureur['COURSE']) & 
                        (df['SEXE'] == coureur['SEXE']) & 
                        (df['Indice BETRAIL'].notna())
                    ].sort_values(by='Indice BETRAIL', ascending=False).reset_index(drop=True)
                    
                    pos = df_meme_course_sexe[df_meme_course_sexe['DOSSARD'] == coureur['DOSSARD']].index
                    if not pos.empty:
                        rang_str = f"N° {pos[0] + 1} ({coureur['SEXE']})"

                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(label="Ville / Origine", value=str(coureur.get('VILLE_CLEAN', 'Inconnu')))
                with col2:
                    betrail = coureur.get('Indice BETRAIL', 'N/A')
                    st.metric(label="Indice Betrail", value=f"{betrail}" if pd.notna(betrail) else "Non renseigné")
                with col3:
                    st.metric(label="Rang théorique", value=rang_str)

                st.markdown("---")
                col_com, col_hist = st.columns(2)
                
                with col_com:
                    st.markdown("### 📝 Commentaires & Notes Speaker")
                    if col_boldair and pd.notna(coureur.get(col_boldair)) and str(coureur.get(col_boldair)).strip() not in ["", "-", "NONE", "NAN"]:
                        st.info(f"🌲 **Bol d'Air 2026 :** {coureur.get(col_boldair)}")
                    
                    if col_renaissance and pd.notna(coureur.get(col_renaissance)) and str(coureur.get(col_renaissance)).strip() not in ["", "-", "NONE", "NAN"]:
                        st.info(f"🏰 **Trail de la Renaissance 2026 :** {coureur.get(col_renaissance)}")
                    
                    commentaires = coureur.get('COMMENTAIRES', None)
                    if pd.notna(commentaires) and str(commentaires).strip() != "":
                        st.info(f"📝 **Note :** {commentaires}")
                    
                    no_ba = (not col_boldair or pd.isna(coureur.get(col_boldair)) or str(coureur.get(col_boldair)).strip() in ["", "-", "NONE", "NAN"])
                    no_ren = (not col_renaissance or pd.isna(coureur.get(col_renaissance)) or str(coureur.get(col_renaissance)).strip() in ["", "-", "NONE", "NAN"])
                    no_com = (pd.isna(commentaires) or str(commentaires).strip() == "")
                    
                    if no_ba and no_ren and no_com:
                        st.write("Aucun commentaire spécifique.")

                with col_hist:
                    st.markdown("### 📜 Historique éditions précédente")
                    f2025 = coureur.get('FOULEES 2025', None)
                    f2024 = coureur.get('FOULEES 2024', None)
                    
                    if pd.notna(f2025):
                        st.write(f"- **Édition 2025 :** {f2025}")
                    if pd.notna(f2024):
                        st.write(f"- **Édition 2024 :** {f2024}")
                    if pd.isna(f2025) and pd.isna(f2024):
                        st.write("Pas de participation enregistrée en 2024/2025.")

                st.markdown("---")
                st.markdown("### 📍 Origine & Représentation Locale")
                
                nom_ville = coureur['NOM_VILLE']
                cp_ville = coureur['CODE_POSTAL']
                
                df_ville_all = df[(df['NOM_VILLE'] == nom_ville) & (df['CODE_POSTAL'] == cp_ville)]
                nb_coureurs_ville = len(df_ville_all)
                
                col_map_c, col_info_c = st.columns([1, 1])
                
                with col_map_c:
                    st.markdown(f"#### 🗺️ Localisation : {coureur['VILLE_CLEAN']}")
                    df_v_unique = pd.DataFrame([{'NOM_VILLE': nom_ville, 'CODE_POSTAL': cp_ville}])
                    coords_c = geolocaliser_communes(df_v_unique)
                    
                    if not coords_c.empty:
                        lat = coords_c.iloc[0]['latitude']
                        lon = coords_c.iloc[0]['longitude']
                        
                        m_coureur = folium.Map(
                            location=[lat, lon], 
                            zoom_start=11,
                            tiles="https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png",
                            attr="&copy; OpenStreetMap France"
                        )
                        folium.Marker(
                            location=[lat, lon],
                            popup=f"<b>{coureur['VILLE_CLEAN']}</b><br>{nb_coureurs_ville} participant(s)",
                            tooltip=coureur['VILLE_CLEAN'],
                            icon=folium.Icon(color="red", icon="user")
                        ).add_to(m_coureur)
                        
                        d_key = f"{coureur.get('DOSSARD', 'no_dos')}_{coureur.get('NOM', '')}"
                        st_folium(m_coureur, width="100%", height=280, key=f"map_coureur_{d_key}")
                    else:
                        st.write("Carte non disponible.")

                with col_info_c:
                    st.markdown(f"#### 🏘️ Inscrits de {coureur['NOM_VILLE']} ({nb_coureurs_ville} participants)")
                    dist_counts = df_ville_all['COURSE'].value_counts()
                    dist_str = " | ".join([f"**{course}** : {cnt}" for course, cnt in dist_counts.items()])
                    st.markdown(f"📊 **Répartition :** {dist_str}")
                    
                    cols_v = ['NOM', 'PRENOM', 'COURSE', 'Catégorie']
                    if 'DOSSARD' in df_ville_all.columns and df_ville_all['DOSSARD'].notna().any(): 
                        cols_v.insert(0, 'DOSSARD')
                    df_v_display = df_ville_all[cols_v].sort_values(by='COURSE').reset_index(drop=True)
                    st.dataframe(df_v_display, use_container_width=True, hide_index=True)

                if is_club_valid:
                    st.markdown("---")
                    df_club_all = df[df['CLUB'] == club_name]
                    st.markdown(f"### 🛡️ Membres de l'association **{club_name}** ({len(df_club_all)} inscrits)")
                    dist_club_counts = df_club_all['COURSE'].value_counts()
                    dist_club_str = " | ".join([f"**{course}** : {cnt}" for course, cnt in dist_club_counts.items()])
                    st.markdown(f"📊 **Répartition par épreuve :** {dist_club_str}")
                    
                    cols_c = ['NOM', 'PRENOM', 'COURSE', 'Catégorie', 'SEXE']
                    if 'DOSSARD' in df_club_all.columns and df_club_all['DOSSARD'].notna().any(): 
                        cols_c.insert(0, 'DOSSARD')
                    df_club_display = df_club_all[cols_c].sort_values(by='COURSE').reset_index(drop=True)
                    st.dataframe(df_club_display, use_container_width=True, hide_index=True)

            else:
                st.warning(f"Aucun participant trouvé avec la recherche \"{query_input}\"")

    # -------------------------------------------------------------
    # ONGLET 4 : FAVORIS ET COTES BETRAIL
    # -------------------------------------------------------------
    with tab_favoris:
        st.subheader("🏆 Favoris / Classement potentiel par cote Betrail")
        
        df_trails = df[df['Indice BETRAIL'].notna()]
        courses_trail_raw = df_trails['COURSE'].dropna().unique()
        
        def get_distance_num(course_str):
            match = re.search(r'(\d+)', str(course_str))
            return int(match.group(1)) if match else 999
            
        courses_dispo = sorted(courses_trail_raw, key=get_distance_num)
        
        if len(courses_dispo) > 0:
            for course_name in courses_dispo:
                st.markdown("---")
                st.markdown(f"### 🚩 Épreuve : **{course_name}**")
                
                df_course = df_trails[df_trails['COURSE'] == course_name].copy()
                col_femmes, col_hommes = st.columns(2)
                
                with col_femmes:
                    st.markdown("#### 👩 Top 5 Femmes")
                    top5_f = df_course[df_course['SEXE'] == 'F'].sort_values(by="Indice BETRAIL", ascending=False).head(5)
                    
                    if not top5_f.empty:
                        cols_f = ['NOM', 'PRENOM', 'Indice BETRAIL', 'VILLE_CLEAN']
                        if 'DOSSARD' in top5_f.columns and top5_f['DOSSARD'].notna().any(): cols_f.insert(0, 'DOSSARD')
                        top5_f_display = top5_f[cols_f].reset_index(drop=True)
                        top5_f_display.index += 1
                        st.dataframe(
                            top5_f_display, 
                            use_container_width=True,
                            column_config={
                                "DOSSARD": "Dossard",
                                "NOM": "Nom",
                                "PRENOM": "Prénom",
                                "Indice BETRAIL": st.column_config.NumberColumn("Cote Betrail", format="%.2f"),
                                "VILLE_CLEAN": "Ville / Origine"
                            }
                        )
                    else:
                        st.write("Aucune donnée disponible.")

                with col_hommes:
                    st.markdown("#### 👨 Top 5 Hommes")
                    top5_h = df_course[df_course['SEXE'] == 'H'].sort_values(by="Indice BETRAIL", ascending=False).head(5)
                    
                    if not top5_h.empty:
                        cols_h = ['NOM', 'PRENOM', 'Indice BETRAIL', 'VILLE_CLEAN']
                        if 'DOSSARD' in top5_h.columns and top5_h['DOSSARD'].notna().any(): cols_h.insert(0, 'DOSSARD')
                        top5_h_display = top5_h[cols_h].reset_index(drop=True)
                        top5_h_display.index += 1
                        st.dataframe(
                            top5_h_display, 
                            use_container_width=True,
                            column_config={
                                "DOSSARD": "Dossard",
                                "NOM": "Nom",
                                "PRENOM": "Prénom",
                                "Indice BETRAIL": st.column_config.NumberColumn("Cote Betrail", format="%.2f"),
                                "VILLE_CLEAN": "Ville / Origine"
                            }
                        )
                    else:
                        st.write("Aucune donnée disponible.")

    # -------------------------------------------------------------
    # ONGLET 5 : ORIGINES ET CLUBS
    # -------------------------------------------------------------
    with tab_stats:
        col_map, col_clubs = st.columns([3, 2])
        
        with col_clubs:
            st.subheader("🛡️ Détail par Club / Association")
            
            clubs_valides = [c for c in df['CLUB'].unique() if c != "Indépendant / Non renseigné"]
            
            if clubs_valides:
                stats_clubs = df[df['CLUB'].isin(clubs_valides)]['CLUB'].value_counts().reset_index()
                stats_clubs.columns = ['Club', 'Nb Inscrits']
                
                selected_club = st.selectbox(
                    "Sélectionnez un club pour voir la liste des participants :",
                    options=["-- Choisir un club --"] + list(stats_clubs['Club'])
                )
                
                if selected_club and selected_club != "-- Choisir un club --":
                    cols_cb = ['NOM', 'PRENOM', 'COURSE', 'Catégorie', 'SEXE']
                    if 'DOSSARD' in df.columns and df['DOSSARD'].notna().any(): cols_cb.insert(0, 'DOSSARD')
                    coureurs_club = df[df['CLUB'] == selected_club][cols_cb].sort_values(by='COURSE').reset_index(drop=True)
                    st.write(f"👥 **{len(coureurs_club)} participant(s)** inscrit(s) pour **{selected_club}** :")
                    st.dataframe(coureurs_club, use_container_width=True, hide_index=True)
                else:
                    st.markdown("**Top des clubs les plus représentés :**")
                    st.dataframe(stats_clubs.head(10), use_container_width=True, hide_index=True)
            else:
                st.write("Aucun club renseigné avec slash dans le fichier.")

        with col_map:
            st.subheader("🗺️ Carte & Détail par Ville")
            
            df_villes_uniques = df[['NOM_VILLE', 'CODE_POSTAL']].dropna().drop_duplicates()
            df_coords = geolocaliser_communes(df_villes_uniques)
            
            if not df_coords.empty:
                counts_ville = df.groupby(['NOM_VILLE', 'CODE_POSTAL']).size().reset_index(name='Nb Coureurs')
                df_map_final = pd.merge(df_coords, counts_ville, on=['NOM_VILLE', 'CODE_POSTAL'])
                
                center_lat = df_map_final['latitude'].mean()
                center_lon = df_map_final['longitude'].mean()
                
                m = folium.Map(
                    location=[center_lat, center_lon], 
                    zoom_start=9,
                    tiles="https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png",
                    attr="&copy; OpenStreetMap France"
                )
                
                for _, row in df_map_final.iterrows():
                    c_list = df[(df['NOM_VILLE'] == row['NOM_VILLE']) & (df['CODE_POSTAL'] == row['CODE_POSTAL'])]
                    coureurs_html = "<br>".join([f"- {r['NOM']} {r['PRENOM']} ({r['COURSE']})" for _, r in c_list.iterrows()])
                    
                    popup_content = f"""
                    <div style='font-size:13px; min-width:180px;'>
                        <b>📍 {row['Ville_CP']}</b><br>
                        <i>{row['Nb Coureurs']} participant(s) :</i><br>{coureurs_html}
                    </div>
                    """
                    
                    folium.CircleMarker(
                        location=[row['latitude'], row['longitude']],
                        radius=5 + (row['Nb Coureurs'] * 2),
                        popup=folium.Popup(popup_content, max_width=300),
                        color="#FF4B4B",
                        fill=True,
                        fill_color="#FF4B4B",
                        fill_opacity=0.6
                    ).add_to(m)
                
                st_folium(m, width="100%", height=400, key="map_globale")
                
                selected_ville = st.selectbox(
                    "Ou sélectionnez une ville dans la liste :",
                    options=["-- Choisir une ville --"] + list(df_map_final['Ville_CP'].sort_values())
                )
                
                if selected_ville and selected_ville != "-- Choisir une ville --":
                    cols_vl = ['NOM', 'PRENOM', 'COURSE', 'Catégorie']
                    if 'DOSSARD' in df.columns and df['DOSSARD'].notna().any(): cols_vl.insert(0, 'DOSSARD')
                    coureurs_ville = df[df['VILLE_CLEAN'] == selected_ville][cols_vl].sort_values(by='COURSE').reset_index(drop=True)
                    st.write(f"🏘️ **{len(coureurs_ville)} participant(s)** originaire(s) de **{selected_ville}** :")
                    st.dataframe(coureurs_ville, use_container_width=True, hide_index=True)
                else:
                    st.markdown("**Top 10 des villes les plus représentées :**")
                    top10_villes = df_map_final[['Ville_CP', 'Nb Coureurs']].sort_values(by='Nb Coureurs', ascending=False).head(10)
                    st.dataframe(top10_villes, use_container_width=True, hide_index=True)

    # -------------------------------------------------------------
    # ONGLET 6 : SPONSORS & PARTENAIRES
    # -------------------------------------------------------------
    with tab_sponsors:
        st.subheader("🤝 Nos Partenaires Officiels")
        st.write("Un grand merci aux entreprises et institutions qui soutiennent les Foulées Raids Dingues !")
        
        st.markdown("---")
        
        # 1. SPONSORS ÉVÉNEMENTIELS
        st.markdown("### 🏆 Partenaires Événementiels")
        
        sponsors_evt = [
            ("L'Entrepote", "L'ENTREPOTE.png" if os.path.exists("L'ENTREPOTE.png") else "TC TRAITEUR.png", "150€ pour les dossards"),
            ("Intersport", "Intersport.png", "300€ de lots"),
            ("Pays de Fontenay", "PAYS DE FONTENAY.png", "Subvention de 400€"),
            ("La Cibulle", "LA CIBULLE.png" if os.path.exists("LA CIBULLE.png") else "LA CIBULL.png", "10% sur les fûts + 6 réglettes (lot)"),
            ("Vendée Marais Poitevin", "mvp.png", "Kit parcours orientation (lot)"),
            ("Valega", "VALEGA.png", "Massage de 45' (lot)"),
            ("CNAILS", "CNAILS.PNG" if os.path.exists("CNAILS.PNG") else "CNAILS.png", "Bon cadeau (lot)"),
            ("AXA", "AXA.png", "1 cafetière (lot)"),
            ("Bioporc", "BIOPORC.png", "3 terrines (lot)"),
            ("Les Pâtés de Lison", "PATES LISON.png", "3 lots de pâtes (lot)"),
            ("Vins Mercier", "VINS MERCIER.png", "3 bouteilles (lot)"),
            ("Hyper U", "HYPER U.png", "Paniers garnis (récompense course)"),
            ("Les Vergers de Vendée", "VERGERS DE VENDEE.png", "Paniers garnis (récompense course)"),
            ("Boucherie Gouin", "MAISON GOUIN.png", "Paniers garnis (récompense course)"),
            ("New Loc", "NEW LOC.png", "Lumière et groupe électrogène"),
            ("Édition du Chemin des Crêtes", "CHEMIN DES CRETES.png", "Livres (lot)"),
            ("Végétal 85", "VEGETAL85.png" if os.path.exists("VEGETAL85.png") else "VEGETAL 85.png", "Agapanthes (dotation coureurs)"),
            ("L'Escale des Ponts", "L'ESCALE.png", "Mise à disposition de l'emplacement")
        ]
        
        for sp_nom, sp_file, sp_desc in sponsors_evt:
            with st.container():
                c_logo, c_info = st.columns([1, 4])
                
                with c_logo:
                    if os.path.exists(sp_file):
                        st.image(sp_file, width=130)
                    else:
                        st.info(f"🏷️ **{sp_nom}**")
                        
                with c_info:
                    st.markdown(f"#### **{sp_nom}**")
                    if sp_desc:
                        st.markdown(f"##### 🎁 **Participation :** {sp_desc}")
                
                st.markdown("<hr style='margin: 8px 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # 2. SPONSORS ANNUELS
        st.markdown("### 🌟 Sponsors Annuels")
        sponsors_annuels = [
            ("BERNARD JOHANNE", "BERNARD JOHANNE.png"),
            ("BLANCHET ENERGIE", "BLANCHET ENERGIE.png"),
            ("BREMAUD", "BREMAUD.png"),
            ("CAJEV", "CAJEV.png"),
            ("LE GRAIN DE BLE", "LE GRAIN DE BLE.png"),
            ("MAISON BAUDRY", "MAISON BAUDRY.png"),
            ("MAISON GOUIN", "MAISON GOUIN.png"),
            ("ROBIN", "ROBIN.png"),
            ("SIGNALISATION 85", "SIGNALISATION 85.png"),
            ("SYMTA PIECES", "SYMTA PIECES.png"),
            ("VINCENDEAU AGENCEMENT", "VICENDEAU AGENCEMENT.png")
        ]
        
        cols_ann = st.columns(3)
        for idx, (sp_nom, sp_file) in enumerate(sponsors_annuels):
            with cols_ann[idx % 3]:
                if os.path.exists(sp_file):
                    st.image(sp_file, width=180)
                else:
                    st.info(f"🏷️ **{sp_nom}**")

    # -------------------------------------------------------------
    # 🔄 RAFRAÎCHISSEMENT AUTOMATIQUE DU TEMPS
    # -------------------------------------------------------------
    time_lib.sleep(1)
    st.rerun()

except Exception as e:
    st.error(f"Erreur lors de l'exécution : {e}")