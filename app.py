import streamlit as st
import pandas as pd
import CoolProp.CoolProp as CP

# --- Властивості для таблиці ---
PROPERTIES = {
    "Density [kg/m³]": "D",
    "Enthalpy [kJ/kg]": "H",
    "Entropy [kJ/kg/K]": "S",
    "Internal Energy [kJ/kg]": "U",
    "Cp [kJ/kg/K]": "C",
    "Cv [kJ/kg/K]": "O",
    "Speed of Sound [m/s]": "A",
    "Viscosity [Pa·s]": "V",
    "Thermal Conductivity [W/m/K]": "L",
}

st.title("CoolProp Property Calculator")

# --- Список доступних рідин ---
fluids_str = CP.get_global_param_string("FluidsList")
all_fluids = sorted(fluids_str.split(","))
fluid = st.selectbox("Оберіть рідину", all_fluids, index=all_fluids.index("Water"))

# --- Вхідні дані ---
temperature = st.number_input("Температура [°C]", value=200.0)
pressure    = st.number_input("Тиск [Па]", value=100_000.0, step=100.0)

EPS_REL = 1e-3  # відносний допуск для перевірки насичення

if st.button("Розрахувати"):
    try:
        T = temperature + 273.15  # K
        P = pressure              # Pa

        results = {}

        # --- Фаза ---
        try:
            phase = CP.PhaseSI("T", T, "P", P, fluid)  # 'gas', 'liquid', 'twophase', ...
        except Exception:
            phase = "unknown"
        results["Phase"] = phase

        # --- Довідкові насичені величини (можуть кидати виключення поза 2-фаз. обл.) ---
        Psat_T = None
        Tsat_P = None
        try:
            Psat_T = CP.PropsSI("P", "T", T, "Q", 0, fluid)
            results["P_sat@T [Па]"] = Psat_T
        except Exception:
            results["P_sat@T [Па]"] = "N/A"

        try:
            Tsat_P = CP.PropsSI("T", "P", P, "Q", 0, fluid)
            results["T_sat@P [°C]"] = Tsat_P - 273.15
        except Exception:
            results["T_sat@P [°C]"] = "N/A"

        # --- Якість (Q): тільки якщо точно двофазний стан або дуже близько до насичення ---
        is_twophase = str(phase).lower() == "twophase"
        near_saturation = False
        try:
            if Psat_T is not None and Psat_T > 0:
                near_saturation |= abs(P - Psat_T) / Psat_T < EPS_REL
        except Exception:
            pass
        try:
            if Tsat_P is not None and Tsat_P > 0:
                near_saturation |= abs(T - Tsat_P) / Tsat_P < EPS_REL
        except Exception:
            pass

        if is_twophase or near_saturation:
            try:
                Q = CP.PropsSI("Q", "T", T, "P", P, fluid)
                if 0.0 <= Q <= 1.0:
                    results["Quality (x)"] = f"{Q:.3f}"
                else:
                    # Значення на кшталт -1 або >1 трактуємо як однорідну фазу
                    results["Quality (x)"] = "Однорідна фаза"
            except Exception:
                results["Quality (x)"] = "N/A"
        else:
            results["Quality (x)"] = "Однорідна фаза"

        # --- Основні властивості при (T, P) ---
        for name, code in PROPERTIES.items():
            try:
                val = CP.PropsSI(code, "T", T, "P", P, fluid)
                # kJ-одиниці для ентальпії/ентропії/внутр. енергії/Cp/Cv
                if code in ["H", "S", "U", "C", "O"]:
                    val /= 1000.0
                results[name] = val
            except Exception:
                results[name] = "N/A"

        df = pd.DataFrame(list(results.items()), columns=["Property", "Value"])
        st.table(df)

    except Exception as e:
        st.error(f"Помилка: {e}")
