"""
Security Agent — Milestone 3 (Weeks 5-6): Occupancy & Security Intelligence

Responsibilities (from spec section 4.4):
  - Monitor access control systems
  - Detect unauthorized access attempts
  - Analyze CCTV events
  - Track visitor movement
  - Generate security alerts
  - Support incident investigation
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..models import SecurityEvent, Alert

HIGH_SEVERITY_TYPES = {"Unauthorized Access", "Forced Door Attempt"}


class SecurityAgent:
    def __init__(self, db: Session):
        self.db = db

    def _recent(self, facility_id: int | None = None, hours: int = 24):
        since = datetime.utcnow() - timedelta(hours=hours)
        q = self.db.query(SecurityEvent).filter(SecurityEvent.timestamp >= since)
        if facility_id:
            q = q.filter(SecurityEvent.facility_id == facility_id)
        return q.order_by(SecurityEvent.timestamp.desc()).all()

    # ---------- KPIs (matches mock: Security Events, Unauthorized Access) ----------
    def kpis(self, facility_id: int | None = None, hours: int = 24):
        rows = self._recent(facility_id, hours)
        unauthorized = [r for r in rows if r.event_type in HIGH_SEVERITY_TYPES]
        return {
            "security_events": len(rows),
            "unauthorized_access": len(unauthorized),
            "high_severity": len([r for r in rows if r.severity == "High"]),
        }

    # ---------- Access monitoring ----------
    def unauthorized_attempts(self, facility_id: int | None = None, hours: int = 24 * 7):
        rows = self._recent(facility_id, hours)
        flagged = [r for r in rows if r.event_type in HIGH_SEVERITY_TYPES]
        return [{
            "event_id": r.event_id,
            "facility_id": r.facility_id,
            "event_type": r.event_type,
            "severity": r.severity,
            "zone": r.zone,
            "timestamp": r.timestamp.isoformat(),
        } for r in flagged]

    # ---------- CCTV / event-type breakdown ----------
    def event_type_breakdown(self, facility_id: int | None = None, hours: int = 24 * 7):
        rows = self._recent(facility_id, hours)
        totals: dict[str, int] = {}
        for r in rows:
            totals[r.event_type] = totals.get(r.event_type, 0) + 1
        return dict(sorted(totals.items(), key=lambda x: -x[1]))

    # ---------- Zone-level incident map (supports investigation) ----------
    def events_by_zone(self, facility_id: int | None = None, hours: int = 24 * 7):
        rows = self._recent(facility_id, hours)
        totals: dict[str, int] = {}
        for r in rows:
            totals[r.zone] = totals.get(r.zone, 0) + 1
        return dict(sorted(totals.items(), key=lambda x: -x[1]))

    # ---------- Incident log for investigation ----------
    def incident_log(self, facility_id: int | None = None, hours: int = 24 * 7, limit: int = 50):
        rows = self._recent(facility_id, hours)[:limit]
        return [{
            "event_id": r.event_id,
            "event_type": r.event_type,
            "severity": r.severity,
            "zone": r.zone,
            "timestamp": r.timestamp.isoformat(),
        } for r in rows]

    # ---------- Alerts ----------
    def generate_alerts(self, facility_id: int | None = None):
        created = []
        for r in self._recent(facility_id, hours=1):
            if r.event_type in HIGH_SEVERITY_TYPES:
                alert = Alert(
                    facility_id=r.facility_id,
                    alert_type="Security Incident",
                    severity="Critical" if r.severity == "High" else "Warning",
                    message=f"{r.event_type} detected in {r.zone} at {r.timestamp.isoformat()}.",
                )
                self.db.add(alert)
                created.append(alert)
        if created:
            self.db.commit()
        return len(created)
