# RC8.2 — rollback of aligned STEP restart

User requested reverting the STEP round-trip experiment after RC8.1 CAD failures. Current build no longer installs aligned_step_restart.py or its CLI patch, and no longer runs restart-specific tests against the reverted behavior. It builds the original RC7 in-memory comparison with the parametric proof patch and isolated Common safeguard retained. The original regression suite includes the assertion that verified aligned pairs are reused rather than independently compared after a round-trip. Additional build assertions reject the restart call sites and require certified-pair reuse.

No history is rewritten. RC8/RC8.1 experimental scripts and results remain for reproducibility; they are not installed into RC8.2. Previous downloadable RC8.1 binaries remain experimental, not superseded in place.

This rollback removes temporary STEP serialization, reimport, metadata reconstruction and certificate invalidation from the comparison path. It does not by itself fix all residual geometric failures. Windows regression/build and six CAD scenarios are scheduled by the workflow, with unchanged operation and analysis timeouts.

Proposed next algorithm: original-frame matching first; spatial/geometric voting for one global translation; representative independent B-Rep verification with ambiguous cases rejected; apply transform once in memory; retain valid world/definition proofs in that same frame; finish only unmatched pairs. Diagnose Trident pair 178/178 independently before changing Boolean behavior. No timeout or failed proof may count as identical geometry.
