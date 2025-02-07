from transformers import pipeline
import torch

class QASystem:
    def __init__(self):
        self.device = 0 if torch.cuda.is_available() else -1
        self.qa_pipeline = pipeline(
            "question-answering",
            model="deepset/roberta-base-squad2",
            device=self.device
        )

    def answer_question(self, question, context):
        if not question.strip():
            return {"error": "Question cannot be empty."}
        if not context.strip():
            context = "Please provide context for better accuracy."

        try:
            response = self.qa_pipeline({'question': question, 'context': context})
            return {
                "answer": response['answer'],
                "confidence": response['score'],
                "context": context  
            }
        except Exception as e:
            return {"error": f"Error processing request: {e}"}

# Example usage
if __name__ == "__main__":
    qa = QASystem()
    question = "Who discovered gravity?"
    context = "Isaac Newton was a physicist who formulated the laws of motion and universal gravitation."
    print(qa.answer_question(question, context))
