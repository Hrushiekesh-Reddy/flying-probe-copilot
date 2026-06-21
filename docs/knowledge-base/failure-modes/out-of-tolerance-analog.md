# Out-of-Tolerance Analog Value

## Summary

An out-of-tolerance analog failure occurs when a passive component measures outside its
allowed limits. The part is present and connected, but its value (resistance, capacitance,
inductance) falls beyond the test window.

## Symptoms

- Measured value exceeds the upper or lower tolerance limit for the refdes.
- Slow drift of a value across panels or shifts.
- Functional behaviour degraded but not dead.

## Likely causes

- Wrong value part loaded (mis-kitted reel).
- Damaged or degraded component (overstressed, moisture, heat).
- Measurement affected by parallel paths or in-circuit loading.

## ICT signature

The flying-probe in-circuit measurement returns a value that is outside the configured
low/high limits for the test. Distinguish a genuine wrong-value part from in-circuit
loading by checking whether the deviation is consistent across panels and whether guarding
was applied. A systematic one-directional drift suggests process drift rather than a single
bad part.

## Corrective actions

- Confirm the loaded part value against the bill of materials.
- Re-measure with proper guarding to remove parallel-path error.
- If drift is systematic, investigate the upstream source (reel, supplier lot).

## References

- Measurement and acceptance limits are defined per test program; document the limit set
  used, not standards text.
