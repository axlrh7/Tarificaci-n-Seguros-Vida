
# ============================================================
# PROYECTO ACTUARIAL
# COTIZADOR DE SEGUROS DE VIDA - MVP
# ============================================================

import streamlit as st
import pandas as pd
from datetime import date
from io import BytesIO

# ============================================================
# 1. CONFIGURACION
# ============================================================

st.set_page_config(
    page_title="Calculo de primas de seguros de Vida",
    layout="wide"
)

st.title("Calculo de primas de seguros de Vida")
st.caption("Cotizador actuarial | Seguro temporal de fallecimiento")

st.divider()


# ============================================================
# 2. FUNCIONES ACTUARIALES AUXILIARES
# ============================================================

def cumpleanos_en_anio(fecha_nacimiento, anio):

    try:
        return fecha_nacimiento.replace(year=anio)

    except ValueError:
        # Tratamiento de nacimientos el 29 de febrero
        return date(anio, 2, 28)


def calcular_edad_actuarial(fecha_nacimiento, fecha_efecto):

    edad = fecha_efecto.year - fecha_nacimiento.year

    ultimo_cumpleanos = cumpleanos_en_anio(
        fecha_nacimiento,
        fecha_efecto.year
    )

    if ultimo_cumpleanos > fecha_efecto:
        edad -= 1

    siguiente_cumpleanos = cumpleanos_en_anio(
        fecha_nacimiento,
        fecha_efecto.year + 1
    )

    dias_desde = (fecha_efecto - ultimo_cumpleanos).days
    dias_hasta = (siguiente_cumpleanos - fecha_efecto).days

    # Redondeo al cumpleaños más próximo
    # En caso de empate se conserva la edad cumplida

    if dias_hasta < dias_desde:
        edad += 1

    return edad


def sumar_anios(fecha, anios):

    try:
        return fecha.replace(year=fecha.year + anios)

    except ValueError:
        return date(fecha.year + anios, 2, 28)


# ============================================================
# 3. ALMACENAMIENTO DE SOLICITUDES
# ============================================================

columnas = [
    "solicitud",
    "producto",
    "fecha_nacimiento",
    "edad_actuarial",
    "fecha_efecto",
    "fecha_vencimiento",
    "duracion",
    "capital_asegurado",
    "modalidad_pago"
]

# Almacenamiento temporal en memoria de sesión.
# Los datos se perderán al finalizar la sesión.

if "polizas" not in st.session_state:

    st.session_state.polizas = pd.DataFrame(
        columns=columnas
    )


# ============================================================
# 4. FORMULARIO DE COTIZACION
# ============================================================

st.header("Nueva cotización")

with st.form("formulario_cotizacion"):

    # --------------------------------------------------------
    # BLOQUE A: DATOS DEL ASEGURADO
    # --------------------------------------------------------

    st.subheader("01. Datos del asegurado")

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        solicitud = st.text_input(
            "Número de solicitud",
            placeholder="Ej. SOL-0001"
        )

    with col2:

        fecha_nacimiento = st.date_input(
            "Fecha de nacimiento",
            value=date(1990, 1, 1),
            min_value=date(1900, 1, 1),
            max_value=date.today(),
            format="DD/MM/YYYY"
        )

    with col3:

        fecha_efecto = st.date_input(
            "Fecha de efecto",
            value=date.today(),
            min_value=date.today(),
            format="DD/MM/YYYY"
        )

    with col4:

        producto = st.selectbox(
            "Producto",
            ["Temporal de fallecimiento"]
        )

    # --------------------------------------------------------
    # BLOQUE B: CARACTERISTICAS DEL SEGURO
    # --------------------------------------------------------

    st.divider()

    st.subheader("02. Características del seguro")

    col5, col6 = st.columns(2)

    with col5:

        capital_asegurado = st.number_input(
            "Capital asegurado (€)",
            min_value=1000.0,
            max_value=10000000.0,
            value=100000.0,
            step=5000.0,
            format="%.2f"
        )

    with col6:

        duracion = st.selectbox(
            "Duración del seguro (años)",
            list(range(1, 41)),
            index=19
        )

    fecha_vencimiento = sumar_anios(
        fecha_efecto,
        duracion
    )

    # --------------------------------------------------------
    # BLOQUE C: MODALIDAD DE PAGO
    # --------------------------------------------------------

    st.divider()

    st.subheader("03. Modalidad de pago")

    modalidad_pago = st.radio(
        "Modalidades que se desean cotizar",
        ["Ambas", "Anual", "Mensual"],
        horizontal=True,
        index=0
    )

    # --------------------------------------------------------
    # BLOQUE D: EDAD ACTUARIAL
    # --------------------------------------------------------

    edad_actuarial = calcular_edad_actuarial(
        fecha_nacimiento,
        fecha_efecto
    )

    st.divider()

    st.subheader("04. Resumen actuarial")

    col7, col8, col9 = st.columns(3)

    col7.metric(
        "Edad actuarial",
        f"{edad_actuarial} años"
    )

    col8.metric(
        "Duración",
        f"{duracion} años"
    )

    col9.metric(
        "Fecha de vencimiento",
        fecha_vencimiento.strftime("%d/%m/%Y")
    )

    st.divider()

    # --------------------------------------------------------
    # BOTON DE COTIZACION
    # --------------------------------------------------------

    enviar = st.form_submit_button(
        "Generar solicitud de cotización",
        type="primary",
        use_container_width=True
    )


