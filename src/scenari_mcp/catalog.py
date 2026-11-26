"""Editorial guidance keyed by real Dokiel model IDs, never an invented creation schema."""

DOKIEL_TYPES = {
    "dk_concept": ("Concept", "Explain a notion or topic."),
    "dk_stepList": (
        "Procedure",
        "Describe a process using ordered steps, prerequisites and results.",
    ),
    "dk_steps": ("Procedure fragment", "Reuse a group of steps within procedures."),
    "dk_stepScreen": ("On-screen procedure", "Attach ordered steps to areas of a screenshot."),
    "dk_exercise": (
        "Guided exercise",
        "A statement with worked questions, answers and a general correction; "
        "distinct from an interactive quiz.",
    ),
    "dk_mcqSur": ("Single-choice question", "An interactive quiz with one correct answer."),
    "dk_mcqMur": ("Multiple-choice question", "An interactive quiz with several correct answers."),
    "dk_field": ("Closed question", "An interactive text-answer question."),
    "dk_numerical": ("Numerical question", "An interactive question expecting a number."),
    "dk_cloze": ("Fill-in-the-gaps", "An interactive exercise with missing words."),
    "dk_order": ("Ordering", "An interactive ordering exercise."),
    "dk_match": ("Matching", "An interactive matching exercise."),
    "dk_mcgSur": ("Single-choice graphic question", "A graphic quiz with one correct answer."),
    "dk_mcgMur": (
        "Multiple-choice graphic question",
        "A graphic quiz with several correct answers.",
    ),
    "dk_quizList": (
        "List of questions",
        "Group interactive quiz questions under a shared statement.",
    ),
    "dk_module": (
        "Training module",
        "Arrange theory, demonstrations, guided exercises and interactive quizzes.",
    ),
    "dk_theory": (
        "Theoretical contribution",
        "Present knowledge, reusing business items and parts.",
    ),
    "dk_demo": ("Demonstration", "Present a demonstration with optional visual resources."),
    "dk_eval": ("Assessment", "Organize an assessment using quiz content."),
    "dk_tutorial": ("Tutorial", "Combine training modules and assessments."),
    "dk_tutorialRoot": ("Training web publication", "Publication root for web training outputs."),
    "dk_trainingRoot": (
        "Onsite training publication",
        "Publication root for slides and training booklets.",
    ),
    "dk_screen": ("Screen", "Explain screenshot areas."),
    "dk_fragment": ("Content fragment", "Reuse a block of content."),
    "dk_part": ("Part", "Structure reusable content."),
    "dk_section": ("Section", "Organize a guide into sections."),
    "dk_userGuide": ("User guide", "Assemble reusable documentation items."),
    "dk_guideRoot": ("Guide publication", "Publication root for guide outputs."),
    "dk_definition": ("Definition", "Define a term for reuse."),
}


def describe_type(model: str | None, signature: str | None) -> dict:
    result = {
        "model": model,
        "signature": signature,
        "is_dokiel": bool(model and model.startswith("dk_")),
    }
    if model in DOKIEL_TYPES:
        result["label"], result["purpose"] = DOKIEL_TYPES[model]
    return result
