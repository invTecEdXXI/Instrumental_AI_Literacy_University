# DATA DICTIONARY v2 — dataset_analitico.xlsx

Generado automáticamente desde el fichero real (16-ago-2026).
Hojas: T0_PreTest, T1_PostTest, T2_FollowUp, Formato_Largo, Resumen_Estadistico.
N = 150 por ola (75 Experimental / 75 Control); 72 columnas por hoja
de ola; Formato_Largo = 450 filas con columna `Tiempo`.
Codificación de los CSV exportados: UTF-8.

| Columna | Tipo/Rango | Descripción |
|---|---|---|
| `ID_estudiante` | int 1-150 | Identificador anonimizado del estudiante |
| `Grupo` | Experimental|Control | Condición asignada (nivel sección) |
| `Facultad` | 6 categorías | Facultad de procedencia (estratificación descriptiva) |
| `Seccion` | int 1-8 | Sección intacta = unidad de asignación y de conglomeración primaria (1-4 experimental; 5-8 control) |
| `Seccion_area` | texto | Área disciplinar de la sección |
| `Genero` | Masculino|Femenino|No binario | Género autoinformado |
| `Anio_nacimiento` | int | Año de nacimiento |
| `Ciclo_academico` | int 1-10 | Ciclo académico |
| `Experiencia_previa_IA` | Ninguna|Básica|Intermedia|Avanzada | Experiencia previa con herramientas de IA |
| `D1_01` | int 1-5 | Ítem Likert de autopercepción (dimensión D1) |
| `D1_02` | int 1-5 | Ítem Likert de autopercepción (dimensión D1) |
| `D1_03` | int 1-5 | Ítem Likert de autopercepción (dimensión D1) |
| `D1_04` | int 1-5 | Ítem Likert de autopercepción (dimensión D1) |
| `D1_05` | int 1-5 | Ítem Likert de autopercepción (dimensión D1) |
| `D1_06` | int 1-5 | Ítem Likert de autopercepción (dimensión D1) |
| `D2_01` | int 1-5 | Ítem Likert de autopercepción (dimensión D2) |
| `D2_02` | int 1-5 | Ítem Likert de autopercepción (dimensión D2) |
| `D2_03` | int 1-5 | Ítem Likert de autopercepción (dimensión D2) |
| `D2_04` | int 1-5 | Ítem Likert de autopercepción (dimensión D2) |
| `D2_05` | int 1-5 | Ítem Likert de autopercepción (dimensión D2) |
| `D2_06` | int 1-5 | Ítem Likert de autopercepción (dimensión D2) |
| `D3_01` | int 1-5 | Ítem Likert de autopercepción (dimensión D3) |
| `D3_02` | int 1-5 | Ítem Likert de autopercepción (dimensión D3) |
| `D3_03` | int 1-5 | Ítem Likert de autopercepción (dimensión D3) |
| `D3_04` | int 1-5 | Ítem Likert de autopercepción (dimensión D3) |
| `D3_05` | int 1-5 | Ítem Likert de autopercepción (dimensión D3) |
| `D3_06` | int 1-5 | Ítem Likert de autopercepción (dimensión D3) |
| `D3_07` | int 1-5 | Ítem Likert de autopercepción (dimensión D3) |
| `D3_08` | int 1-5 | Ítem Likert de autopercepción (dimensión D3) |
| `D4_01` | int 1-5 | Ítem Likert de autopercepción (dimensión D4) |
| `D4_02` | int 1-5 | Ítem Likert de autopercepción (dimensión D4) |
| `D4_03` | int 1-5 | Ítem Likert de autopercepción (dimensión D4) |
| `D4_04` | int 1-5 | Ítem Likert de autopercepción (dimensión D4) |
| `D4_05` | int 1-5 | Ítem Likert de autopercepción (dimensión D4) |
| `D4_06` | int 1-5 | Ítem Likert de autopercepción (dimensión D4) |
| `OBJ_D1_01` | 0|1 | Ítem del test de conocimiento objetivo (D1), 1 = correcto |
| `OBJ_D1_02` | 0|1 | Ítem del test de conocimiento objetivo (D1), 1 = correcto |
| `OBJ_D1_03` | 0|1 | Ítem del test de conocimiento objetivo (D1), 1 = correcto |
| `OBJ_D1_04` | 0|1 | Ítem del test de conocimiento objetivo (D1), 1 = correcto |
| `OBJ_D1_05` | 0|1 | Ítem del test de conocimiento objetivo (D1), 1 = correcto |
| `OBJ_D1_06` | 0|1 | Ítem del test de conocimiento objetivo (D1), 1 = correcto |
| `OBJ_D2_01` | 0|1 | Ítem del test de conocimiento objetivo (D2), 1 = correcto |
| `OBJ_D2_02` | 0|1 | Ítem del test de conocimiento objetivo (D2), 1 = correcto |
| `OBJ_D2_03` | 0|1 | Ítem del test de conocimiento objetivo (D2), 1 = correcto |
| `OBJ_D2_04` | 0|1 | Ítem del test de conocimiento objetivo (D2), 1 = correcto |
| `OBJ_D2_05` | 0|1 | Ítem del test de conocimiento objetivo (D2), 1 = correcto |
| `OBJ_D2_06` | 0|1 | Ítem del test de conocimiento objetivo (D2), 1 = correcto |
| `OBJ_D3_01` | 0|1 | Ítem del test de conocimiento objetivo (D3), 1 = correcto |
| `OBJ_D3_02` | 0|1 | Ítem del test de conocimiento objetivo (D3), 1 = correcto |
| `OBJ_D3_03` | 0|1 | Ítem del test de conocimiento objetivo (D3), 1 = correcto |
| `OBJ_D3_04` | 0|1 | Ítem del test de conocimiento objetivo (D3), 1 = correcto |
| `OBJ_D3_05` | 0|1 | Ítem del test de conocimiento objetivo (D3), 1 = correcto |
| `OBJ_D3_06` | 0|1 | Ítem del test de conocimiento objetivo (D3), 1 = correcto |
| `OBJ_D3_07` | 0|1 | Ítem del test de conocimiento objetivo (D3), 1 = correcto |
| `OBJ_D3_08` | 0|1 | Ítem del test de conocimiento objetivo (D3), 1 = correcto |
| `OBJ_D4_01` | 0|1 | Ítem del test de conocimiento objetivo (D4), 1 = correcto |
| `OBJ_D4_02` | 0|1 | Ítem del test de conocimiento objetivo (D4), 1 = correcto |
| `OBJ_D4_03` | 0|1 | Ítem del test de conocimiento objetivo (D4), 1 = correcto |
| `OBJ_D4_04` | 0|1 | Ítem del test de conocimiento objetivo (D4), 1 = correcto |
| `OBJ_D4_05` | 0|1 | Ítem del test de conocimiento objetivo (D4), 1 = correcto |
| `OBJ_D4_06` | 0|1 | Ítem del test de conocimiento objetivo (D4), 1 = correcto |
| `Tiempo` | T0|T1|T2 | Ola de medición (solo en Formato_Largo) |
| `Score_conocimiento` | int 0-26 | Suma de aciertos del test objetivo (outcome primario 2) |
| `Score_D1` | float 1-5 | Media de los 6 ítems de autopercepción D1 |
| `Score_conocimiento_D1` | int 0-6 | Aciertos del test objetivo en D1 |
| `Score_D2` | float 1-5 | Media de los 6 ítems de autopercepción D2 |
| `Score_conocimiento_D2` | int 0-6 | Aciertos del test objetivo en D2 |
| `Score_D3` | float 1-5 | Media de los 8 ítems de autopercepción D3 |
| `Score_conocimiento_D3` | int 0-8 | Aciertos del test objetivo en D3 |
| `Score_D4` | float 1-5 | Media de los 6 ítems de autopercepción D4 |
| `Score_conocimiento_D4` | int 0-6 | Aciertos del test objetivo en D4 |
| `Score_total_autopercepcion` | float 1-5 | Media de los 26 ítems Likert (outcome primario 1) |

## Variables administrativas NO incluidas en el fichero público

`ID_bruto`, `Codigo_estudiante`, `Fecha_T0`, `Consentimiento_informado`,
`Participo_piloto`, `Total_sesiones`, `Sesiones_asistidas`,
`Asistencia_pct`, `Completo_T0/T1/T2`, `Motivo_exclusion`,
`Fecha_abandono` — permanecen en el fichero bruto custodiado por el IP
(`dataset_raw2_T0.xlsx`); el flujo bruto→analítico es reproducible con
`limpieza_bruto_a_analiticov2.py` (CONSORT y atrición incluidos).