# ============================================================
# 5. VALIDACION Y REGISTRO
# ============================================================

if enviar:

    solicitud = solicitud.strip().upper()

    solicitudes_existentes = (
        st.session_state.polizas["solicitud"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    if not solicitud:

        st.error(
            "Introduce un número de solicitud."
        )

    elif fecha_nacimiento >= fecha_efecto:

        st.error(
            "La fecha de nacimiento debe ser anterior "
            "a la fecha de efecto."
        )

    elif fecha_efecto < date.today():

        st.error(
            "La fecha de efecto no puede estar en el pasado."
        )

    elif edad_actuarial < 18:

        st.error(
            "La edad actuarial mínima permitida es de 18 años."
        )

    elif edad_actuarial > 80:

        st.error(
            "La edad actuarial máxima provisional es de 80 años."
        )

    elif capital_asegurado < 1000:

        st.error(
            "El capital mínimo asegurado es de 1.000 €."
        )

    elif solicitud in solicitudes_existentes.values:

        st.error(
            "Esta solicitud ya existe."
        )

    else:

        nueva_poliza = {

            "solicitud": solicitud,

            "producto": producto,

            "fecha_nacimiento": fecha_nacimiento,

            "edad_actuarial": edad_actuarial,

            "fecha_efecto": fecha_efecto,

            "fecha_vencimiento": fecha_vencimiento,

            "duracion": duracion,

            "capital_asegurado": capital_asegurado,

            "modalidad_pago": modalidad_pago

        }

        st.session_state.polizas = pd.concat(
            [
                st.session_state.polizas,
                pd.DataFrame([nueva_poliza])
            ],
            ignore_index=True
        )

        st.success(
            f"Solicitud {solicitud} registrada correctamente."
        )


# ============================================================
# 6. GESTION DE SOLICITUDES
# ============================================================

st.divider()

st.header("Solicitudes registradas")

if not st.session_state.polizas.empty:

    # --------------------------------------------------------
    # INDICADORES
    # --------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total de solicitudes",
        len(st.session_state.polizas)
    )

    col2.metric(
        "Capital total asegurado",
        f"{st.session_state.polizas['capital_asegurado'].sum():,.2f} €"
    )

    col3.metric(
        "Duración media",
        f"{st.session_state.polizas['duracion'].mean():.1f} años"
    )

    st.divider()

    # --------------------------------------------------------
    # TABLA DE SOLICITUDES
    # --------------------------------------------------------

    st.subheader("Histórico de solicitudes")

    st.dataframe(
        st.session_state.polizas,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # DESCARGA EXCEL
    # --------------------------------------------------------

    st.subheader("Exportación de datos")

    buffer = BytesIO()

    with pd.ExcelWriter(
        buffer,
        engine="openpyxl"
    ) as writer:

        st.session_state.polizas.to_excel(
            writer,
            index=False,
            sheet_name="Solicitudes"
        )

    st.download_button(
        label="Descargar histórico en Excel",
        data=buffer.getvalue(),
        file_name="historico_cotizaciones.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    # --------------------------------------------------------
    # ELIMINACION DE SOLICITUDES
    # --------------------------------------------------------

    st.divider()

    st.subheader("Eliminar solicitud")

    solicitudes = st.session_state.polizas["solicitud"].tolist()

    solicitud_eliminar = st.selectbox(
        "Selecciona la solicitud que deseas eliminar",
        solicitudes
    )

    if st.button(
        "Eliminar solicitud seleccionada",
        type="secondary"
    ):

        st.session_state.polizas = (
            st.session_state.polizas[
                st.session_state.polizas["solicitud"]
                != solicitud_eliminar
            ]
            .reset_index(drop=True)
        )

        st.success(
            f"Solicitud {solicitud_eliminar} eliminada."
        )

        st.rerun()

else:

    st.info(
        "Todavía no hay solicitudes registradas."
    )


# ============================================================
# 7. INFORMACION DEL MODELO
# ============================================================

st.divider()

with st.expander("Información del modelo actuarial"):

    st.write(
        """
        **Producto:** Seguro temporal de fallecimiento.

        **Criterio de edad:** Edad actuarial por cumpleaños
        más próximo.

        **Duración:** Entre 1 y 40 años.

        **Modalidades:** Anual, mensual o ambas.

        **Almacenamiento:** Temporal mediante session_state.

        **Tarificación:** Pendiente de implementar.

        **Tabla de mortalidad:** Pendiente de incorporar.
        """
    )

st.caption(
    "Life Insurance Analytics | Proyecto actuarial | MVP"
)
