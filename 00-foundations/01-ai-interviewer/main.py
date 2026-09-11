from langgraph.graph import StateGraph,START, END
from typing import TypedDict, Dict, List
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
import httpx
from dotenv import load_dotenv
import json

load_dotenv()

model = ChatOpenAI(
    model="gpt-4o-mini",
    http_client=httpx.Client(verify=False),
)

class Criteria(BaseModel):
    description: str = Field(
        description="A single, specific thing the answer is judged on (e.g. 'Explains the virtual DOM and reconciliation')."
    )
    max_score: int = Field(
        description="Maximum points this criterion is worth. Should be a positive integer.",
        ge=1,
    )

class Rubric(BaseModel):
    total_score: int = Field(
        description="Sum of the max_score of all criteria. Must equal the total of every criterion's max_score."
    )
    criteria: List[Criteria] = Field(
        description="The list of criteria used to grade the answer. Provide 3-5 distinct, non-overlapping criteria."
    )

class QuestionRubric(BaseModel):
    question: str = Field(
        description="A clear, role-appropriate interview question. Ask exactly one question."
    )
    rubric: Rubric = Field(
        description="The rubric used to evaluate the candidate's answer to the question above."
    )

class Evaluation(BaseModel):
    score: str = Field(
        description="The awarded score as 'earned/total' (e.g. '7/10'), reflecting how well the answer meets the rubric criteria."
    )
    feedback: str = Field(
        description="Constructive feedback referencing specific rubric criteria: what was done well and what was missing."
    )

class LLMState(TypedDict):
    role: str
    rubric: QuestionRubric
    answer: str
    score: str
    feedback: str

question_llm = model.with_structured_output(QuestionRubric)

evaluation_llm = model.with_structured_output(Evaluation)

def generat_question_rubric(state:LLMState) -> LLMState:

    prompt = f"""
Generate an interview question and evaluation rubric for a {state["role"]}.
"""

    response = question_llm.invoke(prompt)

    print(f"""
    AI: {response.question}
    """)

    state["rubric"] = response

    return state;

def get_user_answer(state:LLMState) -> LLMState:

    answer = input("Enter your answer: ")

    state["answer"] = answer

    return state;

def evaluation(state:LLMState) -> LLMState:

    prompt = f"""
    user is {state["role"]}
    based this question and rubric: {state["rubric"]}
    evaluate given this answer :{state["answer"]}
    """

    response = evaluation_llm.invoke(prompt)

    state["score"] = response.score
    state["feedback"] = response.feedback

    return state;


graph = StateGraph(LLMState);
graph.add_node('generat_question_rubric',generat_question_rubric);
graph.add_node('get_user_answer',get_user_answer);
graph.add_node('evaluation',evaluation)

graph.add_edge(START,'generat_question_rubric')
graph.add_edge('generat_question_rubric','get_user_answer')
graph.add_edge('get_user_answer','evaluation')
graph.add_edge('evaluation',END)
workflow = graph.compile()

initial_state = {
    "role": "react developer",
    "rubric": {},
    "answer": "",
    "score": "",
    "feedback": "",
}

try:
    final_state = workflow.invoke(initial_state)
    print(json.dumps(final_state, indent=4, default=lambda o: o.model_dump()))
except Exception as e:
    import traceback
    traceback.print_exc()