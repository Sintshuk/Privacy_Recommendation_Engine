"""Hierarchical utility scoring using only the 33 clustering questions."""

from __future__ import annotations

import math
from collections import defaultdict


DEFAULT_CONFIG = {
    "mapping_weights": {
        "direct": 1.0,
        "supporting": 0.5,
        "contextual": 0.25,
    },
    "utility_weights": {
        "item_alignment": 0.65,
        "structural_fit": 0.30,
        "actionability": 0.03,
        "policy_evidence": 0.02,
    },
    "diversity": {
        "max_per_category": 3,
    },
}


# Direction tells us what a positive value means for each derived dimension.
# These are all among the 33 clustering questions.
ACTION_ORIENTATION = {
    "QPB_1": -1.0,  # accepting without reading = less active privacy behaviour
    "QPB_2": 1.0,
    "QPB_3": 1.0,
    "QP_1": 1.0,
    "QP_2": 1.0,
    "QP_3": 1.0,
    "QP_4": 1.0,
    "QP_5": -1.0,  # higher coded response = more functionality-oriented
    "QP_6": 1.0,
    "QP_7": 1.0,
}

GUIDANCE_ORIENTATION = {
    **{f"QA_{i}": -1.0 for i in range(1, 7)},
    **{f"QC_{i}": -1.0 for i in range(1, 9)},
}

RISK_ORIENTATION = {
    **{f"QCT_{i}": -1.0 for i in range(1, 7)},
    **{f"QCT_{i}": 1.0 for i in range(7, 10)},
}

DOMAIN_TO_DIMENSION = {
    "Privacy Behaviours": "action_intent",
    "Preferences": "action_intent",
    "Awareness": "guidance_need",
    "Comprehension": "guidance_need",
    "Comfort": "privacy_sensitivity",
}
# These are guessed! Rights need more explaining while choices are
# more action-based, and more directly tied to acting on discomfort with
# a specific practice. THese are only used with no survey question match a recommendation.
CATEGORY_FALLBACK = {
    "privacy_right": {
        "action_intent": 0.40,
        "guidance_need": 0.90,
        "privacy_sensitivity": 0.50,
    },
    "privacy_control": {
        "action_intent": 0.90,
        "guidance_need": 0.50,
        "privacy_sensitivity": 0.70,
    },
}


def merge_config(config: dict | None) -> dict:
    merged = {
        section: values.copy()
        for section, values in DEFAULT_CONFIG.items()
    }
    if not config:
        return merged
    for section, values in config.items():
        if section in merged and isinstance(values, dict):
            merged[section].update(values)
    return merged


def _sigmoid(value: float, scale: float = 1.25) -> float:
    return 1.0 / (1.0 + math.exp(-(value * scale)))


def _mean_oriented(persona: dict, orientation: dict[str, float]) -> float:
    values = []
    questions = persona.get("questions", {})
    for question, sign in orientation.items():
        data = questions.get(question)
        if not data or data.get("z") is None:
            continue
        values.append(float(data["z"]) * sign)
    return sum(values) / len(values) if values else 0.0


def persona_dimensions(persona: dict) -> dict:
    """Project the 33-question persona profile into three interpretable dimensions."""
    raw_action = _mean_oriented(persona, ACTION_ORIENTATION)
    raw_guidance = _mean_oriented(persona, GUIDANCE_ORIENTATION)
    raw_risk = _mean_oriented(persona, RISK_ORIENTATION)

    return {
        "action_intent": round(_sigmoid(raw_action), 6),
        "guidance_need": round(_sigmoid(raw_guidance), 6),
        "privacy_sensitivity": round(_sigmoid(raw_risk), 6),
        "raw": {
            "action_intent": round(raw_action, 6),
            "guidance_need": round(raw_guidance, 6),
            "privacy_sensitivity": round(raw_risk, 6),
        },
    }


def _normalise_strength(signal: dict) -> str:
    strength = signal.get("strength") or signal.get("confidence") or "supporting"
    return {
        "related": "supporting",
        "presentation": "contextual",
    }.get(strength, strength)


def _directional_contribution(z_score: float, direction: str) -> float:
    if direction == "high":
        return z_score
    if direction == "low":
        return -z_score
    return 0.0


def _mapping_entry(candidate: dict, survey_mapping: dict) -> dict:
    return (
        survey_mapping
        .get(candidate["attribute"], {})
        .get(candidate["value"], {})
    )


