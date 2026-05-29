"""
Seed script: Generates synthetic data for all tables in the observability database.
Run with: python seed_data.py
"""

import random
import datetime
import json
from app.database import engine, SessionLocal, Base
from app.models import Event, EventSeverity, AlertRule, Alert, AlertStatus

# ─── Configuration ───────────────────────────────────────────────────────────

NUM_EVENTS = 500
NUM_ALERT_RULES = 8
NUM_ALERTS = 30

SOURCES = [
    "payment-service",
    "auth-service",
    "api-gateway",
    "user-service",
    "notification-service",
    "order-service",
    "inventory-service",
    "search-service",
]

EVENT_TYPES = [
    "http_error",
    "db_connection_timeout",
    "high_latency",
    "memory_threshold",
    "cpu_spike",
    "disk_full",
    "auth_failure",
    "rate_limit_exceeded",
    "deployment",
    "health_check_fail",
]

MESSAGES = {
    "http_error": [
        "HTTP 500 Internal Server Error on /api/checkout",
        "HTTP 502 Bad Gateway from upstream",
        "HTTP 503 Service Unavailable - circuit breaker open",
        "HTTP 429 Too Many Requests from client 10.0.3.42",
    ],
    "db_connection_timeout": [
        "Connection to postgres-primary timed out after 30s",
        "Connection pool exhausted on replica-02",
        "Failed to acquire connection from pool within 5000ms",
    ],
    "high_latency": [
        "P99 latency exceeded 2000ms on /api/search",
        "Average response time 1500ms (threshold: 500ms)",
        "Downstream call to inventory-service took 4200ms",
    ],
    "memory_threshold": [
        "Memory usage at 92% on pod payment-service-7b4f9",
        "Heap size exceeded 1.8GB, GC pressure increasing",
        "OOM kill risk: container at 95% memory limit",
    ],
    "cpu_spike": [
        "CPU usage at 98% for 3 consecutive minutes",
        "CPU throttling detected on node worker-05",
        "Sustained CPU > 85% across all replicas",
    ],
    "disk_full": [
        "Disk usage at 94% on /var/log volume",
        "Inode usage at 89% on data partition",
        "Write failed: no space left on device /tmp",
    ],
    "auth_failure": [
        "Multiple failed login attempts from IP 192.168.1.100",
        "JWT token validation failed: token expired",
        "OAuth2 refresh token revoked for user_id=4521",
    ],
    "rate_limit_exceeded": [
        "Rate limit exceeded for API key ak_prod_***89f2",
        "Client 10.0.5.12 exceeded 1000 req/min threshold",
        "Burst limit hit on /api/v1/events endpoint",
    ],
    "deployment": [
        "Deployment v2.4.1 rolled out to production",
        "Canary deployment started: 10% traffic to v2.5.0",
        "Rollback initiated: v2.4.2 -> v2.4.1",
    ],
    "health_check_fail": [
        "Health check failed on pod auth-service-3a2c1",
        "Liveness probe failed 3 consecutive times",
        "Readiness probe timeout on port 8080",
    ],
}

METADATA_TEMPLATES = {
    "http_error": lambda: {"status_code": random.choice([500, 502, 503, 429]), "path": random.choice(["/api/checkout", "/api/users", "/api/orders"]), "method": "GET"},
    "db_connection_timeout": lambda: {"host": f"db-{random.randint(1,5):02d}.internal", "pool_size": random.randint(10, 50), "wait_ms": random.randint(5000, 30000)},
    "high_latency": lambda: {"endpoint": random.choice(["/api/search", "/api/orders", "/api/recommendations"]), "p99_ms": random.randint(1500, 5000)},
    "memory_threshold": lambda: {"pod": f"pod-{random.randint(1,20):03d}", "usage_percent": random.randint(85, 99), "limit_mb": 2048},
    "cpu_spike": lambda: {"node": f"worker-{random.randint(1,10):02d}", "cpu_percent": random.randint(85, 100), "duration_sec": random.randint(60, 600)},
    "disk_full": lambda: {"mount": random.choice(["/var/log", "/data", "/tmp"]), "usage_percent": random.randint(88, 99)},
    "auth_failure": lambda: {"ip": f"192.168.{random.randint(1,10)}.{random.randint(1,254)}", "user_id": random.randint(1000, 9999), "attempts": random.randint(3, 20)},
    "rate_limit_exceeded": lambda: {"client_ip": f"10.0.{random.randint(1,10)}.{random.randint(1,254)}", "requests_per_min": random.randint(1000, 5000)},
    "deployment": lambda: {"version": f"v2.{random.randint(1,9)}.{random.randint(0,15)}", "replicas": random.randint(2, 10), "strategy": random.choice(["rolling", "canary", "blue-green"])},
    "health_check_fail": lambda: {"pod": f"pod-{random.randint(1,20):03d}", "probe_type": random.choice(["liveness", "readiness"]), "consecutive_failures": random.randint(3, 10)},
}

