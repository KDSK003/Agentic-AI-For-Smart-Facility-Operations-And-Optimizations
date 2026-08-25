
from fastapi import FastAPI, Depends, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from sqlalchemy.orm import Session
from typing import Optional

from .database import get_db, engine, Base
from .models import Facility, Asset
from .simulator import seed_database
from .agents.energy_agent import EnergyAgent
from .agents.maintenance_agent import MaintenanceAgent
from .agents.occupancy_agent import OccupancyAgent
from .agents.security_agent import SecurityAgent

app = FastAPI(title="Agentic FacilityOps AI Platform", version="1.0.0")

Base.metadata.create_all(bind=engine)
seed_database()  # no-op if already seeded

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


# ---------------------------------------------------------------- Facilities
@app.get("/api/facilities")
def list_facilities(db: Session = Depends(get_db)):
    rows = db.query(Facility).all()
    return [{"facility_id": f.facility_id, "facility_name": f.facility_name,
             "facility_type": f.facility_type, "location": f.location} for f in rows]


# ---------------------------------------------------------------- Milestone 1: Energy
@app.get("/api/energy/summary")
def energy_summary(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    return EnergyAgent(db).summary(facility_id)


@app.get("/api/energy/distribution")
def energy_distribution(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    return EnergyAgent(db).system_distribution(facility_id)


@app.get("/api/energy/anomalies")
def energy_anomalies(facility_id: Optional[int] = None, hours: int = 168, db: Session = Depends(get_db)):
    agent = EnergyAgent(db)
    return {"anomalies": agent.detect_anomalies(facility_id, hours),
            "accuracy_pct": agent.anomaly_detection_accuracy(facility_id, hours)}


@app.get("/api/energy/hvac")
def energy_hvac(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    return EnergyAgent(db).hvac_efficiency(facility_id)


@app.get("/api/energy/forecast")
def energy_forecast(facility_id: Optional[int] = None, days: int = 3, db: Session = Depends(get_db)):
    return EnergyAgent(db).forecast_demand(facility_id, days)


@app.get("/api/energy/recommendations")
def energy_recommendations(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    return EnergyAgent(db).recommendations(facility_id)


@app.post("/api/energy/generate-alerts")
def energy_generate_alerts(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    return {"alerts_created": EnergyAgent(db).generate_alerts(facility_id)}


# ---------------------------------------------------------------- Milestone 2: Maintenance
@app.get("/api/maintenance/kpis")
def maintenance_kpis(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    return MaintenanceAgent(db).kpis(facility_id)


@app.get("/api/maintenance/health-distribution")
def maintenance_health_distribution(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    return MaintenanceAgent(db).health_distribution(facility_id)


@app.get("/api/maintenance/predictions")
def maintenance_predictions(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    return MaintenanceAgent(db).predict_failures(facility_id)


@app.get("/api/maintenance/work-orders")
def maintenance_work_orders(facility_id: Optional[int] = None, status: Optional[str] = None,
                             db: Session = Depends(get_db)):
    return MaintenanceAgent(db).work_orders(facility_id, status)


@app.post("/api/maintenance/generate-work-orders")
def maintenance_generate_work_orders(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    return {"work_orders_created": MaintenanceAgent(db).generate_work_orders(facility_id)}


# ---------------------------------------------------------------- Milestone 3: Occupancy
@app.get("/api/occupancy/kpis")
def occupancy_kpis(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    return OccupancyAgent(db).kpis(facility_id)


@app.get("/api/occupancy/zones")
def occupancy_zones(facility_id: Optional[int] = None, hours: int = 24, db: Session = Depends(get_db)):
    return OccupancyAgent(db).zone_distribution(facility_id, hours)


@app.get("/api/occupancy/overcrowding")
def occupancy_overcrowding(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    return OccupancyAgent(db).detect_overcrowding(facility_id)


@app.get("/api/occupancy/heatmap")
def occupancy_heatmap(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    return OccupancyAgent(db).heatmap(facility_id)


@app.get("/api/occupancy/forecast")
def occupancy_forecast(facility_id: Optional[int] = None, days: int = 3, db: Session = Depends(get_db)):
    return OccupancyAgent(db).forecast_usage(facility_id, days)


@app.get("/api/occupancy/recommendations")
def occupancy_recommendations(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    return OccupancyAgent(db).recommendations(facility_id)


# ---------------------------------------------------------------- Milestone 3: Security
@app.get("/api/security/kpis")
def security_kpis(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    return SecurityAgent(db).kpis(facility_id)


@app.get("/api/security/unauthorized")
def security_unauthorized(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    return SecurityAgent(db).unauthorized_attempts(facility_id)


@app.get("/api/security/event-types")
def security_event_types(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    return SecurityAgent(db).event_type_breakdown(facility_id)


@app.get("/api/security/zones")
def security_zones(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    return SecurityAgent(db).events_by_zone(facility_id)


@app.get("/api/security/incidents")
def security_incidents(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    return SecurityAgent(db).incident_log(facility_id)


# ---------------------------------------------------------------- Dashboards (HTML + Chart.js)
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request=request, name="home.html")


@app.get("/dashboard/energy")
def dashboard_energy(request: Request):
    return templates.TemplateResponse(request=request, name="energy_dashboard.html")


@app.get("/dashboard/maintenance")
def dashboard_maintenance(request: Request):
    return templates.TemplateResponse(request=request, name="maintenance_dashboard.html")


@app.get("/dashboard/occupancy-security")
def dashboard_occupancy_security(request: Request):
    return templates.TemplateResponse(request=request, name="occupancy_security_dashboard.html")
