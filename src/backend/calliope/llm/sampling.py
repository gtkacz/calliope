from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from calliope.domain.enums import CanonPolicy

# Grounded policies need low variance to stay on-source; creative allows more
# temperature to produce richer prose without contradicting canon.
TEMP_STRICT_CANON: float = 0.2
TEMP_CANON_PLUS_INFERENCE: float = 0.35
TEMP_CREATIVE_BUT_CONSISTENT: float = 0.65

_POLICY_TEMPS: dict[CanonPolicy, float] = {
    CanonPolicy.STRICT_CANON: TEMP_STRICT_CANON,
    CanonPolicy.CANON_PLUS_INFERENCE: TEMP_CANON_PLUS_INFERENCE,
    CanonPolicy.CREATIVE_BUT_CONSISTENT: TEMP_CREATIVE_BUT_CONSISTENT,
}

# min_p 0.05 cuts the probability tail without over-constraining creative policies.
MIN_P_DEFAULT: float = 0.05
# Light repetition penalty to prevent verbatim repetition of source passages.
REPETITION_PENALTY_DEFAULT: float = 1.1

# Conservative nucleus; reduces hallucinated long-tails on commercial APIs.
TOP_P_DEFAULT: float = 0.9
# Light de-duplication pressure without suppressing valid repetition of canon terms.
FREQUENCY_PENALTY_DEFAULT: float = 0.25


@dataclass(frozen=True)
class SamplingParams:
    temperature: float
    # Exactly one of (min_p / top_p+frequency_penalty) is populated, depending on
    # prefer_min_p. The other fields are None so callers can pass the struct directly
    # without branching on the backend type.
    min_p: float | None
    top_p: float | None
    repetition_penalty: float | None
    frequency_penalty: float | None


def resolve_sampling_params(
    policy: CanonPolicy,
    *,
    prefer_min_p: bool,
    sampling_override: dict[str, Any] | None,
) -> SamplingParams:
    """Merge policy defaults with per-profile overrides.

    Merge order: policy defaults <- sampling_override wins field-by-field.
    The override is a free-form dict so operators can tune any field without
    changing the schema; unknown keys are silently ignored to prevent 400s on
    forward-compatibility."""
    base_temp = _POLICY_TEMPS[policy]

    if prefer_min_p:
        base: dict[str, Any] = {
            "temperature": base_temp,
            "min_p": MIN_P_DEFAULT,
            "top_p": None,
            "repetition_penalty": REPETITION_PENALTY_DEFAULT,
            "frequency_penalty": None,
        }
    else:
        base = {
            "temperature": base_temp,
            "min_p": None,
            "top_p": TOP_P_DEFAULT,
            "repetition_penalty": None,
            "frequency_penalty": FREQUENCY_PENALTY_DEFAULT,
        }

    if sampling_override:
        for key in (
            "temperature",
            "min_p",
            "top_p",
            "repetition_penalty",
            "frequency_penalty",
        ):
            if key in sampling_override:
                base[key] = sampling_override[key]

    # Re-enforce the profile's backend-type invariant after applying overrides:
    # an operator-supplied override must not smuggle commercial-only params onto a
    # local profile (or vice versa), which would cause the downstream API to reject
    # the request or produce unexpected behaviour.
    if prefer_min_p:
        base["top_p"] = None
        base["frequency_penalty"] = None
    else:
        base["min_p"] = None
        base["repetition_penalty"] = None

    return SamplingParams(
        temperature=base["temperature"],
        min_p=base["min_p"],
        top_p=base["top_p"],
        repetition_penalty=base["repetition_penalty"],
        frequency_penalty=base["frequency_penalty"],
    )
