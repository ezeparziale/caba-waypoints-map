import streamlit as st
import pandas as pd
from streamlit_folium import folium_static
import folium
import geopandas as gpd
from folium.plugins import HeatMap
import plotly.express as px
from shapely import geometry
from shapely.wkt import loads
from shapely.geometry import Point

# Config
st.set_page_config(
     page_title="CABA Waypoints",
     page_icon="🗺️",
     layout="wide",
     initial_sidebar_state="expanded"
 )


# Titulo
titulo_col_1, titutlo_col_2 = st.columns([2,20])

with titulo_col_1:
    st.image("https://upload.wikimedia.org/wikipedia/commons/4/4d/Escudo_de_la_Ciudad_de_Buenos_Aires.svg", width=64)

with titutlo_col_2:
    st.title("Ciudad Autónoma de Buenos Aires")


## Data
path = "app/data/"
df_subte = pd.read_csv(path+"estaciones-de-subte.csv")
df_colores = pd.read_csv(path+"colores-subte.csv")
df_subte = pd.merge(df_subte, df_colores, how="left")
df_cajeros = pd.read_csv(path+"cajeros-automaticos-fix-comuna.csv")
df_barrios = pd.DataFrame(gpd.read_file(path+"barrios.geojson"))
df_barrios = df_barrios[["BARRIO","COMUNA"]]
df_barrios["COMUNA"] = df_barrios["COMUNA"].astype(str).astype(float).astype(int)
df_delitos = pd.read_csv(path+"delitos_2020.csv", parse_dates=[4])
df_delitos = df_delitos[df_delitos.latitud != "SD"]
df_delitos = df_delitos[df_delitos.longitud != "SD"]
df_delitos = df_delitos.astype({"latitud": float, "longitud": float})
df_comunas = pd.DataFrame(gpd.read_file(path+"CABA_comunas.geojson"))
df_comunas = df_comunas[["ID","COMUNAS","BARRIOS"]]
df_comunas["COMUNAS_2"] = df_comunas["COMUNAS"]
df_comunas["ID"] = df_comunas["ID"].astype(int)
df_comunas["COMUNAS"] = df_comunas["COMUNAS"].astype(str).astype(float).astype(int)
df_comunas_wkt = pd.DataFrame(gpd.read_file(path+"CABA_comunas.geojson"))
df_comunas_wkt = df_comunas_wkt[["WKT","COMUNAS"]]
df_comunas_wkt["COMUNAS"] = df_comunas_wkt["COMUNAS"].astype(str).astype(float).astype(int)
df_gastronomia = pd.read_csv(path+"gastronomia/gastronomia.csv")
df_cafe_heladeria_otros = pd.read_csv(path+"cafes-heladerias-otros/cafes-heladerias-otros.csv")
df_combustibles = pd.read_csv(path+"combustibles/combustibles.csv")

df_subte_comuna = pd.DataFrame()
df_delitos_comuna = pd.DataFrame()

# Load map
m = folium.Map(location=[-34.5984, -58.4038], zoom_start=12)

# Side bar
st.sidebar.header("Opciones:")

st.sidebar.subheader("Capas")

capas_view = st.sidebar.multiselect(
    "Ver", 
    ["Subte", "Delitos", "Barrios", "Comunas", "Cajeros", "Gastronomía", "Cafés, Heladerias y otros", "Combustibles"], 
    ["Subte"],
    help="Capas a visualizar"
    )


## Selectores
comunas = set(df_comunas["ID"].tolist())
if capas_view:
    options_comunas = st.sidebar.multiselect("Comunas", comunas, comunas)
else:
    options_comunas = []
lineas = set(df_subte["linea"].tolist())
if "Subte" in capas_view:
    options_lineas = st.sidebar.multiselect("Lineas", lineas, lineas)

if "Cajeros" in capas_view:
    check_cajeros = st.sidebar.checkbox("Ver cajeros automáticos", True)
    if check_cajeros:
        red_cajeros = set(df_cajeros["red"].tolist())
        options_red_cajeros = st.sidebar.multiselect("Red", red_cajeros, red_cajeros)

