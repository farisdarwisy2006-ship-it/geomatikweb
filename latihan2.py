import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, LineString, MultiPoint
import folium
from streamlit_folium import folium_static
import json

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="PUO Survey Lot System", layout="wide")

# --- DATABASE USER (Ikut maklumat profil dalam gambar) ---
USER_DB = {
    "1": ["123", "1", "FARIS DARWISY"],
    "2": ["123", "2", "DHIA ARWIENA"],
    "3": ["123", "3", "AIN"],
    "admin": ["admin123", "0", "ADMINISTRATOR"]
}

# Inisialisasi session state untuk login
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_data'] = None

# --- FUNGSI HALAMAN LOGIN ---
def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Logo Politeknik (Ikut paparan skrin login)
        st.image("https://www.puo.edu.my/webportal/wp-content/uploads/2023/12/Poli_Logo1-1024x599.png", width=300)
        st.markdown("### 🔑 Log Masuk Sistem")
        
        u_input = st.text_input("Username (1, 2, 3 atau admin)")
        p_input = st.text_input("Password", type="password")
        
        if st.button("Masuk"):
            if u_input in USER_DB and p_input == USER_DB[u_input][0]:
                st.session_state['logged_in'] = True
                st.session_state['user_data'] = {
                    "id": USER_DB[u_input][1],
                    "name": USER_DB[u_input][2]
                }
                st.rerun()
            else:
                st.error("Username atau Password salah!")

# --- KAWALAN ALIRAN HALAMAN ---
if not st.session_state['logged_in']:
    login_page()
