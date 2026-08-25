from server.workflow.catalog import QUESTION_TYPES, recommended_types

class RecommenderAgent:
    def run(self, learner_level, difficulty, school_mode, words):
        keys = recommended_types(learner_level, difficulty, school_mode)
        names = [QUESTION_TYPES[k][0] for k in keys]
        return {
            "recommended_type_ids": keys,
            "recommended_types": [
                {"id": k, "name": QUESTION_TYPES[k][0], "description": QUESTION_TYPES[k][1]}
                for k in keys
            ],
            "reason": (
                f"{learner_level} · {difficulty} · {school_mode} 설정과 "
                f"업로드된 {len(words)}개 학습 단어를 기준으로 "
                f"{', '.join(names)} 유형을 우선 추천했습니다."
            ),
        }
