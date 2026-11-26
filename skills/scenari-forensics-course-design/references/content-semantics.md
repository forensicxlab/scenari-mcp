# Select Dokiel structures by meaning

Read before selecting item types, building source XML, or reviewing authored
content. Distinguish a reusable content/reference item, a block inside an item,
and an inline link or text enrichment. Choose semantics before appearance.

## Reusable items and learning structure

| Content intent | Native item model | Selection guidance |
| --- | --- | --- |
| Short definition of a term or notion | `dk_definition` | Reuse a definition reference; link it from a concept or the relevant text. Supports glossary publication when configured. |
| Explanation of a forensic concept | `dk_concept` | Use for a substantive explanation, potentially drawing on linked definitions. A concept and a short term definition serve different purposes. |
| Citation of a book, paper, standard, report, or other source | `dk_bib` | Record source information and link it at the relevant claim; supports bibliography/webography publication. A heading called "References" with plain-text entries is not equivalent. |
| Reusable website or document address | `dk_url` | Centralize a destination that is reused or maintained as a reference. A URL item alone does not supply bibliographic authorship, date, or source description. |
| Ordered operating procedure | `dk_stepList` | Use native steps, prerequisites, results and relevant blocks; reuse `dk_steps` for a shared sequence when appropriate. |
| Explanation of screenshot regions | `dk_screen` | Use native screen/zone structure when the activity needs it, rather than a flat screenshot with unrelated prose. |
| Reusable content fragment or structured part | `dk_fragment` / `dk_part` | Use meaningful reusable units. Avoid a separate item for every short paragraph or note. |
| Demonstration | `dk_demo` | Present a worked method and its reasoning using the permitted demonstration structure. |
| Theoretical contribution in a training sequence | `dk_theory` | Assemble explanations and reference reusable business items, including concepts and procedures. |
| Guided practical investigation with open questions and worked answers | `dk_exercise` | Keep the case, learner questions and solutions in their native roles. |
| Interactive automatically assessed question | Appropriate quiz model | Select single/multiple choice, text, numeric, matching or another supported type from the response and scoring needed. A practical report or reasoning rubric may require teacher assessment. |
| Group of related interactive questions | `dk_quizList` | Use when shared context and the permitted question grouping serve the activity. |
| Assessment | `dk_eval` | Organize questions and assessment feedback. |
| Learning sequence | `dk_module` | Compose theory, demonstrations, practical activities and other supported elements. |
| Module combined with an assessment | `dk_tutorial` | Link the relevant module and assessment. |

Search for suitable existing definitions and references before creating new ones.
Check meaning, source edition and scope, not just matching titles. Link reusable
items rather than duplicating them across e-learning and onsite content. Keep
teacher-produced evidence references distinct from external bibliographic sources.

Use the permitted native inline reference or link where the term, claim or
destination occurs. A reference item that is merely stored in the workspace is
not automatically included in a publication. Verify the link and applicable
publication settings; do not promise a glossary or bibliography solely because
the corresponding item exists. Do not invent missing citation details.

## Intention blocks within content

These are semantic blocks, not necessarily standalone items. The labels below
describe Dokiel's editorial meanings; determine the exact XML slot and nesting
from the installed version and existing source examples.

| Meaning | Native intention block | Forensic teaching example |
| --- | --- | --- |
| Neutral explanation, introduction or transition | Information | Introduce the artefacts provided for an activity. |
| Methodological guidance | Advice | Recommend corroborating a finding with an independent artefact. |
| Optional shortcut or practical convenience | Tip | Offer a filtering shortcut after the learner understands its purpose. |
| Qualification, clarification or contextual note | Remark | Clarify the scope or interpretation of a displayed result. |
| Consequential risk or condition needing attention | Warning | Explain that a proposed operation would change the evidence being examined. |
| Illustration of a concept or explanation | Example | Show a clearly identified sample output and explain what it illustrates. |
| Legal information or a mandatory requirement | Legal | Present an applicable, sourced requirement; do not turn a local preference into a legal claim. |
| Optional material for further investigation | Complement | Offer a deeper explanation that the main task does not depend on. |

Use a tip for something optional; a task-critical step or a limitation essential
to interpreting the evidence must remain in the main instructions or an
appropriately prominent block. A mandatory methodological requirement should not
be disguised as an optional shortcut. Avoid filling content with warnings just
for visual emphasis. The meaning, not the desired icon or colour, selects the block.

Use real title, prerequisite, step, result, question, hint and solution slots where
the item provides them. Do not simulate these with styled paragraphs. Keep hints
and solutions in the exercise structure established by the teacher's release
strategy; an ordinary Tip block does not itself implement progressive disclosure.

## Custom types and teacher notes

Inspect and reuse installed custom types when their intended use is established.
For example, the dedicated workspace contains `Tool.type`, `Trace.type`,
`CommandList.type` and `Trainer.type`. Their filenames alone do not establish the
complete structure, intended payload or publishing behaviour. Verify an existing
definition and usage before creating a typed block that references one.

The teacher's `VirtualMachineBlock.type` has the specific e-learning lab purpose
described in [delivery and Dokiel mapping](delivery-and-dokiel.md); follow that
contract rather than treating it as an ordinary explanatory block.

Use the model's trainer-note structure for facilitation instructions intended for
the teacher. Do not assume a styled block named `Trainer.type` makes its contents
teacher-only. Check the actual output behaviour and distinguish publishing
visibility from access controls.

## Verify the selection and implementation

For substantial authoring, a compact plan can list the content unit, editorial
purpose, native model or block, reused references and delivery-specific placement.
This makes the choices reviewable without asking the teacher to approve every tag.

Check the target workspace's installed model and extensions. `list_item_types`
discovers item model IDs; it does not enumerate all nested blocks, fields or their
allowed order. Use existing valid source examples and version-matched model
documentation to establish those details. When a mapping is unverified, report
that fact instead of inventing a plausible tag or silently using generic text.

After an authorized write, inspect returned models, native blocks and reference
links, and check Scenari's validation results where available. In generated
outputs, check reference destinations, glossary/bibliography inclusion when
enabled, semantic block presentation, solution visibility and both delivery modes
as relevant. Successful XML validation alone does not prove an editorial choice
matches the intended teaching meaning.

## Sources and verified scope

- [Dokiel 26: intention blocks and rich text](https://doc.scenari.software/Dokiel@26/reference/en/co/blocIntention.xhtml)
- [Dokiel 26: reference items](https://doc.scenari.software/Dokiel@26/reference/en/co/references.xhtml)
- [Dokiel 26: definitions](https://doc.scenari.software/Dokiel@26/reference/en/co/references_1.xhtml)
- [Dokiel 26: bibliographic entries](https://doc.scenari.software/Dokiel@26/reference/en/co/references_2.xhtml)
- [Dokiel 26: web addresses](https://doc.scenari.software/Dokiel@26/reference/en/co/references_3.xhtml)

The `dk_definition`, `dk_bib` and `dk_url` models and representative XML structures
were also inspected through the dedicated instance's read-only API. This reference
is a selection guide, not a complete XML schema or proof of support in every
Dokiel version.
