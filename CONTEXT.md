# Session Handoff - 2026-09-08

## Accomplished This Session
- Continuous collection and onboarding opt-out are merged in Runmeter PRs 8 and 9; Cockpit PR 25 and RCM PR 7 are merged.
- Runmeter pricing support is merged in PR 10 at 495e6129019458b5a3e342c91913ffd6743879ed. All 28 tests passed on Python 3.10 through 3.13.
- Installed eight verified private model rates and updated the native collector pin.
- Independently recalculated 25797 priced imported rows and verified exact agreement with the live Cockpit aggregate.
- Corrected Mac SSH source-address selection for the existing coon-noc profile. Latest native scheduled delivery exited 0; interval remains 900 seconds.
- Saved private local pricing sources, validation, backups, and PRICING.md under Library/Application Support/Aptica/runmeter/host.

## In Progress - Pick Up Here
None for pricing or aggregate delivery. Optional operations documentation transfer remains unperformed.

## Decisions Made
- Rates and operational data remain private; reusable pricing mechanics live in public Runmeter.
- Current standard-rate API-equivalent valuation is not historical billed spend or subscription charges.
- Unknown model aliases and unsupported cache-write semantics remain unpriced.
- Raw transcripts and databases remain on the Mac; only allowlisted usage aggregates cross SSH.

## Open Blockers
Automatic approval review rejected copying the private operations runbook to coon-noc because the specific infrastructure payload and destination were not explicitly authorized. Do not retry or use another transport without resolving that approval. This does not block live pricing.

## Next Step
> Recheck Sol promotional rates by 2026-11-21 and preserve explicit Unpriced values for unsupported model aliases.
