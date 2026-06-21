# Tombstoning

## Summary

Tombstoning occurs when a two-terminal chip component (resistor or capacitor) lifts upright
on one end during reflow, leaving the other terminal unconnected. The part resembles a
standing tombstone, hence the name.

## Symptoms

- One terminal of a chip part is open while the other is soldered.
- The affected net reads as an open in continuity testing.
- Visible lifted component standing on one end.

## Likely causes

- Uneven heating causing one pad to reflow before the other.
- Pad design imbalance or unequal copper thermal mass.
- Excess paste on one pad pulling the part upright via surface tension.

## ICT signature

The component measures as an open across its two pads because one terminal never bonded.
A flying-probe test sees infinite resistance where the part value was expected. Cross-check
against the expected component value for the refdes to distinguish tombstoning from a wrong
or missing part.

## Corrective actions

- Inspect for a physically lifted component at the failing refdes.
- Re-seat and re-flow the part with balanced heating.
- Review pad/thermal balance if the defect recurs at the same location.

## References

- Component-placement acceptance: see IPC-A-610 §8.2 by section number only.
