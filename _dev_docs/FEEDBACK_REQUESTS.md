# ARVO2.0 Feedback & Advice Requests

**Date**: October 20, 2025  
**Status**: v2.2.0 PoC complete (n=2), seeking guidance before 100+ project evaluation

---

## 🎯 Current Status

**Achieved**:
- ✅ 2/2 high-complexity projects (curl, ImageMagick) built successfully
- ✅ Average 12 LLM turns, $0.03 per build
- ✅ v2.2.0 implementation ready

**Next Phase**:
- 📋 Evaluate on 100+ ARVO failed projects
- 📋 Target: 85%+ success rate
- 📋 Integrate into ARVO dataset pipeline

---

## 🤔 Areas Seeking Feedback

### 1. **Evaluation Strategy & Project Selection**

**Current plan**: Test on 100+ projects from ARVO's 36.7% failure set (~1,850 projects)

**Questions**:
- **Sample selection criteria**: Should we:
  - a) Random sampling (unbiased but may miss edge cases)
  - b) Stratified by build system (Autoconf/CMake/Make proportional to ARVO distribution)
  - c) Difficulty-based (start with simple → complex to measure ceiling)
  - d) Failure-reason-based (dependency issues vs. config issues vs. build script problems)

- **Sample size justification**: 
  - Is 100 projects sufficient for statistical significance?
  - Should we aim for larger n (200+) for publication-grade confidence?
  - How to handle computational cost (~$3-4 for 100 builds)?

- **Success criteria**:
  - Is 85% target realistic? (Repo2Run achieved 86% on Python, but C/C++ is harder)
  - Should we define tiered success (build-only vs. build+test vs. build+patch)?

**Specific feedback needed**:
> "Given Repo2Run's 86% on Python and our 2/2 PoC, is targeting 85% for C/C++ reasonable or overly optimistic?"

---

### 2. **Research Novelty vs. Engineering Application**

**Current framing**: "Extension of Repo2Run to C/C++"

**Questions**:
- **Is this sufficient research contribution for a course project / paper?**
  - Repo2Run already demonstrated dual-environment + rollback
  - ARVO2.0 adds domain adaptations (runtest.py, batching, prompts)
  - Is this "engineering application" or "novel research"?

- **How to strengthen novelty claim**:
  - a) Emphasize **error-driven dependency inference** as new technique (vs. deterministic pipreqs)
  - b) Present **multi-build-system fallback** as LLM reasoning contribution
  - c) Frame as **cross-domain generalization study** (Python → C/C++)
  - d) Add ablation study showing each component's necessity

**Specific feedback needed**:
> "Does this feel like 'applying existing tool to new domain' or 'demonstrating LLM capabilities in a harder setting'? How to frame contributions?"

---

### 3. **Technical Risks & Limitations**

**Identified risks**:

**a) Scalability**:
- Current: 2 projects, manually monitored
- Target: 100+ projects, automated pipeline
- **Risk**: Timeout handling, disk space (build artifacts), Docker image bloat
- **Mitigation plan**: 2-hour timeout (already implemented), periodic cleanup, monitor `/dev/vdb` usage
- **Question**: What else should we prepare for at scale?

**b) Cost explosion**:
- Current: ~$0.03 per simple build, up to $0.10 for complex (curl: 17 turns)
- 100 projects × $0.05 avg = **$5** (manageable)
- **Risk**: If many projects fail like curl (17 turns), cost could hit $10-15
- **Question**: Is there a cost ceiling we should set? Should we implement early stopping?

**c) Generalization failures**:
- Current PoC: 2 Autoconf/CMake projects
- Untested: Meson, SCons, Bazel, custom build scripts, header-only libraries
- **Risk**: Success rate drops sharply on non-standard build systems
- **Question**: Should we preemptively add Meson/Bazel handling? Or evaluate first, then fix?

**d) False positives**:
- Current verification: `runtest.py` checks for `*.o` and `*.so` files
- **Risk**: Build produces artifacts but they're broken/incomplete
- **Question**: Should we add deeper verification (e.g., try linking test executable, run basic sanity checks)?

**Specific feedback needed**:
> "Given n=2 PoC, what are the biggest risks you see in scaling to 100+? Which should we address *before* evaluation vs. *during* iteration?"

---

### 4. **Baseline Comparison & Evaluation Design**

**Current baseline**: ARVO's template-based approach (63.3% success)

