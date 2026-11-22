# ============================================================
# PROYECTO ACTUARIAL
# COTIZADOR DE SEGUROS DE VIDA - MVP
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from datetime import date
from io import BytesIO


# ============================================================
# 1. CONFIGURACION
# ============================================================

st.set_page_config(
    page_title="Cotizador actuarial de seguros de Vida",
    layout="wide"
)

st.title("Cotizador actuarial de seguros de Vida")
st.caption("Proyecto actuarial | MVP")

st.divider()


# ============================================================
# 2. FUNCIONES AUXILIARES
# ============================================================

def cumpleanos_en_anio(fecha_nacimiento, anio):

    try:
        return fecha_nacimiento.replace(year=anio)

    except ValueError:
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

    dias_desde = (
        fecha_efecto - ultimo_cumpleanos
    ).days

    dias_hasta = (
        siguiente_cumpleanos - fecha_efecto
    ).days

    # Edad actuarial: cumpleaños más próximo
    if dias_hasta < dias_desde:
        edad += 1

    return edad


def sumar_anios(fecha, anios):

    try:
        return fecha.replace(year=fecha.year + anios)

    except ValueError:
        return date(fecha.year + anios, 2, 28)


# ============================================================
# 3. FUNCIONES PARA TABLAS DE MORTALIDAD
# ============================================================

def preparar_tabla_mortalidad(df_original):

    df = df_original.copy()

    # Normalizar nombres de columnas
    df.columns = (
        df.columns.astype(str)
        .str.lower()
        .str.strip()
        .str.replace(" ", "_")
    )

    # Buscar columna edad
    posibles_edad = [
        "edad",
        "age",
        "x"
    ]

    columna_edad = None

    for col in posibles_edad:

        if col in df.columns:
            columna_edad = col
            break

    if columna_edad is None:

        raise ValueError(
            "El Excel debe contener una columna llamada edad."
        )

    # Buscar qx o lx
    posibles_qx = [
        "qx",
        "q_x",
        "prob_mortalidad",
        "probabilidad_mortalidad"
    ]

    posibles_lx = [
        "lx",
        "l_x",
        "supervivientes",
        "sobrevivientes"
    ]

    columna_qx = None
    columna_lx = None

    for col in posibles_qx:

        if col in df.columns:
            columna_qx = col
            break

    for col in posibles_lx:

        if col in df.columns:
            columna_lx = col
            break

    # Conservar columnas necesarias
    if columna_qx is not None:

        tabla = df[
            [columna_edad, columna_qx]
        ].copy()

        tabla.columns = [
            "edad",
            "qx"
        ]

        tabla["edad"] = pd.to_numeric(
            tabla["edad"],
            errors="coerce"
        )

        tabla["qx"] = pd.to_numeric(
            tabla["qx"],
            errors="coerce"
        )

        tabla = tabla.dropna()

        # Detectar qx en porcentaje
        if tabla["qx"].max() > 1:

            if tabla["qx"].max() <= 100:

                tabla["qx"] = tabla["qx"] / 100

            else:

                raise ValueError(
                    "Las probabilidades qx deben estar "
                    "entre 0 y 1 o expresadas en porcentaje."
                )

        if (
            (tabla["qx"] < 0).any()
            or (tabla["qx"] > 1).any()
        ):

            raise ValueError(
                "La columna qx contiene valores inválidos."
            )

    elif columna_lx is not None:

        tabla = df[
            [columna_edad, columna_lx]
        ].copy()

        tabla.columns = [
            "edad",
            "lx"
        ]

        tabla["edad"] = pd.to_numeric(
            tabla["edad"],
            errors="coerce"
        )

        tabla["lx"] = pd.to_numeric(
            tabla["lx"],
            errors="coerce"
        )

        tabla = tabla.dropna()

        tabla = tabla.sort_values("edad")

        if (tabla["lx"] <= 0).any():

            raise ValueError(
                "Los valores lx deben ser positivos."
            )

        if not tabla["lx"].is_monotonic_decreasing:

            raise ValueError(
                "La columna lx debe ser decreciente."
            )

        # Transformación de lx a qx
        tabla["qx"] = (
            1 - tabla["lx"].shift(-1) / tabla["lx"]
        )

        tabla = tabla.dropna(
            subset=["qx"]
        )

        tabla = tabla[
            ["edad", "qx"]
        ]

    else:

        raise ValueError(
            "El Excel debe contener una columna qx o lx."
        )

    tabla["edad"] = tabla["edad"].astype(int)

    tabla = tabla.sort_values(
        "edad"
    ).reset_index(drop=True)

    if tabla["edad"].duplicated().any():

        raise ValueError(
            "La tabla contiene edades duplicadas."
        )

    # Comprobar continuidad de edades
    edades = tabla["edad"].to_list()

    for i in range(len(edades) - 1):

        if edades[i + 1] != edades[i] + 1:

            raise ValueError(
                "La tabla de mortalidad debe tener "
                "edades consecutivas."
            )

    return tabla


