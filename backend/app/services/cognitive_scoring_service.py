from __future__ import annotations


def compute_rule_based_score(
    acoustic: dict, temporal: dict, linguistic: dict
) -> dict[str, int | str | dict]:
    score = 100
    penalties: dict[str, int] = {}

    lexical_div = float(linguistic.get("lexical_diversity", 0.0))
    if lexical_div < 0.35:
        penalties["low_lexical_diversity"] = 15

    speech_rate = float(temporal.get("speech_rate_estimate", 0.0))
    if speech_rate < 1.6:
        penalties["slow_speech_rate"] = 10

    # acoustic keys: prefer new name, fallback to legacy
    mfcc_var = None
    if isinstance(acoustic.get("mfcc_variability_mean"), (int, float)):
        mfcc_var = float(acoustic.get("mfcc_variability_mean"))
    elif isinstance(acoustic.get("mfcc_variance_avg"), (int, float)):
        mfcc_var = float(acoustic.get("mfcc_variance_avg"))

    if mfcc_var is not None and mfcc_var < 25:
        penalties["low_acoustic_variability"] = 10

    score -= sum(penalties.values())
    score = max(0, min(100, score))

    if score >= 80:
        risk = "low"
    elif score >= 60:
        risk = "moderate"
    else:
        risk = "high"

    return {"score": score, "risk_level": risk, "rule_breakdown": penalties}

