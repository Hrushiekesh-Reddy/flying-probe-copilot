# Component Misorientation

## Summary

Misorientation means a polarized or keyed component is placed in the wrong rotation or
reversed polarity. The part may be soldered well yet behave incorrectly because its pins
map to the wrong nets.

## Symptoms

- Polarized part (diode, electrolytic capacitor, IC) installed backwards or rotated.
- Functional test fails even though joints look sound.
- Reverse-biased junction or swapped pin functions.

## Likely causes

- Reel loaded with the wrong rotation in the feeder.
- Placement program offset or mirrored footprint.
- Operator hand-placement error during rework.

## ICT signature

A reversed diode or electrolytic shows the opposite junction polarity on a flying-probe
diode or polarity test. The measured forward/reverse behaviour is flipped relative to the
expected orientation for that refdes, while basic continuity may still pass.

## Corrective actions

- Confirm the pin-1 / polarity marker against the assembly drawing.
- Remove and re-place the part in the correct orientation.
- Verify feeder rotation and placement program if the defect repeats.

## References

- Orientation / polarity acceptance: see IPC-A-610 §8.2 by section number only.
