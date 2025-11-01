# Laboratorio 1: Simulación con parámetros y evaluación de métricas de desempeño

Este proyecto utiliza gem5 y McPAT para explorar configuraciones de arquitectura mediante el algoritmo de recocido simulado (simulated annealing). El objetivo es encontrar configuraciones óptimas considerando tiempo de ejecución, consumo energético y la métrica EDP (Energy Delay Product).

## Descripción general

1. Ejecutar script_sa.py en resources_uarch_sim_assignment

   * Usa gem5 con recocido simulado.
   * Genera:

     * Carpeta outputs con muchas subcarpetas. En cada subcarpeta hay un stats.txt y un config.json.
     * Archivos explored_configs.csv y annealing_results.csv.

2. Mover archivos necesarios a mcpat

   * Desde resources_uarch_sim_assignment mover:

     * explored_configs.csv
   * Desde cada carpeta dentro de outputs mover a mcpat/collected:

     * stats.txt
     * config.json
   * No es necesario mover toda la carpeta outputs completa, solo los archivos stats.txt y config.json organizados dentro de mcpat/collected.

3. Procesamiento dentro de mcpat

   a) Ejecutar xml_mcpat.py

   * Convierte cada par stats_*.txt + config_*.json dentro de mcpat/collected en config_*.xml.

   b) Ejecutar mcpat_anal_script.py

   * Usa los archivos XML generados para correr McPAT.
   * Genera archivos output_*.txt dentro de mcpat_salidas.

   c) Ejecutar attach_edp_csv.py

   * Lee explored_configs.csv, los archivos stats_*.txt en mcpat/collected y los output_*.txt de mcpat_salidas.
   * Calcula EDP usando la fórmula:
     EDP = (Total Leakage + Runtime Dynamic) * CPI
   * Genera explored_configs_with_edp.csv.

---

Ubicaciones esperadas de archivos y carpetas

resources_uarch_sim_assignment contiene:

* script_sa.py
* outputs (carpeta generada por gem5)
* explored_configs.csv
* annealing_results.csv

mcpat contiene:

* xml_mcpat.py
* mcpat_anal_script.py
* attach_edp_csv.py
* carpeta collected (debe contener los archivos stats_.txt y config_.json movidos desde outputs)
* carpeta mcpat_salidas (donde se guardan output_*.txt generados por McPAT)
* explored_configs.csv
* explored_configs_with_edp.csv (después de ejecutar attach_edp_csv.py)

---

Requisitos

* gem5 compilado
* McPAT compilado
* Python 3 con pandas instalado:
  pip install pandas

---

Comandos de ejecución

Etapa 1: Ejecutar gem5 con recocido simulado
cd gem5/resources_uarch_sim_assignment
python3 script_sa.py

Etapa 2: Mover archivos generados
Mover explored_configs.csv al directorio gem5/mcpat
Mover todos los archivos stats.txt y config.json desde outputs al directorio gem5/mcpat/collected

Etapa 3: Conversión y análisis con McPAT
cd gem5/mcpat
python3 xml_mcpat.py
python3 mcpat_anal_script.py
python3 attach_edp_csv.py

## Métricas obtenidas

| Métrica            | Fuente | Descripción                                           |
|--------------------|--------|-------------------------------------------------------|
| simSeconds         | gem5   | Tiempo de simulación utilizado como costo.           |
| system.cpu.cpi     | gem5   | Ciclos por instrucción.                              |
| Total Leakage      | McPAT  | Consumo energético estático.                         |
| Runtime Dynamic    | McPAT  | Consumo energético dinámico.                         |
| EDP                | Script | (Total Leakage + Runtime Dynamic) × CPI.             |

## Resultado

El archivo explored_configs_with_edp.csv contiene todas las configuraciones probadas junto con su tiempo de simulación, consumo energético y la métrica EDP.# lab1_arq_adv_comp
