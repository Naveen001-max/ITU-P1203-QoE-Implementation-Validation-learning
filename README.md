# ITU-T P.1203 — QoE Implementation, Validation & Learning

> A research and development repository documenting my study, implementation work, testing, validation, debugging, and technical learning around the ITU-T P.1203 Quality of Experience (QoE) model for adaptive audiovisual streaming.

---

## About This Project

This repository is my practical study of **ITU-T Recommendation P.1203**, a parametric model designed to estimate the Quality of Experience of adaptive audiovisual streaming sessions.

The work goes beyond simply running an existing implementation. I studied the internal architecture of P.1203, investigated the mathematical algorithms behind its modules, worked specifically with the **P.1203.2 Audio Quality Estimation Module**, examined the P.1203.1 and P.1203.3 processing pipeline, built validation and error-analysis tooling, and investigated differences between generated outputs and reference results.

The project is also intended as a learning record: it documents what I understood, what I implemented, what failed during development, how I debugged it, and what the validation results showed.

---

## Project Goals

- Understand the architecture and mathematical foundations of ITU-T P.1203.
- Study the interaction between audio, video, and session-level QoE estimation.
- Work specifically with **P.1203.2 — Audio Quality Estimation**.
- Study **P.1203.1 — Video Quality Estimation**.
- Study **P.1203.3 — Quality Integration**.
- Understand P.1203 operating modes 0–3.
- Validate implementation outputs against the P.1203 reference/open dataset.
- Develop reproducible tests and validation scripts.
- Investigate numerical differences instead of treating every mismatch as an implementation bug.
- Explore integration with adaptive streaming/DASH workflows.
- Build a foundation for future research into modern audiovisual QoE models.

---

# 1. Understanding ITU-T P.1203

P.1203 estimates streaming QoE using a modular architecture:

```text
                 Adaptive Streaming Session
                           |
          +----------------+----------------+
          |                                 |
          v                                 v
   Video Quality                       Audio Quality
    P.1203.1                           P.1203.2
          |                                 |
          v                                 v
         O22                               O21
          \                                 /
           \                               /
            +-------------+---------------+
                          |
                          v
                    P.1203.3
                Quality Integration
                          |
                          v
                         O46
                   Session-level QoE
```

The model separates:

- **P.1203.1** — Video Quality Estimation Module
- **P.1203.2** — Audio Quality Estimation Module
- **P.1203.3** — Quality Integration Module

The final integration stage considers the evolution of audiovisual quality and streaming impairments such as stalling.

---

# 2. P.1203 Operating Modes

| Mode | Information level | Main idea |
|---|---|---|
| **Mode 0** | Metadata | Codec, bitrate, resolution, frame rate, segments and loading/stalling information |
| **Mode 1** | Metadata + frame information | Adds frame headers/types/sizes |
| **Mode 2** | Partial bitstream information | Adds deeper bitstream information such as QP information |
| **Mode 3** | Full bitstream | Uses full bitstream-level information |

These modes illustrate how P.1203 can estimate quality with progressively richer information about the streamed media.

---

# 3. P.1203.2 — Audio Quality Estimation

A major focus of this project was understanding and working with the audio-quality module.

The coding degradation is calculated using:

```text
QcodA = a1A × exp(a2A × Bitrate) + a3A
```

Audio quality is then:

```text
QA = 100 − QcodA
```

The resulting quality value is converted into an estimated Mean Opinion Score:

```text
O21 = MOSfromR(QA)
```

The MOS conversion used by the model is:

```text
MOS = 1.05 + (4.9 − 1.05)
      × [Q/100 + Q(Q − 60)(100 − Q)(0.000007)]
```

with the result bounded to:

```text
1.05 ≤ MOS ≤ 4.9
```

For AAC-LC, the coefficients studied in this implementation are:

```text
a1 = 100
a2 = -0.05
a3 = 14.60
```

Conceptually:

```text
Audio Codec + Bitrate
        |
        v
   Coding Quality
        |
        v
    QA (0–100)
        |
        v
   MOSfromR()
        |
        v
       O21
```

---

# 4. P.1203.1 — Video Quality Estimation

I also studied the video-quality processing chain and how the model converts video characteristics into a quality estimate.

