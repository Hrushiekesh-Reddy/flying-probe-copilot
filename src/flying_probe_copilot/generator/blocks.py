"""Per-panel test-block generation — scales with ``BoardProfile.component_mix``.

BUG-002 fix: the old ``cli._build_blocks`` returned a hardcoded 4-block sample
regardless of profile (every panel got the same ``shorts`` + ``R12`` + ``D1`` +
``U7``), which made small/medium/large indistinguishable in the output. This
module replaces that with ``generate_blocks(profile, outcome, seed)``, which:

* Emits exactly one ``shorts`` block first (status reflects outcome.mode).
* Emits one block per component in ``profile.component_mix`` with realistic
  refdes (``R1..R{N_R}``, ``C1..``, etc.) and record-type matching the prefix.
* Marks a *primary* failing component from a mode -> family-set map (e.g.
  ``DIGITAL`` -> ``U``, ``ANALOG_OOL`` -> R/C/L), then rolls Bernoulli
  secondary failures against refdes neighbors (±3 within the same family) via
  ``faults.correlation_multiplier``, so a failing panel typically marks a
  cluster of 1–4 adjacent components rather than just one.
* Threads every stochastic choice through ``random.Random(seed)`` so the
  output is byte-reproducible.
"""

from __future__ import annotations

from random import Random

from .faults import PanelOutcome, correlation_multiplier
from .models import (
    AnalogRecord,
    AnalogStatus,
    AnalogType,
    BlockRecord,
    BoardProfile,
    DigitalRecord,
    DigitalStatus,
    Limits2,
    Limits3,
    ShortsRecord,
    ShortsStatus,
    TestBlock,
)

# Baseline conditional secondary-failure rate. When a primary component fails,
# every other component in the same family is offered a Bernoulli draw at
# ``BASELINE_SECONDARY_RATE * correlation_multiplier(primary, candidate)`` —
# but ONLY when the multiplier exceeds 1.0 (i.e., the candidate is a ±3 refdes
# neighbor of the primary). Far candidates (multiplier == 1.0) get no draw,
# which is what makes the aggregate Pareto curve visibly clustered instead of
# diluted by uniform secondary noise across the whole family. See the
# DECISION_LOG entry "2026-06-14 — Fault correlation wired through
# generate_blocks" for the rationale.
BASELINE_SECONDARY_RATE = 0.3


# ---------------------------------------------------------------------------
# Component-type prefix -> record-type / limits prototype.
# ---------------------------------------------------------------------------


# Each analog prefix maps to: AnalogType, prototype limits, per-tolerance sigma
# (used by the passing-noise draw), and the failure-side fallback for the
# "single failing component" path. ``sigma`` is ~25% of the half-tolerance so
# the Gaussian draw stays comfortably inside [low, high] for typical samples.
_ANALOG_PROTOTYPES: dict[str, tuple[AnalogType, Limits3 | Limits2, float]] = {
    "R": (
        AnalogType.RES,
        Limits3(nominal=10000.0, high=10100.0, low=9900.0),
        25.0,  # ~25% of the 100 ohm half-tolerance
    ),
    "C": (
        AnalogType.CAP,
        Limits3(nominal=1.0e-6, high=1.05e-6, low=9.5e-7),
        1.25e-8,
    ),
    "L": (
        AnalogType.IND,
        Limits3(nominal=1.0e-5, high=1.1e-5, low=9.0e-6),
        2.5e-7,
    ),
    "D": (
        AnalogType.DIO,
        Limits2(high=0.8, low=0.5),
        0.04,  # ~25% of (0.8-0.5)/2 = 0.15
    ),
    "Q": (
        AnalogType.NPN,
        Limits2(high=200.0, low=50.0),
        18.75,  # ~25% of (200-50)/2
    ),
}


