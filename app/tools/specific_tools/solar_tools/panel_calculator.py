from langchain.tools import BaseTool
from typing import Type, Any
from pydantic import BaseModel, Field


class SolarPanelInput(BaseModel):
    roof_area_sqm: float = Field(description="Available roof area in square meters")
    sunlight_hours_avg: float = Field(description="Average daily sunlight hours")
    panel_efficiency: float = Field(
        default=0.2, description="Solar panel efficiency (e.g., 0.2 for 20%)"
    )


class SolarPanelCalculatorTool(BaseTool):
    name: str = "solar_panel_potential_calculator"
    description: str = (
        "Calculates potential solar panel electricity generation based on roof area, "
        "sunlight hours, and panel efficiency. Use this to estimate solar energy output."
    )
    args_schema: Type[BaseModel] = SolarPanelInput

    def _run(
        self,
        roof_area_sqm: float,
        sunlight_hours_avg: float,
        panel_efficiency: float = 0.2,
        **kwargs: Any,
    ) -> str:
        print(
            f"SolarPanelCalculatorTool received: area={roof_area_sqm} sqm, "
            f"sunlight={sunlight_hours_avg} hrs, efficiency={panel_efficiency}"
        )
        # Simplified stub calculation
        # A more realistic calculation would consider panel wattage, inverter losses, etc.
        # Average solar irradiance (kW/m^2), let's assume 1 kW/m^2 during peak sunlight
        # For simplicity, let's say potential_power_kw = roof_area_sqm * panel_efficiency * 1 kW/m^2 (very rough)
        potential_power_kw = (
            roof_area_sqm * panel_efficiency * 0.15
        )  # A more conservative estimate for average panel output per sqm
        estimated_daily_energy_kwh = potential_power_kw * sunlight_hours_avg

        return (
            f"Based on {roof_area_sqm} sqm roof area, {sunlight_hours_avg} average daily sunlight hours, "
            f"and {panel_efficiency*100}% panel efficiency, the estimated daily energy generation "
            f"is approximately {estimated_daily_energy_kwh:.2f} kWh. "
            f"(This is a simplified stub calculation.)"
        )

    async def _arun(
        self,
        roof_area_sqm: float,
        sunlight_hours_avg: float,
        panel_efficiency: float = 0.2,
        **kwargs: Any,
    ) -> str:
        print(
            f"SolarPanelCalculatorTool (async) received: area={roof_area_sqm} sqm, "
            f"sunlight={sunlight_hours_avg} hrs, efficiency={panel_efficiency}"
        )
        return self._run(roof_area_sqm, sunlight_hours_avg, panel_efficiency, **kwargs)
