# Open Circuit

## Summary

An open is a missing electrical connection where the design expects continuity. The net
is electrically broken, so signal or supply does not reach the downstream pin.

## Symptoms

- Continuity test fails between two nodes that should be joined.
- Downstream digital logic reads a floating or stuck value.
- Functional test reports a dead section of the board.

## Likely causes

- Lifted lead or unsoldered pin on a fine-pitch component.
- Hairline crack in a trace or via barrel.
- Cold or starved joint that opened under thermal cycling.
- Connector not fully seated during assembly.

## ICT signature

On a flying-probe or in-circuit test, an open shows as a very high or infinite resistance
across the expected net. Probe the two endpoints directly; a true open reads near the
instrument's maximum range while a good net reads near zero ohms.

## Corrective actions

- Re-probe both endpoints to rule out a probe-contact issue.
- Inspect the suspect joint and trace under magnification.
- Re-flow or hand-solder the lifted lead; repair the trace if cracked.

## References

- General workmanship acceptance: see IPC-A-610 §8 (soldering) by section number only.
