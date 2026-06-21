# Short Circuit (Solder Bridge)

## Summary

A short is an unintended low-resistance connection between two nets that should be
isolated. The most common cause on assembled boards is a solder bridge spanning adjacent
pads or pins.

## Symptoms

- Continuity test passes between two nets that should be isolated.
- Supply rail collapses or draws excess current.
- Adjacent signals track each other instead of switching independently.

## Likely causes

- Excess solder bridging fine-pitch leads or adjacent pads.
- Stray solder ball lodged between conductors.
- Conductive contamination or debris across a gap.

## ICT signature

A short reads near zero ohms between nets that the netlist marks as separate. On a
flying-probe test, probe the two suspect nets directly; an unexpected low resistance
confirms the bridge. Current-limited supply tests may also flag the over-current draw.

## Corrective actions

- Locate the bridge under magnification along the failing net pair.
- Remove excess solder with wick or a fine iron; clear any solder balls.
- Re-test continuity between the affected nets after rework.

## References

- Bridging / excess-solder acceptance: see IPC-A-610 §8.3 by section number only.
