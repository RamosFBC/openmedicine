from open_medicine.mcp.calculators.rivaroxaban_dosing import calculate_rivaroxaban_dosing, RivaroxabanDosingParams, RivaroxabanIndication
from open_medicine.mcp.calculators.enoxaparin_dosing import calculate_enoxaparin_dosing, EnoxaparinDosingParams, EnoxaparinIndication

def test_rivaroxaban_nvaf_normal_renal():
    params = RivaroxabanDosingParams(crcl=60.0, indication=RivaroxabanIndication.NVAF)
    res = calculate_rivaroxaban_dosing(params)
    assert "20 mg once daily" in res.interpretation
    
def test_rivaroxaban_nvaf_moderate_renal():
    params = RivaroxabanDosingParams(crcl=35.0, indication=RivaroxabanIndication.NVAF)
    res = calculate_rivaroxaban_dosing(params)
    assert "15 mg once daily" in res.interpretation

def test_rivaroxaban_vte_prophylaxis_severe_renal():
    params = RivaroxabanDosingParams(crcl=20.0, indication=RivaroxabanIndication.VTE_PROPHYLAXIS)
    res = calculate_rivaroxaban_dosing(params)
    assert "Avoid. Use is not recommended." in res.interpretation

def test_enoxaparin_treatment_normal_renal():
    params = EnoxaparinDosingParams(crcl=80.0, weight=80.0, indication=EnoxaparinIndication.VTE_TREATMENT)
    res = calculate_enoxaparin_dosing(params)
    # Output should include 80.0 mg every 12 hours (1mg/kg) OR 120.0 mg once daily (1.5mg/kg)
    assert "80.0 mg subcutaneously every 12 hours" in res.interpretation
    assert "120.0 mg subcutaneously once daily" in res.interpretation

def test_enoxaparin_treatment_severe_renal():
    params = EnoxaparinDosingParams(crcl=25.0, weight=75.0, indication=EnoxaparinIndication.VTE_TREATMENT)
    res = calculate_enoxaparin_dosing(params)
    # Severe renal impairment treatment dosing is exactly 1 mg/kg ONCE daily
    assert "75.0 mg subcutaneously ONCE daily" in res.interpretation

def test_enoxaparin_prophylaxis_severe_renal():
    params = EnoxaparinDosingParams(crcl=20.0, weight=90.0, indication=EnoxaparinIndication.VTE_PROPHYLAXIS)
    res = calculate_enoxaparin_dosing(params)
    # Severe renal impairment drops it globally to 30mg daily
    assert "30 mg subcutaneously once daily" in res.interpretation
