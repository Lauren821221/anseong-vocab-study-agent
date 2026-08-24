from server.utils.config import generate_json
class GraderAgent:
    def run(self, questions, answers, words):
        objective=[]
        writing=[]
        for q in questions:
            ans=str(answers.get(str(q["id"]), answers.get(q["id"], ""))).strip()
            if q.get("format")=="short_answer":
                writing.append({"question":q,"user_answer":ans})
            else:
                correct=ans==str(q.get("answer","")).strip()
                objective.append({"id":q["id"],"correct":correct,"target_word":q.get("target_word",""),"user_answer":ans,"answer":q.get("answer","")})
        writing_results=[]
        if writing:
            prompt=f"""Grade these short English vocabulary-writing answers for a {len(writing)}-item vocabulary quiz.
Be age-appropriate and accept reasonable variants. Return JSON:
{{"items":[{{"id":1,"correct":true,"feedback":"Korean feedback"}}]}}
DATA={writing}
"""
            writing_results=generate_json(prompt).get("items",[])
        wr={str(x["id"]):x for x in writing_results}
        details=[]
        for x in objective: details.append(x)
        for item in writing:
            q=item["question"]; rr=wr.get(str(q["id"]),{})
            details.append({"id":q["id"],"correct":bool(rr.get("correct",False)),"target_word":q.get("target_word",""),"user_answer":item["user_answer"],"answer":q.get("answer",""),"feedback":rr.get("feedback","")})
        details.sort(key=lambda x:x["id"])
        correct=sum(1 for x in details if x["correct"])
        score=round(correct/len(questions)*100) if questions else 0
        weak=sorted({x["target_word"] for x in details if not x["correct"] and x.get("target_word")})
        learned=[w.get("word","") for w in words if w.get("word")]
        prompt=f"""Learner missed these vocabulary items: {weak}. Studied vocabulary: {learned}.
Suggest useful companion words to study together (synonyms, antonyms, collocations, or same semantic family), appropriate to the learner.
Return JSON: {{"review":[{{"word":"target","why":"Korean short reason","related_words":["word1","word2","word3"]}}]}}"""
        review=generate_json(prompt).get("review",[]) if weak else []
        return {"score":score,"correct_count":correct,"total":len(questions),"details":details,"weak_words":weak,"review":review}
