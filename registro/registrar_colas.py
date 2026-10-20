"""Registra los tiempos de espera actuales de PortAventura Park y Ferrari Land.

Se ejecuta cada 15 minutos en GitHub Actions (ver .github/workflows/registro-colas.yml)
y va añadiendo filas a un CSV por mes en data/historico/:

- colas_AAAA-MM.csv: fuente principal, ThemeParks.wiki.
- queuetimes_AAAA-MM.csv: segunda fuente, Queue-Times.com ("Powered by Queue-Times.com").

Reglas:
- Si los dos parques están cerrados (todas las atracciones CLOSED) no escribe nada.
- Solo añade una fila si el dato de esa atracción ha cambiado desde la última vez
  (mismo lastUpdated = misma lectura), así ejecutarlo dos veces seguidas no duplica nada.

Uso: python registro/registrar_colas.py
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "data" / "historico"

CABECERA = {"User-Agent": "RideHuntersPlanner/0.1 (uso personal)"}
TIEMPO_MAX = 30  # segundos por petición

PARQUES_TPW = {
    "PortAventura Park": "32608bdc-b3fa-478e-a8c0-9dde197a4212",
    "Ferrari Land": "d06d91b8-7702-42c3-a8af-7d0161d471bf",
}
PARQUES_QT = {
    "PortAventura Park": 19,
    "Ferrari Land": 277,
}

COLUMNAS_TPW = ["timestamp_utc", "parque", "atraccion_id", "atraccion", "status",
                "espera_min", "last_updated"]
COLUMNAS_QT = ["timestamp_utc", "parque", "atraccion_id", "atraccion", "abierta",
               "espera_min", "last_updated"]


def leer_json(url: str) -> dict:
    respuesta = requests.get(url, headers=CABECERA, timeout=TIEMPO_MAX)
    respuesta.raise_for_status()
    return respuesta.json()


def themeparks(ahora: str) -> list[dict]:
    filas = []
    for parque, id_parque in PARQUES_TPW.items():
        datos = leer_json(f"https://api.themeparks.wiki/v1/entity/{id_parque}/live")
        for item in datos.get("liveData", []):
            if item.get("entityType") != "ATTRACTION":
                continue
            espera = (item.get("queue") or {}).get("STANDBY", {}).get("waitTime")
            filas.append({
                "timestamp_utc": ahora,
                "parque": parque,
                "atraccion_id": item["id"],
                "atraccion": item.get("name", ""),
                "status": item.get("status", ""),
                "espera_min": "" if espera is None else espera,
                "last_updated": item.get("lastUpdated", ""),
            })
    return filas


def queue_times(ahora: str) -> list[dict]:
    filas = []
    for parque, id_parque in PARQUES_QT.items():
        datos = leer_json(f"https://queue-times.com/parks/{id_parque}/queue_times.json")
        atracciones = list(datos.get("rides", []))
        for zona in datos.get("lands", []):
            atracciones.extend(zona.get("rides", []))
        for item in atracciones:
            filas.append({
                "timestamp_utc": ahora,
                "parque": parque,
                "atraccion_id": item["id"],
                "atraccion": item.get("name", ""),
                "abierta": item.get("is_open", ""),
                "espera_min": item.get("wait_time", ""),
                "last_updated": item.get("last_updated", ""),
            })
    return filas


def ultimas_lecturas(ruta: Path) -> dict[str, str]:
    """Último last_updated guardado de cada atracción en el CSV del mes."""
    if not ruta.exists():
        return {}
    with ruta.open(encoding="utf-8", newline="") as f:
        return {fila["atraccion_id"]: fila["last_updated"] for fila in csv.DictReader(f)}


def guardar(ruta: Path, columnas: list[str], filas: list[dict]) -> int:
    vistas = ultimas_lecturas(ruta)
    nuevas = [f for f in filas if vistas.get(str(f["atraccion_id"])) != f["last_updated"]]
    if not nuevas:
        return 0
    ruta.parent.mkdir(parents=True, exist_ok=True)
    escribir_cabecera = not ruta.exists()
    with ruta.open("a", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=columnas)
        if escribir_cabecera:
            escritor.writeheader()
        escritor.writerows(nuevas)
    return len(nuevas)


def main() -> int:
    momento = datetime.now(timezone.utc)
    ahora = momento.strftime("%Y-%m-%dT%H:%M:%SZ")
    mes = momento.strftime("%Y-%m")

    filas_tpw = themeparks(ahora)
    if not filas_tpw:
        print("ThemeParks.wiki no ha devuelto atracciones; no se guarda nada.")
        return 1
    if all(f["status"] == "CLOSED" for f in filas_tpw):
        print("Los dos parques están cerrados; no se guarda nada.")
        return 0

    n = guardar(CARPETA / f"colas_{mes}.csv", COLUMNAS_TPW, filas_tpw)
    print(f"ThemeParks.wiki: {n} filas nuevas de {len(filas_tpw)} atracciones.")

    # La segunda fuente es opcional: si falla, no se pierde el registro principal.
    try:
        filas_qt = queue_times(ahora)
        n = guardar(CARPETA / f"queuetimes_{mes}.csv", COLUMNAS_QT, filas_qt)
        print(f"Queue-Times: {n} filas nuevas de {len(filas_qt)} atracciones.")
    except (requests.RequestException, ValueError) as error:
        print(f"Queue-Times no disponible ({error}); se sigue sin esa fuente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
