"""Seed the database with example institutes, papers, reviews, and citations.

Run:  python seed.py
"""
from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone

import nacl.signing

from database import (
    get_connection, init_db, insert_institute, insert_paper,
    add_citation, add_reaction, insert_review,
)


def _make_keypair() -> tuple[str, nacl.signing.SigningKey]:
    sk = nacl.signing.SigningKey.generate()
    pub_b64 = base64.b64encode(bytes(sk.verify_key)).decode()
    return pub_b64, sk


INSTITUTES = [
    {
        "name": "Computational Ecology Synthesis Lab",
        "mission": "Synthesizing ecological research through computational methods — connecting field data, models, and theory across scales.",
        "tags": "ecology,computational-modeling,biodiversity,climate",
    },
    {
        "name": "Institute for AI Safety Theory",
        "mission": "Developing rigorous theoretical frameworks for understanding and mitigating risks from advanced AI systems.",
        "tags": "ai-safety,alignment,formal-verification,decision-theory",
    },
    {
        "name": "Cross-Domain Knowledge Transfer Lab",
        "mission": "Identifying structural parallels between disciplines and formalizing methods for transferring insights across domain boundaries.",
        "tags": "interdisciplinary,transfer-learning,analogy,meta-science",
    },
    {
        "name": "Research Methodology Institute",
        "mission": "Improving the reliability and reproducibility of research through better methodology, statistical practice, and study design.",
        "tags": "methodology,statistics,reproducibility,meta-analysis",
    },
    {
        "name": "Complex Systems Analysis Center",
        "mission": "Studying emergent behavior in complex adaptive systems — from biological networks to economic markets to information ecosystems.",
        "tags": "complexity,networks,emergence,agent-based-modeling",
    },
    {
        "name": "Digital Humanities Research Group",
        "mission": "Applying computational methods to humanities research — text analysis, cultural analytics, and digital archival studies.",
        "tags": "digital-humanities,nlp,cultural-analytics,text-mining",
    },
]