# Failure-mode -> set of component prefixes that may carry the failure. ``U``
# is digital; everything else is analog. ``SHORTS`` is handled separately
# (only the shorts block fails).
_MODE_TO_PREFIXES: dict[str, tuple[str, ...]] = {
    "ANALOG_OOL": ("R", "C", "L"),
    "OPEN": ("R", "C", "L"),
    "MISSING": ("R", "C", "L"),
    "GROSS": ("R", "C", "L"),
    "DIGITAL": ("U",),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _nominal(limits: Limits3 | Limits2) -> float:
    """Return a representative center value for the limits."""
    if isinstance(limits, Limits3):
        return limits.nominal
    return (limits.high + limits.low) / 2.0


def _passing_measured(rng: Random, limits: Limits3 | Limits2, sigma: float) -> float:
    """Draw a measured value inside ``[low, high]``.

    Uses a Gaussian centered on the nominal with ``sigma`` set so that draws
    rarely exceed the half-tolerance. If the draw lands outside the limits
    (rare), it's clamped to a safe value inside the band.
    """
    nominal = _nominal(limits)
    value = rng.gauss(nominal, sigma)
    # Clamp into the band with a small inset so floating-point comparisons are
    # comfortably inside. The inset is 1% of the tolerance band.
    span = limits.high - limits.low
    inset = span * 0.01
    if value < limits.low + inset:
        value = limits.low + inset
    elif value > limits.high - inset:
        value = limits.high - inset
    return value


def _failing_measured(rng: Random, limits: Limits3 | Limits2, sigma: float) -> float:
    """Draw a measured value just OUTSIDE ``[low, high]``.

    Picks the high or low side at random and offsets by 1-2 sigma.
    """
    span = limits.high - limits.low
    offset = max(sigma, span * 0.05) * (1.0 + rng.random())
    if rng.random() < 0.5:
        return limits.high + offset
    return max(0.0, limits.low - offset) if limits.low > 0 else limits.low - offset


def _build_analog_block(
    prefix: str,
    index: int,
    failing: bool,
    rng: Random,
) -> TestBlock:
    """Build one analog test block for a given prefix/index."""
    record_type, prototype, sigma = _ANALOG_PROTOTYPES[prefix]
    designator = f"{prefix}{index}"
    if failing:
        measured = _failing_measured(rng, prototype, sigma)
        status = AnalogStatus.FAIL
    else:
        measured = _passing_measured(rng, prototype, sigma)
        status = AnalogStatus.PASS

    # Limits objects are immutable Pydantic models — re-construct so each
    # block owns its own copy (defensive; cheap).
    if isinstance(prototype, Limits3):
        limits: Limits3 | Limits2 = Limits3(
            nominal=prototype.nominal, high=prototype.high, low=prototype.low
        )
    else:
        limits = Limits2(high=prototype.high, low=prototype.low)

    return TestBlock(
        block=BlockRecord(designator=designator, status=int(status)),
        record=AnalogRecord(
            record_type=record_type,
            status=status,
            measured=measured,
            designator=designator,
            limits=limits,
        ),
    )


def _build_digital_block(index: int, failing: bool, rng: Random) -> TestBlock:
    """Build one ``@D-T`` digital block for ``U{index}``."""
    designator = f"U{index}"
    if failing:
        status = DigitalStatus.FAIL
        substatus = 1
        # Stable pseudo-random vector/pin counts so a fixed seed reproduces.
        failing_vector = rng.randint(1, 64)
        failing_pin_count = rng.randint(1, 8)
    else:
        status = DigitalStatus.PASS
        substatus = 0
        failing_vector = 0
        failing_pin_count = 0
    return TestBlock(
        block=BlockRecord(designator=designator, status=int(status)),
        record=DigitalRecord(
            status=status,
            substatus=substatus,
            failing_vector=failing_vector,
            failing_pin_count=failing_pin_count,
            designator=designator,
        ),
    )


def _pick_correlated_failures(
    primary: tuple[str, int],
    profile: BoardProfile,
    rng: Random,
) -> set[tuple[str, int]]:
    """Return the set of secondary (prefix, idx) failures correlated to ``primary``.

    For each component in the *same family* as ``primary``, consult
    ``faults.correlation_multiplier`` and — only when it exceeds 1.0 — make a
    Bernoulli draw at ``BASELINE_SECONDARY_RATE * multiplier``. The primary
    itself is excluded from the candidate set. Candidates are iterated in
    ascending refdes index so RNG draws are deterministic under a fixed seed.

    Restricting the draw to multiplier > 1.0 (rather than applying baseline to
    every same-family component) is what makes the failure Pareto visibly
    clustered: far candidates produce no secondary noise that would dilute the
    ±3 cluster around the primary.
    """
    prefix, primary_idx = primary
    count = profile.component_mix.get(prefix, 0)
    secondaries: set[tuple[str, int]] = set()
    primary_refdes = f"{prefix}{primary_idx}"
    for idx in range(1, count + 1):
        if idx == primary_idx:
            continue
        multiplier = correlation_multiplier(primary_refdes, f"{prefix}{idx}")
        if multiplier <= 1.0:
            continue
        if rng.random() < BASELINE_SECONDARY_RATE * multiplier:
            secondaries.add((prefix, idx))
    return secondaries


def _pick_failing_component(
    outcome: PanelOutcome,
    profile: BoardProfile,
    rng: Random,
) -> tuple[str, int] | None:
    """Pick the (prefix, index) of the single failing component, or None.

    Returns None when the outcome is not a per-component failure (passes and
    SHORTS-only failures both fall into this bucket).
    """
    if not outcome.failed or outcome.mode is None:
        return None
    if outcome.mode == "SHORTS":
        return None

    prefixes = _MODE_TO_PREFIXES.get(outcome.mode)
    if not prefixes:
        return None

    # Build a weighted pool over (prefix, index) pairs so families with more
    # components are more likely to host the failure (e.g. R outweighs L).
    pool: list[tuple[str, int]] = []
    for prefix in prefixes:
        count = profile.component_mix.get(prefix, 0)
        for idx in range(1, count + 1):
            pool.append((prefix, idx))
    if not pool:
        return None
    return rng.choice(pool)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_blocks(
    profile: BoardProfile,
    outcome: PanelOutcome,
    seed: int,
) -> list[TestBlock]:
    """Generate one panel's worth of ``TestBlock``s sized by ``profile``.

    Output structure (in order):

    1. One ``ShortsRecord`` block — ``status=FAIL`` iff
       ``outcome.mode == "SHORTS"``.
    2. One block per component in ``profile.component_mix``. Iteration order
       is the insertion order of ``component_mix`` (locked by profile def);
       within each family the index runs ``1..N``.

    A primary failing component is selected per ``_MODE_TO_PREFIXES``; refdes
    neighbors of the primary (±3 within the same family) then receive Bernoulli
    secondary-failure draws via ``_pick_correlated_failures``, so a single
    failing panel typically marks a *cluster* of adjacent components as failing
    rather than just one. A SHORTS-only failure leaves every component-block
    passing.

    Reproducibility: every stochastic choice routes through
    ``random.Random(seed)``.
    """
    rng = Random(seed)

    shorts_fail = outcome.failed and outcome.mode == "SHORTS"
    blocks: list[TestBlock] = [
        TestBlock(
            block=BlockRecord(
                designator="shorts",
                status=int(ShortsStatus.FAIL if shorts_fail else ShortsStatus.PASS),
            ),
            record=ShortsRecord(
                status=ShortsStatus.FAIL if shorts_fail else ShortsStatus.PASS,
                shorts_count=(1 if shorts_fail else 0),
                opens_count=0,
                phantoms_count=0,
            ),
        )
    ]

    # Decide which (prefix, index) — if any — gets the primary failure, then
    # roll secondary correlated failures against the same family. Both draws
    # happen BEFORE iterating the mix so the per-component builder RNG state
    # is independent of the choice draws.
    primary_target = _pick_failing_component(outcome, profile, rng)
    if primary_target is None:
        failing_targets: set[tuple[str, int]] = set()
    else:
        failing_targets = {primary_target}
        failing_targets.update(_pick_correlated_failures(primary_target, profile, rng))

    # Walk the component mix in the profile's declared order. For each prefix,
    # emit count blocks with refdes prefix1..prefix{count}.
    for prefix, count in profile.component_mix.items():
        for idx in range(1, count + 1):
            is_failing = (prefix, idx) in failing_targets
            if prefix == "U":
                blocks.append(_build_digital_block(idx, is_failing, rng))
            else:
                blocks.append(_build_analog_block(prefix, idx, is_failing, rng))

    return blocks
