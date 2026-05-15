
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def mix_process(alpha, temp_return, temp_range):
    """
    Parameters
    ----------
    alpha : TYPE
        DESCRIPTION.
    temp_return : TYPE
        DESCRIPTION.
    temp_range : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    theta_r = temp_return
    # Range for theta_o
    theta_o = np.linspace(temp_range[0], temp_range[1], 400)

    # Compute theta_m for alpha = 0.15
    theta_m = alpha * theta_o + (1 - alpha) * theta_r

    # Compute theta_m for alpha = 0 and alpha = 1
    theta_m_0 = 0 * theta_o + (1 - 0) * theta_r  # alpha = 0
    theta_m_1 = 1 * theta_o + (1 - 1) * theta_r  # alpha = 1

    # Create the figure and axis
    fig, ax = plt.subplots(figsize=(8, 5))

    # Plot the main line (alpha = 0.15)
    ax.plot(theta_o, theta_m,
            label=rf'$\alpha = {alpha}$')

    # Plot the additional lines in red
    ax.plot(theta_o, theta_m_0, '--', color='gray', label=r'$\alpha = 0$')
    ax.plot(theta_o, theta_m_1, '-', color='gray', label=r'$\alpha = 1$')

    # Mark the point (θr, θr)
    ax.scatter(theta_r, theta_r, color='red', zorder=5)
    ax.annotate(
        r'$(\theta_r,\theta_r)$',
        xy=(theta_r, theta_r),
        xytext=(theta_r + 1, theta_r - 3),
        fontsize=12
    )

    # Labels, title, grid, legend
    ax.set_xlabel(r'Outdoor air temperature, $\theta_o$ / °C')
    ax.set_ylabel(r'Mixed air temperature, $\theta_m$ / °C')
    ax.grid(True)
    ax.set_aspect('equal')
    ax.legend()
    plt.show()

    return


def ideal_mix_temp(
    θo,     # [θomin, θomax, dθo]
    θB,     # [θBh, θBc]
    θM,     # Mixed-air temperature setpoint in free cooling
    θL,     # Outdoor dry-bulb limit
    θr,     # [θrh, θrc]
    α       # mixing coefficient
):
    """
    Creates a dataframe of ideal operation of the economizer.

    Parameters
    ----------
    θo : list of floats [θomin, θomax, dθo]
        Outdoor temperarure from θomin to θomax with step dθo.

    θB : list of floats [θBh, θBc]
        Base temperature for heating θBh and cooling θBc.

    θM : float
        Mixed air temperature setpoint in free-cooling.

    θL : float
        Outdoor dry‑bulb limit setpoint for free-cooling.

    θr : list of floats [θrh, θrc]
        Return air temperature for heating θrh and cooling θrc.

    α : float
        Mixing ratio (of outdoor air in the mixed air), α ∈ [0, 1]

    Returns
    -------
    df : pandas.DataFrame
    DataFrame containing the temperature data. Must include:

    - 'θo' : float
        Outdor temperature.
    - 'θm' : float
        Mixed air temperature.
    - 'process' : str
        Thermal regime ('heating', 'free-running', 'free-cooling', 'cooling').


    Algorithm
    ---------

    - Make a dataframe df_θo with θo from θomin to θomax with step dθo.

    - Create the dataframe df_θm with columns θo, θm, “process” so that:

    1.	For  θo ∈ [θomin, θBh]:

        θm = ɑ·θo + (1 - ɑ) · θrh

        process = “heating”

    2. 	For θo ∈ [θBh, θBc]:

        θm = y0 + (y1−y0) / (x1−x0) · (x−x0)

        process = “free-running”

        where:

            x0 = θBh

            y0 = ɑ·θBh + (1 - ɑ) · θrh
            x1 = θBc

            y1 is the 1st value of zone 3 (free-cooling)


    3.	For θo ∈ [θBc, θM]:

    - if θBc > θC = 1/ɑ·(θM - (1- ɑ) ·θrc):

        θm = θM

        process = “free-cooling”

    - else:
        for θo ∈ [θBc, θC]:

            θm = ɑ·θo + (1 - ɑ)·θrc

            process = “free-cooling”

        for θo ∈ [θC, θM]:

            θm = θM

            process = “free-cooling”

    4.	For θm ∈ [θM, θL]:

        θm =  θo;

        process = “free-cooling”

    5.	For θm ∈ [θL, θomax]:

        θm = ɑ·θo + (1 - ɑ)·θr;

        process = “cooling” 
    """
    θBh, θBc = θB
    θrh, θrc = θr

    θomin, θomax, dθo = θo
    θo_values = np.arange(θomin, θomax + dθo, dθo)
    df_θo = pd.DataFrame({"θo": θo_values})

    df = df_θo.copy()
    df["θm"] = np.nan
    df["process"] = ""

    def mix(θo, θr):
        """
        Mixed air.

        Parameters
        ----------
        θo : pandas.Series
            Outdoor temperature.
        θr : float
            Return air, equal to indoor air temperature set-point.

        Returns
        -------
        pandas.Series
            Mixed air temperature.

        """
        return α * θo + (1 - α) * θr

    # ----------------------------------------------------------
    # 0. Compute y1 for zone 2 (based on the FIRST point of zone 3)
    # ----------------------------------------------------------
    θC = (θM - (1 - α) * θrc) / α

    if θBc > θC:
        # Zone 3 is entirely equal to θM
        y1 = θM
    else:
        # First part of zone 3 starts with the mixing with θrc
        y1 = α * θBc + (1 - α) * θrc

    # ----------------------------------------------------------
    # 1. Heating: θo ≤ θBh
    # ----------------------------------------------------------
    heat = (df["θo"] <= θBh)
    df.loc[heat, "θm"] = mix(df.loc[heat, "θo"], θrh)
    df.loc[heat, "process"] = "heating"

    # ----------------------------------------------------------
    # 2. Free-running: θBh ≤ θo ≤ θBc
    # interpolation between:
    # (x0, y0) = (θBh, αθBh + (1−α)θrh)
    # (x1, y1) as defined above
    # ----------------------------------------------------------
    f_run = (df["θo"] > θBh) & (df["θo"] <= θBc)

    if f_run.any():
        x0, x1 = θBh, θBc
        y0 = α * θBh + (1 - α) * θrh
        θo_vals = df.loc[f_run, "θo"]
        df.loc[f_run, "θm"] = y0 + (y1 - y0) / (x1 - x0) * (θo_vals - x0)
        df.loc[f_run, "process"] = "free-running"

    # ----------------------------------------------------------
    # 3. Free-cooling region: θBc < θo ≤ θM
    # ----------------------------------------------------------
    f_cool = (df["θo"] >= θBc) & (df["θo"] <= θM)

    if f_cool.any():

        if θBc > θC:
            # Entire region uses θM
            df.loc[f_cool, "θm"] = θM
            df.loc[f_cool, "process"] = "free-cooling"

        else:
            # [θBc, θC]
            f_coola = (df["θo"] > θBc) & (df["θo"] <= θC)
            df.loc[f_coola, "θm"] = mix(df.loc[f_coola, "θo"], θrc)
            df.loc[f_coola, "process"] = "free-cooling"

            # [θC, θM]
            f_coolb = (df["θo"] > θC) & (df["θo"] <= θM)
            df.loc[f_coolb, "θm"] = θM
            df.loc[f_coolb, "process"] = "free-cooling"

    # ----------------------------------------------------------
    # 4. Free-cooling: θM < θo ≤ θL → θm = θo
    # ----------------------------------------------------------
    f_cool = (df["θo"] >= θM) & (df["θo"] <= θL)
    df.loc[f_cool, "θm"] = df.loc[f_cool, "θo"]
    df.loc[f_cool, "process"] = "free-cooling"

    # ----------------------------------------------------------
    # 5. Cooling: θo > θL
    # ----------------------------------------------------------
    cool = df["θo"] > θL
    df.loc[cool, "θm"] = mix(df.loc[cool, "θo"], θrc)
    df.loc[cool, "process"] = "cooling"

    df[["θo", "θm"]] = df[["θo", "θm"]].round(3)

    return df


def mix_ratio(df_θm):
    """
    Compute the mixing ratio u for different operating processes.

    Parameters
    ----------
    df_θm : pandas.DataFrame
        DataFrame with columns:
        - 'θo'      : outdoor temperature
        - 'θm'      : mixed air temperature
        - 'process' : 'heating', 'cooling', 'free-cooling', or 'free-running'

    θr : list or tuple of length 2
        Reference temperatures [θrh, θrc]
        - θrh : heating reference temperature
        - θrc : cooling reference temperature

    Returns
    -------
    df_u : pandas.DataFrame
        DataFrame with columns ['θo', 'θm', 'u', 'process']
    """

    # Infer parameters from df_θm
    α = (df_θm["θm"].iloc[1] - df_θm["θm"].iloc[0]
         ) / (df_θm["θo"].iloc[1] - df_θm["θo"].iloc[0])

    x0 = df_θm['θo'].iloc[-1]
    y0 = df_θm['θm'].iloc[-1]
    θrc = (y0 - α * x0) / (1 - α)

    x0 = df_θm['θo'].iloc[0]
    y0 = df_θm['θm'].iloc[0]
    θrh = (y0 - α * x0) / (1 - α)

    # Copy input dataframe
    df = df_θm.copy()
    df[["θo", "θm"]] = df[["θo", "θm"]].round(3)

    # Initialize u
    df["u"] = np.nan

    # --------------------------------------------------
    # Heating
    # --------------------------------------------------
    mask_h = df["process"] == "heating"
    df.loc[mask_h, "u"] = (
        (df.loc[mask_h, "θm"] - θrh) /
        (df.loc[mask_h, "θo"] - θrh)
    )

    # --------------------------------------------------
    # Cooling and free-cooling
    # --------------------------------------------------
    mask_c = df["process"].isin(["cooling", "free-cooling"])
    df.loc[mask_c, "u"] = (
        (df.loc[mask_c, "θm"] - θrc) /
        (df.loc[mask_c, "θo"] - θrc)
    )
    # Enforce u = α when θo == θrc
    df.loc[np.isclose(df["θo"], θrc), "u"] = α

    # --------------------------------------------------
    # Free-running
    # θr varies linearly from θrh to θrc with θo
    # --------------------------------------------------
    mask_fr = df["process"] == "free-running"

    if mask_fr.any():
        θo_fr = df.loc[mask_fr, "θo"]

        θo_min = θo_fr.min()
        θo_max = θo_fr.max()

        # Linear interpolation of θr(θo)
        θr_var = θrh + (θrc - θrh) * (
            (θo_fr - θo_min) / (θo_max - θo_min)
        )

        df.loc[mask_fr, "u"] = (
            (df.loc[mask_fr, "θm"] - θr_var) /
            (df.loc[mask_fr, "θo"] - θr_var)
        )

    # Return requested columns only
    df_u = df[["θo", "θm", "u", "process"]]

    return df_u


def plot_ideal_mix_temp(df_θm):
    """
    Plots the ideal operation of the economizer
    on the current matplotlib axes.
    """

    # Infer parameters from df_θm
    α = (df_θm["θm"].iloc[1] - df_θm["θm"].iloc[0]) / \
        (df_θm["θo"].iloc[1] - df_θm["θo"].iloc[0])

    x0 = df_θm['θo'].iloc[-1]
    y0 = df_θm['θm'].iloc[-1]
    θrc = (y0 - α * x0) / (1 - α)

    x0 = df_θm['θo'].iloc[0]
    y0 = df_θm['θm'].iloc[0]
    θrh = (y0 - α * x0) / (1 - α)

    # Reference domain
    θo_ref = df_θm["θo"]

    # Reference lines
    θm_bisect = θo_ref
    θm_rh_line = α * θo_ref + (1 - α) * θrh
    θm_rc_line = α * θo_ref + (1 - α) * θrc

    # Gray reference lines
    plt.plot(θo_ref, θm_bisect, color="gray", linewidth=1.2,
             label="100 % outdoor air")
    plt.plot(θo_ref, θm_rh_line, '--', color='gray',
             label=f"{100*α:.0f} % outdoor air, heating")
    plt.plot(θo_ref, θm_rc_line, '-.', color='gray',
             label=f"{100*α:.0f} % outdoor air, cooling")

    # Colored process segments
    colors = {
        "heating": "red",
        "free-running": "magenta",
        "free-cooling": "green",
    }

    for process, color in colors.items():
        mask = df_θm["process"] == process
        plt.plot(df_θm.loc[mask, "θo"],
                 df_θm.loc[mask, "θm"],
                 color=color, label=process)

    plt.xlabel(r"Outdoor temperature, $\theta_o$ / °C")
    plt.ylabel(r"Mixed air temperature, $\theta_m$ / °C")
    plt.grid(True)
    plt.legend()


def plot_mix_ratio(df_u):
    """
    Plot the mixing ratio u as a function of θo using fixed colors per process,
    with legend in the order: heating, free-running, free-cooling, cooling.
    """

    # Fixed colors dictionary (also defines plotting/legend order)
    colors = {
        "heating": "red",
        "free-running": "magenta",
        "free-cooling": "green",
    }

    for process, color in colors.items():
        mask = df_u["process"] == process
        if mask.any():  # Only plot if this process exists in the data
            plt.plot(
                df_u.loc[mask, "θo"],
                df_u.loc[mask, "u"],
                color=color, label=process)

    plt.xlabel(r"Outdoor temperature, $\theta_o$ / °C")
    plt.ylabel("Mixing ratio, $u$")
    # plt.title("Mixing ratio $u$ as a function of outdoor temperature")
    plt.legend()
    plt.grid(True)


def plot_mix_temp_ratio(df_θm, df_u):
    """
    Plot ideal mixed temperature and mixing ratio
    in two stacked panels with custom height ratio.
    Upper panel 4 times taller than lower panel.
    """

    # plt.figure(figsize=(10, 10))
    plt.figure(figsize=(8, 8))
    gs = plt.GridSpec(2, 1, height_ratios=[4, 1], hspace=0.3)

    # Upper panel (ideal mixed temperature)
    plt.subplot(gs[0])
    plot_ideal_mix_temp(df_θm)
    plt.title("Ideal economizer operation")

    # Lower panel (mixing ratio)
    plt.subplot(gs[1])
    plot_mix_ratio(df_u)

    # plt.tight_layout()
    plt.show()


α = 0.10    # 100 %, outdoor air mixing rate
θr = 23     # °C, return air temperature
mix_process(α, θr, [-10, 40])

# Input values
θo = [10, 26, 0.01]     # °C, Outdoor temperarure from min to max with step dθo
θB = [12, 13]           # °C, Base temperature for heating θBh and cooling θBc
θM = 16.                # °C, Mixed air temperature setpoint in free-cooling
θL = 24.                # °C, Outdoor dry‑bulb limit setpoint for free-cooling
θr = [22, 24]           # °C,, Return air temperature for heating and cooling
α = 0.1                 # α ∈ [0, 1], Ratio of outdoor air in the mixed air

# Compute & plot df_θm
df_θm = ideal_mix_temp(θo, θB, θM, θL, θr, α)
plot_ideal_mix_temp(df_θm)

# Compute & plot df_θu
df_u = mix_ratio(df_θm)
plt.figure()
plot_mix_ratio(df_u)

plot_mix_temp_ratio(df_θm, df_u)