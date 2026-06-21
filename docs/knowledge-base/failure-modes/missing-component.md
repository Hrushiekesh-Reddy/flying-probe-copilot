# Missing Component

## Summary

A missing component is a part that the bill of materials requires but that is absent from
the assembled board. The footprint is bare, so the expected electrical behaviour at that
location is gone.

## Symptoms

- Open or wrong value at a refdes that should hold a part.
- Bare pads visible at the location during inspection.
- Functional test fails for the circuit that depended on the part.

## Likely causes

- Feeder ran empty or skipped during placement.
- Part knocked off before or during reflow.
- Mis-kitted assembly missing the reel entirely.

## ICT signature

For a passive, a missing part reads as an open (infinite resistance) across its pads — the
same electrical signature as an open joint. Disambiguate by inspecting the footprint:
bare pads indicate a missing component, whereas a present-but-unsoldered lead indicates an
open joint. Cross-reference the expected component value for the refdes.

## Corrective actions

- Inspect the failing refdes footprint for a physically absent part.
- Place and solder the correct component from the BOM.
- Check the feeder and kitting if multiple boards share the same gap.

## References

- Presence / placement acceptance: see IPC-A-610 §8.2 by section number only.
