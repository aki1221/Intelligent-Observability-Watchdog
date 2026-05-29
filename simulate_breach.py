"""
Simulate a threshold breach by injecting a burst of events, then running the watchdog.

Usage: python simulate_breach.py
"""

import datetime
import json
import random
from app.database import SessionLocal, engine, Base
from app.models import Event, EventSeverity
from app.watchdog import run_watchdog_cycle

# Ensure tables exist (including new WebhookLog and HealthSnapshot)
Base.metadata.create_all(bind=engine)


def simulate_burst():
    """Inject a burst of error events to trigger alert rules."""
    db = SessionLocal()

    print("=" * 60)
    print("  🔥 Simulating Event Burst to Trigger Breaches")
    print("=" * 60)

    # Scenario 1: HTTP Error burst (triggers "High Error Rate" rule: count > 10 in 5m)
    print("\n→ Injecting 15 http_error events (threshold: 10 in 5m)...")
    now = datetime.datetime.utcnow()
    for i in range(15):
        event = Event(
            source=random.choice(["payment-service", "api-gateway", "auth-service"]),
            event_type="http_error",
            severity=EventSeverity.ERROR,
            message=f"HTTP 500 Internal Server Error on /api/endpoint-{i}",
            metadata_json=json.dumps({"status_code": 500, "burst_id": "sim-001", "index": i}),
            timestamp=now - datetime.timedelta(seconds=random.randint(0, 180)),
        )
        db.add(event)

    # Scenario 2: DB Connection timeout burst (triggers "DB Connection Crisis": count > 3 in 2m)
    print("→ Injecting 6 db_connection_timeout events (threshold: 3 in 2m)...")
    for i in range(6):
        event = Event(
            source=random.choice(["user-service", "order-service"]),
            event_type="db_connection_timeout",
            severity=EventSeverity.CRITICAL,
            message=f"Connection pool exhausted on replica-{random.randint(1,5):02d}",
            metadata_json=json.dumps({"host": f"db-{random.randint(1,3):02d}.internal", "wait_ms": random.randint(5000, 30000)}),
            timestamp=now - datetime.timedelta(seconds=random.randint(0, 90)),
        )
        db.add(event)

    # Scenario 3: Memory threshold burst (triggers "Memory Pressure": count > 2 in 3m)
    print("→ Injecting 5 memory_threshold events (threshold: 2 in 3m)...")
    for i in range(5):
        event = Event(
            source="payment-service",
            event_type="memory_threshold",
            severity=EventSeverity.CRITICAL,
            message=f"OOM kill risk: container at {random.randint(93, 99)}% memory limit",
            metadata_json=json.dumps({"pod": f"pod-{random.randint(1,5):03d}", "usage_percent": random.randint(93, 99)}),
            timestamp=now - datetime.timedelta(seconds=random.randint(0, 120)),
        )
        db.add(event)

    db.commit()
    db.close()
    print("  ✓ Burst events injected\n")

    # Run watchdog
    print("→ Running watchdog evaluation...")
    breaches = run_watchdog_cycle()

    print(f"\n{'=' * 60}")
    if breaches:
        print(f"  🚨 {len(breaches)} BREACH(ES) DETECTED!")
        print("=" * 60)
        for b in breaches:
            print(f"  • {b['rule_name']}: {b['actual_count']} events (threshold: {b['threshold']}) in {b['window_minutes']}m")
            print(f"    Severity: {b['severity']} | Event type: {b['event_type']}")
        print(f"\n  ✅ Alerts created and webhook notifications fired (simulated)")
    else:
        print("  ✅ No breaches detected")
        print("=" * 60)


if __name__ == "__main__":
    simulate_burst()