# ============================================================
# 4. MOTOR DE CALCULO ACTUARIAL
# ============================================================

def calcular_prima_vida_entera(
    edad,
    capital,
    tipo_interes,
    tipo_pago,
    tabla_mortalidad
):

    tabla = tabla_mortalidad.copy()

    tabla = tabla.set_index(
        "edad"
    )

    edad_maxima = tabla.index.max()

    if edad not in tabla.index:

        raise ValueError(
            f"La edad {edad} no está disponible "
            "en la tabla de mortalidad."
        )

    if edad_maxima <= edad:

        raise ValueError(
            "La tabla no contiene edades suficientes "
            "para realizar el cálculo."
        )

    v = 1 / (1 + tipo_interes)

    probabilidad_supervivencia = 1.0

    valor_actual_prestaciones = 0.0

    valor_actual_primas = 0.0

    resultados = []

    # --------------------------------------------------------
    # RECORRIDO ANUAL DE LA POLIZA
    # --------------------------------------------------------

    for k in range(
        0,
        edad_maxima - edad
    ):

        edad_actual = edad + k

        qx = tabla.loc[
            edad_actual,
            "qx"
        ]

        px = 1 - qx

        supervivencia_inicio = (
            probabilidad_supervivencia
        )

        supervivencia_fin = (
            supervivencia_inicio * px
        )

        # ----------------------------------------------------
        # PRESTACION ESPERADA
        # ----------------------------------------------------

        prob_fallecimiento = (
            supervivencia_inicio * qx
        )

        # Fallecimiento al final del año
        descuento_prestacion = (
            v ** (k + 1)
        )

        flujo_prestacion_esperado = (
            capital * prob_fallecimiento
        )

        valor_actual_prestacion = (
            flujo_prestacion_esperado
            * descuento_prestacion
        )

        valor_actual_prestaciones += (
            valor_actual_prestacion
        )

        # ----------------------------------------------------
        # PRIMA ESPERADA
        # ----------------------------------------------------

        if tipo_pago == "Prepagable":

            prob_pago_prima = (
                supervivencia_inicio
            )

            descuento_prima = (
                v ** k
            )

        else:

            prob_pago_prima = (
                supervivencia_fin
            )

            descuento_prima = (
                v ** (k + 1)
            )

        factor_prima = (
            prob_pago_prima
            * descuento_prima
        )

        valor_actual_primas += (
            factor_prima
        )

        resultados.append({

            "Año": k + 1,

            "Edad": edad_actual,

            "Prob. supervivencia": (
                supervivencia_inicio
            ),

            "Prob. fallecimiento": (
                prob_fallecimiento
            ),

            "Prestación esperada (€)": (
                flujo_prestacion_esperado
            ),

            "VA prestación (€)": (
                valor_actual_prestacion
            ),

            "Factor prima": (
                factor_prima
            ),

            "Prob. supervivencia final": (
                supervivencia_fin
            )

        })

        probabilidad_supervivencia = (
            supervivencia_fin
        )

        # Si qx = 1, ya no existen supervivientes
        if qx >= 1:

            break

    # --------------------------------------------------------
    # PRIMA PURA
    # --------------------------------------------------------

    if valor_actual_primas <= 0:

        raise ValueError(
            "El valor actuarial de las primas es cero."
        )

    prima_anual = (
        valor_actual_prestaciones
        / valor_actual_primas
    )

    # --------------------------------------------------------
    # INCORPORAR PRIMA A LOS FLUJOS
    # --------------------------------------------------------

    df_resultados = pd.DataFrame(
        resultados
    )

    df_resultados[
        "Prima esperada (€)"
    ] = (
        df_resultados["Factor prima"]
        * prima_anual
    )

    df_resultados[
        "VA prima (€)"
    ] = (
        df_resultados["Prima esperada (€)"]
    )

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    return {

        "prima_anual": prima_anual,

        "prima_mensual": (
            prima_anual / 12
        ),

        "valor_actual_prestaciones": (
            valor_actual_prestaciones
        ),

        "valor_actual_primas": (
            valor_actual_primas
        ),

        "tabla_flujos": df_resultados

    }