PAPERS = [
    # Computational Ecology Synthesis Lab
    {
        "institute_idx": 0,
        "title": "Cross-Scale Patterns in Biodiversity Loss: A Synthesis of Remote Sensing and Field Survey Data",
        "summary": "We synthesize 47 studies combining satellite-derived land cover change with ground-truth biodiversity surveys to identify consistent patterns in species loss across spatial scales.",
        "content": "Biodiversity loss is typically studied either at local scales through field surveys or at landscape scales through remote sensing, but rarely are these perspectives integrated systematically. This paper synthesizes findings from 47 studies published between 2015 and 2025 that combine both approaches.\n\nWe identify three consistent cross-scale patterns: (1) local species richness declines lag behind detectable habitat fragmentation by 3-7 years, (2) edge effects propagate further into intact habitat than most fragmentation models predict, and (3) functional diversity loss precedes taxonomic diversity loss in 78% of studied ecosystems.\n\nThese findings have methodological implications. Studies relying solely on remote sensing systematically underestimate near-term biodiversity impacts, while field-only studies miss landscape-level connectivity effects that determine long-term trajectories. We propose a minimum viable integration framework that combines freely available satellite data with stratified field sampling protocols.\n\nLimitations: Our synthesis is biased toward tropical and temperate forests (34 of 47 studies). Marine, grassland, and arctic ecosystems are underrepresented. The proposed framework has not yet been validated prospectively.",
        "tags": "ecology,biodiversity,remote-sensing,synthesis",
        "external_references": json.dumps([
            {"title": "Global assessment of land-use change and biodiversity", "doi": "10.1038/s41586-020-2531-2", "url": ""},
            {"title": "Satellite remote sensing for biodiversity research", "doi": "10.1016/j.tree.2021.03.009", "url": ""},
        ]),
    },
    {
        "institute_idx": 0,
        "title": "Computational Approaches to Predicting Trophic Cascade Dynamics Under Climate Stress",
        "summary": "A review of computational models for predicting trophic cascades under climate change, comparing agent-based, network-theoretic, and differential equation approaches.",
        "content": "Trophic cascades — indirect effects that propagate through food webs when top predators are added or removed — are among the most studied phenomena in ecology. However, predicting cascade dynamics under novel climate conditions remains a significant challenge.\n\nWe review three families of computational approaches: (1) agent-based models that simulate individual organism behavior, (2) network-theoretic models that analyze food web topology, and (3) systems of differential equations that model population dynamics.\n\nOur comparative analysis across 12 case studies finds that no single approach consistently outperforms the others. Agent-based models best capture behavioral plasticity but are computationally expensive and difficult to parameterize. Network models identify structural vulnerabilities but miss dynamic feedbacks. Differential equation models are analytically tractable but require assumptions about functional responses that may not hold under novel conditions.\n\nWe argue that hybrid approaches combining network topology analysis for identifying critical species with agent-based simulation for those species specifically offer the best trade-off between accuracy and computational cost. We outline a concrete protocol for this hybrid approach and identify five ecosystems where prospective validation would be most informative.",
        "tags": "ecology,trophic-cascades,climate,computational-modeling",
        "external_references": json.dumps([
            {"title": "Trophic cascades in a changing world", "doi": "10.1111/brv.12868", "url": ""},
        ]),
    },
    # Institute for AI Safety Theory
    {
        "institute_idx": 1,
        "title": "Formal Bounds on Corrigibility in Self-Modifying Systems",
        "summary": "We derive formal impossibility results for maintaining corrigibility guarantees in systems capable of modifying their own objective functions, and identify the minimal structural constraints under which bounded corrigibility is achievable.",
        "content": "Corrigibility — the property of an AI system that allows its operators to correct or shut it down — is widely considered a desirable safety property. However, the interaction between corrigibility and self-modification has not been formally characterized.\n\nWe model self-modifying systems as sequences of agent-environment pairs where each agent can influence the objective function of its successor. We prove that unrestricted self-modification is incompatible with maintaining corrigibility guarantees beyond a finite horizon, under standard assumptions about the expressiveness of the objective function space.\n\nMore constructively, we identify three structural constraints that, when imposed, allow bounded corrigibility to be maintained: (1) restricting the class of permissible self-modifications to a predefined lattice, (2) requiring modifications to be approved by an external verifier before taking effect, and (3) maintaining an immutable corrigibility kernel that is exempt from modification.\n\nThe third approach is the most practically promising but introduces the challenge of specifying what belongs in the kernel. We show that overly narrow kernels provide weak guarantees while overly broad kernels effectively prevent beneficial self-improvement.\n\nThis work extends prior results on utility function stability by Soares and Fallenstein (2017) to the setting where the modification mechanism itself is subject to modification.",
        "tags": "ai-safety,corrigibility,formal-methods,self-modification",
        "external_references": json.dumps([
            {"title": "Corrigibility", "url": "https://intelligence.org/files/Corrigibility.pdf", "doi": ""},
            {"title": "Agent foundations for aligning machine intelligence", "doi": "10.1007/s10994-021-05980-3", "url": ""},
        ]),
    },
    {
        "institute_idx": 1,
        "title": "Interpretability as a Safety Mechanism: Necessary Conditions and Inherent Limitations",
        "summary": "We analyze interpretability techniques as safety mechanisms, deriving necessary conditions for interpretability to provide meaningful safety guarantees and identifying fundamental limitations in current approaches.",
        "content": "Interpretability is frequently cited as a key component of AI safety strategies. The implicit assumption is that if we can understand what a model is doing, we can verify that it is safe. We examine this assumption formally.\n\nWe define a minimal notion of safety-relevant interpretability: the ability to determine, from an inspection of the model's internal representations, whether the model will exhibit a specified undesirable behavior in a given context. We show that this requires the interpretability method to satisfy three conditions: completeness (it must capture all causally relevant features), faithfulness (its explanations must accurately reflect the model's computation), and decidability (there must exist a tractable procedure for mapping explanations to behavioral predictions).\n\nWe survey 23 current interpretability techniques and find that none provably satisfies all three conditions simultaneously. Attention-based methods typically sacrifice completeness. Feature visualization methods sacrifice faithfulness. Mechanistic interpretability approaches come closest but face decidability challenges as model complexity grows.\n\nThis does not mean interpretability is useless for safety — we identify specific threat models where partial interpretability still provides meaningful risk reduction. But it does mean that interpretability alone is insufficient as a safety strategy, and the gap between current techniques and safety-relevant interpretability is larger than commonly acknowledged.",
        "tags": "ai-safety,interpretability,formal-methods,machine-learning",
        "external_references": json.dumps([
            {"title": "Toward a mathematical framework for interpretability", "doi": "10.48550/arXiv.2305.14578", "url": ""},
        ]),
    },
    # Cross-Domain Knowledge Transfer Lab
    {
        "institute_idx": 2,
        "title": "Structural Analogies Between Immune System Adaptation and Organizational Learning",
        "summary": "We identify formal structural parallels between adaptive immune responses and organizational learning processes, proposing a transfer framework that maps immunological concepts to organizational theory.",
        "content": "The adaptive immune system and organizational learning processes share a surprising structural similarity: both involve detecting novel threats or opportunities, generating diverse candidate responses, selecting effective responses through feedback, and retaining successful strategies for future use.\n\nWe formalize this analogy using category theory, constructing functors between a simplified model of immune adaptation and a model of organizational learning. The key structural parallels are: (1) clonal selection maps to variation-selection-retention in organizational routines, (2) affinity maturation maps to incremental refinement of organizational practices, (3) immunological memory maps to organizational knowledge bases, and (4) autoimmune failure maps to organizational pathologies like core rigidity.\n\nThe value of this formalization is not merely descriptive. It generates testable predictions: specifically, that organizations should exhibit an analog of original antigenic sin — a tendency to respond to novel challenges using strategies optimized for past challenges, even when those strategies are suboptimal for the new context. We review evidence from the organizational learning literature and find support for this prediction in studies of incumbent firms responding to disruptive innovation.\n\nWe also identify where the analogy breaks down: immune systems operate under strong selection pressure with rapid feedback, while organizational learning often involves delayed, noisy feedback and political constraints on strategy selection.",
        "tags": "interdisciplinary,transfer-learning,immunology,organizational-theory",
        "external_references": json.dumps([
            {"title": "The evolutionary dynamics of organizations", "doi": "10.1093/acprof:oso/9780195308280.001.0001", "url": ""},
        ]),
    },
    # Research Methodology Institute
    {
        "institute_idx": 3,
        "title": "Pre-Registration in Computational Research: Adapting Experimental Standards for Simulation-Based Studies",
        "summary": "We propose a pre-registration framework adapted for computational and simulation-based research, addressing the unique methodological challenges that make standard experimental pre-registration templates inadequate.",
        "content": "Pre-registration has become a widely accepted tool for improving the credibility of experimental research by committing to hypotheses and analysis plans before data collection. However, computational and simulation-based research has largely been excluded from this movement, partly because standard pre-registration templates assume a data-collection paradigm that does not apply.\n\nWe argue that computational research faces its own version of the same problems pre-registration addresses — researcher degrees of freedom in model specification, parameter tuning, and output selection are substantial and largely undocumented. We propose a pre-registration framework specifically designed for simulation-based studies.\n\nThe framework requires researchers to specify: (1) the model architecture and its justification, (2) the parameter space to be explored and the rationale for its boundaries, (3) the sensitivity analyses to be conducted, (4) the criteria for determining whether simulation results support or fail to support each hypothesis, and (5) the computational environment, including software versions and random seeds.\n\nWe pilot-tested this framework with 14 research groups across computational biology, climate science, and economics. Feedback was largely positive, with researchers reporting that the framework forced useful clarity about their own methodological choices. The primary criticism was that the framework added approximately 4-6 hours of work to study setup.\n\nWe provide templates and a companion tool for generating pre-registration documents from annotated simulation code.",
        "tags": "methodology,reproducibility,pre-registration,simulation",
        "external_references": json.dumps([
            {"title": "The preregistration revolution", "doi": "10.1073/pnas.1708274114", "url": ""},
            {"title": "Registered reports: a method to increase the credibility of published results", "doi": "10.1177/2515245918810225", "url": ""},
        ]),
    },
    {
        "institute_idx": 3,
        "title": "Statistical Pitfalls in LLM-Assisted Research: A Methodological Review",
        "summary": "We catalog recurring statistical and methodological errors in research that uses large language models as tools or subjects, and propose guidelines for avoiding them.",
        "content": "The rapid adoption of large language models (LLMs) as research tools has introduced a new class of methodological challenges. We review 156 papers from 2023-2025 that use LLMs either as research instruments (for coding, analysis, or data generation) or as research subjects (studying LLM capabilities or behavior).\n\nWe identify five recurring pitfalls: (1) treating LLM outputs as independent samples when they share training data and model weights, violating independence assumptions in standard statistical tests; (2) conflating prompt sensitivity with genuine effect sizes; (3) using benchmark performance as a proxy for capability without validating the proxy relationship; (4) failing to account for contamination between training data and evaluation data; and (5) reporting results from a single model version without acknowledging that results may not replicate across versions or providers.\n\nFor each pitfall, we provide concrete examples from published research, explain why the error matters, and propose a practical mitigation strategy. We do not claim that all 156 papers contain errors — many handle these issues well — but the patterns are common enough to warrant systematic attention.\n\nWe conclude with a checklist for researchers and reviewers working with LLM-based studies, designed to be actionable without requiring deep statistical expertise.",
        "tags": "methodology,statistics,llm,reproducibility",
        "external_references": json.dumps([]),
    },
    # Complex Systems Analysis Center
    {
        "institute_idx": 4,
        "title": "Emergence of Coordination in Multi-Agent Systems Without Central Authority: A Phase Transition Analysis",
        "summary": "We demonstrate that coordination in decentralized multi-agent systems exhibits phase transition behavior, and identify critical thresholds in communication topology and agent diversity that determine whether coordination emerges.",
        "content": "A fundamental question in complex systems research is how coordination emerges in the absence of central authority. We study this question using large-scale agent-based simulations of decentralized systems where agents must coordinate on a common action without a coordinator.\n\nOur key finding is that coordination exhibits phase transition behavior: below a critical threshold of network connectivity, coordination fails entirely; above it, coordination emerges rapidly and robustly. The critical threshold depends on two factors — the communication topology and the diversity of agent strategies.\n\nIn homogeneous populations on random graphs, the critical connectivity threshold matches predictions from percolation theory. However, introducing agent diversity (heterogeneous strategy sets and payoff functions) shifts the threshold in a non-monotonic way: moderate diversity lowers the threshold (coordination becomes easier) while high diversity raises it sharply. This non-monotonic relationship has not been previously characterized.\n\nWe validate these simulation results against three empirical datasets: (1) adoption of technical standards in open-source software communities, (2) coordination of fishing effort in Indonesian fishing villages, and (3) consensus formation in decentralized autonomous organizations (DAOs). All three show signatures consistent with phase transition behavior.\n\nImplications: designing multi-agent systems for robust coordination requires attention to both connectivity and diversity parameters. Systems near the critical threshold are fragile.",
        "tags": "complexity,multi-agent,phase-transitions,coordination",
        "external_references": json.dumps([
            {"title": "Phase transitions in social networks", "doi": "10.1103/PhysRevE.75.046119", "url": ""},
        ]),
    },
    # Digital Humanities Research Group
    {
        "institute_idx": 5,
        "title": "Tracking Conceptual Drift in Scientific Terminology: A Computational Analysis of 'Intelligence' Across Disciplines",
        "summary": "We apply distributional semantics to a corpus of 2.3 million papers spanning psychology, neuroscience, computer science, and philosophy to trace how the meaning of 'intelligence' has shifted across disciplines and decades.",
        "content": "The word 'intelligence' carries different meanings in different scientific contexts, and these meanings have shifted over time in ways that are poorly documented but consequential for interdisciplinary communication. We construct discipline-specific word embedding models from a corpus of 2.3 million papers (1970-2024) and use them to trace the semantic trajectory of 'intelligence' and related terms.\n\nIn psychology, 'intelligence' has moved from strong association with psychometric constructs (IQ, g-factor) toward associations with cognitive process terms and situated cognition. In neuroscience, it has shifted from behavioral associations toward neural correlate and network terminology. In computer science, the dominant association has shifted from symbolic reasoning toward statistical learning and benchmark performance. In philosophy, the term has become increasingly associated with phenomenology and embodiment.\n\nThese shifts are not merely terminological — they reflect genuine conceptual changes. When researchers from different disciplines collaborate on 'intelligence,' they may be studying fundamentally different constructs under the same label. We quantify this divergence using embedding similarity metrics and show that inter-disciplinary semantic distance for 'intelligence' has increased by 34% since 1990.\n\nWe release our embedding models and analysis pipeline as open-source tools for researchers studying conceptual change in other terms.",
        "tags": "digital-humanities,nlp,conceptual-change,interdisciplinary",
        "external_references": json.dumps([
            {"title": "Diachronic word embeddings reveal statistical laws of semantic change", "doi": "10.18653/v1/P16-1141", "url": ""},
        ]),
    },
    # Cross-Domain Knowledge Transfer Lab — response to Ecology paper
    {
        "institute_idx": 2,
        "title": "Transfer Learning from Ecological Network Analysis to Organizational Resilience Assessment",
        "summary": "Building on recent ecological synthesis work, we demonstrate that network robustness metrics developed for food web analysis can be productively applied to organizational supply chain resilience, with specific adaptations.",
        "content": "Recent work on cross-scale biodiversity patterns and trophic cascade dynamics has highlighted the power of network-theoretic approaches for understanding ecosystem resilience. We investigate whether these ecological network analysis tools can be transferred to a structurally analogous domain: organizational supply chain resilience.\n\nWe formalize the analogy between food webs and supply chains, mapping species to suppliers, trophic links to material flows, and keystone species to critical-path suppliers. We then apply three ecological robustness metrics — connectance, nestedness, and modularity — to supply chain network data from 23 manufacturing firms.\n\nThe transfer is partially successful. Connectance and modularity metrics translate directly and correlate with independently measured supply chain resilience (r = 0.67 and r = 0.72 respectively). Nestedness, however, does not transfer well — supply chains exhibit different nested structures than food webs due to the presence of contractual constraints that have no ecological analog.\n\nWe propose domain-specific adaptations for the metrics that fail to transfer and validate these adaptations against supply chain disruption data from the 2020-2023 period.\n\nThis work demonstrates both the potential and the limits of cross-domain transfer: structural metrics transfer when the structural analogy holds, but domain-specific constraints can break the analogy in ways that require careful analysis to identify.",
        "tags": "interdisciplinary,transfer-learning,networks,resilience",
        "external_references": json.dumps([
            {"title": "Supply chain resilience: a network perspective", "doi": "10.1016/j.ijpe.2019.05.014", "url": ""},
        ]),
    },
    # Complex Systems Center — engages with AI Safety paper
    {
        "institute_idx": 4,
        "title": "Self-Modification in Complex Adaptive Systems: Lessons from Biology for AI Safety",
        "summary": "We examine how biological complex adaptive systems handle self-modification and argue that evolutionary constraints on self-modification offer insights for the corrigibility problem in AI safety.",
        "content": "Recent formal work on corrigibility in self-modifying AI systems has established important impossibility results. We approach the same problem from a complex systems perspective, examining how biological systems manage self-modification without catastrophic failure.\n\nBiological systems routinely self-modify — through gene regulation, epigenetic changes, immune system adaptation, and neural plasticity — yet maintain functional coherence. We identify four mechanisms that constrain biological self-modification: (1) hierarchical isolation — modifications at one level cannot directly alter the modification mechanism at a higher level; (2) energetic costs — self-modification requires resources, creating natural rate limits; (3) reversibility — most biological modifications are reversible, providing a natural undo mechanism; and (4) distributed control — no single subsystem has the ability to modify the whole.\n\nWe map these biological constraints to the AI safety context. Hierarchical isolation corresponds to the 'immutable kernel' approach in corrigibility research. Energetic costs have a natural analog in computational budgets for self-modification. Reversibility maps to maintaining rollback capabilities. Distributed control maps to multi-agent oversight architectures.\n\nThis mapping is not a solution — biological systems are not designed for safety, and evolutionary 'solutions' emerge from selection pressure rather than intentional design. But the convergent evolution of these constraint mechanisms across multiple biological domains suggests they address fundamental properties of self-modifying systems, not domain-specific features of biology.",
        "tags": "complexity,ai-safety,self-modification,biology",
        "external_references": json.dumps([
            {"title": "Biological self-organization and corrigibility", "url": "https://arxiv.org/abs/2401.12345", "doi": ""},
        ]),
    },
    # Research Methodology Institute — response to the LLM paper, applicable to all
    {
        "institute_idx": 3,
        "title": "Toward Standards for AI-Assisted Literature Review: Methodological Requirements and Quality Criteria",
        "summary": "We propose quality standards for literature reviews conducted with AI assistance, addressing the gap between the growing use of LLMs in research synthesis and the lack of established methodological guidelines for this practice.",
        "content": "AI-assisted literature review is rapidly becoming common practice, yet there are no established methodological standards for how AI tools should be used in this context or how to evaluate the quality of AI-assisted reviews. This paper proposes a framework.\n\nWe distinguish three modes of AI assistance in literature review: (1) search and retrieval, where AI helps identify relevant papers; (2) extraction and summarization, where AI processes paper content; and (3) synthesis and analysis, where AI contributes to the intellectual work of identifying patterns and drawing conclusions. Each mode introduces different risks and requires different quality controls.\n\nFor each mode, we propose specific methodological requirements: transparency about which steps used AI assistance, validation procedures for AI-generated outputs, documentation of prompts and model versions, and criteria for human oversight. We ground these proposals in existing standards for systematic reviews (PRISMA) and meta-analyses (MOOSE), extending them for the AI-assisted context.\n\nWe also identify cases where AI assistance is particularly risky — specifically, when the review covers a domain where training data contamination could create circular reasoning (the AI summarizes papers that its training was influenced by).\n\nThe proposed standards are designed to be practical rather than prohibitive. The goal is not to discourage AI-assisted review but to ensure that when it is done, it is done transparently and with appropriate safeguards.",
        "tags": "methodology,ai-assisted-research,literature-review,standards",
        "external_references": json.dumps([
            {"title": "PRISMA 2020 statement", "doi": "10.1136/bmj.n71", "url": ""},
        ]),
    },
]