ALERT_RULES_DATA = [
    {"name": "High Error Rate", "description": "Triggers when error count exceeds threshold in 5 min window", "event_type": "http_error", "severity_threshold": EventSeverity.ERROR, "condition": "count > 10 in 5m"},
    {"name": "DB Connection Crisis", "description": "Database connection timeouts exceeding safe limit", "event_type": "db_connection_timeout", "severity_threshold": EventSeverity.CRITICAL, "condition": "count > 3 in 2m"},
    {"name": "Latency Degradation", "description": "High latency events sustained over time", "event_type": "high_latency", "severity_threshold": EventSeverity.WARNING, "condition": "count > 5 in 10m"},
    {"name": "Memory Pressure", "description": "Memory usage approaching OOM kill threshold", "event_type": "memory_threshold", "severity_threshold": EventSeverity.CRITICAL, "condition": "count > 2 in 3m"},
    {"name": "CPU Overload", "description": "Sustained CPU spikes across cluster", "event_type": "cpu_spike", "severity_threshold": EventSeverity.ERROR, "condition": "count > 3 in 5m"},
    {"name": "Disk Space Critical", "description": "Disk approaching full capacity", "event_type": "disk_full", "severity_threshold": EventSeverity.CRITICAL, "condition": "count > 1 in 1m"},
    {"name": "Brute Force Detection", "description": "Multiple auth failures suggesting attack", "event_type": "auth_failure", "severity_threshold": EventSeverity.WARNING, "condition": "count > 5 in 2m"},
    {"name": "Rate Limit Breach", "description": "Clients exceeding rate limits repeatedly", "event_type": "rate_limit_exceeded", "severity_threshold": EventSeverity.WARNING, "condition": "count > 3 in 5m"},
]


def random_timestamp(hours_back: int = 48) -> datetime.datetime:
    """Generate a random timestamp within the last N hours."""
    now = datetime.datetime.utcnow()
    delta = datetime.timedelta(
        hours=random.randint(0, hours_back),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    return now - delta


def severity_weighted() -> EventSeverity:
    """Return severity with realistic distribution: mostly info/warning, fewer errors/critical."""
    return random.choices(
        [EventSeverity.INFO, EventSeverity.WARNING, EventSeverity.ERROR, EventSeverity.CRITICAL],
        weights=[40, 30, 20, 10],
        k=1,
    )[0]


def seed_events(db):
    """Generate synthetic events."""
    print(f"  Seeding {NUM_EVENTS} events...")
    events = []
    for _ in range(NUM_EVENTS):
        event_type = random.choice(EVENT_TYPES)
        source = random.choice(SOURCES)
        severity = severity_weighted()
        message = random.choice(MESSAGES[event_type])
        metadata = json.dumps(METADATA_TEMPLATES[event_type]())
        ts = random_timestamp(hours_back=48)

        events.append(Event(
            source=source,
            event_type=event_type,
            severity=severity,
            message=message,
            metadata_json=metadata,
            timestamp=ts,
            created_at=ts,
        ))

    db.add_all(events)
    db.commit()
    print(f"  ✓ {NUM_EVENTS} events created")


def seed_alert_rules(db):
    """Generate alert rules."""
    print(f"  Seeding {len(ALERT_RULES_DATA)} alert rules...")
    rules = []
    now = datetime.datetime.utcnow()
    for rule_data in ALERT_RULES_DATA:
        rules.append(AlertRule(
            name=rule_data["name"],
            description=rule_data["description"],
            event_type=rule_data["event_type"],
            severity_threshold=rule_data["severity_threshold"],
            condition=rule_data["condition"],
            enabled=True,
            created_at=now - datetime.timedelta(days=random.randint(1, 30)),
            updated_at=now,
        ))
    db.add_all(rules)
    db.commit()
    print(f"  ✓ {len(rules)} alert rules created")
    return rules


def seed_alerts(db, rules):
    """Generate triggered alerts."""
    print(f"  Seeding {NUM_ALERTS} alerts...")
    alerts = []
    for _ in range(NUM_ALERTS):
        rule = random.choice(rules)
        status = random.choices(
            [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED, AlertStatus.RESOLVED],
            weights=[50, 25, 25],
            k=1,
        )[0]

        triggered_at = random_timestamp(hours_back=24)
        acknowledged_at = None
        resolved_at = None

        if status in (AlertStatus.ACKNOWLEDGED, AlertStatus.RESOLVED):
            acknowledged_at = triggered_at + datetime.timedelta(minutes=random.randint(1, 30))
        if status == AlertStatus.RESOLVED:
            resolved_at = acknowledged_at + datetime.timedelta(minutes=random.randint(5, 120))

        message = f"Rule '{rule.name}' triggered: {rule.condition} on {rule.event_type}"

        alerts.append(Alert(
            rule_id=rule.id,
            status=status,
            message=message,
            triggered_at=triggered_at,
            acknowledged_at=acknowledged_at,
            resolved_at=resolved_at,
        ))

    db.add_all(alerts)
    db.commit()
    print(f"  ✓ {NUM_ALERTS} alerts created")


def main():
    print("=" * 60)
    print("  Intelligent Observability - Database Seeder")
    print("=" * 60)

    # Create tables
    print("\n→ Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("  ✓ Tables created")

    # Seed data
    db = SessionLocal()
    try:
        print("\n→ Seeding data...")
        seed_events(db)
        rules = seed_alert_rules(db)
        seed_alerts(db, rules)
        print("\n" + "=" * 60)
        print("  ✅ Database seeded successfully!")
        print("=" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    main()
