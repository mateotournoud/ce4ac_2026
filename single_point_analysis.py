import numpy as np
import pandas as pd
from ce4ac_rec_air_cav import RecAirCAV


class SinglePointAnalysis:
    """
    Computes economizer state, mixing ratio, and electric power
    for a single outdoor temperature condition.
    """

    EFF_FAN   = 0.6
    EFF_BELT  = 0.9
    EFF_MOTOR = 0.85
    PRESS_ATM = 101325   # Pa
    DP_PA     = 500      # Pa
    ETA_HP    = 0.3      # Heat pump efficiency (fraction of Carnot)

    def __init__(self, θ01, θ02, θSd, θId, φIsp, φO, c_da, l_v,
                 Qsa, Qla, minf, UA, ma, df_u, θB):
        """
        Parameters
        ----------
        θ01, θ02  : state transition thresholds [°C]
        θSd       : supply air design temperature [°C]
        θId       : indoor setpoint temperature [°C]
        φIsp      : indoor relative humidity setpoint [-]
        φO        : outdoor relative humidity [-]
        c_da      : specific heat of dry air [J/kg·K]
        l_v       : latent heat of vaporisation [J/kg]
        Qsa, Qla  : sensible and latent auxiliary heat [W]
        minf      : infiltration mass flow rate [kg/s]
        UA        : building global conductance [W/K]
        ma        : supply air mass flow rate [kg/s]
        df_u      : DataFrame with columns ['θo', 'u', 'process']
        θB        : tuple (θB_heating, θB_free_running) [°C]
        """
        self.θ01  = θ01
        self.θ02  = θ02
        self.θSd  = θSd
        self.θId  = θId
        self.φIsp = φIsp
        self.φO   = φO
        self.c_da = c_da
        self.l_v  = l_v
        self.Qsa  = Qsa
        self.Qla  = Qla
        self.minf = minf
        self.UA   = UA
        self.ma   = ma
        self.df_u = df_u
        self.θB   = θB

    def _get_state(self, θout):
        if θout < self.θ01:
            return "heating"
        elif self.θ01 <= θout < self.θ02:
            return "free-running"
        elif self.θ02 <= θout < 24:
            return "free-cooling"
        else:
            return "undefined"

    def _get_mix_ratio(self, θout):
        idx = (self.df_u["θo"] - θout).abs().idxmin()
        return self.df_u.loc[idx, "u"]

    def _get_θB_target(self, θout):
        row = self.df_u.loc[(self.df_u["θo"] - θout).abs().idxmin()]
        process = row["process"]
        if process == "heating":
            return self.θB[0]
        elif process == "free-running":
            return self.θB[1]
        elif process == "free-cooling":
            return None
        return None

    def _fan_power(self, θB_target):
        eff_total = self.EFF_FAN * self.EFF_BELT * self.EFF_MOTOR
        temp      = θB_target + 273.15
        density   = self.PRESS_ATM / (287.05 * temp)
        flow_m3s  = self.ma / density
        return (flow_m3s * self.DP_PA) / eff_total

    def run(self, θout, verbose=True):
        """
        Run single-point analysis for a given outdoor temperature.

        Returns
        -------
        dict with keys: state, mix_ratio, P_fan_W, P_total_W, θB_target
        """
        state     = self._get_state(θout)
        mix_ratio = self._get_mix_ratio(θout)
        θB_target = self._get_θB_target(θout)

        if state == "undefined":
            if verbose:
                print(f"State: undefined for θout = {θout} °C")
            return {"state": state, "mix_ratio": None,
                    "P_fan_W": None, "P_total_W": None, "θB_target": None}

        P_fan_W = self._fan_power(θB_target)

        if state == "heating":
            m, v, Q = RecAirCAV(
                c=self.c_da, l=self.l_v, α=0.1,
                θS=self.θSd, θIsp=self.θId, φIsp=self.φIsp,
                θOd=θout, φO=self.φO,
                Qsa=self.Qsa, Qla=self.Qla,
                mi=self.minf, UA=self.UA,
                verbose=False
            )
            T_hot     = self.θSd + 273.15
            T_cold    = θout + 273.15
            COP_real  = self.ETA_HP * (T_hot / (T_hot - T_cold))
            P_hp_W    = Q['QsHC'] / COP_real + Q['QlVH']
            P_total_W = P_hp_W + P_fan_W

            if verbose:
                print(f"Mode: heating")
                print(f"  Total heating power:              {(Q['QsHC'] + Q['QlVH'])/1000:.3f} kW")
                print(f"  Electric power (heat pump):       {P_hp_W:.3f} W")
                print(f"  Electric power (fan):             {P_fan_W:.3f} W")
                print(f"  Electric power (heat pump + fan): {P_total_W:.3f} W")
                print(f"  Mixing ratio:                     {mix_ratio:.4f}")

        else:  # free-running or free-cooling
            P_total_W = P_fan_W

            if verbose:
                print(f"Mode: {state}")
                print(f"  Electric power (fan): {P_fan_W:.4f} W")
                print(f"  Mixing ratio:         {mix_ratio:.4f}")

        return {
            "state":      state,
            "mix_ratio":  mix_ratio,
            "P_fan_W":    P_fan_W,
            "P_total_W":  P_total_W,
            "θB_target":  θB_target
        }