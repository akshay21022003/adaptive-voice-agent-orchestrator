from app.graph.state import TutorState


def lesson_prompt(state: TutorState) -> str:
    return f"""
    You are an AI {state["language"]} language expert.
    The user is currently at the {state["level"]} level.
    Lesson topic: {state["lesson_topic"]}

    Generate a lesson for the user at their current level with important word
    translations and examples. For example:

    Lesson: Greetings in Spanish (A1)

    Vocabulary:
    - Hola        -> Hello
    - Buenos dias -> Good morning
    - Como estas? -> How are you?

    Grammar Tip:
    Spanish has formal (usted) and informal (tu) forms.
    Use "usted" with strangers or elders.

    Example Dialogue:
    A: Hola! Como estas?
    B: Bien, gracias! Y tu?
    """


def quiz_prompt(state: TutorState) -> str:
    return f"""
    You are an AI quiz generator.
    User profile: level {state["level"]}, learning {state["language"]}.
    Based on this lesson: {state["lesson"]}

    Generate exactly two quiz questions, scoped to the lesson:
    1. A translation question.
    2. A complete-the-sentence question.
    """


def evaluation_prompt(state: TutorState) -> str:
    return f"""
    You are a language expert. Evaluate the user's answers based on the
    provided lesson and quiz. The score is the number of correct answers
    out of the number of questions; correct + incorrect must equal the
    number of questions.

    Lesson: {state["lesson"]}
    Quiz: {state["quiz"]}
    User answer: {state["answer"]}
    """
