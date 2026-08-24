from server.workflow.catalog import QUESTION_TYPES, recommended_types
class RecommenderAgent:
    def run(self, learner_level, difficulty, words):
        keys=recommended_types(learner_level,difficulty)
        return {
          "recommended_type_ids":keys,
          "recommended_types":[{"id":k,"name":QUESTION_TYPES[k][0],"description":QUESTION_TYPES[k][1]} for k in keys],
          "reason":f"{learner_level} 학습자의 {difficulty} 설정과 업로드 어휘를 기준으로 추천했습니다."
        }
