import json
import random
import os
import ascvd

def generate_patient_profiles(count=200):
    profiles = []
    for _ in range(count):
        isMale = random.choice([True, False])
        isBlack = random.choice([True, False])
        smoker = random.choice([True, False])
        hypertensive = random.choice([True, False])
        diabetic = random.choice([True, False])
        age = random.randint(40, 79)
        systolicBloodPressure = random.randint(90, 200)
        totalCholesterol = random.randint(130, 320)
        hdl = random.randint(20, 100)

        # compute using the verified py pypi library
        expected_score = ascvd.compute_ten_year_score(
            isMale=isMale,
            isBlack=isBlack,
            smoker=smoker,
            hypertensive=hypertensive,
            diabetic=diabetic,
            age=age,
            systolicBloodPressure=systolicBloodPressure,
            totalCholesterol=totalCholesterol,
            hdl=hdl,
        )

        profiles.append({
            "isMale": isMale,
            "isBlack": isBlack,
            "smoker": smoker,
            "hypertensive": hypertensive,
            "diabetic": diabetic,
            "age": age,
            "systolicBloodPressure": systolicBloodPressure,
            "totalCholesterol": totalCholesterol,
            "hdl": hdl,
            "expected_score": expected_score
        })
    return profiles

if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "ascvd_test_cases.json")
    
    data = generate_patient_profiles(200)
    with open(out_file, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Generated {len(data)} profiles and saved to {out_file}")
