"""Componente de Haystack que consulta el clima actual y las alertas de WeatherAPI."""

import logging

import requests
from haystack import component

logger = logging.getLogger(__name__)

BASE_URL = "https://api.weatherapi.com/v1"
TIMEOUT_SECONDS = 10


@component
class GetCurrentWeather:
    def __init__(self, api_key: str):
        self.api_key = api_key

    @component.output_types(text=str)
    def run(self, city: str):
        try:
            current = self._get("current.json", city)
        except requests.RequestException as error:
            logger.warning("Error consultando el clima de %s: %s", city, error)
            return {"text": f"No pude obtener el clima de {city} en este momento."}

        if "error" in current:
            return {"text": f"No encontré el clima de {city}: {current['error'].get('message', 'error desconocido')}."}

        condition = current["current"]["condition"]["text"]
        temp_c = current["current"]["temp_c"]
        precipitation = current["current"].get("precip_mm", 0)
        cloud_cover = current["current"].get("cloud", 0)  # Porcentaje de nubes, no probabilidad de lluvia real

        alerts_text = self._alerts_text(city)

        return {
            "text": (
                f"El clima en {city} es {condition} con {temp_c} °C. "
                f"Precipitación: {precipitation} mm. Nubosidad: {cloud_cover}%. {alerts_text}"
            )
        }

    def _get(self, endpoint: str, city: str) -> dict:
        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            params={"q": city, "key": self.api_key, "lang": "es"},
            timeout=TIMEOUT_SECONDS,
        )
        return response.json()

    def _alerts_text(self, city: str) -> str:
        try:
            alerts_response = self._get("alerts.json", city)
        except requests.RequestException as error:
            logger.warning("Error consultando alertas de %s: %s", city, error)
            return ""

        alerts = alerts_response.get("alerts", {}).get("alert", [])
        # dict.fromkeys elimina duplicados conservando el orden original
        headlines = list(dict.fromkeys(alert["headline"] for alert in alerts))
        if not headlines:
            return "No hay alertas meteorológicas."
        return f"Alertas meteorológicas: {'. '.join(headlines)}"
