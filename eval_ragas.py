import os
import json
from dotenv import load_dotenv
from groq import Groq
from query_engine import query_sop, get_working_model

load_dotenv()

TEST_CASES = [
    {
        "question": "Verification process kitna time leta hai?",
        "ground_truth": "Within 24 hours / 24 ghante ke andar"
    },
    {
        "question": "What is the primary objective of acute public health event management?",
        "ground_truth": "Minimize negative health and socioeconomic consequences through a timely, appropriate, and well-coordinated response"
    }
]

def evaluate_with_llm():
    print("--- Running Robust LLM-as-a-Judge Evaluation ---\n")
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    eval_model = get_working_model(groq_client)
    
    passed = 0
    
    for idx, test in enumerate(TEST_CASES, 1):
        q = test["question"]
        truth = test["ground_truth"]
        
        response = query_sop(q)
        
        judge_prompt = f"""You are an objective evaluation judge for a RAG system.
Compare the Generated Answer against the Ground Truth.
Evaluate factual consistency and correctness. Ignore language differences (English vs Roman Urdu).

Question: {q}
Ground Truth: {truth}
Generated Answer: {response}

Respond ONLY in valid JSON format with two keys:
"verdict": "PASSED" or "FAILED"
"reason": "a brief 1-sentence explanation"
"""

        try:
            res = groq_client.chat.completions.create(
                model=eval_model,
                messages=[{"role": "user", "content": judge_prompt}],
                temperature=0.0,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            eval_data = json.loads(res.choices[0].message.content)
            verdict = eval_data.get("verdict", "FAILED").upper()
            reason = eval_data.get("reason", "No explanation returned.")
        except Exception as err:
            verdict = "FAILED"
            reason = f"JSON evaluation error: {err}"
        
        is_passed = verdict == "PASSED"
        if is_passed:
            passed += 1
            
        print(f"Test #{idx}:")
        print(f"  Question : {q}")
        print(f"  Answer   : {response}")
        print(f"  Verdict  : {verdict}")
        print(f"  Reason   : {reason}\n")
        
    accuracy = (passed / len(TEST_CASES)) * 100
    print(f"Final System Accuracy: {passed}/{len(TEST_CASES)} ({accuracy:.1f}%)")

if __name__ == "__main__":
    evaluate_with_llm()