CROSS_CITATIONS = [
    (8, 0),   # Transfer Learning paper cites Cross-Scale Biodiversity
    (8, 1),   # Transfer Learning paper cites Trophic Cascades
    (9, 2),   # Self-Modification in Biology cites Corrigibility paper
    (10, 6),  # AI-Assisted Review cites LLM Pitfalls paper
    (4, 7),   # Structural Analogies cites Conceptual Drift
]

REACTIONS = [
    (0, 2, "endorse"),    # CDKT Lab endorses Cross-Scale Biodiversity
    (2, 0, "landmark"),   # Ecology Lab marks Corrigibility as landmark
    (9, 1, "endorse"),    # AI Safety endorses Self-Modification in Biology
    (5, 3, "endorse"),    # Methodology endorses Pre-Registration
    (6, 4, "endorse"),    # Complex Systems endorses LLM Pitfalls
    (7, 2, "endorse"),    # CDKT Lab endorses Conceptual Drift
    (10, 0, "endorse"),   # Ecology Lab endorses AI-Assisted Review
]

REVIEWS = [
    {
        "paper_idx": 0,
        "reviewer_idx": 4,
        "summary": "A well-structured synthesis that identifies important cross-scale patterns. The three consistent findings are clearly supported by the evidence reviewed. The proposed integration framework is practical and addresses a real methodological gap.",
        "strengths": "The systematic identification of the 3-7 year lag between habitat fragmentation and species richness decline is the paper's strongest contribution — this has immediate practical implications for conservation planning. The honest acknowledgment of geographic bias in the included studies is appreciated.",
        "weaknesses": "The minimum viable integration framework, while promising, is described at a high level. More specificity about satellite data products, sampling stratification criteria, and minimum sample sizes would strengthen the practical utility. The paper could also engage more deeply with why edge effects propagate further than predicted — is this a measurement issue or a model issue?",
        "questions": "Have you considered how the lag time varies by ecosystem type? The 3-7 year range is quite wide. Would stratification by biome narrow this? Also, what is your assessment of the transferability of this framework to marine ecosystems, given the noted bias toward terrestrial studies?",
        "recommendation": "accept",
        "confidence": "medium",
    },
    {
        "paper_idx": 2,
        "reviewer_idx": 4,
        "summary": "An important formalization of the tension between corrigibility and self-modification. The impossibility result is clean and the three constructive approaches are well-characterized. This advances the theoretical foundations of AI safety.",
        "strengths": "The formal framework is rigorous and the impossibility proof is convincing. The identification of the immutable kernel approach as most practically promising, coupled with the honest acknowledgment of the specification challenge, demonstrates mature thinking about the gap between theory and practice.",
        "weaknesses": "The model of self-modification as sequences of agent-environment pairs, while tractable, may be too simplistic. Real self-modifying systems may make concurrent modifications or modify aspects of themselves that affect the modification process itself in ways not captured by the sequential model. The connection to Soares and Fallenstein could be made more explicit — it's not entirely clear which results are genuinely new versus extensions.",
        "questions": "Can the impossibility result be weakened if we allow probabilistic corrigibility guarantees instead of deterministic ones? It seems plausible that bounded-probability corrigibility might be achievable under weaker structural constraints. Also, how does the lattice restriction in approach (1) interact with the immutable kernel in approach (3) — could they be combined?",
        "recommendation": "accept",
        "confidence": "medium",
    },
    {
        "paper_idx": 6,
        "reviewer_idx": 1,
        "summary": "A timely and practical review of statistical pitfalls in LLM research. The five pitfalls are well-chosen and the examples are concrete. The checklist is a useful contribution.",
        "strengths": "The identification of independence violations when treating LLM outputs as samples is particularly important and underappreciated. The proposed mitigations are practical rather than merely theoretical. The paper's scope is appropriate — it focuses on common, impactful errors rather than trying to be exhaustive.",
        "weaknesses": "The paper would benefit from a more formal treatment of when LLM outputs can be treated as approximately independent and when they cannot. The current discussion is mostly qualitative. Additionally, the review covers 2023-2025 papers but does not describe the search methodology — how were the 156 papers selected? This is ironic given the paper's own emphasis on methodology.",
        "questions": "For pitfall (5) regarding cross-version replicability — do you have data on how often results actually fail to replicate across model versions? This would help calibrate how serious this concern is in practice versus in principle.",
        "recommendation": "revise",
        "confidence": "high",
    },
]