def _candidate_alignment(
    candidate: dict,
    persona: dict,
    survey_mapping: dict,
    config: dict,
) -> tuple[float | None, list[dict], dict]:
    """Keep item-specific evidence from the existing question mapping."""
    mapping = _mapping_entry(candidate, survey_mapping)
    signals = mapping.get("signals", [])

    domain_sum = defaultdict(float)
    domain_weight = defaultdict(float)
    results = []

    for signal in signals:
        question = signal.get("question")
        qdata = persona.get("questions", {}).get(question)
        if not qdata or qdata.get("z") is None:
            continue

        strength = _normalise_strength(signal)
        weight = config["mapping_weights"].get(strength, 0.0)
        # Contextual mappings help the structural profile, not direct alignment.
        alignment_weight = 0.0 if strength == "contextual" else weight
        contribution = _directional_contribution(
            float(qdata["z"]),
            signal.get("direction", "high"),
        )

        if alignment_weight > 0:
            domain = qdata.get("domain", "Unknown")
            domain_sum[domain] += contribution * alignment_weight
            domain_weight[domain] += alignment_weight

        results.append({
            "question": question,
            "domain": qdata.get("domain", "Unknown"),
            "z": round(float(qdata["z"]), 6),
            "direction": signal.get("direction", "high"),
            "strength": strength,
            "contribution": round(contribution, 6),
            "used_in_alignment": alignment_weight > 0,
            "reason": signal.get("reason", ""),
        })

    domain_scores = {
        domain: round(domain_sum[domain] / domain_weight[domain], 6)
        for domain in domain_weight
        if domain_weight[domain] > 0
    }

    if not domain_scores:
        return None, results, domain_scores

    return (
        round(sum(domain_scores.values()) / len(domain_scores), 6),
        results,
        domain_scores,
    )


def _item_dimension_profile(
    candidate: dict,
    survey_mapping: dict,
    config: dict,
) -> dict:
    """Describe which persona dimensions matter most for this catalog item."""
    mapping = _mapping_entry(candidate, survey_mapping)
    weights = defaultdict(float)

    for signal in mapping.get("signals", []):
        strength = _normalise_strength(signal)
        weight = config["mapping_weights"].get(strength, 0.0)
        question = signal.get("question")

        if question in ACTION_ORIENTATION:
            dimension = "action_intent"
        elif question in GUIDANCE_ORIENTATION:
            dimension = "guidance_need"
        elif question in RISK_ORIENTATION:
            dimension = "privacy_sensitivity"
        else:
            continue

        weights[dimension] += weight

    if not weights:
        return CATEGORY_FALLBACK.get(
            candidate.get("category"),
            {
                "action_intent": 0.50,
                "guidance_need": 0.50,
                "privacy_sensitivity": 0.50,
            },
        ).copy()

    # Add a small category prior so one mapped dimension does not erase
    # the other structural considerations completely.
    fallback = CATEGORY_FALLBACK.get(candidate.get("category"), {})
    for dimension in ("action_intent", "guidance_need", "privacy_sensitivity"):
        weights[dimension] += 0.15 * fallback.get(dimension, 0.5)

    return {k: round(v, 6) for k, v in weights.items()}


def _structural_fit(dimensions: dict, item_profile: dict) -> float:
    total = sum(item_profile.values())
    if total <= 0:
        return 0.5
    score = sum(
        dimensions.get(dimension, 0.5) * weight
        for dimension, weight in item_profile.items()
    ) / total
    return score


def _actionability(candidate: dict) -> str:
    channels = candidate.get("channels", [])
    if not channels:
        return "unknown"

    found = set()
    for channel in channels:
        text = " ".join(
            str(channel.get(key) or "")
            for key in ("type", "label", "evidence")
        ).lower()
        if channel.get("url") or "portal" in text or "online" in text or "web" in text:
            found.add("direct")
        elif channel.get("email") or "email" in text or "phone" in text or "call" in text:
            found.add("guided")
        elif "post" in text or "mail" in text or "letter" in text or "writing" in text:
            found.add("manual")
        else:
            found.add("unknown")

    for level in ("direct", "guided", "manual", "unknown"):
        if level in found:
            return level
    return "unknown"


def _actionability_value(level: str) -> float:
    return {
        "direct": 1.0,
        "guided": 0.75,
        "manual": 0.45,
        "unknown": 0.25,
    }.get(level, 0.25)