else:
    # --- JIKA SUDAH LOGIN, TUNJUK SISTEM UTAMA ---

    # --- SIDEBAR: PROFIL (Ikut gambar profil ID & Nama) ---
    st.sidebar.markdown(f"### 👤 ID: {st.session_state['user_data']['id']}")
    st.sidebar.info(f"Nama: {st.session_state['user_data']['name']}")
    
    # --- BAHAGIAN: EKSPORT DATA (Ikut gambar) ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💾 Eksport Data")
    
    # Placeholder untuk meletakkan butang download di bawah tajuk Eksport
    export_placeholder = st.sidebar.empty()

    if st.sidebar.button("Log Keluar"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- CUSTOM CSS UNTUK HEADER & METRIC ---
    st.markdown("""
        <style>
        .header-box {
            background-color: white; padding: 25px; border-radius: 10px;
            border-left: 10px solid #007bff; color: black;
            box-shadow: 2px 2px 15px rgba(0,0,0,0.3); margin-bottom: 20px;
        }
        .stMetric { background-color: #1e1e1e; padding: 15px; border-radius: 10px; color: white; }
        </style>
        """, unsafe_allow_html=True)

    # --- HEADER UTAMA ---
    col_logo, col_title = st.columns([1, 3])
    with col_logo:
        st.image("https://www.puo.edu.my/webportal/wp-content/uploads/2023/12/Poli_Logo1-1024x599.png", width=220)

    with col_title:
        st.markdown("""
            <div class="header-box">
                <h1 style='margin:0; font-family: sans-serif; font-size: 32pt;'>SISTEM SURVEY LOT</h1>
                <p style='margin:0; font-size: 14pt; color: #555;'>Politeknik Ungku Omar | Jabatan Kejuruteraan Awam</p>
            </div>
        """, unsafe_allow_html=True)

    # --- SIDEBAR: KAWALAN PAPARAN ---
    st.sidebar.header("⚙️ Kawalan Paparan")
    sz_marker = st.sidebar.slider("Saiz Marker Stesen", 5, 40, 22)
    sz_font = st.sidebar.slider("Saiz Bearing/Jarak", 8, 25, 12)
    zoom_lvl = st.sidebar.slider("Tahap Zoom Awal", 10, 25, 19)
    poly_color = st.sidebar.color_picker("Warna Poligon", "#FFFF00")

    st.sidebar.markdown("---")
    uploaded_file = st.sidebar.file_uploader("Muat naik fail CSV (STN, E, N)", type=["csv"])
    base_map = st.sidebar.radio("Pilihan Peta:", ["Google Hybrid (Satelit)", "Peta Jalan (OSM)"], index=0)

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        
        if 'E' in df.columns and 'N' in df.columns:
            try:
                # --- PROSES DATA GEOSPATIAL ---
                gdf_rso = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.E, df.N), crs="EPSG:4390")
                gdf_wgs = gdf_rso.to_crs("EPSG:4326")
                
                df['lat'], df['lon'] = gdf_wgs.geometry.y, gdf_wgs.geometry.x
                coords_wgs84 = list(zip(df.lat, df.lon))
                coords_meter = df[['E', 'N']].values.tolist()
                coords_closed = coords_wgs84 + [coords_wgs84[0]]
                
                area_val = Polygon(coords_meter).area
                perimeter_val = Polygon(coords_meter).length
                current_surveyor = st.session_state['user_data']['name']

                # --- POPUP MAKLUMAT LOT (Ikut gambar) ---
                lot_popup_html = f"""
                <div style="font-family: sans-serif; min-width: 200px;">
                    <b style="color: #007bff; font-size: 14px; text-transform: uppercase;">MAKLUMAT LOT</b><br><br>
                    <table style="width:100%; border-collapse: collapse; font-size: 13px;">
                        <tr><td style="padding-bottom:5px;"><b>Surveyor:</b></td><td style="padding-bottom:5px;">{current_surveyor}</td></tr>
                        <tr><td style="padding-bottom:5px;"><b>Luas:</b></td><td style="padding-bottom:5px;">{area_val:.3f} m²</td></tr>
                        <tr><td style="padding-bottom:5px;"><b>Perimeter:</b></td><td style="padding-bottom:5px;">{perimeter_val:.3f} m</td></tr>
                    </table>
                </div>
                """

                # --- BINA PETA FOLIUM ---
                m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=zoom_lvl, max_zoom=25)
                
                if "Google Hybrid" in base_map:
                    folium.TileLayer(
                        tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
                        attr='Google', name='Google Hybrid', max_zoom=25, max_native_zoom=22, overlay=False
                    ).add_to(m)

                # 1. Lukis Poligon Lot
                folium.Polygon(locations=coords_closed, color=poly_color, weight=3, fill=True, fill_opacity=0.2,
                               popup=folium.Popup(lot_popup_html, max_width=300)).add_to(m)

                # 2. Lukis Bearing & Jarak
                for i in range(len(coords_meter)):
                    p1, p2 = coords_meter[i], coords_meter[(i+1)%len(coords_meter)]
                    w1, w2 = coords_wgs84[i], coords_wgs84[(i+1)%len(coords_wgs84)]
                    de, dn = p2[0]-p1[0], p2[1]-p1[1]
                    dist_val = np.sqrt(de**2 + dn**2)
                    brg_raw = np.degrees(np.arctan2(de, dn)) % 360
                    
                    angle = np.degrees(np.arctan2(w2[0]-w1[0], w2[1]-w1[1]))
                    if angle > 90: angle -= 180
                    if angle < -90: angle += 180
                    
                    deg, mnt = int(brg_raw), int((brg_raw - int(brg_raw)) * 60)
                    sec = round(((brg_raw - deg) * 60 - mnt) * 60)
                    label_text = f"{deg}°{mnt:02d}'{sec:02d}\"<br>{dist_val:.2f}m"
                    
                    folium.Marker(location=[(w1[0]+w2[0])/2, (w1[1]+w2[1])/2],
                        icon=folium.DivIcon(html=f'<div style="font-size:{sz_font}pt; color:#FFFF00; font-weight:bold; text-align:center; text-shadow:2px 2px 2px #000; transform:translate(-50%,-50%) rotate({-angle}deg);">{label_text}</div>')
                    ).add_to(m)

                # 3. Marker Stesen dengan Popup E & N (Ikut gambar)
                for i, row in df.iterrows():
                    stn_pop_html = f"""
                    <div style="font-family: sans-serif; min-width: 150px;">
                        <b style="color: red; font-size: 14px; text-transform: uppercase;">STESEN {int(row['STN'])}</b><br><br>
                        <table style="width:100%; font-size: 13px;">
                            <tr><td><b>E:</b></td><td>{row['E']:.3f}</td></tr>
                            <tr><td><b>N:</b></td><td>{row['N']:.3f}</td></tr>
                        </table>
                    </div>
                    """
                    folium.CircleMarker([row['lat'], row['lon']], radius=sz_marker/2.5, color='white', fill=True, fill_color='red', fill_opacity=1,
                                       popup=folium.Popup(stn_pop_html, max_width=250)).add_to(m)
                    folium.Marker([row['lat'], row['lon']],
                        icon=folium.DivIcon(html=f'<b style="color:white; font-size:{sz_font}pt; transform:translate(-50%,-50%); display:block; text-align:center; width:30px;">{int(row["STN"])}</b>')
                    ).add_to(m)

                # --- PAPARAN WEB ---
                col_m, col_i = st.columns([3, 1])
                with col_m:
                    folium_static(m, width=950, height=600)
                with col_i:
                    st.metric("Luas (m²)", f"{area_val:.3f}")
                    st.metric("Perimeter (m)", f"{perimeter_val:.3f}")
                
                # --- LOGIK EKSPORT 3-DALAM-1 (TITIK, LINE, POLIGON) ---
                # Mengumpulkan geometri untuk QGIS
                poly_geom = Polygon(coords_wgs84)
                line_geom = LineString(coords_closed)
                points_geom = MultiPoint(coords_wgs84)
                
                # Membuat GeoDataFrame gabungan
                export_gdf = gpd.GeoDataFrame({
                    'Feature': ['Polygon', 'Boundary', 'Stations'],
                    'Surveyor': [current_surveyor] * 3,
                    'Area_m2': [area_val, 0, 0],
                    'Perimeter_m': [perimeter_val, perimeter_val, 0]
                }, geometry=[poly_geom, line_geom, points_geom], crs="EPSG:4326")

                # Menjana butang download roket di sidebar
                export_placeholder.download_button(
                    label="🚀 Export to QGIS (.geojson)", 
                    data=export_gdf.to_json(), 
                    file_name=f"survey_{st.session_state['user_data']['id']}.geojson",
                    mime="application/json"
                )

            except Exception as e:
                st.error(f"Error: {e}")