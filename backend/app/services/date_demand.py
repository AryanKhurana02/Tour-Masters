from datetime import date


def estimate_date_demand(target_date: date, best_months: list[int]) -> tuple[int | None, list[str]]:
    if not best_months:
        return None, ["Curated peak-month information is unavailable; date demand uses neutral 50."]

    score = 50
    if target_date.weekday() >= 5:
        score += 10
    if target_date.month in best_months:
        score += 20
    else:
        score -= 10
    return max(0, min(100, score)), []
