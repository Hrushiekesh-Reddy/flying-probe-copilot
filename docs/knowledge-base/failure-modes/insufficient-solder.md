# Insufficient Solder

## Summary

Insufficient solder leaves too little fillet to form a reliable joint. The connection may
be electrically marginal at test and prone to early field failure as the small joint
fatigues.

## Symptoms

- Marginal or intermittent continuity at the affected pin.
- Small, concave, or incomplete fillet on inspection.
- Joint resistance slightly elevated versus neighbouring joints.

## Likely causes

- Too little solder paste deposited (clogged or worn stencil aperture).
- Poor wetting from oxidized surfaces or weak flux activity.
- Misregistered stencil print starving one pad.

## ICT signature

A starved joint may still conduct, so it can pass continuity yet show a slightly higher
series resistance than a healthy joint. Trend the per-pad resistance across panels; a
creeping increase at one refdes points to a stencil or paste-volume problem upstream.

## Corrective actions

- Add solder and reform the fillet at the affected joint.
- Inspect and clean the stencil aperture; verify paste volume.
- Monitor the refdes on subsequent panels for recurrence.

## References

- Minimum fillet / solder-quantity acceptance: see IPC-A-610 §8.3 by section number only.