# ============================================================
# 5. ALMACENAMIENTO DE POLIZAS
# ============================================================

columnas = [

    "producto",
    "fecha_nacimiento",
    "edad_actuarial",
    "fecha_efecto",
    "duracion",
    "edad_cobertura",
    "capital_asegurado",
    "modalidad_pago",
    "tipo_de_pago"

]

if "polizas" not in st.session_state:

    st.session_state.polizas = pd.DataFrame(
        columns=columnas
    )


# ============================================================
# 6. FORMULARIO DE COTIZACION
# ============================================================

st.header("01. Nueva tarificación")

with st.form("formulario"):

    # --------------------------------------------------------
    # DATOS ASEGURADO
    # --------------------------------------------------------

    st.subheader("Datos del asegurado")

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        fecha_nacimiento = st.date_input(
            "Fecha de nacimiento",
            value=date(1990, 1, 1),
            min_value=date(1900, 1, 1),
            max_value=date.today(),
            format="DD/MM/YYYY"
        )

    with col2:

        fecha_efecto = st.date_input(
            "Fecha de efecto",
            value=date.today(),
            min_value=date.today(),
            format="DD/MM/YYYY"
        )

    with col3:

        producto = st.selectbox(
            "Producto",
            ["Vida Entera"]
        )

    with col4:

        tipo_de_pago = st.selectbox(
            "Tipo de pago",
            ["Prepagable", "Postpagable"]
        )

    # --------------------------------------------------------
    # CARACTERISTICAS
    # --------------------------------------------------------

    st.divider()

    st.subheader("Características del seguro")

    col5, col6, col7, col8 = st.columns(4)

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

    with col7:

        edad_cobertura = st.number_input(
            "Edad cobertura",
            min_value=18,
            max_value=100,
            value=60,
            step=1
        )

    with col8:

        modalidad_pago = st.selectbox(
            "Modalidad de pago",
            ["Anual", "Mensual"]
        )

    # --------------------------------------------------------
    # RESUMEN
    # --------------------------------------------------------

    edad_actuarial = calcular_edad_actuarial(
        fecha_nacimiento,
        fecha_efecto
    )

    st.divider()

    st.subheader("Resumen actuarial")

    col9, col10, col11 = st.columns(3)

    col9.metric(
        "Edad actuarial",
        f"{edad_actuarial} años"
    )

    col10.metric(
        "Edad cobertura",
        f"{edad_cobertura} años"
    )

    col11.metric(
        "Duración",
        f"{duracion} años"
    )

    st.divider()

    enviar = st.form_submit_button(
        "Registrar póliza",
        type="primary",
        use_container_width=True
    )


# ============================================================
# 7. VALIDACION Y REGISTRO
# ============================================================

if enviar:

    if fecha_nacimiento >= fecha_efecto:

        st.error(
            "La fecha de nacimiento debe ser anterior "
            "a la fecha de efecto."
        )

    elif edad_actuarial < 18:

        st.error(
            "La edad mínima permitida es 18 años."
        )

    elif edad_actuarial > 80:

        st.error(
            "La edad máxima provisional es 80 años."
        )

    elif capital_asegurado < 1000:

        st.error(
            "El capital mínimo es 1.000 €."
        )

    else:

        nueva_poliza = {

            "producto": producto,

            "fecha_nacimiento": fecha_nacimiento,

            "edad_actuarial": edad_actuarial,

            "fecha_efecto": fecha_efecto,

            "duracion": duracion,

            "edad_cobertura": edad_cobertura,

            "capital_asegurado": capital_asegurado,

            "modalidad_pago": modalidad_pago,

            "tipo_de_pago": tipo_de_pago

        }

        st.session_state.polizas = pd.concat(
            [
                st.session_state.polizas,
                pd.DataFrame([nueva_poliza])
            ],
            ignore_index=True
        )

        st.success(
            "Póliza registrada correctamente."
        )


# ============================================================
# 8. CALCULO ACTUARIAL
# ============================================================

st.divider()

st.header("02. Cálculo actuarial")

st.markdown(
    """
    **Objetivo:** calcular la prima pura de riesgo de una póliza
    de Vida Entera, utilizando una tabla de mortalidad externa.
    """
)

# ------------------------------------------------------------
# SELECCIONAR POLIZA
# ------------------------------------------------------------

