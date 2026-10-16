import random
from locust import HttpUser, task, between

# Diverse legal queries to avoid caching distortion (Handbook pg. 29)
BENCHMARK_LEGAL_QUESTIONS = [
    "ما هي شروط صحة الوعد بالتعاقد والاتفاق على المسائل الجوهرية؟",
    "العقد شريعة المتعاقدين ولا يجوز نقضه إلا باتفاق الطرفين",
    "متى يجوز للمتعاقد طلب إبطال العقد بسبب الوقوع في غلط جوهري؟",
    "ما هو حكم إجبار المدين على التنفيذ العيني للالتزام بعد إعذاره؟",
    "ما هي شروط رجوع الكفيل على المدين الأصلي بعد وفاء الدين وإخطاره؟",
    "ما هو نطاق حق مالك الشيء في استعماله واستغلاله والتصرف فيه؟",
    "ما هي التزامات مالك العقار المرتفق في صيانة واستعمال الارتفاق؟",
    "ما هو الوضع القانوني للمواد من 54 إلى 80 الملغاة؟",
    "كيف تنتهي حقوق الارتفاق وفقا لأحكام القانون المدني؟",
    "ما هي الآثار المترتبة على هلاك الشيء المرهون رهنا حيازيا؟",
]


class LegalRAGLoadTester(HttpUser):
    # Realistic user think-time between requests (Handbook pg. 29)
    wait_time = between(1, 3)

    @task(8)  # 80% traffic: Full synthesized answers
    def test_ask_endpoint(self):
        question = random.choice(BENCHMARK_LEGAL_QUESTIONS)
        self.client.post(
            "/ask",
            json={"question": question, "top_k": 3},
            name="POST /ask"
        )

    @task(2)  # 20% traffic: Streaming token answers
    def test_ask_stream_endpoint(self):
        question = random.choice(BENCHMARK_LEGAL_QUESTIONS)
        self.client.post(
            "/ask_stream",
            json={"question": question, "top_k": 3},
            name="POST /ask_stream"
        )