if "Delitos" in capas_view:
    check_delitos = st.sidebar.checkbox("Ver delitos")
    if check_delitos:
        delitos_mode_view = st.sidebar.radio("Modo", ("HeatMap", "Waypoint"))
        delitos_fechas = st.sidebar.date_input("Filtro de fechas", [])

if "Barrios" in capas_view:
    check_barrios = st.sidebar.checkbox("Ver barrios", True)

if "Comunas" in capas_view:
    check_comunas = st.sidebar.checkbox("Ver comunas", True)

if "Gastronomía" in capas_view:
    gastronomia_list = set(df_gastronomia["local"].tolist())
    options_burger = st.sidebar.multiselect("Gastronomía", gastronomia_list, gastronomia_list)

if "Cafés, Heladerias y otros" in capas_view:
    cafe_heladeria_otros_list = set(df_cafe_heladeria_otros["local"].tolist())
    options_cafe_hedelaria_otros = st.sidebar.multiselect("Cafés, Heladerias y otros", cafe_heladeria_otros_list, cafe_heladeria_otros_list)

if "Combustibles" in capas_view:
    combustibles_list = set(df_combustibles["local"].tolist())
    options_combustibles = st.sidebar.multiselect("Combustibles", combustibles_list, combustibles_list)

# Pre filtrado
if options_comunas:
    if "Subte" in capas_view:
        for x in options_comunas:
            polygon = loads(df_comunas_wkt[df_comunas_wkt.COMUNAS == x]["WKT"].iloc[0])
            for y in range(df_subte.shape[0]):
                point = Point(df_subte.iloc[y]["long"], df_subte.iloc[y]["lat"])
                if polygon.contains(point):
                    df_subte_comuna = df_subte_comuna.append(df_subte.iloc[y])
else:
    df_subte_comuna=df_subte.copy()

# Poligono barrios
if "Barrios" in capas_view:
    if check_barrios:
        cp_barrios = folium.Choropleth(
            geo_data=path+"barrios.geojson",
            name="Barrios",
            data=df_barrios,
            columns=["BARRIO", "COMUNA"],
            key_on="feature.properties.BARRIO",
            fill_color="YlGn",
            fill_opacity=0.7,
            line_opacity=0.2,
            highlight=True,
        ).add_to(m)
        for key in cp_barrios._children:
            if key.startswith("color_map"):
                del(cp_barrios._children[key])
        folium.GeoJsonTooltip(["BARRIO", "COMUNA"]).add_to(cp_barrios.geojson)


# Poligono comunas
if "Comunas" in capas_view:
    if check_comunas:
        # color_comuna = st.sidebar.color_picker("Color poligono comuna", "#000000")
        df_comunas_aux = df_comunas.copy()
        df_comunas_aux["flag_color"] = df_comunas_aux.COMUNAS.isin(options_comunas)
        cp_comuna = folium.Choropleth(
            geo_data=path+"CABA_comunas.geojson",
            name="Comunas seleccionadas",
            data=df_comunas_aux,
            columns=["COMUNAS_2","flag_color"],
            key_on="feature.properties.COMUNAS",
            # fill_color="BuGn",
            fill_opacity=0.7,
            line_opacity=0.2,
            highlight=True,
        ).add_to(m)
        for key in cp_comuna._children:
            if key.startswith("color_map"):
                del(cp_comuna._children[key])
        folium.GeoJsonTooltip(["COMUNAS","BARRIOS"]).add_to(cp_comuna.geojson)
        
        # style = {"fillColor": "#000000", "color": color_comuna}
        # folium.GeoJson(
        #     path+"CABA_comunas.geojson", 
        #     name="Comunas poligono",
        #     style_function=lambda x:style
        # ).add_to(m)


