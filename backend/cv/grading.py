"""
Grading and Variance calculation logic for OrganicLink produce quality assessment.
"""

def compute_quality_score(
    prob_fresh: float,
    prob_minor: float,
    prob_major: float,
    colour_vibrancy: float,
    colour_uniformity: float,
    defect_coverage_percent: float
) -> float:
    """
    Computes overall explainable quality score (0-100) from PyTorch classification probabilities
    and OpenCV extracted visual features.
    """
    class_component = 100.0 * prob_fresh + 60.0 * prob_minor + 20.0 * prob_major
    defect_component = max(0.0, 100.0 - (defect_coverage_percent * 2.0))
    colour_component = 0.6 * colour_vibrancy + 0.4 * colour_uniformity

    quality_score = (
        0.60 * class_component +
        0.25 * defect_component +
        0.15 * colour_component
    )
    return round(max(0.0, min(100.0, quality_score)), 2)


def score_to_grade(quality_score: float) -> str:
    """
    Maps quality score to letter grade:
    >= 85: Grade A (Premium)
    70-84: Grade B (Good)
    50-69: Grade C (Fair)
    < 50: Grade R (Reject)
    """
    if quality_score >= 85.0:
        return "A"
    elif quality_score >= 70.0:
        return "B"
    elif quality_score >= 50.0:
        return "C"
    else:
        return "R"


def compute_variance(farm_score: float, delivery_score: float, tolerance_percent: float = 10.0) -> dict:
    """
    Computes quality score variance between farm inspection and delivery inspection.
    variance_percent = ((farm_score - delivery_score) / farm_score) * 100
    """
    if farm_score <= 0:
        variance_percent = 0.0
    else:
        variance_percent = ((farm_score - delivery_score) / farm_score) * 100.0

    variance_percent = round(variance_percent, 2)

    # Check against tolerance threshold
    if abs(variance_percent) <= tolerance_percent:
        acceptable = True
        dispute_required = False
        anomaly = False
    elif variance_percent > tolerance_percent:
        acceptable = False
        dispute_required = True
        anomaly = False
    else:
        # delivery score is materially higher than farm score (> tolerance_percent higher)
        acceptable = True
        dispute_required = False
        anomaly = True

    return {
        "variance_percent": variance_percent,
        "variance_acceptable": acceptable,
        "dispute_flag": dispute_required,
        "is_anomaly": anomaly
    }
