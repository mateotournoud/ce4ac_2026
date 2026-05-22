# Design of a Constant Air Volume (CAV) heating system with an economizer 

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/mateotournoud/ce4ac_2026.git/main?urlpath=%2Fdoc%2Ftree%2FHeating-Economizer-Project.ipynb)

Authors:
- Fiant, Cristian
- Tournoud, Mateo
- Nekouei, Ali

This project models and analyzes a **Recycled Air Heating System with Economizer** under the constant air volume (CAV) assumption. The goal is to verify whether the system satisfies both the **thermal and humidity demands** of an office space through detailed mass and energy balance simulations. The model is based on the mass and energy balances for each component. The following characteristics are provided:
- Characteristics of the office: dimensions of the room, width of the wall, infiltration flow rate.
- Characteristics of the people: number of people, clothing, activities.
- Desired ambient conditions inside the room: temperature, humidity.

First, the user can define the weather conditions for his own purposes by modifying the boundary conditions. The second part of this Jupyter Notebook includes a section where real weather data in .epw format can be imported and used.

This framework follows the examples and uses the Python scripts from `PsychroAn_tuto` [[1](#ref-1)] and `dm4bem` [[2](#ref-2)]
