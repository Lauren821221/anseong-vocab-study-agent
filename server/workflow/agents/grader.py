from server.utils.config import generate_json

class GraderAgent:
    def run(self, learner_level, questions, answers, words):
        details, writing = [], []
        for q in questions:
            ans = str(answers.get(str(q["id"]), answers.get(q["id"], ""))).strip()
            if q.get("format") == "short_answer":
                writing.append({"question": q, "user_answer": ans})
            else:
                details.append({
                    "id": q["id"],
                    "correct": ans == str(q.get("answer", "")).strip(),
                    "target_word": q.get("target_word", ""),
                    "user_answer": ans,
                    "answer": q.get("answer", ""),
                })

        if writing:
            prompt = f"""
Grade these short vocabulary-writing answers for learner level '{learner_level}'.
Accept reasonable age-appropriate variants.
Return JSON only:
{{"items":[{{"id":1,"correct":true,"feedback":"Korean feedback"}}]}}
DATA={writing}
"""
            judged = generate_json(prompt).get("items", [])
            judged_map = {str(x["id"]): x for x in judged}
            for item in writing:
                q = item["question"]
                rr = judged_map.get(str(q["id"]), {})
                details.append({
                    "id": q["id"],
                    "correct": bool(rr.get("correct", False)),
                    "target_word": q.get("target_word", ""),
                    "user_answer": item["user_answer"],
                    "answer": q.get("answer", ""),
                    "feedback": rr.get("feedback", ""),
                })

        details.sort(key=lambda x: x["id"])
        correct = sum(1 for x in details if x["correct"])
        score = round(correct / len(questions) * 100) if questions else 0
        weak = sorted({x["target_word"] for x in details if not x["correct"] and x.get("target_word")})

        review = []
        if weak:
            prompt = f"""
Learner level: {learner_level}
Weak vocabulary: {weak}

For EACH weak word, create a compact study card.
Suggest words that are genuinely useful to learn together:
- synonyms
- antonyms
- related words / word family / semantic neighbors
- collocations or common expressions
Also give TWO example sentences adjusted to learner level.

Return JSON only:
{{
 "review":[
   {{
     "word":"target",
     "synonyms":["..."],
     "antonyms":["..."],
     "related_words":["..."],
     "collocations":["..."],
     "examples":["English sentence 1","English sentence 2"],
     "tip":"short Korean learning tip"
   }}
 ]
}}
"""
            review = generate_json(prompt).get("review", [])

        return {
            "score": score,
            "correct_count": correct,
            "total": len(questions),
            "details": details,
            "weak_words": weak,
            "review": review,
        }
