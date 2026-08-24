from server.utils.config import analyze_image
class MaterialAnalyzerAgent:
    def run(self, image_bytes, mime_type, learner_level):
        return analyze_image(image_bytes, mime_type, learner_level)
