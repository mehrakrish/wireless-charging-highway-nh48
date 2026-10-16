"""
Solar layer: hourly AC output per kWp of fixed-tilt PV from a typical-meteorological-year (EPW) file.

Chain (standard NREL PVWatts method, implemented with pvlib):
  1. Sun position for every hour (pvlib.solarposition, NREL SPA algorithm).
  2. Irradiance on the tilted panel from the measured global, direct and diffuse values in the EPW file
     (Perez transposition model, ground albedo 0.2).
  3. Cell temperature from irradiance, air temperature and wind (SAPM model, open-rack glass/polymer).
  4. DC power: PVWatts, temperature coefficient -0.37 %/degC (typical mono-PERC datasheet value).
  5. System losses 14 % (PVWatts default: soiling, wiring, mismatch, availability) and inverter efficiency 96 %.
Output: kW of AC power per kWp installed, for each of the 8760 hours.
"""
import numpy as np
import pvlib


def per_kwp(epw_path, tilt=None, azimuth=180.0, gamma=-0.0037, losses=0.14, eta_inv=0.96):
    data, meta = pvlib.iotools.read_epw(epw_path, coerce_year=2023)
    lat, lon = meta["latitude"], meta["longitude"]
    tilt = abs(lat) if tilt is None else tilt
    # EPW values are averages over the hour ending at the time stamp; evaluate the sun at mid-hour
    times = data.index - np.timedelta64(30, "m")
    sp = pvlib.solarposition.get_solarposition(times, lat, lon, altitude=meta.get("altitude", 0))
    dni_extra = pvlib.irradiance.get_extra_radiation(times)
    poa = pvlib.irradiance.get_total_irradiance(
        tilt, azimuth, sp["apparent_zenith"].values, sp["azimuth"].values,
        data["dni"].values, data["ghi"].values, data["dhi"].values,
        dni_extra=dni_extra.values, model="perez", albedo=0.2)
    poa_g = np.nan_to_num(np.asarray(poa["poa_global"]), nan=0.0).clip(min=0)
    p = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"]["open_rack_glass_polymer"]
    t_cell = pvlib.temperature.sapm_cell(poa_g, data["temp_air"].values, data["wind_speed"].values, **p)
    p_dc = pvlib.pvsystem.pvwatts_dc(poa_g, t_cell, pdc0=1.0, gamma_pdc=gamma)   # kW per kWp
    p_ac = np.clip(p_dc * (1 - losses) * eta_inv, 0, None)
    info = dict(site=meta.get("city"), lat=lat, lon=lon, tilt=tilt,
                ghi_kwh_m2_yr=float(data["ghi"].sum() / 1e3),
                yield_kwh_per_kwp=float(p_ac.sum()), cuf=float(p_ac.mean()))
    return np.asarray(p_ac), data["temp_air"].values, info


if __name__ == "__main__":
    import sys
    y, _, info = per_kwp(sys.argv[1])
    print(info)
