from open_medicine.mcp.calculators.gcs import calculate_gcs, GCSParams

def test_gcs_mild_injury():
    # E4, V5, M6 = 15 (Fully awake/Normal)
    params = GCSParams(eye_response=4, verbal_response=5, motor_response=6)
    res = calculate_gcs(params)
    assert res.value == 15
    assert "Mild" in res.interpretation
    assert "E4 V5 M6" in res.interpretation

def test_gcs_moderate_injury():
    # E3, V3, M4 = 10 (Moderate)
    params = GCSParams(eye_response=3, verbal_response=3, motor_response=4)
    res = calculate_gcs(params)
    assert res.value == 10
    assert "Moderate" in res.interpretation

def test_gcs_severe_injury():
    # E1, V1, M1 = 3 (Deep coma/Brain death proxy limit)
    params = GCSParams(eye_response=1, verbal_response=1, motor_response=1)
    res = calculate_gcs(params)
    assert res.value == 3
    assert "Severe" in res.interpretation
    assert "Intubation strongly considered" in res.interpretation
    assert res.evidence.source_doi == "10.1016/s0140-6736(74)91639-0"
