
# ============================================================
# PROYECTO ACTUARIAL
# UI - GESTOR DE POLIZAS
# ============================================================

import streamlit as st
import pandas as pd
from datetime import date

# ============================================================
# 1. CONFIGURACION DE LA APLICACION
# ============================================================

st.set_page_config(
    page_title="Gestor de Polizas Actuariales",
    page_icon="📊",
    layout="wide"
)

st.title("Gestor de Polizas Actuariales")

st.write(
    "Aplicacion para registrar y gestionar polizas "
    "de seguros de vida."
)

# ============================================================
# 2. DEFINIR LAS VARIABLES
# ============================================================

columnas = [
    'poliza',
    'producto',
    'sexo',
    'fecha_nacimiento',
    'fecha_efecto',
    'fecha_vencimiento',
    'capital_asegurado'
]

# Crear almacenamiento de polizas durante la sesion

if "polizas" not in st.session_state:

    st.session_state.polizas = pd.DataFrame(
        columns=columnas
    )

# ============================================================
# 3. FORMULARIO DE INTRODUCCION DE POLIZAS
# ============================================================

st.header("1. Introduccion de una nueva poliza")

with st.form("formulario_poliza"):

    col1, col2 = st.columns(2)

    with col1:

        poliza = st.text_input(
            "Numero de poliza"
        )

        producto = st.selectbox(
            "Producto",
            ["Temporal fallecimiento"]
        )

        sexo = st.selectbox(
            "Sexo",
            ["H", "M"]
        )

        fecha_nacimiento = st.date_input(
            "Fecha de nacimiento",
            value=date(1989, 5, 15),
            min_value=date(1900, 1, 1)
        )

    with col2:

        fecha_efecto = st.date_input(
            "Fecha de efecto",
            value=date.today()
        )

        fecha_vencimiento = st.date_input(
            "Fecha de vencimiento",
            value=date(date.today().year + 20,
                       date.today().month,
                       date.today().day)
        )

        capital_asegurado = st.number_input(
            "Capital asegurado (€)",
            min_value=0.01,
            value=100000.0,
            step=1000.0
        )


    # Boton de registro

    enviar = st.form_submit_button(
        "Registrar poliza"
    )

# ============================================================
# 4. VALIDAR Y GUARDAR LA POLIZA
# ============================================================

if enviar:

    if not poliza.strip():

        st.error("Debe introducir un numero de poliza.")

    elif fecha_nacimiento >= fecha_efecto:

        st.error(
            "La fecha de nacimiento debe ser anterior "
            "a la fecha de efecto."
        )

    elif fecha_efecto >= fecha_vencimiento:

        st.error(
            "La fecha de efecto debe ser anterior "
            "al vencimiento."
        )

    elif poliza in st.session_state.polizas['poliza'].values:

        st.error("Esta poliza ya existe.")

    else:

        nueva_poliza = {
            'poliza': poliza,
            'producto': producto,
            'sexo': sexo,
            'fecha_nacimiento': fecha_nacimiento,
            'fecha_efecto': fecha_efecto,
            'fecha_vencimiento': fecha_vencimiento,
            'capital_asegurado': capital_asegurado
        }

        st.session_state.polizas = pd.concat(
            [
                st.session_state.polizas,
                pd.DataFrame([nueva_poliza])
            ],
            ignore_index=True
        )

        st.success("Poliza registrada correctamente.")

# ============================================================
# 5. MOSTRAR CARTERA DE POLIZAS
# ============================================================

st.divider()

st.header("2. Cartera de polizas")

polizas = st.session_state.polizas

if not polizas.empty:

    st.metric(
        "Numero de polizas registradas",
        len(polizas)
    )

    st.dataframe(
        polizas,
        use_container_width=True,
        hide_index=True
    )

    # ========================================================
    # 6. EXPORTAR A EXCEL
    # ========================================================

    archivo_excel = polizas.to_excel(
        index=False,
        engine="openpyxl"
    )

    st.download_button(
        label="Descargar cartera en Excel",
        data=archivo_excel,
        file_name="cartera_polizas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:

    st.info(
        "Todavia no hay polizas registradas. "
        "Introduce una poliza en el formulario."
    )