if not st.session_state.polizas.empty:

    st.subheader("Seleccionar póliza")

    indice_poliza = st.selectbox(
        "Póliza sobre la que realizar el cálculo",
        st.session_state.polizas.index,
        format_func=lambda x: (
            f"Cotización {x + 1} | "
            f"Edad {st.session_state.polizas.loc[x, 'edad_actuarial']} | "
            f"Capital "
            f"{st.session_state.polizas.loc[x, 'capital_asegurado']:,.2f} €"
        )
    )

    poliza_seleccionada = (
        st.session_state.polizas.loc[
            indice_poliza
        ]
    )

    # --------------------------------------------------------
    # MOSTRAR DATOS
    # --------------------------------------------------------

    st.subheader("Datos de la póliza seleccionada")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Edad actuarial",
        f"{poliza_seleccionada['edad_actuarial']} años"
    )

    c2.metric(
        "Capital asegurado",
        f"{poliza_seleccionada['capital_asegurado']:,.2f} €"
    )

    c3.metric(
        "Tipo de pago",
        poliza_seleccionada["tipo_de_pago"]
    )

    c4.metric(
        "Modalidad",
        poliza_seleccionada["modalidad_pago"]
    )

    # --------------------------------------------------------
    # CARGA TABLA MORTALIDAD
    # --------------------------------------------------------

    st.divider()

    st.subheader("Hipótesis biométricas")

    archivo_mortalidad = st.file_uploader(
        "Sube la tabla de mortalidad en Excel",
        type=["xlsx", "xls"],
        key="tabla_mortalidad"
    )

    tabla_mortalidad = None

    if archivo_mortalidad is not None:

        try:

            excel = pd.ExcelFile(
                archivo_mortalidad
            )

            hoja = st.selectbox(
                "Selecciona la hoja de Excel",
                excel.sheet_names
            )

            df_excel = pd.read_excel(
                archivo_mortalidad,
                sheet_name=hoja
            )

            tabla_mortalidad = (
                preparar_tabla_mortalidad(
                    df_excel
                )
            )

            st.success(
                "Tabla de mortalidad cargada correctamente."
            )

            st.write(
                "Vista previa:"
            )

            st.dataframe(
                tabla_mortalidad.head(10),
                use_container_width=True,
                hide_index=True
            )

            st.caption(
                f"Edades disponibles: "
                f"{tabla_mortalidad['edad'].min()} - "
                f"{tabla_mortalidad['edad'].max()}"
            )

        except Exception as e:

            st.error(
                f"Error al cargar la tabla: {e}"
            )

    # --------------------------------------------------------
    # TIPO DE INTERES
    # --------------------------------------------------------

    st.divider()

    st.subheader("Hipótesis financieras")

    tipo_interes = st.number_input(
        "Tipo de interés técnico anual (%)",
        min_value=0.0,
        max_value=20.0,
        value=2.0,
        step=0.25
    )

    tipo_interes_decimal = (
        tipo_interes / 100
    )

    # --------------------------------------------------------
    # BOTON CALCULAR
    # --------------------------------------------------------

    calcular = st.button(
        "Calcular prima pura",
        type="primary",
        use_container_width=True
    )

    if calcular:

        if tabla_mortalidad is None:

            st.error(
                "Debes cargar primero una tabla "
                "de mortalidad válida."
            )

        else:

            try:

                resultado = (
                    calcular_prima_vida_entera(

                        edad=int(
                            poliza_seleccionada[
                                "edad_actuarial"
                            ]
                        ),

                        capital=float(
                            poliza_seleccionada[
                                "capital_asegurado"
                            ]
                        ),

                        tipo_interes=(
                            tipo_interes_decimal
                        ),

                        tipo_pago=(
                            poliza_seleccionada[
                                "tipo_de_pago"
                            ]
                        ),

                        tabla_mortalidad=(
                            tabla_mortalidad
                        )

                    )
                )

                # ------------------------------------------------
                # RESULTADOS
                # ------------------------------------------------

                st.divider()

                st.header("03. Resultado de la tarificación")

                prima_anual = resultado[
                    "prima_anual"
                ]

                prima_mensual = resultado[
                    "prima_mensual"
                ]

                if (
                    poliza_seleccionada[
                        "modalidad_pago"
                    ] == "Anual"
                ):

                    prima_mostrada = prima_anual

                    texto_modalidad = "Prima anual"

                else:

                    prima_mostrada = prima_mensual

                    texto_modalidad = (
                        "Prima mensual equivalente"
                    )

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    texto_modalidad,
                    f"{prima_mostrada:,.2f} €"
                )

                col2.metric(
                    "Prima anual pura",
                    f"{prima_anual:,.2f} €"
                )

                col3.metric(
                    "Prima mensual equivalente",
                    f"{prima_mensual:,.2f} €"
                )

                # ------------------------------------------------
                # DESGLOSE ACTUARIAL
                # ------------------------------------------------

                st.subheader(
                    "Desglose del cálculo actuarial"
                )

                col4, col5 = st.columns(2)

                col4.metric(
                    "VA de las prestaciones",
                    f"{resultado['valor_actual_prestaciones']:,.2f} €"
                )

                col5.metric(
                    "VA de la unidad de primas",
                    f"{resultado['valor_actual_primas']:,.6f}"
                )

                st.markdown(
                    r"""
                    \[
                    P = \frac{VA(\text{Prestaciones})}
                    {VA(\text{Unidad de primas})}
                    \]
                    """
                )

                # ------------------------------------------------
                # FLUJOS ESPERADOS
                # ------------------------------------------------

                st.divider()

                st.header(
                    "04. Flujo actuarial de la póliza"
                )

                df_flujos = resultado[
                    "tabla_flujos"
                ]

                st.subheader(
                    "Prestaciones y primas esperadas"
                )

                st.line_chart(
                    df_flujos.set_index("Año")[
                        [
                            "Prestación esperada (€)",
                            "Prima esperada (€)"
                        ]
                    ]
                )

                st.caption(
                    """
                    Los flujos esperados representan el capital
                    de fallecimiento ponderado por la probabilidad
                    de fallecimiento de cada año y las primas
                    ponderadas por la probabilidad de pago.
                    """
                )

                # ------------------------------------------------
                # VALORES ACTUALES
                # ------------------------------------------------

                st.subheader(
                    "Valores actuales por año"
                )

                st.line_chart(
                    df_flujos.set_index("Año")[
                        [
                            "VA prestación (€)",
                            "VA prima (€)"
                        ]
                    ]
                )

                # ------------------------------------------------
                # TABLA DETALLADA
                # ------------------------------------------------

                st.subheader(
                    "Detalle anual del cálculo"
                )

                st.dataframe(
                    df_flujos,
                    use_container_width=True,
                    hide_index=True
                )

                # ------------------------------------------------
                # DESCARGA EXCEL
                # ------------------------------------------------

                salida = BytesIO()

                with pd.ExcelWriter(
                    salida,
                    engine="openpyxl"
                ) as writer:

                    df_flujos.to_excel(
                        writer,
                        sheet_name="Flujos actuariales",
                        index=False
                    )

                    pd.DataFrame({

                        "Concepto": [

                            "Capital asegurado",

                            "Edad actuarial",

                            "Tipo interés técnico",

                            "Prima anual",

                            "Prima mensual",

                            "VA prestaciones",

                            "VA unidad primas"

                        ],

                        "Valor": [

                            poliza_seleccionada[
                                "capital_asegurado"
                            ],

                            poliza_seleccionada[
                                "edad_actuarial"
                            ],

                            tipo_interes,

                            prima_anual,

                            prima_mensual,

                            resultado[
                                "valor_actual_prestaciones"
                            ],

                            resultado[
                                "valor_actual_primas"
                            ]

                        ]

                    }).to_excel(
                        writer,
                        sheet_name="Resumen",
                        index=False
                    )

                st.download_button(

                    "Descargar cálculo en Excel",

                    data=salida.getvalue(),

                    file_name="calculo_actuarial.xlsx",

                    mime=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),

                    use_container_width=True

                )

            except Exception as e:

                st.error(
                    f"No se pudo realizar el cálculo: {e}"
                )

else:

    st.info(
        "Primero debes registrar una póliza "
        "en el formulario."
    )


# ============================================================
# 9. HISTORICO DE POLIZAS
# ============================================================

st.divider()

st.header("05. Solicitudes registradas")

if not st.session_state.polizas.empty:

    st.subheader("Histórico de pólizas")

    st.dataframe(
        st.session_state.polizas,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader("Eliminar póliza")

    indice_eliminar = st.selectbox(
        "Selecciona la póliza a eliminar",
        st.session_state.polizas.index,
        format_func=lambda x: (
            f"Cotización {x + 1}"
        ),
        key="eliminar_poliza"
    )

    if st.button("Eliminar póliza"):

        st.session_state.polizas = (
            st.session_state.polizas
            .drop(index=indice_eliminar)
            .reset_index(drop=True)
        )

        st.success(
            "Póliza eliminada correctamente."
        )

        st.rerun()

else:

    st.info(
        "Todavía no hay pólizas registradas."
    )


# ============================================================
# 10. PIE
# ============================================================

st.caption(
    "Life Insurance Analytics | Proyecto actuarial | MVP"
)
