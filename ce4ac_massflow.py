import numpy as np
import pandas as pd

# Physical constants
l = 2495e3  # J/kg, specific latent heat for vaporization
c = 1e3     # J/(kg·K), specific heat of dry air
cv = 1.96e3 # J/(kg·K), specific heat of water vapor

M = 28.9645 # kg/kmol, molar mass of dry air
Mv = 18.015 # kg/kmol, molar mass of water vapor
R = 8314    # J/(kmol·K), gas constant

def pvs(θ: float) -> float:
    """
    Saturation vapor pressure over liquid water, in Pa,
    as a function of tempetature θ, in °C
    Valid for temperaure range 0 ... 200°C
    ASHRAE-01 (2017) eq. (6), p. 1.8
    """
    import numpy as np
    T = θ + 273.15 # K, temperature

    C8 = -5.800_220_6e3
    C9 = 1.391_499_3e0
    C10 = -4.864_023_9e-2
    C11 = 4.176_476_8e-5
    C12 = -1.445_209_3e-8
    C13 = 6.545_967_3e0
    return np.exp(C8/T + C9 + C10 * T + C11 * T **2 + C12 * T **3 + C13 * np.log(T))  # Pa

def partial_pressure_dry_air(θ, z, ϕ):
    p = 101.325e3 * (1 - 2.25577e-5 * z)**5.2559 # Pa, air pressure as a function of altitude
    pv = ϕ * pvs(θ) # Pa, vapor pressure as a function of relative humidity ϕ and temperature θ
    pda = p - pv # Pa, dry-air partial pressure
    return p, pv, pda

def humidity_ratio(p, pv):
    w = Mv / M * pv / (p - pv)  # kg/kg, humidity ratio (mass vapor / mass dry air)
    return w

def density(pv, pda, θ):
    T = θ + 273.15      # K, temperature
    ρ = M / R * pda / T + Mv / R * pv / T # kg/m³, density
    v = 1/ρ # m³/kg, specific volume
    return ρ, v

def specific_enthalpy(w, θ):
    h = c * θ + w * (l + cv * θ)
    return h

def mass_flow_rate(ρ, V, p, w, θ):
    mha = ρ * V # kg/s mass flow rate of humid air
    ws = Mv / M * pvs(θ) / (p - pvs(θ)) # kg/kg, water content at saturation
    mv = (ws - w) * mha # kg/s, mass flow of water needed to saturate
    return mha, ws, mv

def calculate_air_parameters(V, θ, ϕ, z):
    """
    Calculate air parameters from input data.
    ----------
    Inputs
    V : float
        Volume flow rate in m³/s
    θ : float
        Indoor air temperature in °C
    ϕ : float
        Indoor relative humidity (-)
    z : float
        Altitude in m
    ----------
    Returns
    parameters : dict
        Dictionary containing the calculated air parameters:
        - p: Air pressure in Pa
        - pv: Vapor pressure in Pa
        - pda: Dry air partial pressure in Pa
        - w: Humidity ratio (kg/kg)
        - ρ: Density of humid air in kg/m³
        - v: Specific volume of humid air in m³/kg
        - h: Specific enthalpy of humid air in J/kg
        - mha: Mass flow rate of humid air in kg/s
        - ws: Water content at saturation in kg/kg
        - mv: Mass flow of water needed to saturate in kg/s
    """
    p, pv, pda = partial_pressure_dry_air(θ, z, ϕ)
    w = humidity_ratio(p, pv)
    ρ, v = density(pv, pda, θ)
    h = specific_enthalpy(w, θ)
    mha, ws, mv = mass_flow_rate(ρ, V, p, w, θ)
    
    parameters = {
        'p': p,
        'pv': pv,
        'pda': pda,
        'w': w,
        'ρ': ρ,
        'v': v,
        'h': h,
        'mha': mha,
        'ws': ws,
        'mv': mv
    }
    return parameters