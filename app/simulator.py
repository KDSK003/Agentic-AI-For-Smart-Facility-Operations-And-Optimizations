
import random
import math
from datetime import datetime, timedelta

from .database import SessionLocal, engine, Base
from .models import (
    Facility, Asset, AssetReading, EnergyUsage,
    OccupancyRecord, SecurityEvent,
)

random.seed(42)

FACILITIES = [
    {"facility_name": "Anna Nagar Tech Park", "facility_type": "IT Park", "location": "Chennai"},
    {"facility_name": "Coimbatore Corporate Tower", "facility_type": "Office", "location": "Coimbatore"},
    {"facility_name": "Madurai Campus Block A", "facility_type": "University", "location": "Madurai"},
]

ASSET_TYPES = [
    ("Chiller Unit", 15),
    ("HVAC Air Handler", 12),
    ("Elevator", 20),
    ("Backup Generator", 15),
    ("Water Pump", 10),
    ("Transformer", 25),
]

SYSTEM_TAGS = ["HVAC", "Lighting", "Equipment", "Other"]
SYSTEM_WEIGHTS = [0.45, 0.28, 0.18, 0.09]  # matches the Milestone 1 mock's energy distribution

# Milestone 3 — occupancy zones with rough capacity, matches the mock's "Zone Occupancy Distribution"
ZONES = [
    ("Office Floors", 400, 0.82),
    ("Meeting Rooms", 60, 0.65),
    ("Common Areas", 150, 0.48),
    ("Parking Areas", 300, 0.37),
]

SECURITY_EVENT_TYPES = [
    ("Unauthorized Access", "High", 0.08),
    ("Tailgating", "Medium", 0.20),
    ("Forced Door Attempt", "High", 0.05),
    ("CCTV Motion After Hours", "Low", 0.35),
    ("Card Read Failure", "Low", 0.32),
]


def seed_database(days_of_history: int = 14, hours_step: int = 1, reset: bool = False):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if reset:
            for model in [EnergyUsage, AssetReading, Asset, Facility]:
                db.query(model).delete()
            db.commit()

        if db.query(Facility).count() > 0:
            print("Database already seeded — skipping. Pass reset=True to force re-seed.")
            return

        facilities = []
        for f in FACILITIES:
            fac = Facility(**f)
            db.add(fac)
            db.flush()
            facilities.append(fac)

        assets = []
        for fac in facilities:
            n_assets = random.randint(6, 9)
            for i in range(n_assets):
                atype, lifespan = random.choice(ASSET_TYPES)
                install_days_ago = random.randint(200, lifespan * 365)
                asset = Asset(
                    facility_id=fac.facility_id,
                    asset_name=f"{atype} #{i+1}",
                    asset_type=atype,
                    status="Operational",
                    install_date=datetime.utcnow() - timedelta(days=install_days_ago),
                    expected_lifespan_years=lifespan,
                    runtime_hours=install_days_ago * random.uniform(6, 14),
                )
                db.add(asset)
                db.flush()
                assets.append(asset)
        db.commit()

        # --- Energy usage: hourly readings per facility for N days, with daily/weekly cycles ---
        now = datetime.utcnow()
        start = now - timedelta(days=days_of_history)
        for fac in facilities:
            base_load = random.uniform(180, 260)  # kWh baseline for the facility
            t = start
            while t <= now:
                hour = t.hour
                # Daytime/office-hours load curve (peaks ~10am-4pm on weekdays)
                is_weekday = t.weekday() < 5
                day_factor = 1.0 if is_weekday else 0.55
                hour_factor = 0.35 + 0.9 * math.exp(-((hour - 13) ** 2) / 30)
                noise = random.gauss(1.0, 0.06)

                # Inject occasional anomalies (equipment left on, wastage spikes)
                anomaly = 1.0
                if random.random() < 0.02:
                    anomaly = random.uniform(1.4, 1.9)

                total_kwh = base_load * day_factor * hour_factor * noise * anomaly
                water_l = total_kwh * random.uniform(1.8, 2.4)

                tag = random.choices(SYSTEM_TAGS, weights=SYSTEM_WEIGHTS)[0]

                db.add(EnergyUsage(
                    facility_id=fac.facility_id,
                    timestamp=t,
                    electricity_usage_kwh=round(total_kwh, 2),
                    water_usage_l=round(water_l, 1),
                    system_tag=tag,
                ))
                t += timedelta(hours=hours_step)
        db.commit()

        # --- Asset sensor readings: daily readings for the last 60 days, drifting toward failure ---
        for asset in assets:
            # Give ~15% of assets a degrading trend (candidates for predictive maintenance)
            degrading = random.random() < 0.15
            base_vibration = random.uniform(1.5, 3.0)
            base_temp = random.uniform(35, 45)
            base_load = random.uniform(55, 75)

            days = 60
            for d in range(days, 0, -1):
                ts = now - timedelta(days=d)
                progress = (days - d) / days  # 0 -> 1 over the window

                drift = progress * random.uniform(2.5, 5.5) if degrading else progress * random.uniform(-0.2, 0.3)
                vibration = max(0.2, base_vibration + drift + random.gauss(0, 0.15))
                temperature = base_temp + drift * 1.8 + random.gauss(0, 0.8)
                load = min(100, max(10, base_load + drift * 2 + random.gauss(0, 2)))

                db.add(AssetReading(
                    asset_id=asset.asset_id,
                    timestamp=ts,
                    vibration_mm_s=round(vibration, 2),
                    temperature_c=round(temperature, 1),
                    load_pct=round(load, 1),
                ))

            if degrading:
                asset.status = "Warning" if random.random() < 0.7 else "Critical"

        db.commit()

        # --- Occupancy: hourly headcount per zone per facility, office-hours curve ---
        for fac in facilities:
            t = start
            while t <= now:
                hour = t.hour
                is_weekday = t.weekday() < 5
                day_factor = 1.0 if is_weekday else 0.2
                hour_factor = max(0.03, 0.9 * math.exp(-((hour - 13) ** 2) / 22))
                for zone, capacity, target_util in ZONES:
                    noise = random.gauss(1.0, 0.08)
                    count = int(min(capacity, max(0, capacity * target_util * day_factor * hour_factor * noise)))
                    db.add(OccupancyRecord(
                        facility_id=fac.facility_id,
                        zone=zone,
                        occupancy_count=count,
                        capacity=capacity,
                        timestamp=t,
                    ))
                t += timedelta(hours=hours_step)
        db.commit()

        # --- Security events: sparse, weighted by severity, mostly during off-hours ---
        for fac in facilities:
            t = start
            while t <= now:
                for event_type, severity, prob in SECURITY_EVENT_TYPES:
                    off_hours_boost = 1.6 if (t.hour < 7 or t.hour > 20) else 1.0
                    if random.random() < (prob / 24) * off_hours_boost:
                        zone = random.choice([z[0] for z in ZONES])
                        db.add(SecurityEvent(
                            facility_id=fac.facility_id,
                            event_type=event_type,
                            severity=severity,
                            zone=zone,
                            timestamp=t,
                        ))
                t += timedelta(hours=hours_step)
        db.commit()

        n_occ = db.query(OccupancyRecord).count()
        n_sec = db.query(SecurityEvent).count()
        print(f"Seeded {len(facilities)} facilities, {len(assets)} assets, "
              f"energy usage for {days_of_history} days, asset readings for 60 days, "
              f"{n_occ} occupancy records, {n_sec} security events.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database(reset=True)
