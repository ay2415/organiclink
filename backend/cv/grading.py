"""
Grading and variance logic for OrganicLink produce quality assessment.

CHANGE vs the previous version:
  defect_coverage_percent has been REMOVED from the score.

  Why: it measured "pixels darker than the local median", which on real
  produce photographs captures specular highlights, shadows, stems and
  background as readily as it captures actual blemishes. A glossy healthy
  apple produced HIGH coverage (punished) while a uniformly brown rotten
  apple produced LOW coverage (rewarded) - inverting the grade.

  The trained classifier is now the dominant term (80%), with colour as a
  small explainability contribution (20%). defect_coverage is still computed
  and shown in the UI as a diagnostic, but it no longer affects the score.
"""

# Score weighting
W_CLASSIFIER = 0.80
W_COLOUR = 0.20

# Score assigned to each condition class when it has full probability mass
SCORE_FRESH = 100.0
SCORE_MINOR = 55.0
SCORE_MAJOR = 8.0


def compute_quality_score(
    prob_fresh: float,
    prob_minor: float,
    prob_major: float,
    colour_vibrancy: float,
    colour_uniformity: float,
) -> float:
    """
    Overall quality score (0-100), dominated by the trained classifier.

    prob_* are softmax probabilities from the defect head (they sum to 1).
    colour_* are 0-100 OpenCV sub-metrics used as a minor, explainable
    adjustment - they cannot by themselves flip a grade.
    """
    total = prob_fresh + prob_minor + prob_major
    if total > 0:
        prob_fresh /= total
        prob_minor /= total
        prob_major /= total

    class_component = (
        SCORE_FRESH * prob_fresh
        + SCORE_MINOR * prob_minor
        + SCORE_MAJOR * prob_major
    )

    colour_component = 0.6 * colour_vibrancy + 0.4 * colour_uniformity

    quality_score = W_CLASSIFIER * class_component + W_COLOUR * colour_component
    return round(max(0.0, min(100.0, quality_score)), 2)


def score_to_grade(quality_score: float) -> str:
    """
    >= 85 : A (Premium)
    70-84 : B (Good)
    50-69 : C (Fair)
    < 50  : R (Reject)
    """
    if quality_score >= 85.0:
        return "A"
    if quality_score >= 70.0:
        return "B"
    if quality_score >= 50.0:
        return "C"
    return "R"


def compute_variance(farm_score: float,
                     delivery_score: float,
                     tolerance_percent: float = 10.0) -> dict:
    """
    Quality variance between the farm inspection and the delivery inspection.

        variance_percent = ((farm_score - delivery_score) / farm_score) * 100

    Positive variance means quality DROPPED in transit.

    The tolerance band exists because the two photographs are taken by two
    different people, on two different devices, under two different lighting
    conditions. Some difference is measurement noise, not real quality loss.
    """
    if farm_score <= 0:
        variance_percent = 0.0
    else:
        variance_percent = ((farm_score - delivery_score) / farm_score) * 100.0

    variance_percent = round(variance_percent, 2)

    if abs(variance_percent) <= tolerance_percent:
        acceptable, dispute_required, anomaly = True, False, False
    elif variance_percent > tolerance_percent:
        # Quality dropped beyond tolerance
        acceptable, dispute_required, anomaly = False, True, False
    else:
        # Delivery scored materially HIGHER than farm. Not a dispute - usually
        # inconsistent photo conditions rather than produce improving.
        acceptable, dispute_required, anomaly = True, False, True

    return {
        "variance_percent": variance_percent,
        "variance_acceptable": acceptable,
        "dispute_flag": dispute_required,
        "is_anomaly": anomaly,
    }