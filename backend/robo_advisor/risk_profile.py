"""
Risk questionnaire -> risk profile.

Five questions, each answered 1 (most cautious) to 4 (most risk-tolerant).
The frontend shows the questions; the backend only needs the 5 numbers.
"""

QUESTIONS = [
    {"id": 1, "text": "How long do you plan to stay invested?",
     "options": ["Under 2 years", "2-4 years", "4-7 years", "More than 7 years"]},
    {"id": 2, "text": "If your portfolio fell 20% in a month, what would you do?",
     "options": ["Sell everything", "Sell some", "Hold", "Buy more"]},
    {"id": 3, "text": "What is your main goal?",
     "options": ["Protect my money", "Steady income", "Balanced growth", "Maximum growth"]},
    {"id": 4, "text": "How much investing experience do you have?",
     "options": ["None", "A little", "Moderate", "A lot"]},
    {"id": 5, "text": "How stable is your income?",
     "options": ["Very unstable", "Somewhat unstable", "Stable", "Very stable"]},
]


def score_risk_profile(answers: list[int]) -> tuple[str, int]:
    """
    answers: 5 integers, each 1-4. Returns (profile_name, total_score).
        5-10 -> conservative | 11-15 -> balanced | 16-20 -> aggressive
    """
    if len(answers) != len(QUESTIONS):
        raise ValueError(f"Expected {len(QUESTIONS)} answers, got {len(answers)}.")
    if any(a not in (1, 2, 3, 4) for a in answers):
        raise ValueError("Each answer must be 1, 2, 3 or 4.")
    score = sum(answers)
    if score <= 10:
        return "conservative", score
    if score <= 15:
        return "balanced", score
    return "aggressive", score
