from langgraph.graph import END, StateGraph

from server.retrieval.material_rag import retrieve_focus_words
from server.workflow.agents.material_analyzer import MaterialAnalyzerAgent
from server.workflow.agents.problem_recommender import ProblemRecommenderAgent
from server.workflow.agents.quiz_generator import QuizGeneratorAgent
from server.workflow.agents.grader import GraderAgent
from server.workflow.agents.study_coach import StudyCoachAgent
from server.workflow.state import StudyState


def create_analysis_graph():
    graph = StateGraph(StudyState)

    analyzer = MaterialAnalyzerAgent()
    recommender = ProblemRecommenderAgent()

    graph.add_node("ANALYZE_MATERIAL", analyzer.run)
    graph.add_node("RECOMMEND_PROBLEMS", recommender.run)

    graph.set_entry_point("ANALYZE_MATERIAL")
    graph.add_edge("ANALYZE_MATERIAL", "RECOMMEND_PROBLEMS")
    graph.add_edge("RECOMMEND_PROBLEMS", END)

    return graph.compile()


def create_quiz_graph():
    graph = StateGraph(StudyState)
    generator = QuizGeneratorAgent()

    def retrieve_node(state):
        focus = retrieve_focus_words(
            state["analysis"],
            query=(
                f"{state['learner_level']} 수준 영어 문제 "
                f"{' '.join(state['problem_types'])}"
            ),
            k=max(8, state["question_count"]),
        )
        return {**state, "focus_words": focus}

    graph.add_node("RAG_RETRIEVE", retrieve_node)
    graph.add_node("GENERATE_QUIZ", generator.run)

    graph.set_entry_point("RAG_RETRIEVE")
    graph.add_edge("RAG_RETRIEVE", "GENERATE_QUIZ")
    graph.add_edge("GENERATE_QUIZ", END)

    return graph.compile()


def create_grading_graph():
    graph = StateGraph(StudyState)

    grader = GraderAgent()
    coach = StudyCoachAgent()

    graph.add_node("GRADE", grader.run)
    graph.add_node("STUDY_COACH", coach.run)

    graph.set_entry_point("GRADE")
    graph.add_edge("GRADE", "STUDY_COACH")
    graph.add_edge("STUDY_COACH", END)

    return graph.compile()