### DELITOS
if "Delitos" in capas_view:
    if check_delitos:
        if delitos_fechas:
            fecha_desde = delitos_fechas[0]
            if len(delitos_fechas)==1:
                fecha_hasta = delitos_fechas[0]
            else:
                fecha_hasta = delitos_fechas[1]

            df_delitos_filtered = df_delitos[
                (df_delitos["fecha"] >= str(fecha_desde)) & 
                (df_delitos["fecha"] <= str(fecha_hasta)) &
                (df_delitos["comuna"].isin(options_comunas))
                ]
        else:
            df_delitos_filtered = df_delitos[(df_delitos["comuna"].isin(options_comunas))]
            
        if delitos_mode_view=="HeatMap":   
            # Heat Map
            HeatMap(
                df_delitos_filtered[["latitud","longitud"]],
                radius=20,
                show=False
            ).add_to(folium.FeatureGroup(name="Delitos").add_to(m))
        if delitos_mode_view=="Waypoint":
            for i in range(0,len(df_delitos_filtered)):
                folium.Marker(
                    location=[
                        df_delitos_filtered.iloc[i]["latitud"], 
                        df_delitos_filtered.iloc[i]["longitud"]
                        ],
                    popup=df_delitos_filtered.iloc[i][("tipo")],
                    icon=folium.Icon(
                        color="gray",
                        icon_color="#ffffff", 
                        icon= "gratipay" if df_delitos_filtered.iloc[i][("tipo")]=="Homicidio" else 
                            "warning" if df_delitos_filtered.iloc[i][("tipo")]=="Hurto (sin violencia)" else 
                            "close" if df_delitos_filtered.iloc[i][("tipo")]=="Robo (con violencia)" else 
                            "ambulance" if df_delitos_filtered.iloc[i][("tipo")]=="Lesiones" else "warning", 
                        prefix="fa")
                    # icon=folium.DivIcon(
                    #     html=f'''
                    #     <i class="fa fa-subway" aria-hidden="true" style="color:{df_subte_filtered.iloc[i]['color']};font-size:24px;" ></i>
                    #     '''
                    # )
                        
                ).add_to(m)
                if i==3000:
                    break


## Waypoint estaciones de subte
if "Subte" in capas_view:
    df_subte_filtered = df_subte_comuna[df_subte_comuna["linea"].isin(options_lineas)]
    df_subte_filtered = df_subte_filtered.sort_values(by=["linea","id"])
    for i in range(0,len(df_subte_filtered)):
        folium.Marker(
            location=[
                df_subte_filtered.iloc[i]["lat"], 
                df_subte_filtered.iloc[i]["long"]
                ],
            popup=df_subte_filtered.iloc[i][("estacion")],
            icon=folium.Icon(
                color="gray",
                icon_color=df_subte_filtered.iloc[i]["color"], 
                icon="subway", 
                prefix="fa")
            # icon=folium.DivIcon(
            #     html=f'''
            #     <i class="fa fa-subway" aria-hidden="true" style="color:{df_subte_filtered.iloc[i]['color']};font-size:24px;" ></i>
            #     '''
            # )
                
        ).add_to(m)

# Gastronomia
if "Gastronomía" in capas_view:
    df_gastronomia_filtered = df_gastronomia[
        (df_gastronomia["local"].isin(options_burger)) &
        (df_gastronomia["comuna"].isin(options_comunas))
    ]
    df_gastronomia_filtered = df_gastronomia_filtered.sort_values(by=["local","comuna"])
    for i in range(len(df_gastronomia_filtered)):
        print(df_gastronomia_filtered.iloc[i]['icon'])
        folium.Marker(
            location=[
                df_gastronomia_filtered.iloc[i]["lat"], 
                df_gastronomia_filtered.iloc[i]["long"]
                ],
            popup=df_gastronomia_filtered.iloc[i][("name")]+"\n"+df_gastronomia_filtered.iloc[i][("desc")],
            icon=folium.DivIcon(
                html=f"<img src='https://raw.githubusercontent.com/ezeparziale/caba-waypoints-map/main/app/data/gastronomia/{df_gastronomia_filtered.iloc[i]['icon']}.bmp' style='display:block;margin-left:auto;margin-right:auto;width:30px;border:0;'>"
                ),                 
        ).add_to(m)


