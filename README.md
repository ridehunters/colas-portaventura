# Colas de PortAventura

Histórico de tiempos de espera de **PortAventura Park** y **Ferrari Land**, recogido automáticamente para uso personal.

GitHub Actions ejecuta `registro/registrar_colas.py` cada 15 minutos en horario de parque (ver `.github/workflows/registro-colas.yml`) y guarda el resultado en `data/historico/`, un archivo por mes:

| Archivo | Fuente | Columnas |
|---|---|---|
| `colas_AAAA-MM.csv` | [ThemeParks.wiki](https://api.themeparks.wiki) | `timestamp_utc`, `parque`, `atraccion_id`, `atraccion`, `status` (`OPERATING`, `CLOSED`, `DOWN`, `REFURBISHMENT`), `espera_min`, `last_updated` |
| `queuetimes_AAAA-MM.csv` | Powered by [Queue-Times.com](https://queue-times.com/) | `timestamp_utc`, `parque`, `atraccion_id`, `atraccion`, `abierta`, `espera_min`, `last_updated` |

Las horas están en UTC (en Madrid, +2 h en verano y +1 h en invierno).

Solo se añade una fila cuando el dato de una atracción cambia, y no se guarda nada si los dos parques están cerrados. Para saber la espera en un momento dado, toma la última fila anterior de esa atracción.

Se puede lanzar a mano desde la pestaña *Actions* → *Registro de colas* → *Run workflow*.
