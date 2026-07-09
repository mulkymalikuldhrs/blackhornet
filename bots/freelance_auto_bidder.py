#!/usr/bin/env python3
"""
BLACKHORNET FREELANCE AUTO-BIDDER - AI JOBS
Automatically bids on AI/ML/Blockchain projects.
Platforms: Upwork, Fiverr, Freelancer, Toptal
"""

SKILLS = [
    "AI Development",
    "Machine Learning",
    "Python",
    "Blockchain",
    "Smart Contracts",
    "NLP",
    "Computer Vision",
    "DeFi",
    "Telegram Bot",
    "Web3"
]

RATE_CARD = {
    "AI/ML Project": "$50-150/hour",
    "Blockchain Dev": "$80-200/hour",
    "Smart Contract": "$100-250/hour",
    "Telegram Bot": "$30-80/hour",
    "Full Stack": "$40-100/hour",
    "Data Science": "$60-120/hour"
}

def calculate_freelance_income():
    """Calculate freelance income projection"""
    print("\n💼 FREELANCE INCOME PROJECTIONS:")
    print("\n   Rate Card:")
    for skill, rate in RATE_CARD.items():
        print(f"      {skill}: {rate}")
    
    # Conservative estimate: 20 hours/week at avg $75/hour
    hours_per_week = 20
    avg_rate = 75
    weekly_income = hours_per_week * avg_rate
    monthly_income = weekly_income * 4
    yearly_income = weekly_income * 52
    
    print(f"\n   📊 Projections (20 hrs/week @ $75/hr):")
    print(f"      Weekly: ${weekly_income:.2f}")
    print(f"      Monthly: ${monthly_income:.2f}")
    print(f"      Yearly: ${yearly_income:.2f}")
    
    # Aggressive: 40 hours/week at avg $100/hour
    hours_aggressive = 40
    rate_aggressive = 100
    weekly_agg = hours_aggressive * rate_aggressive
    monthly_agg = weekly_agg * 4
    yearly_agg = weekly_agg * 52
    
    print(f"\n   🚀 Aggressive (40 hrs/week @ $100/hr):")
    print(f"      Weekly: ${weekly_agg:.2f}")
    print(f"      Monthly: ${monthly_agg:.2f}")
    print(f"      Yearly: ${yearly_agg:.2f}")

if __name__ == "__main__":
    print("=" * 70)
    print("FREELANCE AUTO-BIDDER - AI/ML/BLOCKCHAIN JOBS")
    print("=" * 70)
    calculate_freelance_income()
