# Delivery modes and native content

Read this when agreeing the delivery mode, attaching a lab, or implementing content
in Scenari. The delivery requirements below come from the teacher; they do not
imply that the corresponding custom block is installed in every instance.

## Delivery contract

| Aspect | E-learning | Onsite |
| --- | --- | --- |
| Learner environment | Kasm container shared using casting | Dedicated VM provided outside the slideshow |
| Integration | Existing `VirtualMachineBlock.type` block contains the casting URL and presents the container beside the content | No Kasm casting block or URL in the slideshow |
| Instructions | Refer to the lab panel when useful | Refer to the learner's dedicated VM |
| Preparation | Establish which casting URL and lab state apply to the activity | Describe VM image, evidence placement and setup prerequisites for the teacher |
| Learning expectations | Use the agreed objective, investigative task and assessment | Preserve those expectations when adapting the delivery |

Reuse shared forensic concepts, methods, and evidence tasks where appropriate.
Keep lab access and presentation-specific directions in the corresponding delivery
branch or an existing, verified publishing mechanism. Do not misuse unrelated
short/standard-version filters as if they were onsite/e-learning selectors.

The teacher identifies the generated traces and evidence for the activity. Confirm
their actual locations and relevant lab state in each delivery mode. Do not assume
that the Kasm container and the onsite VM contain identical files or tool versions;
make any differences that affect the task or its worked answers explicit.

Do not substitute a generic iframe or a remote-web item for the custom block
without discussing that change. A casting URL is an activity resource supplied
or selected by the teacher; do not invent one or open it merely to author content.
Keep access-bearing casting URLs out of reusable skill instructions and templates.

## Discover the actual custom block

1. Search the selected workspace for `VirtualMachineBlock.type` and inspect its
   native model, configuration and links.
2. Read an existing usage and establish where the casting URL is actually stored.
   Do not assume that the `.type` definition and the activity's block instance
   contain the same fields.
3. Follow the established structure and publishing conventions. Verify side-panel
   rendering in e-learning and absence from onsite output when both are generated.

An optional integration can define a native block at
`/_formattingBlocks/VirtualMachineBlock.type`. The inspected example uses
`dk_blockType`, label `Virtual lab`, formatting `focus`, and publication class
`virtualMachineBlock` (case-sensitive). Its definition configures the block;
**the activity instance contains the URL**. Other workspaces still need discovery.

With a compatible custom lab-panel skin, insert a native user-defined block,
select this type, give it an optional activity title, and put **one HTTPS casting
URL in its own text paragraph**. No iframe HTML is authored. The verified native
fragment inside a `dk:content` is:

```xml
<sp:typed>
  <dk:blocTi>
    <sp:type sc:refUri="/_formattingBlocks/VirtualMachineBlock.type"/>
  </dk:blocTi>
  <dk:flowAll><sp:txt><dk:text>
    <sc:para xml:space="preserve">https://kasm.example/cast/activity</sc:para>
  </dk:text></sp:txt></dk:flowAll>
</sp:typed>
```

Namespaces are `sc="http://www.utc.fr/ics/scenari/v3/core"`,
`sp="http://www.utc.fr/ics/scenari/v3/primitive"`, and `dk="kelis.fr:dokiel"`.
For the MCP's `kind=xml` path, include the fragment in a complete native parent
item and preserve the rest of its content. Read and preview before replacement.
The usual native validation and reference checks still apply.

The generated course must be opened through its `index.html` shell for the
persistent side panel. A lab block offers the panel; the learner presses
**Connect to lab** to load its URL. The iframe survives native lesson navigation,
hiding and resizing. Pages without the block hide the panel while retaining an
already loaded lab. A different URL requires explicit confirmation before
replacing the current lab page. Mobile learners switch between Lesson and Lab.

Put the same URL block on each e-learning page that needs the lab. The native
type **does not itself filter onsite output**: keep the block and URL in the
e-learning branch, outside shared content reused in onsite slides. CSS print
hiding is presentation behaviour, not source-level delivery separation.

Embedding is separate from authentication and VM availability. An iframe load
event does not prove access, connection or task completion. If sign-in is blocked
inside the iframe, the learner can use the new-tab link, authenticate, return and
press Reconnect. The lab provider controls whether reconnecting resumes a session.
Do not change Kasm or identity-provider settings or claim successful VM access
merely because the block validates or the panel appears.

If another target workspace lacks the block or compatible skin, identify that
dependency and continue the pedagogical design. Reuse a verified installation or
create the native definition within the teacher's authorized implementation scope.

## Publication and content selection

Use `dk_tutorialRoot` for e-learning and `dk_trainingRoot` for onsite slides and
booklets, subject to the installed model and extensions. For the choice of content
items, references and intention blocks, read
[semantic content selection](content-semantics.md). A publication root assembles
and configures an output; it does not replace the course's learning content.

Teacher notes and solution sections have publishing behaviours that must be
checked in the generated output. They are not, by themselves, access controls for
confidential assessment answers. Follow the teacher's agreed release strategy.
