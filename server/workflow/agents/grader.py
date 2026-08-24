class GraderAgent:

    def run(self, state):
        quiz = state["quiz"]
        answers = state["answers"]

        details = []
        weak_words = []
        score = 0

        for q in quiz.get("questions", []):
            qid = q["id"]
            user_answer = str(answers.get(qid, "")).strip()
            correct_answer = str(q.get("correct_answer", "")).strip()

            is_correct = (
                user_answer.casefold() == correct_answer.casefold()
            )

            if is_correct:
                score += 1
            elif q.get("target_word"):
                weak_words.append(q["target_word"])

            details.append(
                {
                    "id": qid,
                    "question": q.get("question", ""),
                    "correct": is_correct,
                    "user_answer": user_answer,
                    "correct_answer": correct_answer,
                    "target_word": q.get("target_word", ""),
                    "explanation": q.get("explanation", ""),
                }
            )

        total = len(quiz.get("questions", []))
        accuracy = round(score / total * 100) if total else 0

        grading = {
            "score": score,
            "total": total,
            "accuracy": accuracy,
            "details": details,
            "weak_words": list(dict.fromkeys(weak_words)),
        }

        return {**state, "grading": grading}