Important concepts include:

- bitrate
- coding resolution
- display resolution
- frame rate
- quantization
- frame-size information
- I-frame/non-I-frame characteristics
- spatial upscaling
- temporal impairment

The processing eventually produces:

```text
O22 = Video Quality MOS
```

An important concept learned during this work is that the internal `quant` parameter should not automatically be interpreted as the actual codec QP in every mode. In metadata-based modes it acts as an internal quality/compression parameter derived from available stream information.

The model estimates degradation components such as:

```text
Dq = Quantization / compression degradation
Du = Upscaling degradation
Dt = Temporal degradation
```

and combines them on a common quality/degradation scale before converting the final result back to MOS.

---

# 5. Why P.1203 Converts MOS Back to Degradation

One important conceptual point investigated in this project was why the model does not simply add or subtract multiple MOS values.

MOS is nonlinear.

Therefore, the model uses a common degradation/quality representation:

```text
MOS
 ↓
RfromMOS()
 ↓
0–100 quality/degradation representation
 ↓
Combine impairments
 ↓
MOSfromR()
 ↓
Final MOS
```

For video, this allows compression, scaling, and temporal impairments to be combined consistently.

This was an important lesson in understanding why a mathematical QoE model may internally use representations that are different from its final user-facing MOS output.

---

# 6. P.1203.3 — Quality Integration

P.1203.3 combines audio and video quality into an integrated audiovisual quality representation.

The one-second audiovisual quality is calculated using:

```text
O34'_t =
clip(
    av1
    + av2 × O21_t
    + av3 × O22_t
    + av4 × O21_t × O22_t,
    1,
    5
)
```

The resulting sequence is then used for longer-term quality estimation.

The model also accounts for temporal effects and stalling.

---

# 7. Stalling and Session-Level QoE

The stalling influence is represented through:

```text
SI =
exp(−numStalls / s1)
× exp(−totalStallLength / (T × s2))
× exp(−avgStallInterval / s3)
```

and:

```text
O23 = 1 + 4 × SI
```

This is one reason P.1203 differs from video-only quality metrics: it considers playback/session experience rather than only visual quality.

---

# 8. Random Forest Component

Another important part of the study was the machine-learning component inside P.1203.3.

The model uses a **Random Forest consisting of 20 decision trees**, with the tree predictions averaged to obtain the RF prediction.

Conceptually:

```text
Session Features
      |
      v
+-----+-----+-----+-----+
| Tree 1    | ... | Tree 20
+-----+-----+-----+-----+
      |
      v
Average predictions
      |
      v
RFprediction
```

The RF prediction is combined with the analytical/session-quality component:

```text
O46_temp =
    0.75 × [1 + (O35 − 1) × SI]
    + 0.25 × RFprediction
```

This demonstrated how a standardized QoE model can combine **analytical equations with a supervised machine-learning ensemble**.

---

# 9. O46 Final Linearization

A significant part of the validation investigation concerned the final O46 calculation.

The final calibration is:

```text
O46 =
0.02833052
+
0.98117059 × O46_temp
```

Therefore:

```text
O21 ───────────────┐
                   |
O22 ───────────────┤
                   v
              O34 / O35
                   |
                   +------> Stalling information
                   |
                   +------> Random Forest
                   |
                   v
               O46_temp
                   |
                   v
              Final Eq. 30
                   |
                   v
                  O46
```

A key learning outcome was that **the final linearization is not the same thing as the 75/25 analytical/RF weighting**.

The 75/25 weighting produces `O46_temp`.

Equation 30 performs the final linear calibration.

---

# 10. Validation Work

A major part of the project was validating the implementation against the P.1203 reference/open dataset.

The validation covered:

```text
4 modes × 314 cases
=
1,256 validation cases
```

All cases were successfully processed:

```text
1,256 / 1,256
```

The validation framework compares generated outputs with corresponding reference outputs and calculates numerical error metrics.

---

# 11. Validation Results

| Metric | Result |
|---|---:|
| Total cases | **1,256** |
| Successfully processed | **1,256 / 1,256** |
| O34 reference agreement | **Exact** |
| O35 reference agreement | **Exact** |
| O23 MAE | **≈ 0.0079** |
| O46 MAE | **≈ 0.036–0.042**, depending on mode |

