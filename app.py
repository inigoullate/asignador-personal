import pandas as pd
import streamlit as st

# Función para extraer rotaciones por zona
def rotaciones_por_zona(rotaciones_str, zona_objetivo):
    if pd.isna(rotaciones_str):
        return ""
    rotaciones = [r.strip() for r in str(rotaciones_str).split(",")]
    rotaciones_filtradas = [r for r in rotaciones if r.startswith(f"{zona_objetivo}.")]
    return ", ".join(rotaciones_filtradas)

# Cargar datos (forzando "Rotaciones que conoce" como texto)
empleados_df = pd.read_excel("empleados.xlsx", dtype={"Rotaciones que conoce": str})

# Asegurar que cualquier valor no texto también se convierta correctamente
empleados_df["Rotaciones que conoce"] = empleados_df["Rotaciones que conoce"].apply(
    lambda x: str(x) if isinstance(x, str) else str(int(x)) if pd.notna(x) else ""
)

# Interfaz
st.title("Asignador de Personal con Triangulaciones y Rotaciones")

# Obtener todas las zonas únicas desde "Zona Base" y "Zonas que conoce"
zonas_base = empleados_df["Zona Base"].dropna().unique().tolist()
zonas_conocidas = (
    empleados_df["Zonas que conoce"]
    .dropna()
    .str.split(",")
    .explode()
    .str.strip()
    .unique()
    .tolist()
)

zonas = sorted(set(zonas_base + zonas_conocidas))

# Selección de zonas que necesitan y zonas que pueden ceder personal
st.subheader("Selecciona las zonas que necesitan personal y las zonas que pueden ceder personal")

zonas_necesitan = st.multiselect("Zonas que necesitan personal", zonas)
zonas_pueden_ceder = st.multiselect("Zonas que pueden ceder personal", zonas)

# Calcular personal disponible
empleados_disponibles = empleados_df.copy()
empleados_disponibles["Puede Prestar"] = True

exceso_por_zona = (
    empleados_disponibles.groupby("Zona Base")
    .size()
    .subtract(pd.Series({zona: 0 for zona in zonas_pueden_ceder}))
    .fillna(0)
    .astype(int)
)

# Asignaciones directas
st.subheader("Asignaciones directas:")
asignados_total = []
cambios_directos = []

for zona_necesitada in zonas_necesitan:
    asignados = []

    posibles = empleados_disponibles[
        empleados_disponibles["Zonas que conoce"].fillna("").str.contains(rf'\b{zona_necesitada}\b')
        & (empleados_disponibles["Zona Base"] != zona_necesitada)
        & (empleados_disponibles["Zona Base"].map(exceso_por_zona.get) > 0)
    ]

    posibles = posibles.copy()

    posibles["Rotaciones que conoce (filtradas)"] = posibles["Rotaciones que conoce"]

    for idx, row in posibles.iterrows():
        cambios_directos.append({
            "NIE": row["NIE"],
            "Nombre": row["Nombre"],
            "Zona Base": row["Zona Base"],
            "Rotaciones que conoce": row["Rotaciones que conoce (filtradas)"]
        })
        asignados.append(idx)

    asignados_total.extend(asignados)

if cambios_directos:
    st.subheader("Tabla de Cambios Directos:")
    cambios_df = pd.DataFrame(cambios_directos)
    st.dataframe(cambios_df)

# Triangulaciones
if zonas_pueden_ceder:
    st.subheader("Triangulaciones posibles:")
    empleados_restantes = empleados_df.drop(index=asignados_total, errors="ignore")

    for zona_necesitada in zonas_necesitan:
        posibles_tri = []

        for zona_origen in zonas_pueden_ceder:
            origen_df = empleados_df[empleados_df["Zona Base"] == zona_origen]

            for idx_origen, row_origen in origen_df.iterrows():
                zonas_conocidas_origen = str(row_origen["Zonas que conoce"]).split(",")

                for zona_intermedia in zonas_conocidas_origen:
                    zona_intermedia = zona_intermedia.strip()
                    if zona_intermedia == zona_necesitada or zona_intermedia == zona_origen:
                        continue

                    intermedios = empleados_df[
                        (empleados_df["Zona Base"] == zona_intermedia)
                        & (empleados_df["Zonas que conoce"].fillna("").str.contains(rf'\b{zona_necesitada}\b'))
                    ]

                    for idx_inter, row_inter in intermedios.iterrows():
                        posible = {
                            "NIE": row_origen["NIE"],
                            "Nombre": row_origen["Nombre"],
                            "Zona Base": row_origen["Zona Base"],
                            "Va a": zona_intermedia,
                            "Intermediario NIE": row_inter["NIE"],
                            "Intermediario Nombre": row_inter["Nombre"],
                            "Intermediario Base": row_inter["Zona Base"],
                            "Intermediario va a": zona_necesitada,
                            "Rotaciones que conoce (destino)": row_inter["Rotaciones que conoce"]
                        }
                        posibles_tri.append(posible)

        if posibles_tri:
            st.markdown(f"**Zona {zona_necesitada}:**")
            df_tri = pd.DataFrame(posibles_tri)
            df_tri = df_tri[[
                "NIE", "Nombre", "Zona Base", "Va a",
                "Intermediario NIE", "Intermediario Nombre", "Intermediario Base", "Intermediario va a",
                "Rotaciones que conoce (destino)",
            ]]
            st.dataframe(df_tri)