**Questions**:
- **Is ARVO the right baseline?**
  - Alternative: Compare against manual expert debugging time?
  - Alternative: Compare against Repo2Run (but it doesn't support C/C++)
  - Alternative: Ablation vs. ARVO2.0 without C/C++ adaptations?

- **Ablation study design**:
  ```
  Full ARVO2.0:      runtest.py + batching + prompts + multi-build
  - runtest.py:      Use pytest approach (expect failures)
  - batching:        Install packages one-by-one (expect more turns)
  - prompts:         Use generic prompts (expect confusion)
  - multi-build:     Try only one build system (expect failures)
  ```
  **Question**: Is this ablation design sound? Any component we should add/remove?

- **What to measure**:
  - ✅ Success rate (primary metric)
  - ✅ Turn count (efficiency)
  - ✅ Cost per build (economics)
  - ❓ Time to first success (convergence speed)?
  - ❓ Robustness (success rate on retry)?
  - ❓ Dockerfile quality (verified builds in clean env)?

**Specific feedback needed**:
> "What would make this evaluation convincing? Are we missing critical metrics or comparison points?"

---

### 5. **Long-Term Viability & Maintenance**

**Current approach**: GPT-4o API calls (~$0.04 per build)

**Questions**:
- **Cost sustainability**:
  - 1,850 ARVO failures × $0.04 = **$74** one-time
  - But ARVO updates continuously (new CVEs weekly)
  - **Question**: Is API cost sustainable long-term? Should we evaluate local LLMs (Llama 3.1 70B)?

- **Prompt drift**:
  - GPT-4o might change behavior in future API versions
  - **Question**: Should we version-lock (`gpt-4o-2024-05-13`) or test periodically?

- **ARVO integration**:
  - ARVO pipeline is mature, adding LLM step is non-trivial
  - **Question**: Should we propose as optional enhancement or core replacement?

**Specific feedback needed**:
> "For ARVO integration, should this be positioned as (a) research prototype, (b) production-ready tool, or (c) hybrid (research now, production later)?"

---

### 6. **Research Narrative & Positioning**

**Current framing**: "Extending Repo2Run to C/C++"

**Alternative framings**:
- **Frame A**: "Demonstrating LLM generalization from easy (Python) to hard (C/C++) domains"
- **Frame B**: "Unlocking 1,850 vulnerabilities via automated build synthesis"
- **Frame C**: "Domain-specific adaptations for LLM-based build automation"
- **Frame D**: "Towards automated vulnerability reproduction at scale"

**Questions**:
- Which framing resonates better for:
  - a) Course project submission (academic rigor vs. practical impact)?
  - b) Research paper (if we pursue publication)?
  - c) ARVO team (convincing them to integrate)?

- **Contribution claims**:
  - Primary: "First LLM-based build automation for C/C++ vulnerability reproduction"
  - Secondary: "Novel techniques: compilation-first verification, error-driven inference, multi-system fallback"
  - **Question**: Are these claims defensible? Too weak? Too strong?

**Specific feedback needed**:
> "How should we position this work? As incremental improvement, significant extension, or new research direction?"

---

### 7. **Immediate Next Steps (Pre-Evaluation)**

**What we should do BEFORE running 100+ project evaluation**:

**Option A: Conservative (minimize risk)**
1. Test 10 medium-complexity projects first
2. Analyze failure modes
3. Fix critical bugs
4. Then scale to 100+

**Option B: Ambitious (fast iteration)**
1. Run all 100+ immediately
2. Analyze failures in batch
3. Implement fixes
4. Re-run failed subset

**Option C: Systematic (scientific rigor)**
1. Manually categorize ARVO's 1,850 failures by build system/failure reason
2. Design stratified sample (20 Autoconf, 20 CMake, 20 Make, 20 custom, 20 mixed)
3. Run evaluation with controls
4. Report per-category success rates

**Specific feedback needed**:
> "Which approach balances scientific rigor with practical constraints? Is there a better alternative?"

---

## 📋 Summary: Top 5 Feedback Requests

| Priority | Topic | Key Question |
|----------|-------|--------------|
| **1** | **Evaluation design** | Is 100 projects sufficient? How to select them? What metrics beyond success rate? |
| **2** | **Success rate target** | Is 85% realistic given Repo2Run's 86% on easier Python and our 2/2 PoC? |
| **3** | **Research novelty** | Are our contributions (runtest.py, batching, multi-build) enough for research vs. just engineering? |
| **4** | **Baseline & ablation** | Is comparing vs. ARVO (63.3%) sufficient? How to design ablation study? |
| **5** | **Scaling risks** | What are biggest risks in 2→100 project jump? Address before or during eval? |

---

## 💡 How to Use This Document

**For advisors/reviewers**:
- Please provide feedback on any numbered section above
- Even brief guidance ("Option A looks good", "85% is too ambitious, aim for 75%") is valuable
- We can iterate on the plan based on your input

**For team discussion**:
- Each section has specific decision points
- We need consensus before proceeding to large-scale evaluation
- Mark decisions in this document as we go

**Timeline**:
- **Now**: Gather feedback (target: 1-2 days)
- **Next**: Finalize evaluation plan
- **Then**: Execute 100+ project evaluation (target: 1 week)

---

**Contact**: Please add feedback inline or in separate notes.