O34 and O35 matching the reference outputs provided strong evidence that the core integration stages were functioning consistently with the reference cases.

O23 also showed a small mean absolute error.

O46 showed a larger but still relatively small systematic residual.

---

# 12. O46 Error Investigation

Instead of treating the O46 difference as an unexplained error, I investigated the calculation path and implementation/reference version relationship.

The investigation showed that the reference outputs were associated with an earlier P.1203 implementation/reference version, while the current implementation includes the later final linearization represented by Equation 30.

This explains why O46 results can differ even when the preceding processing stages are consistent.

The main lesson was:

> A numerical mismatch does not automatically mean that the implementation is fundamentally wrong. Version differences, calibration changes, and reference-generation procedures must also be considered.

---

# 13. Testing and Development

The project includes additional tests and experiments around the P.1203 implementation.

Examples include:

```text
p1203_core_tests/
test_p1203_2_real.py
```

and example inputs such as:

```text
examples/constant_aaclc_128.json
examples/p1203_2_20sec.json
```

I also used command-line execution and example sessions to inspect model outputs and verify individual processing stages.

---

# 14. DASH Integration Experiments

The project also contains exploratory work around adaptive streaming and DASH:

```text
dash_integration/
dash_player/
```

The purpose is to connect the QoE model with a more realistic adaptive-streaming workflow rather than treating the model only as an isolated mathematical implementation.

---

# 15. Technical Learning

### QoE Modelling

- Difference between Quality of Experience and raw media quality.
- Why audiovisual QoE needs more than a video-quality score.
- How temporal playback events influence perceived experience.
- Why session-level QoE differs from frame-level/video-level quality.

### Audio Quality

- Codec-specific quality estimation.
- Bitrate-dependent quality degradation.
- Nonlinear MOS conversion.
- P.1203.2 processing flow.

### Video Quality

- Bitrate, resolution and frame-rate relationships.
- Quantization-related quality estimation.
- Spatial scaling impairment.
- Temporal impairment modelling.
- Mode-dependent video information.

### Machine Learning

- Random Forest regression inside a standardized QoE model.
- Feature-based prediction.
- Ensemble averaging.
- Combining ML predictions with analytical equations.

### Software Engineering

- Python virtual environments.
- Dependency management.
- Unit and integration testing.
- CLI-based execution.
- Debugging numerical discrepancies.
- Building validation scripts.
- Organizing reproducible experiments.

### Research Methodology

- Working from a technical standard.
- Translating mathematical specifications into executable logic.
- Comparing implementation outputs with reference outputs.
- Using MAE and other numerical error measures.
- Investigating systematic residuals.
- Distinguishing implementation defects from version/calibration differences.
- Documenting limitations instead of overclaiming results.

---

# 16. What This Project Taught Me About Model Validation

A central lesson from this project is that validation is not simply:

```text
Run model
   ↓
Compare number
   ↓
Different → bug
```

A stronger validation workflow is:

```text
Reference Specification
        ↓
Implementation
        ↓
Controlled Test Cases
        ↓
Reference Outputs
        ↓
Numerical Comparison
        ↓
Error Pattern Analysis
        ↓
Version / Formula / Parameter Investigation
        ↓
Technical Conclusion
```

This approach was particularly important for understanding the O46 residual.

---

# 17. Current Research Direction

The project began primarily as an implementation and learning exercise around P.1203 and is now developing toward a broader QoE research direction.

Areas being investigated include:

- Modern streaming video-quality models.
- ITU-T P.1204 family.
- Netflix VMAF and related video-quality tooling.
- Modern audiovisual/session-level QoE modelling.
- Comparison between standardized QoE approaches and industry video-quality tools.
- Potential integration of newer video-quality estimators into a session-level QoE architecture.

The objective is not simply to replace P.1203, but to understand how modern video-quality technologies can coexist with or extend session-level audiovisual QoE estimation.

---

# 18. Limitations

This repository should be interpreted as a research, learning and implementation project.

Important limitations include:

