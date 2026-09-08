from app.analytics.schemas import VideoReport
def build_report(llm, production, stats, rates, retention, comparison, growth) -> VideoReport:
    score=min(100,round((retention.avg_pct*60+rates.engagement_rate*400+min(20,comparison.vs_mean*10)),1))
    worked=["Retention held" if retention.avg_pct>=.6 else "Initial distribution recorded"]
    failed=[f"{len(retention.drops)} retention drops detected"] if retention.drops else []
    next_step="Keep the hook and tighten the first detected drop." if retention.drops else "Test a stronger first-two-second hook."
    return VideoReport(markdown=f"# Video report\n\nGrowth: {growth}\nVirality score: {score}",what_worked=worked,what_failed=failed,next_recommendation=next_step,virality_score=score)
