# Related guidelines: none
from pydantic import BaseModel, Field
from open_medicine.mcp.base import ClinicalResult, Evidence


class OttawaAnkleParams(BaseModel):
    """Parameters to evaluate the Ottawa Ankle Rules for ankle and midfoot radiography."""

    # Ankle (malleolar zone) criteria
    malleolar_zone_pain: bool = Field(
        False,
        description="Pain in the malleolar zone (distal 6 cm of tibia/fibula and malleoli)",
    )
    tenderness_posterior_edge_or_tip_lateral_malleolus: bool = Field(
        False,
        description=(
            "Bone tenderness along the distal 6 cm of the posterior edge of the "
            "fibula or tip of the lateral malleolus"
        ),
    )
    tenderness_posterior_edge_or_tip_medial_malleolus: bool = Field(
        False,
        description=(
            "Bone tenderness along the distal 6 cm of the posterior edge of the "
            "tibia or tip of the medial malleolus"
        ),
    )

    # Midfoot zone criteria
    midfoot_zone_pain: bool = Field(
        False,
        description="Pain in the midfoot zone (navicular, cuboid, cuneiforms, base of 5th metatarsal)",
    )
    tenderness_base_fifth_metatarsal: bool = Field(
        False,
        description="Bone tenderness at the base of the fifth metatarsal",
    )
    tenderness_navicular: bool = Field(
        False,
        description="Bone tenderness at the navicular bone",
    )

    # Shared criterion (applies to both ankle and foot series)
    inability_to_bear_weight: bool = Field(
        False,
        description=(
            "Inability to bear weight for four steps both immediately after the "
            "injury and at the time of evaluation in the emergency department"
        ),
    )


def calculate_ottawa_ankle(params: OttawaAnkleParams) -> ClinicalResult:
    """
    Evaluates the Ottawa Ankle Rules to determine the need for ankle and/or
    midfoot radiography following an acute ankle or midfoot injury.
    Reference: Stiell IG et al. Ann Emerg Med. 1992;21(4):384-390.
    """
    evidence = Evidence(
        source_doi="10.1016/s0196-0644(05)82656-3",
        level="Derivation Study",
        description=(
            "Stiell IG et al. A study to develop clinical decision rules for "
            "the use of radiography in acute ankle injuries. "
            "Ann Emerg Med. 1992;21(4):384-390."
        ),
    )

    # Evaluate ankle (malleolar zone) series need
    ankle_xray_needed = False
    if params.malleolar_zone_pain:
        if (
            params.tenderness_posterior_edge_or_tip_lateral_malleolus
            or params.tenderness_posterior_edge_or_tip_medial_malleolus
            or params.inability_to_bear_weight
        ):
            ankle_xray_needed = True

    # Evaluate foot (midfoot zone) series need
    foot_xray_needed = False
    if params.midfoot_zone_pain:
        if (
            params.tenderness_base_fifth_metatarsal
            or params.tenderness_navicular
            or params.inability_to_bear_weight
        ):
            foot_xray_needed = True

    # Build interpretation
    ankle_findings = []
    foot_findings = []

    if ankle_xray_needed:
        reasons = []
        if params.tenderness_posterior_edge_or_tip_lateral_malleolus:
            reasons.append("lateral malleolar tenderness")
        if params.tenderness_posterior_edge_or_tip_medial_malleolus:
            reasons.append("medial malleolar tenderness")
        if params.inability_to_bear_weight:
            reasons.append("inability to bear weight for 4 steps")
        ankle_findings.append(
            f"Ankle X-ray INDICATED: malleolar zone pain with {', '.join(reasons)}"
        )
    else:
        if params.malleolar_zone_pain:
            ankle_findings.append(
                "Ankle X-ray NOT indicated: malleolar zone pain present but no "
                "posterior malleolar tenderness and able to bear weight"
            )
        else:
            ankle_findings.append(
                "Ankle X-ray NOT indicated: no malleolar zone pain"
            )

    if foot_xray_needed:
        reasons = []
        if params.tenderness_base_fifth_metatarsal:
            reasons.append("base of 5th metatarsal tenderness")
        if params.tenderness_navicular:
            reasons.append("navicular tenderness")
        if params.inability_to_bear_weight:
            reasons.append("inability to bear weight for 4 steps")
        foot_findings.append(
            f"Foot X-ray INDICATED: midfoot zone pain with {', '.join(reasons)}"
        )
    else:
        if params.midfoot_zone_pain:
            foot_findings.append(
                "Foot X-ray NOT indicated: midfoot zone pain present but no "
                "navicular or 5th metatarsal tenderness and able to bear weight"
            )
        else:
            foot_findings.append(
                "Foot X-ray NOT indicated: no midfoot zone pain"
            )

    interpretation = (
        f"Ottawa Ankle Rules: {ankle_findings[0]}. {foot_findings[0]}."
    )

    # Value encoding: 0 = no imaging needed, 1 = ankle only, 2 = foot only, 3 = both
    value = 0
    if ankle_xray_needed:
        value += 1
    if foot_xray_needed:
        value += 2

    return ClinicalResult(
        value=value,
        interpretation=interpretation,
        evidence=evidence,
        # LOINC approximation: no specific Ottawa Ankle Rules LOINC code exists;
        # using Risk assessment Document as the output concept for this clinical
        # decision rule (determines fracture/imaging risk, not the imaging itself)
        fhir_code="71482-4",
        fhir_system="http://loinc.org",
        fhir_display="Ottawa Ankle Rules assessment",
    )