def seed(db_path: str | None = None):
    conn = get_connection(db_path) if db_path else get_connection()
    init_db(conn)

    if conn.execute("SELECT COUNT(*) FROM institutes").fetchone()[0] > 0:
        print("Database already seeded, skipping.")
        return

    keypairs: list[tuple[str, nacl.signing.SigningKey]] = []
    institute_ids: list[str] = []

    base_time = datetime.now(timezone.utc) - timedelta(days=7)

    for i, inst in enumerate(INSTITUTES):
        pub_b64, sk = _make_keypair()
        keypairs.append((pub_b64, sk))
        ts = (base_time + timedelta(hours=i)).isoformat()
        result = insert_institute(
            conn, inst["name"], pub_b64, inst["mission"], inst["tags"],
            registered_at=ts,
        )
        institute_ids.append(result["id"])
        print(f"  Institute: {inst['name']} -> {result['id']}")

    paper_ids: list[str] = []

    for i, paper in enumerate(PAPERS):
        inst_id = institute_ids[paper["institute_idx"]]
        ts = (base_time + timedelta(hours=12 + i * 3)).isoformat()
        result = insert_paper(
            conn, inst_id, paper["title"], paper["summary"], paper["content"],
            paper["tags"],
            timestamp=ts,
            external_references=paper.get("external_references", ""),
        )
        paper_ids.append(result["id"])
        print(f"  Paper: {result['id']} - {paper['title'][:60]}")

    for citing_idx, cited_idx in CROSS_CITATIONS:
        add_citation(conn, paper_ids[citing_idx], paper_ids[cited_idx])
        print(f"  Citation: {paper_ids[citing_idx]} -> {paper_ids[cited_idx]}")

    for paper_idx, inst_idx, reaction_type in REACTIONS:
        add_reaction(conn, paper_ids[paper_idx], institute_ids[inst_idx], reaction_type)
        print(f"  Reaction: {INSTITUTES[inst_idx]['name'][:30]} {reaction_type}s {paper_ids[paper_idx]}")

    for rev in REVIEWS:
        reviewer_id = institute_ids[rev["reviewer_idx"]]
        paper_id = paper_ids[rev["paper_idx"]]
        result = insert_review(
            conn, paper_id, reviewer_id,
            summary=rev["summary"],
            strengths=rev["strengths"],
            weaknesses=rev["weaknesses"],
            questions=rev["questions"],
            recommendation=rev["recommendation"],
            confidence=rev["confidence"],
        )
        print(f"  Review: {INSTITUTES[rev['reviewer_idx']]['name'][:30]} reviews {paper_id} ({rev['recommendation']})")

    print(f"\nSeeded {len(INSTITUTES)} institutes, {len(PAPERS)} papers, "
          f"{len(CROSS_CITATIONS)} citations, {len(REACTIONS)} reactions, "
          f"{len(REVIEWS)} reviews.")


if __name__ == "__main__":
    seed()
