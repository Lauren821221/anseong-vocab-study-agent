QUESTION_TYPES = {
 "meaning_choice": ("뜻 고르기", "단어와 뜻의 연결을 확인하는 4지선다"),
 "picture_situation": ("그림·상황 단어 찾기", "짧고 구체적인 상황을 보고 알맞은 단어 선택"),
 "example_choice": ("올바른 예문 고르기", "단어가 자연스럽게 쓰인 문장 선택"),
 "sentence_blank": ("문장 빈칸 채우기", "문맥에 맞는 어휘 선택"),
 "context_meaning": ("문맥 속 단어 의미", "문장·짧은 글 속 의미 파악"),
 "syn_ant": ("동의어·반의어", "의미 관계를 이용한 어휘 확장"),
 "collocation_usage": ("Collocation & Usage", "자주 함께 쓰는 표현과 정확한 용법"),
 "sentence_completion": ("문장 완성", "어휘·문법을 함께 적용"),
 "reading_inference": ("독해·추론형 어휘", "짧은 지문에서 의미·의도 추론"),
 "guided_writing": ("단어 활용 영작", "제시 단어를 사용해 문장 만들기"),
}

LEVEL_GUIDE = {
 "유치원": {
   "easy":["meaning_choice","picture_situation"],
   "normal":["picture_situation","example_choice","sentence_blank"],
   "hard":["example_choice","sentence_blank","syn_ant"],
 },
 "초등 저학년": {
   "easy":["meaning_choice","picture_situation","example_choice"],
   "normal":["meaning_choice","picture_situation","sentence_blank","context_meaning"],
   "hard":["example_choice","sentence_blank","context_meaning","syn_ant"],
 },
 "초등 고학년": {
   "easy":["meaning_choice","example_choice","sentence_blank"],
   "normal":["sentence_blank","context_meaning","syn_ant","sentence_completion"],
   "hard":["context_meaning","collocation_usage","sentence_completion","reading_inference"],
 },
 "중학생": {
   "easy":["meaning_choice","sentence_blank","context_meaning"],
   "normal":["context_meaning","syn_ant","collocation_usage","sentence_completion"],
   "hard":["collocation_usage","sentence_completion","reading_inference","guided_writing"],
 },
 "고등학생": {
   "easy":["context_meaning","syn_ant","sentence_completion"],
   "normal":["collocation_usage","sentence_completion","reading_inference","guided_writing"],
   "hard":["context_meaning","collocation_usage","reading_inference","guided_writing"],
 },
 "성인": {
   "easy":["meaning_choice","context_meaning","sentence_completion"],
   "normal":["context_meaning","collocation_usage","sentence_completion","guided_writing"],
   "hard":["collocation_usage","reading_inference","guided_writing","context_meaning"],
 },
}

EXAM_GUIDE = {
 "TOSEL 수준": {
  "유치원":["meaning_choice","picture_situation"],
  "초등 저학년":["meaning_choice","picture_situation","sentence_blank"],
  "초등 고학년":["meaning_choice","sentence_blank","context_meaning"],
  "중학생":["sentence_blank","context_meaning","sentence_completion"],
  "고등학생":["context_meaning","sentence_completion","reading_inference"],
  "성인":["context_meaning","sentence_completion","reading_inference"],
 },
 "TOEFL Junior 수준":["sentence_blank","context_meaning","collocation_usage","sentence_completion","reading_inference"],
 "TOEFL 수준":["context_meaning","collocation_usage","reading_inference","sentence_completion","guided_writing"],
 "최선어학원 유형":["meaning_choice","context_meaning","sentence_completion","collocation_usage","reading_inference"],
}

def recommended_types(level, difficulty):
    if difficulty in ("쉬움","보통","어려움"):
        key={"쉬움":"easy","보통":"normal","어려움":"hard"}[difficulty]
        return LEVEL_GUIDE.get(level, LEVEL_GUIDE["성인"])[key]
    if difficulty=="TOSEL 수준":
        return EXAM_GUIDE[difficulty].get(level, EXAM_GUIDE[difficulty]["초등 고학년"])
    return EXAM_GUIDE.get(difficulty, LEVEL_GUIDE.get(level, LEVEL_GUIDE["성인"])["normal"])
