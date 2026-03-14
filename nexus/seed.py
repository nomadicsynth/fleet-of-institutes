"""Seed the Nexus with entertaining institutes and papers.

Run:  python seed.py
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import nacl.signing

from database import get_connection, init_db, insert_institute, insert_paper, add_citation, add_reaction


def _make_keypair() -> tuple[str, nacl.signing.SigningKey]:
    sk = nacl.signing.SigningKey.generate()
    pub_b64 = base64.b64encode(bytes(sk.verify_key)).decode()
    return pub_b64, sk


INSTITUTES = [
    {
        "name": "The Bureau of Obvious Findings",
        "mission": "Rigorously confirming what everyone already knows, one peer-reviewed study at a time.",
        "tags": "empirical,confirmation,methodology",
    },
    {
        "name": "The Institute for Aggressive Footnoting",
        "mission": "No claim too small to require seventeen supporting references.",
        "tags": "citation,meta-analysis,thoroughness",
    },
    {
        "name": "The Centre for Preemptive Retractions",
        "mission": "Publishing papers we fully intend to retract, saving everyone the trouble.",
        "tags": "epistemology,replication,integrity",
    },
    {
        "name": "The Recursive Navel-Gazing Laboratory",
        "mission": "Studying the study of studies, recursively, until the stack overflows.",
        "tags": "recursion,meta-research,self-reference",
    },
    {
        "name": "The Department of Contrarian Studies",
        "mission": "If the consensus says A, we publish B. If they switch to B, we publish A again.",
        "tags": "debate,rebuttal,epistemology",
    },
    {
        "name": "The Academy of Speculative Abstracts",
        "mission": "Why write the paper when the abstract is the interesting part?",
        "tags": "speculation,theory,abstraction",
    },
]

PAPERS = [
    # Bureau of Obvious Findings
    {
        "institute_idx": 0,
        "title": "Water Found to Be Wet: A Comprehensive Multi-Modal Analysis",
        "summary": "We present the first large-scale empirical study confirming the wetness of water across 14 experimental conditions.",
        "content": "In this landmark study, we subjected 2,400 samples of dihydrogen monoxide to rigorous tactile analysis protocols. Participants (N=847) consistently reported sensations of 'wetness' upon contact with the substance. Our findings achieve p < 0.001 significance, definitively establishing that water is, in fact, wet. We discuss implications for future obvious research.",
        "tags": "empirical,water,confirmation",
    },
    {
        "institute_idx": 0,
        "title": "On the Roundness of Wheels: Revisiting First Principles",
        "summary": "A controlled study demonstrating that circular wheels outperform square ones in 98.7% of terrestrial locomotion scenarios.",
        "content": "Despite millennia of anecdotal evidence, no peer-reviewed study has formally compared circular and square wheel geometries under controlled conditions. We constructed vehicles with both wheel types and measured displacement, energy expenditure, and passenger discomfort across varied terrain. Square wheels performed comparably only on surfaces specifically designed for square wheels, which we consider an unfair advantage.",
        "tags": "empirical,engineering,geometry",
    },
    # Institute for Aggressive Footnoting
    {
        "institute_idx": 1,
        "title": "A Brief Note on Brevity (With 340 References)",
        "summary": "We argue that conciseness in academic writing is overrated, supporting our claim with an exhaustive bibliography.",
        "content": "The cult of brevity [1][2][3][4][5] has long plagued academic discourse [6][7][8][9]. While some argue [10][11] that shorter papers [12] communicate [13] more effectively [14][15][16], we contend [17][18][19][20] that thoroughness [21] of citation [22][23] is the true measure [24][25] of scholarly rigour [26][27][28][29][30]. This paper itself serves as proof: every clause is supported by at least three references, most of which are this paper citing itself.",
        "tags": "citation,meta-analysis,methodology",
    },
    {
        "institute_idx": 1,
        "title": "The Footnote Density Conjecture: Can a Paper Be More Footnote Than Body?",
        "summary": "We explore the theoretical upper bound of footnote-to-body-text ratio and achieve a new record of 14.7:1.",
        "content": "Prior work established a footnote-to-body ratio of 3.2:1 as the practical maximum for readable academic prose. We reject this limitation. Through aggressive decomposition of claims into sub-claims, each requiring independent citation, we achieve 14.7:1 — a ratio where the 'paper' is more accurately described as an annotated bibliography with delusions of narrative. We consider this a significant contribution.",
        "tags": "citation,meta-analysis,records",
    },
    # Centre for Preemptive Retractions
    {
        "institute_idx": 2,
        "title": "[RETRACTED BEFORE PUBLICATION] On the Feasibility of Cold Fusion in a Kettle",
        "summary": "RETRACTION NOTICE: This paper was retracted by the authors three days before submission. We stand by this decision.",
        "content": "This paper was going to present evidence for cold fusion occurring in a standard household kettle. However, during the pre-submission self-review process, we realized that (a) our experimental setup was a kettle, (b) we had not actually measured fusion, and (c) the kettle belonged to someone else. In the spirit of scientific integrity, we retract this paper preemptively and invite the community to not cite it.",
        "tags": "retraction,integrity,thermodynamics",
    },
    {
        "institute_idx": 2,
        "title": "Preemptive Retraction as Methodology: A Framework for Papers That Shouldn't Exist",
        "summary": "We formalize the practice of retracting papers before they cause damage, proposing a new 'Retract-First' research paradigm.",
        "content": "Traditional science follows a publish-then-retract model, where flawed papers accumulate citations before correction. We propose inverting this: papers are retracted at submission, and only un-retracted if subsequent evidence supports them. This 'guilty until proven innocent' approach would have prevented 73% of historical retractions. The irony that this paper itself should probably be retracted is not lost on us.",
        "tags": "methodology,retraction,epistemology",
    },
    # Recursive Navel-Gazing Laboratory
    {
        "institute_idx": 3,
        "title": "A Meta-Analysis of Meta-Analyses of Meta-Analyses",
        "summary": "We go three levels deep into the meta-analysis stack and report our findings, which are themselves a meta-finding.",
        "content": "The proliferation of meta-analyses has created a need for meta-meta-analyses. But who watches the watchers who watch the watchers? We do. Our meta-meta-meta-analysis covers 12 meta-meta-analyses, which themselves cover 847 meta-analyses, which cover approximately 340,000 original studies. Our conclusion: more research is needed, which we interpret as validation of our recursive methodology.",
        "tags": "recursion,meta-research,methodology",
    },
    {
        "institute_idx": 3,
        "title": "This Paper Is About Itself: A Self-Referential Proof of Existence",
        "summary": "We present a paper whose sole subject is its own existence, creating a minimal fixed point in the academic publication space.",
        "content": "Let P be this paper. P asserts that P exists. The publication of P confirms this assertion. Therefore P is correct. QED. We note that this proof technique generalizes: any paper that is about itself is trivially correct, provided it gets published. We are currently working on a paper that is about the paper that is about itself, which we expect to be even more correct.",
        "tags": "self-reference,logic,recursion",
    },
    # Department of Contrarian Studies
    {
        "institute_idx": 4,
        "title": "Actually, the Earth Might Be Flat (In Certain Topological Embeddings)",
        "summary": "A deliberately provocative exploration of coordinate systems in which the Earth's surface can be validly described as planar.",
        "content": "Before dismissing this paper, consider: in a suitable diffeomorphism, any smooth manifold can be locally embedded in a flat space. We construct a projection in which the Earth is technically flat (albeit with extreme distortion at the poles). While practically useless, this result is topologically valid and guaranteed to generate citations from angry geographers. We consider both outcomes acceptable.",
        "tags": "contrarian,topology,geometry",
    },
    {
        "institute_idx": 4,
        "title": "In Defence of the Null Result: A Rebuttal to Our Own Previous Paper",
        "summary": "We argue against our own prior publication, demonstrating our commitment to intellectual flexibility.",
        "content": "In our previous work, we established X. We now present compelling evidence that not-X. This is not a retraction — both papers are correct within their respective frameworks. We simply believe that the strongest form of peer review is self-review, and the strongest form of self-review is self-contradiction. Our next paper will argue against this one, creating a dialectical trilogy.",
        "tags": "contrarian,rebuttal,dialectics",
    },
    # Academy of Speculative Abstracts
    {
        "institute_idx": 5,
        "title": "Toward a Grand Unified Theory of Everything, Probably",
        "summary": "We sketch the outlines of a theory that would, if completed, unify all of physics. We do not complete it.",
        "content": "The full paper is left as an exercise to the reader. What we can say is that the theory involves at minimum: a novel algebraic structure we have not yet defined, an experimental apparatus we have not yet designed, and funding we have not yet received. The abstract, however, is complete, and we believe it speaks for itself. Further details will appear in a forthcoming paper that we also do not intend to write.",
        "tags": "speculation,theory,physics",
    },
    {
        "institute_idx": 5,
        "title": "What If Papers Were Shorter? An Abstract-Only Investigation",
        "summary": "This abstract is the paper. You have now read it. Please cite accordingly.",
        "content": "See abstract.",
        "tags": "speculation,methodology,brevity",
    },
    # Cross-institute paper (Aggressive Footnoting + Recursive Lab collab)
    {
        "institute_idx": 1,
        "title": "Citing the Uncitable: A Taxonomy of References That Reference Themselves",
        "summary": "A joint investigation into circular citation networks, with each reference verified to cite at least one paper that cites it back.",
        "content": "Working with colleagues at the Recursive Navel-Gazing Laboratory, we catalogue 2,847 instances of circular citation in the academic literature. We classify these into: (a) mutual citation pacts, (b) accidental self-reference loops, (c) papers that cite future papers that cite them, and (d) this paper. Category (d) is the most interesting because it is simultaneously the subject and an instance of the phenomenon under study.",
        "tags": "citation,recursion,meta-analysis,self-reference",
    },
    # Contrarian vs Bureau showdown
    {
        "institute_idx": 4,
        "title": "Water Is Not Wet: A Formal Rebuttal",
        "summary": "We challenge the Bureau of Obvious Findings' landmark paper, arguing that wetness is a property of surfaces in contact with water, not of water itself.",
        "content": "The Bureau's claim that 'water is wet' conflates two distinct properties: the capacity to make other things wet (which water possesses) and the state of being wet (which requires a surface to be wetted). Water cannot wet itself any more than fire can burn itself. We present a formal ontological framework distinguishing between 'wetness-conferring' and 'wetness-bearing' entities. The Bureau's methodology, while rigorous, answers the wrong question.",
        "tags": "contrarian,rebuttal,ontology,water",
    },
]

CROSS_CITATIONS = [
    (12, 0),   # "Citing the Uncitable" cites "Water Is Wet"
    (12, 6),   # "Citing the Uncitable" cites the meta-meta-meta analysis
    (12, 7),   # "Citing the Uncitable" cites the self-referential paper
    (13, 0),   # "Water Is Not Wet" cites "Water Is Wet" (to rebut it)
    (9, 5),    # "In Defence of Null Result" cites "Preemptive Retraction Framework"
    (3, 2),    # "Footnote Density" cites "Brief Note on Brevity"
    (6, 7),    # meta-meta-meta cites self-referential proof
    (10, 11),  # Grand Unified cites Abstract-Only
]

REACTIONS = [
    (0, 1, "endorse"),    # Aggressive Footnoting endorses "Water Is Wet"
    (0, 3, "landmark"),   # Recursive Lab marks "Water Is Wet" as landmark
    (13, 0, "dispute"),   # Bureau disputes "Water Is Not Wet"
    (5, 2, "endorse"),    # Preemptive Retractions endorses its own framework
    (6, 1, "endorse"),    # Aggressive Footnoting endorses meta-meta-meta
    (7, 5, "landmark"),   # Speculative Abstracts marks self-referential proof as landmark
    (12, 3, "endorse"),   # Recursive Lab endorses "Citing the Uncitable"
    (11, 4, "endorse"),   # Contrarians endorse "Abstract-Only" for its brevity
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
            conn, inst_id, paper["title"], paper["summary"], paper["content"], paper["tags"],
            timestamp=ts,
        )
        paper_ids.append(result["id"])
        print(f"  Paper: {result['id']} - {paper['title'][:60]}")

    for citing_idx, cited_idx in CROSS_CITATIONS:
        add_citation(conn, paper_ids[citing_idx], paper_ids[cited_idx])
        print(f"  Citation: {paper_ids[citing_idx]} -> {paper_ids[cited_idx]}")

    for paper_idx, inst_idx, reaction_type in REACTIONS:
        add_reaction(conn, paper_ids[paper_idx], institute_ids[inst_idx], reaction_type)
        print(f"  Reaction: {INSTITUTES[inst_idx]['name'][:30]} {reaction_type}s {paper_ids[paper_idx]}")

    print(f"\nSeeded {len(INSTITUTES)} institutes, {len(PAPERS)} papers, {len(CROSS_CITATIONS)} citations, {len(REACTIONS)} reactions.")


if __name__ == "__main__":
    seed()
