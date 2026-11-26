"""Small typed Dokiel grammar. All text is escaped, never interpreted as XML."""

import xml.etree.ElementTree as ET
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from .client import SC_NS

DK_NS = "kelis.fr:dokiel"
SP_NS = "http://www.utc.fr/ics/scenari/v3/primitive"
REF = f"{{{SC_NS}}}refUri"
SPACE = "{http://www.w3.org/XML/1998/namespace}space"
NS = {"sc": SC_NS, "dk": DK_NS, "sp": SP_NS}
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)

Text = Annotated[str, Field(min_length=1, max_length=50000, pattern=r"\S")]
Title = Annotated[str, Field(min_length=1, max_length=500, pattern=r"\S")]
Reference = Annotated[str, Field(min_length=1, max_length=2048)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Block(StrictModel):
    type: Literal["information", "tip", "remark", "warning"] = "information"
    title: Title | None = None
    paragraphs: Annotated[list[Text], Field(min_length=1, max_length=100)]


Blocks = Annotated[list[Block], Field(max_length=100)]
RequiredBlocks = Annotated[list[Block], Field(min_length=1, max_length=100)]


class Definition(StrictModel):
    kind: Literal["definition"]
    term: Title
    synonyms: Annotated[list[Title], Field(max_length=30)] = []
    paragraphs: Annotated[list[Text], Field(min_length=1, max_length=100)]


class Bibliography(StrictModel):
    kind: Literal["bibliography"]
    identifier: Title
    citation: Text


class WebReference(StrictModel):
    kind: Literal["web_reference"]
    title: Title
    url: Annotated[str, Field(min_length=1, max_length=4096)]

    @model_validator(mode="after")
    def check_url(self):
        parts = urlsplit(self.url)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username:
            raise ValueError("Use an HTTP(S) reference URL without credentials.")
        return self


class Concept(StrictModel):
    kind: Literal["concept"]
    title: Title
    definition: Reference | None = None
    blocks: RequiredBlocks


class Step(StrictModel):
    instruction: Title
    details: RequiredBlocks
    result: Blocks = []


class Procedure(StrictModel):
    kind: Literal["procedure"]
    title: Title
    introduction: Blocks = []
    prerequisites: Blocks = []
    steps: Annotated[list[Step], Field(min_length=1, max_length=100)]
    result: Blocks = []
    comments: Blocks = []


class ContentLink(StrictModel):
    type: Literal["concept", "procedure"]
    reference: Reference


class Theory(StrictModel):
    kind: Literal["theory"]
    title: Title
    blocks: Blocks = []
    links: Annotated[list[ContentLink], Field(max_length=100)] = []

    @model_validator(mode="after")
    def nonempty(self):
        if not self.blocks and not self.links:
            raise ValueError("Supply content blocks or linked concepts/procedures.")
        return self


class GuidedQuestion(StrictModel):
    prompt: Text
    solution: RequiredBlocks
    hints: Annotated[list[Text], Field(max_length=20)] = []


class GuidedExercise(StrictModel):
    kind: Literal["guided_exercise"]
    title: Title
    duration: Title | None = None
    statement: RequiredBlocks
    questions: Annotated[list[GuidedQuestion], Field(min_length=1, max_length=100)]
    solution: Blocks = []


class Choice(StrictModel):
    label: Text
    explanation: Text


class SingleChoiceQuiz(StrictModel):
    kind: Literal["single_choice_quiz"]
    question: Text
    choices: Annotated[list[Choice], Field(min_length=2, max_length=30)]
    correct_choice: Annotated[int, Field(ge=1, description="One-based choice number.")]
    feedback_right: Text
    feedback_wrong: Text

    @model_validator(mode="after")
    def correct_exists(self):
        if self.correct_choice > len(self.choices):
            raise ValueError("correct_choice must identify an existing choice (one-based).")
        return self


class Assessment(StrictModel):
    kind: Literal["assessment"]
    title: Title
    quizzes: Annotated[list[Reference], Field(min_length=1, max_length=100)]


class ModulePart(StrictModel):
    type: Literal["theory", "guided_exercise"]
    reference: Reference


class Module(StrictModel):
    kind: Literal["module"]
    title: Title
    objectives: Annotated[list[Text], Field(min_length=1, max_length=30)]
    parts: Annotated[list[ModulePart], Field(min_length=1, max_length=100)]


class Tutorial(StrictModel):
    kind: Literal["tutorial"]
    title: Title
    modules: Annotated[list[Reference], Field(min_length=1, max_length=100)]
    assessment: Reference | None = None


class Publication(StrictModel):
    kind: Literal["publication"]
    content: Reference


class XmlItem(StrictModel):
    """Advanced escape hatch: supplied native XML, not a generic HTTP request."""

    kind: Literal["xml"]
    model: Annotated[str, Field(pattern=r"^dk_[A-Za-z0-9_]+$", max_length=100)]
    xml: Annotated[str, Field(min_length=1, max_length=10485760)]


ItemSpec = Annotated[
    Definition
    | Bibliography
    | WebReference
    | Concept
    | Procedure
    | Theory
    | GuidedExercise
    | SingleChoiceQuiz
    | Assessment
    | Module
    | Tutorial
    | Publication
    | XmlItem,
    Field(discriminator="kind"),
]
ITEM_ADAPTER = TypeAdapter(ItemSpec)
MODELS = {
    "definition": "definition",
    "bibliography": "bib",
    "web_reference": "url",
    "concept": "concept",
    "procedure": "stepList",
    "theory": "theory",
    "guided_exercise": "exercise",
    "single_choice_quiz": "mcqSur",
    "assessment": "eval",
    "module": "module",
    "tutorial": "tutorial",
    "publication": "tutorialRoot",
}


def element(parent, name, text=None, **attrs):
    prefix, local = name.split(":")
    node = ET.SubElement(parent, f"{{{NS[prefix]}}}{local}", attrs)
    node.text = text
    return node


def paragraphs(parent, values):
    for value in values:
        node = element(parent, "sc:para", value)
        node.set(SPACE, "preserve")


def rich(parent, tag, value, container="dk:richTitle"):
    paragraphs(element(element(parent, tag), container), [value])


def flow(parent, values):
    node = element(parent, "dk:flowAll")
    paragraphs(element(element(node, "sp:txt"), "dk:text"), values)


def blocks(parent, values):
    tags = {"information": "infobloc", "tip": "tip", "remark": "note", "warning": "warning"}
    for value in values:
        node = element(parent, "sp:" + tags[value.type])
        meta = element(node, "dk:blocTi")
        if value.title:
            rich(meta, "sp:rTitle", value.title)
        flow(node, value.paragraphs)


def section(parent, tag, values, container="dk:comment"):
    if values:
        blocks(element(element(parent, tag), container), values)


def render_item(spec: ItemSpec) -> tuple[str, str]:
    """Return model ID and native XML. Safe parsing/live checks happen in the writer."""
    if isinstance(spec, XmlItem):
        return spec.model, spec.xml
    name = MODELS[spec.kind]
    root = ET.Element(f"{{{SC_NS}}}item")
    if isinstance(spec, Bibliography | Publication):
        # Dokiel 26 upgrades these items to native format version 1 on saving.
        root.set("version", "1")
    body = element(root, "dk:" + name)
    if isinstance(spec, Definition):
        meta = element(body, "dk:definitionMeta")
        element(meta, "sp:notion", spec.term)
        for synonym in spec.synonyms:
            element(meta, "sp:syn", synonym)
        paragraphs(element(element(meta, "sp:def"), "dk:textSimple"), spec.paragraphs)
    elif isinstance(spec, Bibliography):
        meta = element(body, "dk:bibM")
        element(meta, "sp:id", spec.identifier)
        paragraphs(element(element(meta, "sp:desc"), "dk:docTxt"), [spec.citation])
    elif isinstance(spec, WebReference):
        meta = element(body, "dk:urlM")
        element(meta, "sp:url", spec.url)
        rich(meta, "sp:title", spec.title)
        element(meta, "sp:doc")
    elif isinstance(spec, Concept):
        element(element(body, "dk:conceptM"), "sp:name", spec.title)
        if spec.definition:
            element(body, "sp:def").set(REF, spec.definition)
        section(body, "sp:desc", spec.blocks)
    elif isinstance(spec, SingleChoiceQuiz):
        element(body, "dk:quizM")
        flow(element(body, "sc:question"), [spec.question])
        choices = element(body, "sc:choices")
        for choice in spec.choices:
            node = element(choices, "sc:choice")
            rich(node, "sc:choiceLabel", choice.label, "dk:para")
            rich(node, "sc:choiceExplanation", choice.explanation, "dk:para")
        solution = element(body, "sc:solution", choice=str(spec.correct_choice))
        for tag, text in [
            ("sc:feedbackRight", spec.feedback_right),
            ("sc:feedbackWrong", spec.feedback_wrong),
        ]:
            flow(element(element(element(solution, tag), "dk:fdbck"), "sp:co"), [text])
    elif isinstance(spec, Publication):
        element(body, "dk:tutorialRootM")
        element(body, "sp:content").set(REF, spec.content)
    else:
        meta = element(body, f"dk:{name}M")
        rich(meta, "sp:title", spec.title)
        if isinstance(spec, Procedure):
            section(body, "sp:intro", spec.introduction)
            section(body, "sp:prereq", spec.prerequisites)
            steps = element(element(body, "sp:steps"), "dk:steps")
            element(steps, "dk:stepsM")
            for step in spec.steps:
                node = element(element(steps, "sp:step"), "dk:step")
                rich(element(node, "dk:stepM"), "sp:ti", step.instruction, "dk:para")
                section(node, "sp:detail", step.details)
                section(node, "sp:result", step.result)
            section(body, "sp:result", spec.result)
            section(body, "sp:comment", spec.comments)
        elif isinstance(spec, Theory):
            content = element(element(body, "sp:content"), "dk:content")
            blocks(content, spec.blocks)
            for link in spec.links:
                element(content, "sp:def" if link.type == "concept" else "sp:op").set(
                    REF, link.reference
                )
        elif isinstance(spec, GuidedExercise):
            if spec.duration:
                element(meta, "sp:time", spec.duration)
            section(body, "sp:exposition", spec.statement, "dk:content")
            for question in spec.questions:
                node = element(element(body, "sp:exerciseQ"), "dk:exerciseQ")
                rich(node, "sp:desc", question.prompt, "dk:para")
                values = question.solution + [
                    Block(type="tip", paragraphs=[h]) for h in question.hints
                ]
                section(node, "sp:solution", values, "dk:content")
            section(body, "sp:solution", spec.solution, "dk:content")
        elif isinstance(spec, Assessment):
            for ref in spec.quizzes:
                element(body, "sp:quiz").set(REF, ref)
        elif isinstance(spec, Module):
            start = element(element(body, "sp:start"), "dk:startTrain")
            element(start, "dk:rTitle")
            objective = element(start, "sp:objectives")
            element(objective, "dk:blocTi")
            flow(objective, spec.objectives)
            for part in spec.parts:
                element(body, "sp:theory" if part.type == "theory" else "sp:exercise").set(
                    REF, part.reference
                )
        elif isinstance(spec, Tutorial):
            for ref in spec.modules:
                element(body, "sp:module").set(REF, ref)
            if spec.assessment:
                element(body, "sp:eval").set(REF, spec.assessment)
    return "dk_" + name, ET.tostring(root, encoding="unicode", xml_declaration=True)