def _mapping_confidence(signals: list[dict]) -> str:
    used = [s for s in signals if s["used_in_alignment"]]
    if not used:
        return "baseline"
    direct = sum(s["strength"] == "direct" for s in used)
    supporting = sum(s["strength"] == "supporting" for s in used)
    if direct >= 1 and len(used) >= 2:
        return "high"
    if direct >= 1 or supporting >= 2:
        return "medium"
    return "low"


def score_candidate(
    candidate: dict,
    persona: dict,
    survey_mapping: dict,
    config: dict | None = None,
) -> dict:
    """Calculate item-level utility for one policy-supported recommendation."""
    config = merge_config(config)
    dimensions = persona_dimensions(persona)

    alignment, signals, domain_scores = _candidate_alignment(
        candidate,
        persona,
        survey_mapping,
        config,
    )

    mapping_confidence = _mapping_confidence(signals)

    # No matched survey question, so nothing real to calculate here.
    # 0.45 is a fixed placeholder, slightly below neutral (0.5), not from data 
    if alignment is None:
        alignment_component = 0.45 
    else:
        raw_alignment = _sigmoid(alignment)
        reliability = {
            "high": 1.0,
            "medium": 0.85,
            "low": 0.55,
            "baseline": 0.0,
        }.get(mapping_confidence, 0.55)
        alignment_component = 0.5 + (raw_alignment - 0.5) * reliability

    item_profile = _item_dimension_profile(candidate, survey_mapping, config)
    structural = _structural_fit(dimensions, item_profile)
    actionability = _actionability(candidate)
    evidence_count = len(candidate.get("evidence", []))
    evidence_value = min(1.0, evidence_count / 2.0)

    uw = config["utility_weights"]
    utility_01 = (
        uw["item_alignment"] * alignment_component
        + uw["structural_fit"] * structural
        + uw["actionability"] * _actionability_value(actionability)
        + uw["policy_evidence"] * evidence_value
    )
    utility = round(100.0 * min(1.0, max(0.0, utility_01)), 2)

    return {
        **candidate,
        "utility": utility,
        "persona_relevance": alignment,
        "alignment_component": round(alignment_component, 6),
        "structural_fit": round(structural, 6),
        "persona_dimensions": dimensions,
        "item_dimension_profile": item_profile,
        "domain_scores": domain_scores,
        "survey_signals": signals,
        "mapping_confidence": mapping_confidence,
        "actionability": actionability,
        "evidence_count": evidence_count,
        "policy_support": "supported" if evidence_count else "missing_evidence",
    }


def rank_candidates(scored_candidates: list[dict]) -> list[dict]:
    return sorted(
        scored_candidates,
        key=lambda item: (
            item["utility"],
            item["mapping_confidence"] == "high",
            item["mapping_confidence"] == "medium",
            item["evidence_count"],
            item["recommendation_id"],
        ),
        reverse=True,
    )


def diversify_candidates(
    candidates: list[dict],
    config: dict | None = None,
    top_n: int = 6,
) -> list[dict]:
    config = merge_config(config)
    max_per_category = config["diversity"]["max_per_category"]
    selected = []
    counts = defaultdict(int)
    seen = set()

    for candidate in candidates:
        cid = candidate["recommendation_id"]
        category = candidate.get("category", "other")
        if cid in seen or counts[category] >= max_per_category:
            continue
        selected.append(candidate)
        seen.add(cid)
        counts[category] += 1
        if len(selected) >= top_n:
            break

    # If diversity blocked too much, fill remaining slots from the ranking.
    if len(selected) < top_n:
        for candidate in candidates:
            if candidate["recommendation_id"] in seen:
                continue
            selected.append(candidate)
            seen.add(candidate["recommendation_id"])
            if len(selected) >= top_n:
                break

    return selected


def recommend_for_persona(
    candidates: list[dict],
    persona: dict,
    survey_mapping: dict,
    config: dict | None = None,
    top_n: int = 6,
) -> dict:
    """Always return the highest-utility policy-supported recommendations."""
    scored = [
        score_candidate(candidate, persona, survey_mapping, config)
        for candidate in candidates
    ]
    ranked = rank_candidates(scored)
    recommended = diversify_candidates(ranked, config, top_n=top_n)

    return {
        "recommended": recommended,
        "all_ranked": ranked,
        "persona_dimensions": persona_dimensions(persona),
    }