# Cafés, Heladerias y otros
if "Cafés, Heladerias y otros" in capas_view:
    df_cafe_heladeria_otros_filtered = df_cafe_heladeria_otros[
        (df_cafe_heladeria_otros["local"].isin(options_cafe_hedelaria_otros)) &
        (df_cafe_heladeria_otros["comuna"].isin(options_comunas))
    ]

    df_cafe_heladeria_otros_filtered = df_cafe_heladeria_otros_filtered.sort_values(by=["local","comuna"])
    for i in range(len(df_cafe_heladeria_otros_filtered)):
        folium.Marker(
            location=[
                df_cafe_heladeria_otros_filtered.iloc[i]["lat"], 
                df_cafe_heladeria_otros_filtered.iloc[i]["long"]
                ],
            popup=str(df_cafe_heladeria_otros_filtered.iloc[i][("name")]),
            icon=folium.DivIcon(
                html=f"<img src='https://raw.githubusercontent.com/ezeparziale/caba-waypoints-map/main/app/data/cafes-heladerias-otros/{df_cafe_heladeria_otros_filtered.iloc[i]['icon']}.bmp' style='display:block;margin-left:auto;margin-right:auto;width:30px;border:0;'>"
                ),                 
        ).add_to(m)

# Combustibles
if "Combustibles" in capas_view:
    df_combustibles_filtered = df_combustibles[
        (df_combustibles["local"].isin(options_combustibles)) &
        (df_combustibles["comuna"].isin(options_comunas))
    ]
    df_combustibles_filtered = df_combustibles_filtered.sort_values(by=["local","comuna"])
    for i in range(len(df_combustibles_filtered)):
        print(df_combustibles_filtered.iloc[i]['icon'])
        folium.Marker(
            location=[
                df_combustibles_filtered.iloc[i]["lat"], 
                df_combustibles_filtered.iloc[i]["long"]
                ],
            popup=df_combustibles_filtered.iloc[i][("name")],
            icon=folium.DivIcon(
                html=f"<img src='https://raw.githubusercontent.com/ezeparziale/caba-waypoints-map/main/app/data/combustibles/{df_combustibles_filtered.iloc[i]['icon']}.bmp' style='display:block;margin-left:auto;margin-right:auto;width:30px;border:0;'>"
                ),                 
        ).add_to(m)

df_cajeros_filtered = pd.DataFrame()
# Waypoint cajeros
if "Cajeros" in capas_view:
    if check_cajeros:
        df_cajeros_filtered = df_cajeros[
            (df_cajeros["red"].isin(options_red_cajeros)) &
            (df_cajeros["comuna"].isin(options_comunas))
        ]

        for i in range(0,len(df_cajeros_filtered)):
            html=f"""
                <p>Banco: {df_cajeros_filtered.iloc[i][("banco")]}
                <p>Red: {df_cajeros_filtered.iloc[i][("red")]}
                <p>Direccion: {df_cajeros_filtered.iloc[i][("ubicacion")]}
                <p>Terminales: {df_cajeros_filtered.iloc[i][("terminales")]}
                """
            iframe = folium.IFrame(html=html, width=300, height=150)
            popup = folium.Popup(iframe, max_width=300)


            folium.Marker(
                location=[
                    df_cajeros_filtered.iloc[i]["lat"], 
                    df_cajeros_filtered.iloc[i]["long"]
                    ],
                popup=popup,
                icon=folium.Icon(
                    color="gray",
                    icon="bank", 
                    prefix="fa")
                # icon=folium.DivIcon(
                #     html=f'''
                #     <i class="fa fa-subway" aria-hidden="true" style="color:{df_filtered.iloc[i]['color']};font-size:24px;" ></i>
                #     '''
                # )
                    
            ).add_to(m)

# Layer control
folium.LayerControl().add_to(m)


# KPIs
col1, col2 = st.columns([1,10])

if "Subte" in capas_view:
    col1.metric("# Estaciones", df_subte_filtered.shape[0])
else:
    col1.metric("# Estaciones", df_subte.shape[0])
if "Cajeros" in capas_view:
    if check_cajeros:
        col1.metric("# Cajeros", df_cajeros_filtered.shape[0])
else:
    col1.metric("# Cajeros", df_cajeros.shape[0])

if options_comunas:
    col1.metric("# Comunas", df_comunas[df_comunas["COMUNAS"].isin(options_comunas)].shape[0])
