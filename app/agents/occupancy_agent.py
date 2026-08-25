
import statistics
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..models import OccupancyRecord, Alert

OVERCROWD_THRESHOLD = 0.90  # >=90% of zone capacity counts as overcrowded


class OccupancyAgent:
    def __init__(self, db: Session):
        self.db = db

    def _recent(self, facility_id: int | None = None, hours: int = 24):
        since = datetime.utcnow() - timedelta(hours=hours)
        q = self.db.query(OccupancyRecord).filter(OccupancyRecord.timestamp >= since)
        if facility_id:
            q = q.filter(OccupancyRecord.facility_id == facility_id)
        return q.order_by(OccupancyRecord.timestamp).all()

    # ---------- Zone utilization (matches Milestone-3 mock: "Zone Occupancy Distribution") ----------
    def zone_distribution(self, facility_id: int | None = None, hours: int = 24):
        rows = self._recent(facility_id, hours)
        zones: dict[str, list] = {}
        for r in rows:
            zones.setdefault(r.zone, []).append(r)
        result = {}
        for zone, recs in zones.items():
            avg_count = statistics.mean(r.occupancy_count for r in recs)
            capacity = recs[0].capacity
            result[zone] = round(avg_count / capacity * 100, 1) if capacity else 0
        return dict(sorted(result.items(), key=lambda x: -x[1]))

    # ---------- KPIs (matches mock: Occupancy Rate, Active Visitors) ----------
    def kpis(self, facility_id: int | None = None):
        rows = self._recent(facility_id, hours=1)
        if not rows:
            rows = self._recent(facility_id, hours=6)
        if not rows:
            return {"occupancy_rate_pct": 0, "active_visitors": 0}
        total_count = sum(r.occupancy_count for r in rows)
        total_capacity = sum(r.capacity for r in rows) or 1
        return {
            "occupancy_rate_pct": round(total_count / total_capacity * 100, 1),
            "active_visitors": total_count,
        }

    # ---------- Overcrowding detection ----------
    def detect_overcrowding(self, facility_id: int | None = None, hours: int = 6):
        rows = self._recent(facility_id, hours)
        flagged = []
        for r in rows:
            if r.capacity and (r.occupancy_count / r.capacity) >= OVERCROWD_THRESHOLD:
                flagged.append({
                    "facility_id": r.facility_id,
                    "zone": r.zone,
                    "occupancy_count": r.occupancy_count,
                    "capacity": r.capacity,
                    "utilization_pct": round(r.occupancy_count / r.capacity * 100, 1),
                    "timestamp": r.timestamp.isoformat(),
                })
        return flagged

    # ---------- Heatmap data (zone x hour-of-day average utilization) ----------
    def heatmap(self, facility_id: int | None = None, days: int = 7):
        rows = self._recent(facility_id, hours=24 * days)
        grid: dict[str, dict[int, list]] = {}
        for r in rows:
            grid.setdefault(r.zone, {}).setdefault(r.timestamp.hour, []).append(
                r.occupancy_count / r.capacity * 100 if r.capacity else 0
            )
        heatmap = {}
        for zone, hours_map in grid.items():
            heatmap[zone] = {h: round(statistics.mean(v), 1) for h, v in sorted(hours_map.items())}
        return heatmap

    # ---------- Workspace allocation recommendations ----------
    def recommendations(self, facility_id: int | None = None):
        dist = self.zone_distribution(facility_id, hours=24 * 7)
        recs = []
        for zone, util in dist.items():
            if util >= 85:
                recs.append({
                    "zone": zone, "priority": "High",
                    "recommendation": f"{zone} averaging {util}% utilization — consider "
                                       f"expanding capacity or adding an overflow zone.",
                })
            elif util <= 30:
                recs.append({
                    "zone": zone, "priority": "Low",
                    "recommendation": f"{zone} averaging only {util}% utilization — candidate "
                                       f"for space consolidation or repurposing.",
                })
        if not recs:
            recs.append({"zone": "All", "priority": "Low",
                          "recommendation": "Space utilization is balanced across zones."})
        return recs

    # ---------- Forecast ----------
    def forecast_usage(self, facility_id: int | None = None, days_ahead: int = 3):
        rows = self._recent(facility_id, hours=24 * 14)
        if not rows:
            return []
        daily_totals: dict[str, list] = {}
        for r in rows:
            key = r.timestamp.strftime("%Y-%m-%d")
            daily_totals.setdefault(key, []).append(r.occupancy_count)
        daily_avg = {k: statistics.mean(v) for k, v in daily_totals.items()}
        values = list(daily_avg.values())
        recent = values[-7:] if len(values) >= 7 else values
        weights = list(range(1, len(recent) + 1))
        weighted_avg = sum(v * w for v, w in zip(recent, weights)) / sum(weights)

        forecast = []
        last_date = max(datetime.strptime(d, "%Y-%m-%d") for d in daily_avg)
        for i in range(1, days_ahead + 1):
            future_date = last_date + timedelta(days=i)
            weekday_factor = 1.0 if future_date.weekday() < 5 else 0.4
            forecast.append({
                "date": future_date.strftime("%Y-%m-%d"),
                "predicted_avg_occupancy": round(weighted_avg * weekday_factor),
            })
        return forecast

    # ---------- Alerts ----------
    def generate_alerts(self, facility_id: int | None = None):
        created = []
        for f in self.detect_overcrowding(facility_id, hours=1):
            alert = Alert(
                facility_id=f["facility_id"],
                alert_type="Overcrowding",
                severity="Warning" if f["utilization_pct"] < 98 else "Critical",
                message=f"{f['zone']} at {f['utilization_pct']}% capacity "
                        f"({f['occupancy_count']}/{f['capacity']}).",
            )
            self.db.add(alert)
            created.append(alert)
        if created:
            self.db.commit()
        return len(created)
