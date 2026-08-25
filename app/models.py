
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class Facility(Base):
    __tablename__ = "facilities"

    facility_id = Column(Integer, primary_key=True, index=True)
    facility_name = Column(String, nullable=False)
    facility_type = Column(String, nullable=False)  # Office, IT Park, University, Hospital
    location = Column(String, nullable=False)

    assets = relationship("Asset", back_populates="facility")
    energy_usage = relationship("EnergyUsage", back_populates="facility")
    alerts = relationship("Alert", back_populates="facility")
    occupancy_records = relationship("OccupancyRecord", back_populates="facility")
    security_events = relationship("SecurityEvent", back_populates="facility")


class Asset(Base):
    __tablename__ = "assets"

    asset_id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.facility_id"), nullable=False)
    asset_name = Column(String, nullable=False)
    asset_type = Column(String, nullable=False)  # HVAC, Chiller, Elevator, Generator, Pump...
    status = Column(String, default="Operational")  # Operational, Warning, Critical, Down
    install_date = Column(DateTime, default=datetime.utcnow)
    expected_lifespan_years = Column(Float, default=10.0)
    runtime_hours = Column(Float, default=0.0)

    facility = relationship("Facility", back_populates="assets")
    maintenance_records = relationship("MaintenanceRecord", back_populates="asset")
    readings = relationship("AssetReading", back_populates="asset")


class AssetReading(Base):
    """High-frequency synthetic IoT sensor readings per asset (vibration, temperature, load)."""
    __tablename__ = "asset_readings"

    reading_id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.asset_id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    vibration_mm_s = Column(Float)
    temperature_c = Column(Float)
    load_pct = Column(Float)

    asset = relationship("Asset", back_populates="readings")


class EnergyUsage(Base):
    __tablename__ = "energy_usage"

    energy_id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.facility_id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    electricity_usage_kwh = Column(Float, nullable=False)
    water_usage_l = Column(Float, nullable=False)
    system_tag = Column(String, default="Other")  # HVAC, Lighting, Equipment, Other

    facility = relationship("Facility", back_populates="energy_usage")


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    maintenance_id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.asset_id"), nullable=False)
    issue_type = Column(String, nullable=False)
    maintenance_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="Open")  # Open, Scheduled, In Progress, Completed

    asset = relationship("Asset", back_populates="maintenance_records")


class OccupancyRecord(Base):
    """Milestone 3: Occupancy Agent - zone-level headcount vs capacity over time."""
    __tablename__ = "occupancy_records"

    occupancy_id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.facility_id"), nullable=False)
    zone = Column(String, nullable=False)  # Office Floors, Meeting Rooms, Common Areas, Parking
    occupancy_count = Column(Integer, nullable=False)
    capacity = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    facility = relationship("Facility", back_populates="occupancy_records")


class SecurityEvent(Base):
    """Milestone 3: Security Agent - access-control / CCTV derived events."""
    __tablename__ = "security_events"

    event_id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.facility_id"), nullable=False)
    event_type = Column(String, nullable=False)  # Unauthorized Access, Tailgating, Forced Door, CCTV Motion
    severity = Column(String, nullable=False)  # Low, Medium, High
    zone = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    facility = relationship("Facility", back_populates="security_events")


class Alert(Base):
    __tablename__ = "alerts"

    alert_id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.facility_id"), nullable=False)
    alert_type = Column(String, nullable=False)  # Energy Anomaly, Predictive Maintenance, ...
    severity = Column(String, nullable=False)  # Info, Warning, Critical
    message = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    facility = relationship("Facility", back_populates="alerts")
