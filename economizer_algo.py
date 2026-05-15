import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from ce4ac_rec_air_cav import RecAirCAV


import os, glob, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dm4bem import read_epw


class SystemController:
    def __init__(self, θ01, θ02):
        self.state = None
        self.θ01 = θ01
        self.θ02 = θ02

    def update_state(self, θout):
        if θout < self.θ01:
            self.state = "heating"
        elif self.θ01 <= θout < self.θ02:
            self.state = "free-running"
        elif self.θ02 <= θout < 24:
            self.state = "free-cooling"
        else:
            self.state = "undefined"
        return self.state
    
def _get_θB_target(θout, df_u, θB, θL):
    row = df_u.loc[(df_u["θo"] - θout).abs().idxmin()]
    process = row["process"]
    if process == "heating":
        return θB[0]
    elif process == "free-running":
        return θB[1]
    elif process == "free-cooling":
        return θL
    return None

def process_epw(start_date, end_date, df_u, θ01, θ02, θB, θL, ma_const, c_da, l_v, θSd, θId, φIsp, φO, Qsad, Qlad, minf, UAd, eta_hp=0.3):
    
    import os, glob, sys

    base_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(base_dir)
    from dm4bem import read_epw

    epw_folder = os.path.join(base_dir, "Weather_Data")
    epw_files = glob.glob(os.path.join(epw_folder, "*.epw"))

    if len(epw_files) == 0:
        raise FileNotFoundError(f"No .epw file found in {epw_folder}")
    epw_path = epw_files[0]

    data, meta = read_epw(epw_path)
    weather = data[["temp_air"]]
    weather.index = weather.index.map(lambda t: t.replace(year=2000))

    tz = weather.index.tz
    start = pd.Timestamp(start_date).replace(year=2000).tz_localize(tz)
    end   = pd.Timestamp(end_date).replace(year=2000).tz_localize(tz)
    weather = weather.loc[start:end]

    controller = SystemController(θ01, θ02)
    results = []

    for timestamp, row in weather.iterrows():
        θout = row["temp_air"]
        state = controller.update_state(θout)
        mix_ratio = get_mix_ratio_from_tout(θout, state, df_u)
        ma = ma_const
        theta_B_target = _get_θB_target(θout, df_u, θB, θL)

        energy_W = calculate_energy_kWh(
            state=state, ma=ma, theta_B_target=theta_B_target,
            θout=θout, c_da=c_da, l_v=l_v, θSd=θSd, θId=θId,
            φIsp=φIsp, φO=φO, Qsa=Qsad, Qla=Qlad,
            minf=minf, UA=UAd, eta_hp=eta_hp
        ) if state != "undefined" else None

        results.append({
            "time": timestamp,
            "θout": θout,
            "state": state,
            "mix_ratio": round(mix_ratio, 4) if mix_ratio is not None else None,
            "ma_kg_s": round(ma, 4),
            "Energy_W": round(energy_W, 5) if energy_W is not None else None
        })

    return pd.DataFrame(results)

def get_mix_ratio_from_tout(θout, state, df_u):
    if state == "undefined":
        return None
    idx = (df_u["θo"] - θout).abs().idxmin()
    return df_u.loc[idx, "u"]


def calculate_energy_kWh(state, ma, theta_B_target, θout, c_da, l_v,
                        θSd, θId, φIsp, φO, Qsa, Qla, minf, UA, eta_hp=0.3):
    eff_fan = 0.6
    eff_belt = 0.9
    eff_motor = 0.85
    eff_total = eff_fan * eff_belt * eff_motor

    press_atm = 101325
    dp_Pa = 500
    temp = theta_B_target + 273.15
    density = press_atm / (287.05 * temp)
    flow_m3s = ma / density
    P_fan_W = (flow_m3s * dp_Pa) / eff_total

    if state == "heating":
        m, v, Q = RecAirCAV(
            c=c_da, l=l_v, α=0.1,
            θS=θSd, θIsp=θId, φIsp=φIsp,
            θOd=θout, φO=φO,
            Qsa=Qsa, Qla=Qla,
            mi=minf, UA=UA,
            verbose=False
        )

        T_hot = θSd + 273.15
        T_cold = θout + 273.15
        COP_carnot = T_hot / (T_hot - T_cold)
        COP_real = eta_hp * COP_carnot

        P_el_heater_W = Q['QsHC'] / COP_real + Q['QlVH']
        P_total_W = P_el_heater_W + P_fan_W
        return P_total_W

    elif state in ["free-running", "free-cooling"]:
        return P_fan_W

    else:
        return None



def plot_energy(df_results):
    plt.figure(figsize=(10, 5))
    plt.plot(df_results["time"], df_results["Energy_W"], marker="o")
    plt.xlabel("Time")
    plt.ylabel("Power consumed (W)")
    plt.title("Electrical Power consumed along the time")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def plot_alpha_vs_time(df_results):
    df_plot = df_results.copy()
    df_plot["time_dt"] = pd.to_datetime(df_plot["time"], format="%H:%M")
    df_plot["mix_ratio"] = pd.to_numeric(df_plot["mix_ratio"], errors="coerce")
    df_plot = df_plot.sort_values("time_dt")

    plt.figure(figsize=(10, 5))
    plt.plot(df_plot["time_dt"], df_plot["mix_ratio"], marker='o', linestyle='-')
    plt.xlabel("Time")
    plt.ylabel(r"Mixing ratio $\alpha$")
    plt.title(r"Mixing ratio $\alpha$ over time")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()