else:
    col1.metric("# Comunas", df_comunas.shape[0])

col1.metric("# Barrios", df_barrios.shape[0])

if "Delitos" in capas_view:
    if check_delitos:
        col1.metric("# Delitos", df_delitos_filtered.shape[0])
else:
    col1.metric("# Delitos", df_delitos.shape[0])

if "Gastronomía" in capas_view:
    col1.metric("# Gastronomía", df_gastronomia_filtered.shape[0])
else:
    col1.metric("# Gastronomía", df_gastronomia.shape[0])

if "Cafés, Heladerias y otros" in capas_view:
    col1.metric("# Cafés, Heladerias y otros", df_cafe_heladeria_otros_filtered.shape[0])
else:
    col1.metric("# Cafés, Heladerias y otros", df_cafe_heladeria_otros.shape[0])


# Mapa
st.sidebar.subheader("Mapa")
width = st.sidebar.slider("width", 500, 1800, 1000)
height = st.sidebar.slider("height", 400, 1500, 600)

with col2:
    folium_static(m, width=width, height=height)

    if "Delitos" in capas_view:
        if check_delitos:
            new_order = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
            df_delitos_mes = df_delitos_filtered.groupby(["mes"]).agg(Delitos=("mes","count"))
            df_delitos_mes = df_delitos_mes.reindex(new_order, axis=0)
            df_delitos_mes.reset_index(level=0, inplace=True)
            fig = px.line(df_delitos_mes, x="mes", y="Delitos", title="# Delitos")
            st.plotly_chart(fig, use_container_width=True)


    # Tablas
    if "Subte" in capas_view:
        with st.expander("Estaciones subte data"):
            st.table(data=df_subte_filtered[["id","estacion","linea","lat","long","color","color2"]])
            st.download_button(
            label="Descargar data en CSV",
            data=df_subte_filtered.to_csv().encode('utf-8'),
            file_name='lineas_subte.csv',
            mime='text/csv',
            key="btn_csv_subte"
        )

    if "Barrios" in capas_view:
        if check_barrios:
            with st.expander("Barrios data"):
                st.table(data=df_barrios.sort_values(by=["COMUNA"]))
                st.download_button(
                label="Descargar data en CSV",
                data=df_barrios.to_csv().encode('utf-8'),
                file_name='barrios.csv',
                mime='text/csv',
                key="btn_csv_barrios"
            )

    if "Gastronomía" in capas_view:
        with st.expander("Gastronomía data"):
            st.table(data=df_gastronomia_filtered.sort_values(by=["comuna","local"]))
            st.download_button(
            label="Descargar data en CSV",
            data=df_gastronomia_filtered.to_csv().encode('utf-8'),
            file_name='gastronomia.csv',
            mime='text/csv',
            key="btn_csv_burger"
        )

    if "Cafés, Heladerias y otros" in capas_view:
        with st.expander("Cafés, Heladerias y otros data"):
            st.table(data=df_cafe_heladeria_otros_filtered.sort_values(by=["comuna","local"]))
            st.download_button(
            label="Descargar data en CSV",
            data=df_cafe_heladeria_otros_filtered.to_csv().encode('utf-8'),
            file_name='cafés-heladerias-otros.csv',
            mime='text/csv',
            key="btn_csv_burger"
        )

    if "Cajeros" in capas_view:
        if check_cajeros:
            with st.expander("Cajeros"):
                st.table(data=df_cajeros_filtered)
                st.download_button(
                label="Descargar data en CSV",
                data=df_cajeros_filtered.to_csv().encode('utf-8'),
                file_name='cajeros.csv',
                mime='text/csv',
                key="btn_csv_cajeros"
            )

    if "Combustibles" in capas_view:
        with st.expander("Combustibles data"):
            st.table(data=df_combustibles_filtered.sort_values(by=["comuna","local"]))
            st.download_button(
            label="Descargar data en CSV",
            data=df_combustibles_filtered.to_csv().encode('utf-8'),
            file_name='combustibles.csv',
            mime='text/csv',
            key="btn_csv_burger"
        )