- Reference datasets and implementation versions may not always correspond to the latest specification revision.
- O46 comparisons can be affected by reference-version/calibration differences.
- Numerical agreement on one validation dataset does not by itself prove universal real-world accuracy.
- P.1203 is a parametric model with a defined scope and assumptions.
- Modern streaming systems can introduce codecs, protocols, devices and perceptual effects beyond the original model's design scope.

---

# 19. Future Work

### External Validation

Evaluate P.1203 against independent publicly available audiovisual QoE datasets containing appropriate streaming/session information.

### Modern Video-Quality Comparison

Compare P.1203 video-quality outputs with:

- ITU-T P.1204 family models
- Netflix VMAF
- SSIM / MS-SSIM
- PSNR
- selected modern learned VQA models

### Session-Level Research

Investigate whether a modern session QoE framework can combine:

```text
Audio Quality
      +
Modern Video Quality
      +
Startup Delay
      +
Rebuffering
      +
Quality Switching
      +
Session Context
      ↓
Modern Session QoE
```

### Reproducible Evaluation

Build a standardized evaluation pipeline producing:

- MSE
- RMSE
- MAE
- correlation metrics
- QoE/MOS comparisons
- per-case error
- per-mode analysis
- visualizations
- reproducible result files

---

# 20. Repository Structure

```text
ITU-P1203-QoE-Implementation-Validation-learning/
│
├── itu_p1203/
│   └── P.1203 implementation
│
├── examples/
│   └── reproducible example inputs
│
├── p1203_core_tests/
│   └── core tests
│
├── validation/
│   └── validation resources and results
│
├── dash_integration/
│   └── DASH integration experiments
│
├── dash_player/
│   └── DASH player experiments
│
├── test_p1203_2_real.py
│   └── P.1203.2 testing
│
├── validate_p1203_dataset.py
│   └── reference dataset validation
│
├── o46_error_analysis.py
│   └── O46 numerical/error investigation
│
├── pyproject.toml
├── README.md
└── LICENSE
```

Large datasets, raw media assets, virtual environments and generated files should not be committed unnecessarily.

---

# 21. Reproducibility

The project is intended to be reproducible through the included Python environment configuration, examples and validation scripts.

Typical setup:

```bash
git clone <repository-url>
cd ITU-P1203-QoE-Implementation-Validation-learning

python -m venv .venv
```

Activate the environment and install dependencies according to the project configuration.

Validation can then be performed using the included validation tooling.

---

# 22. Relationship to the Original P.1203 Implementation

This repository is based on the official **ITU-T P.1203 reference implementation**.

The original implementation and its associated work remain attributed to their respective authors and contributors.

This repository documents my own:

- study
- implementation work
- testing
- validation
- experiments
- debugging
- error analysis
- technical interpretation
- research direction

The purpose is to learn from, evaluate, and build around the P.1203 implementation—not to claim authorship of the original standard or upstream implementation.

---

# 23. References

### ITU-T

- ITU-T Recommendation P.1203 — Parametric bitstream-based quality assessment of progressive download and adaptive audiovisual streaming services.
- ITU-T Recommendation P.1203.1 — Video Quality Estimation Module.
- ITU-T Recommendation P.1203.2 — Audio Quality Estimation Module.
- ITU-T Recommendation P.1203.3 — Quality Integration Module.
- ITU-T Recommendation P.1204 family — Streaming video quality assessment.

### Upstream Implementation

Official P.1203 implementation:

```text
https://github.com/itu-p1203/itu-p1203
```

### Validation Dataset

Official P.1203 open dataset:

```text
https://github.com/itu-p1203/open-dataset
```

### Industry Video Quality

Netflix VMAF:

```text
https://github.com/Netflix/vmaf
```

---

# 24. Acknowledgements

This work builds upon the ITU-T P.1203 recommendation, its contributors, and the publicly available P.1203 implementation and validation resources.

The project is maintained as a personal research and learning repository documenting my technical work with audiovisual QoE modelling.

---

## Project Status

**Active Research & Development**

Current work includes:

- P.1203 architecture study
- P.1203.1 investigation
- P.1203.2 implementation/testing
- P.1203.3 investigation
- Reference-dataset validation
- 1,256-case validation run
- O46 error analysis
- DASH integration experiments
- Research into newer audiovisual/video QoE approaches

Further work will focus on independent validation and comparison with modern QoE/video-quality technologies.
