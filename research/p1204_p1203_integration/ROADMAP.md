# P.1204 Video Model + P.1203 Session QoE Research Roadmap

**Status:** Planning / repository audit  
**Started:** 2026-10-14  
**Primary dataset candidate:** LFOVIA Video QoE Database  
**Tracking issue:** https://github.com/Naveen001-max/ITU-P1203-QoE-Implementation-Validation-learning/issues/1

## Research objective

Evaluate a carefully selected ITU-T P.1204-family video-quality estimator as a replacement for the P.1203.1 video estimator, while retaining compatible P.1203 audio and session-level integration. Compare video-only MOS and integrated session QoE against appropriate ground truth. Investigate and reduce prediction errors using leakage-safe development/test protocols.

Do not describe a dataset as never evaluated before unless model-development history and publications support that conclusion.

## Checkpoints and acceptance criteria

- [ ] **C0 — Baseline frozen.** Record repository commit, Python/dependency environment, test commands and outputs. Preserve original P.1203 results.
- [ ] **C1 — Dataset audit.** Download/access the LFOVIA README and QoE MAT files where permitted. Inspect fields, temporal alignment, subjective scoring procedure, overall QoE, video files, and explicit QoS measurements. Dataset page currently confirms continuous subjective QoE and overall QoE for 54 videos; QoS labels remain unverified. See https://people.iith.ac.in/lfovia/downloads.html.
- [ ] **C2 — P.1204 selection.** Compare P.1204.1/.2/.3/.4/.5 edition, inputs available in LFOVIA, implementation maturity, input scope and license. Candidate P.1204.3 repository: https://github.com/Telecommunication-Telemedia-Assessment/bitstream_mode3_p1204_3. Check current recommendation edition and implementation compatibility before committing to a variant.
- [ ] **C3 — Adapter design.** Map P.1204 outputs to the per-second O22 sequence expected by P.1203. Define temporal aggregation, missing samples, stream duration, scale, device assumptions, and stalling alignment.
- [ ] **C4 — Separate implementation.** Implement the adapter in an isolated research module. Use P1203Standalone's injectable Pv class interface if feasible. Do not edit the original P.1203 model until license and regression strategy are clear.
- [ ] **C5 — Synthetic/regression tests.** Verify output shape and range, timestamps, deterministic runs, mismatched durations, missing data, and unaffected P.1203 baseline behavior.
- [ ] **C6 — Independence audit.** Trace published training and validation data for every selected model against candidate datasets. Record overlap and qualify the independence claim accordingly.
- [ ] **C7 — Evaluation.** Report P.1204 video MOS against video-level subjective ground truth separately from integrated P.1203/P.1204 O46 against session-level ground truth. Calculate MAE, RMSE, bias, PLCC, SROCC and confidence intervals where appropriate. Compare against original P.1203 baseline using equivalent inputs/splits.
- [ ] **C8 — Error analysis.** Break down error by bitrate/resolution/adaptation/stalls/content/device where metadata permits. Develop fixes on training/development data only and retain an untouched test set.
- [ ] **C9 — Research package.** Freeze code/configuration/version manifests, dataset access instructions, result tables/CSVs, plots, reproducible commands, limitations, citations, and report.

## Metric definitions

- MAE: mean absolute difference between prediction and ground truth.
- RMSE: square root of mean squared difference; highlights large errors.
- Bias: mean(prediction − ground truth), showing systematic over/under-prediction.
- PLCC: Pearson linear correlation.
- SROCC: Spearman rank correlation.

Do not compare video MOS to session QoE labels as if they were identical targets. QoS means measurable delivery/service properties (e.g. bitrate, rebuffering, throughput, delay); QoE describes user-perceived experience. Only calculate QoS prediction metrics if the dataset supplies independent QoS ground-truth measurements and the proposed model actually predicts those metrics.

## Repository findings from initial read-only audit

- Video module: `itu_p1203/p1203Pv.py` produces `O22`.
- Audio module: `itu_p1203/p1203Pa.py` produces `O21`.
- Session integration: `itu_p1203/p1203Pq.py` consumes `O21`, `O22`, and stalling information; calculates integrated outputs including `O46`.
- Session runner: `itu_p1203/p1203_standalone.py` supports injected `Pv` class, which may provide a clean extension path.
- Existing repository validation artifacts report 314 cases per mode across 4 modes (1,256 mode-cases). Those are prior reference-validation claims/artifacts, not evidence of an LFOVIA external evaluation.
- The current source includes restrictive inherited P.1203 research-use wording. Confirm rights and derivative distribution constraints before sharing integrated source.
- Project dependencies include NumPy >= 2.0; evaluate compatibility carefully for the selected P.1204 implementation and parser.

## Current state

C0: Partial — repository and outputs inspected, but local clean-environment baseline has not been executed in this session.  
C1: Partial — LFOVIA official page inspected; data archives, README and MAT fields are not yet inspected.  
C2–C9: Not started.

## Evidence / references

- LFOVIA downloads: https://people.iith.ac.in/lfovia/downloads.html
- ITU-T P.1204 (2025 edition): https://www.itu.int/rec/T-REC-P.1204/en
- P.1204.3 reference implementation: https://github.com/Telecommunication-Telemedia-Assessment/bitstream_mode3_p1204_3
- P.1203/P.1204 models repository: https://github.com/Telecommunication-Telemedia-Assessment/bitstream_based_models
