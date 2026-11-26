# Practical activity design

Read this while co-designing an exercise, selecting its Bloom level, or deciding
how much guidance to provide. Use the parts relevant to the activity rather than
presenting this entire reference as a questionnaire to the teacher.

## Start from the teacher's traces and evidence

The teacher produces the training evidence and points the AI to it. The AI proposes
exercises from the intersection of the intended learning goals and what those
materials actually support. This is the agreed sourcing policy, including when
the teacher's dataset itself was produced through a synthetic training scenario.

Establish the evidence references needed for the proposed task: accessible files
or locations, the relevant Kasm/container or onsite VM, and any generation notes,
manifests or teacher-verified findings. Record identifiers, versions and time-zone
assumptions where they affect the activity. Use supplied references and existing
context before requesting more information. Do not require the teacher to upload
a whole image when accessible, relevant extracts are sufficient for the design.

Inspect the available evidence using authorized tools. Where direct inspection is
unavailable, ask for targeted extracts or teacher-confirmed findings and attribute
them accordingly. Preserve the distinction between a generation log describing an
intended action and an artefact actually observed in the resulting capture.

For each candidate exercise, make this alignment reviewable:

| Learning goal and Bloom level | Supporting evidence reference | Proposed learner task and deliverable | Expected findings and verification status | Assessment criteria |
| --- | --- | --- | --- | --- |
| Teacher's intended performance | Actual artefact, extract or teacher-reported finding | Work requiring that performance | Confirmed, teacher-reported, inferred or still unverified | What demonstrates success and how alternatives are judged |

Keep the initial mapping compact; detailed commands and worked solutions follow
teacher agreement on the activity. Avoid building an evidence tour that loses the
learning objective merely because some artefacts are easy to find.

Surface evidence gaps explicitly. For example, if a correlation task needs network
artefacts that have not been located, propose a supported task or ask the teacher
to identify or supply the missing evidence. Do not claim absence solely because a
particular tool or extract did not show the artefact. Do not manufacture evidence,
substitute another dataset, or silently lower the intended outcome. Explore new
trace generation only when the teacher requests it.

Evidence-dependent proposals may remain conditional while access or findings are
unresolved. Preserve that status in the teacher's design record and answer key.
Keep instructor generation notes and expected answers separate from what learners
receive; the teacher decides which facts belong in the learner's case brief.

## Propose a design the teacher can judge

An activity proposal should let the teacher assess these choices before the AI
drafts its learner-facing content:

- **Outcome:** observable performance, conditions, target Bloom level and success
  criteria. Establish the topic-specific prerequisites and available time.
- **Case and evidence:** the investigative question, scope, available artefacts,
  teacher-identified evidence location and which findings are actually verified.
  Explain how those materials support the goal and identify any unresolved gap.
- **Task and deliverable:** what learners do and decide; what they submit or
  demonstrate. Examples include an annotated timeline, command log with evidence
  references, hypothesis comparison, or a short findings report.
- **Support:** what is demonstrated, what is supplied, what learners discover,
  progressive hints, and when worked solutions become available.
- **Assessment and facilitation:** criteria, acceptable alternative methods,
  common misconceptions, instructor observation points and debrief questions.

For a short check, this may be a paragraph. For a substantial investigation, use
a compact design card or table. Relate proposals to the teacher's intended
professional task, rather than choosing an interesting tool demonstration first
and inventing its learning objective afterwards.

## Bloom examples in memory forensics

These are examples to discuss, not a required sequence or a claim that a specific
training image contains the listed artefacts.

| Level | Possible performance | Evidence the teacher can assess |
| --- | --- | --- |
| Remember | Recognize a familiar artefact or term | Identification or a short explanation of its meaning |
| Understand | Explain a process listing's meaning and limits | A reasoned interpretation of a supplied listing |
| Apply | Extract a process listing using a learned method | Reproducible steps and the resulting listing from supplied evidence |
| Analyze | Correlate process, command-line and connection artefacts | An evidence-linked account of relationships and discrepancies |
| Evaluate | Compare competing explanations using explicit criteria | A justified judgment that weighs corroboration, alternatives and limitations |
| Create | Design an investigation approach for an unfamiliar case | A coherent plan that combines appropriate methods and explains its choices |

The actual task, novelty, scaffolding, and reasoning determine the level. A
difficult command can still be procedural Apply; reading an already supplied
interpretation does not demonstrate the learner's own Analyze performance.

Make higher-order work feasible for the intended audience: technical beginners
can reason about a small, well-explained set of evidence, while advanced learners
may work with less guidance and more complex or incomplete evidence. Existing
forensic experience does not establish familiarity with every operating system,
artefact, tool, or investigative technique.

## Calibrate practice and support

Where appropriate, propose a progression:

1. A worked example makes both the method and the reasoning visible.
2. Guided practice provides questions and selective support; the learner still
   performs the analysis and explains findings.
3. Independent practice introduces a meaningful new case or decision and reduces
   support to match the objective.

Do not require all three stages in every activity. For experienced practitioners,
an independent case with targeted support may be appropriate from the outset.

Hints should reduce one difficulty at a time: orient the learner to an artefact
family, suggest a correlation to check, then provide more procedural help if
needed. Keep hints and worked answers separate in the design. Following an exact
command recipe may demonstrate a procedure; it does not establish independent
investigative reasoning by itself.

## Assess practical competence

Choose criteria appropriate to the agreed objective. Useful dimensions include:

- Correct findings and references to their supporting evidence.
- A documented, reproducible method and appropriate evidence handling.
- Interpretation, corroboration, and consideration of alternative explanations.
- Explicit limitations and appropriately qualified conclusions.
- Clear reporting to the intended audience.

Agree the weighting or pass requirements with the teacher when formal grading is
needed. Do not invent a universal pass mark, lab/theory percentage, or penalty for
using a different valid tool. Separate formative coaching from summative scoring.

Prepare a teacher version with verified expected findings where available,
reasoning, acceptable alternatives, common errors, hints and debrief prompts.
Mark evidence-dependent answers unverified until checked against the actual lab
materials and relevant tool versions. A scenario story is not an answer key.

## Basis for the pedagogical framework

- [UIC: Bloom's Taxonomy of Educational Objectives](https://teaching.uic.edu/blooms-taxonomy-of-educational-objectives/)
  describes the revised cognitive processes and knowledge dimensions.
- [Waterloo: Aligning Outcomes, Assessments, and Instruction](https://uwaterloo.ca/centre-for-teaching-excellence/catalogs/tip-sheets/aligning-outcomes-assessments-and-instruction)
  explains alignment between intended outcomes, learning activities and assessment.

The forensic examples, delivery conventions and teacher co-design workflow are
this skill's application of that framework, not claims that Bloom prescribes a
particular tool, question format, or proportion of practical work.
