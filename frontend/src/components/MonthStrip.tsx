const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function MonthStrip({ months }: { months: number[] }) {
  return (
    <section className="month-strip" aria-label="Typical months listed for this place">
      <div className="month-list">
        {MONTHS.map((month, index) => (
          <span className={months.includes(index + 1) ? "month is-listed" : "month"} key={month}>{month}</span>
        ))}
      </div>
      <p>Typical months, not a forecast for a specific day.</p>
    </section>
  );
}
