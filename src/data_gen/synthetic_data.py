#!/usr/bin/env python
# coding: utf-8

# In[92]:


import pandas as pd
import random
from faker import Faker
from pathlib import Path

fake = Faker()

Faker.seed(42)
random.seed(42)

# Paramaterized code

PROJECT_ROOT = Path(__file__).resolve().parents[2]

BASE_PATH = PROJECT_ROOT / "data" / "raw"

PLM_PATH = BASE_PATH / "plm"
MES_PATH = BASE_PATH / "mes"

PLM_PATH.mkdir(parents=True, exist_ok=True)
MES_PATH.mkdir(parents=True, exist_ok=True)

NUM_PRODUCTS = 100
NUM_BOM = 700
NUM_ECN = 150
NUM_MACHINE_LOGS = 3000
NUM_ORDERS = 500
NUM_DOWNTIME = 300


# In[63]:


# Generate Product IDs

product_ids = []

for i in range(1, NUM_PRODUCTS + 1):
    product_ids.append(f"PROD-{i:03}")


# In[64]:


product_names = [
    "Widget Alpha",
    "Widget Beta",
    "Widget Gamma",
    "Widget Delta",
    "Gear Assembly",
    "Drive Shaft",
    "Bearing Housing",
    "Brake Disc",
    "Clutch Plate",
    "Engine Block",
    "Cylinder Head",
    "Axle Shaft",
    "Pulley Wheel",
    "Rotor Assembly",
    "Stator Unit",
    "Control Panel",
    "Hydraulic Pump",
    "Valve Body",
    "Roller Bearing",
    "Flexible Coupling",
    "Flywheel",
    "Crankshaft",
    "Piston Kit",
    "Camshaft",
    "Oil Pump",
    "Fuel Injector",
    "Timing Belt",
    "Cooling Fan",
    "Radiator",
    "Air Filter",
    "Exhaust Manifold",
    "Turbocharger",
    "Starter Motor",
    "Alternator",
    "Wheel Hub",
    "Steering Knuckle",
    "Suspension Arm",
    "Brake Caliper",
    "Shock Absorber",
    "Transmission Case",
    "Differential Gear",
    "Planetary Gear",
    "Universal Joint",
    "Seal Ring",
    "O-Ring",
    "Mounting Flange",
    "Fastener Kit",
    "Hex Bolt",
    "Lock Nut",
    "Flat Washer",
    "Chain Sprocket",
    "Roller Chain",
    "Linear Guide",
    "Servo Motor",
    "Stepper Motor",
    "PLC Module",
    "Sensor Module",
    "Pressure Sensor",
    "Temperature Sensor",
    "Flow Meter",
    "Solenoid Valve",
    "Electric Actuator",
    "Control Valve",
    "Hydraulic Cylinder",
    "Pneumatic Cylinder",
    "Air Compressor",
    "Vacuum Pump",
    "Heat Exchanger",
    "Boiler Tube",
    "Conveyor Roller",
    "Conveyor Belt",
    "Mixer Blade",
    "Impeller",
    "Filter Housing",
    "Spray Nozzle",
    "Manifold Block",
    "Electrical Connector",
    "Terminal Block",
    "Fuse Box",
    "Power Supply Unit",
    "Transformer Core",
    "Cooling Jacket",
    "Fan Blade",
    "Motor Shaft",
    "Housing Cover",
    "Gear Wheel",
    "Rack Gear",
    "Pinion Gear",
    "Support Bracket",
    "Mounting Plate",
    "Pipe Clamp",
    "Door Frame",
    "Chassis Frame",
    "Base Plate",
    "Machine Guard",
    "Inspection Cover",
    "Lubrication Unit",
    "Tool Holder",
    "Cutting Head",
    "Spindle Assembly"
]


# In[65]:


product_data = []

for i in range(NUM_PRODUCTS):

    file_name = product_names[i].lower().replace(" ", "_")
    cad_file = f"{file_name}_v1.step"

    row = {
        "product_id": product_ids[i],
        "product_name": product_names[i],
        "design_release_date": fake.date_between(
            start_date="-3y",
            end_date="today"
        ),
        "CAD_file_ref": cad_file
    }

    product_data.append(row)

product_df = pd.DataFrame(product_data)


# In[66]:


product_df.head()


# In[ ]:


product_df.to_csv(
    PLM_PATH / "product_metadata.csv",
    index=False #index is row numbers
)

print("product_metadata.csv created successfully")
print(product_df.shape)


# In[68]:


print("Current Working Directory:")
print(Path.cwd())

print("\nPLM Path:")
print(PLM_PATH.resolve())


# In[69]:


print(NUM_PRODUCTS)
print(len(product_names))
print(len(product_ids))


# In[70]:


#BOM.CSV
product_df = pd.read_csv(PLM_PATH / "product_metadata.csv")
product_df.head()


# In[71]:


components = [
    "COMP-001",
    "COMP-002",
    "COMP-003",
    "COMP-004",
    "COMP-005",
    "COMP-006",
    "COMP-007",
    "COMP-008",
    "COMP-009",
    "COMP-010",
    "COMP-011",
    "COMP-012",
    "COMP-013",
    "COMP-014",
    "COMP-015",
    "COMP-016",
    "COMP-017",
    "COMP-018",
    "COMP-019",
    "COMP-020",
    "COMP-021",
    "COMP-022",
    "COMP-023",
    "COMP-024",
    "COMP-025",
    "COMP-026",
    "COMP-027",
    "COMP-028",
    "COMP-029",
    "COMP-030"
]

versions = [
    "v1.0",
    "v1.1",
    "v2.0",
    "v2.1",
    "v3.0"
]


# In[72]:


bom_data = []

versions = [
    "v1.0",
    "v1.1",
    "v2.0",
    "v2.1",
    "v3.0"
]

for product_id in product_df["product_id"]:

    # Each product will have 5 to 8 unique components
    selected_components = random.sample(components, random.randint(5, 8))

    for component in selected_components:

        row = {
            "product_id": product_id,
            "component_id": component,
            "quantity": random.randint(1, 10),
            "component_version": random.choice(versions)
        }

        bom_data.append(row)

bom_df = pd.DataFrame(bom_data)


# In[73]:


bom_df.to_csv(
    PLM_PATH / "bom.csv",
    index=False
)

print("bom.csv created successfully")
print("Rows :", len(bom_df))


# In[74]:


bom_df.to_csv(
    PLM_PATH / "bom.csv",
    index=False
)

print("bom.csv created successfully")
print(bom_df.shape)


# In[75]:


print(bom_df.shape)
print()

print(bom_df.head())
print()

print(bom_df["product_id"].nunique())


# In[76]:


#ENCR.CSV
product_df = pd.read_csv(PLM_PATH / "product_metadata.csv")
product_df.head()


# In[77]:


# =========================
# ECN REQUESTS
# =========================

change_types = [
    "Design Update",
    "Material Change",
    "Dimension Change",
    "Supplier Change",
    "Quality Improvement",
    "Cost Reduction",
    "Performance Enhancement",
    "Compliance Update"
]

ecn_data = []

# Production period
ecn_start_date = pd.Timestamp("2025-08-15")
ecn_end_date = pd.Timestamp("2026-08-15")

# Ensure every product gets at least one ECN
ecn_products = product_df["product_id"].tolist()

# First ECN for every product
for i, product_id in enumerate(ecn_products, start=1):

    request_date = fake.date_between(
        start_date=ecn_start_date.date(),
        end_date=ecn_end_date.date()
    )

    row = {
        "change_id": f"ECN-{i:03d}",
        "product_id": product_id,
        "change_type": random.choice(change_types),
        "request_date": request_date,
        "approved_flag": random.choices(
            ["True", "False"],
            weights=[80, 20],
            k=1
        )[0]
    }

    ecn_data.append(row)


# Generate remaining ECNs
for i in range(NUM_PRODUCTS + 1, NUM_ECN + 1):

    request_date = fake.date_between(
        start_date=ecn_start_date.date(),
        end_date=ecn_end_date.date()
    )

    row = {
        "change_id": f"ECN-{i:03d}",
        "product_id": random.choice(ecn_products),
        "change_type": random.choice(change_types),
        "request_date": request_date,
        "approved_flag": random.choices(
            ["True", "False"],
            weights=[80, 20],
            k=1
        )[0]
    }

    ecn_data.append(row)


ecn_df = pd.DataFrame(ecn_data)

ecn_df.to_csv(
    PLM_PATH / "ecn_requests.csv",
    index=False
)

print("ecn_requests.csv created successfully")
print(ecn_df.shape)

print("Unique products with ECNs:",
      ecn_df["product_id"].nunique())

print(
    "Products without ECN:",
    set(product_df["product_id"]) - set(ecn_df["product_id"])
)

print(
    "ECN date range:",
    ecn_df["request_date"].min(),
    "to",
    ecn_df["request_date"].max()
)


# In[81]:


print(ecn_df.shape)
print()

print(ecn_df.head())
print()

print(ecn_df.isnull().sum())


# In[93]:


# ============================================================
# MES DATA GENERATION
# Generate production orders first so all MES records can be
# linked using production_order_id.
# ============================================================

machine_ids = [
    "M01", "M02", "M03", "M04", "M05",
    "M06", "M07", "M08", "M09", "M10"
]

status_list = ["Running", "Idle", "Maintenance"]

reason_codes = [
    "Scheduled Maintenance",
    "Machine Failure",
    "Power Outage",
    "Tool Replacement",
    "Material Shortage",
    "Quality Inspection",
    "Operator Break",
    "Sensor Fault"
]


# ------------------------------------------------------------
# 1. Generate production orders FIRST
# ------------------------------------------------------------

product_df = pd.read_csv(PLM_PATH / "product_metadata.csv")

if NUM_ORDERS < NUM_PRODUCTS:
    raise ValueError(
        "NUM_ORDERS must be greater than or equal to NUM_PRODUCTS "
        "so every product receives at least one production order."
    )

production_orders = []

# Ensure every product receives at least one order.
for i, product_id in enumerate(product_df["product_id"], start=1):
    start_time = fake.date_time_between(
        start_date="-1y",
        end_date="now"
    )

    duration = random.randint(1, 8)
    end_time = start_time + pd.Timedelta(hours=duration)

    planned_qty = random.randint(100, 500)
    actual_qty = planned_qty - random.randint(0, 20)

    production_orders.append({
        "order_id": f"ORD-{i:04d}",
        "product_id": product_id,
        "machine_id": random.choice(machine_ids),
        "start_time": start_time,
        "end_time": end_time,
        "planned_qty": planned_qty,
        "actual_qty": actual_qty
    })


# Generate the remaining orders.
for i in range(NUM_PRODUCTS + 1, NUM_ORDERS + 1):
    start_time = fake.date_time_between(
        start_date="-1y",
        end_date="now"
    )

    duration = random.randint(1, 8)
    end_time = start_time + pd.Timedelta(hours=duration)

    planned_qty = random.randint(100, 500)
    actual_qty = planned_qty - random.randint(0, 20)

    production_orders.append({
        "order_id": f"ORD-{i:04d}",
        "product_id": random.choice(product_df["product_id"].tolist()),
        "machine_id": random.choice(machine_ids),
        "start_time": start_time,
        "end_time": end_time,
        "planned_qty": planned_qty,
        "actual_qty": actual_qty
    })


production_orders_df = pd.DataFrame(production_orders)

production_orders_df.to_csv(
    MES_PATH / "production_orders.csv",
    index=False
)

print("production_orders.csv created successfully")
print("Shape:", production_orders_df.shape)
print("Total orders:", len(production_orders_df))
print(
    "Unique products:",
    production_orders_df["product_id"].nunique()
)


# ------------------------------------------------------------
# 2. Generate machine logs linked to production orders
# ------------------------------------------------------------

if NUM_MACHINE_LOGS < NUM_ORDERS:
    raise ValueError(
        "NUM_MACHINE_LOGS must be greater than or equal to NUM_ORDERS "
        "so every order receives at least one machine-log record."
    )

machine_logs = []

base_logs_per_order, extra_logs = divmod(
    NUM_MACHINE_LOGS,
    NUM_ORDERS
)

for order_position, (_, order) in enumerate(
    production_orders_df.iterrows()
):
    order_id = order["order_id"]
    machine_id = order["machine_id"]
    order_start = pd.Timestamp(order["start_time"])
    order_end = pd.Timestamp(order["end_time"])
    actual_qty = int(order["actual_qty"])

    # Distribute the configured number of logs across all orders.
    logs_for_order = base_logs_per_order
    if order_position < extra_logs:
        logs_for_order += 1

    # Split actual production quantity across the order's logs.
    # Sum(output_count) for an order will equal actual_qty exactly.
    base_output, output_remainder = divmod(
        actual_qty,
        logs_for_order
    )

    output_counts = [base_output] * logs_for_order

    for log_position in range(output_remainder):
        output_counts[log_position] += 1

    random.shuffle(output_counts)

    # Generate a unit-level rejected quantity for the order.
    # Rejected units are distributed across its machine-log records.
    total_rejected = random.randint(
        0,
        max(0, int(actual_qty * 0.03))
    )

    rejected_counts = [0] * logs_for_order
    rejected_remaining = total_rejected

    while rejected_remaining > 0:
        eligible_positions = [
            position
            for position, output_count in enumerate(output_counts)
            if rejected_counts[position] < output_count
        ]

        if not eligible_positions:
            raise ValueError(
                f"Could not distribute rejected quantity for {order_id}"
            )

        selected_position = random.choice(eligible_positions)
        rejected_counts[selected_position] += 1
        rejected_remaining -= 1

    order_duration_seconds = max(
        0,
        int((order_end - order_start).total_seconds())
    )

    for log_position, (output_count, rejected_quantity) in enumerate(
        zip(output_counts, rejected_counts),
        start=1
    ):
        random_seconds = random.randint(
            0,
            order_duration_seconds
        )

        event_timestamp = (
            order_start + pd.Timedelta(seconds=random_seconds)
        )

        status = random.choices(
            status_list,
            weights=[80, 15, 5],
            k=1
        )[0]

        machine_logs.append({
            "timestamp": event_timestamp,
            "production_order_id": order_id,
            "machine_id": machine_id,
            "status": status,
            "cycle_time_ms": random.randint(800, 2500),
            "output_count": output_count,
            "rejected_quantity": rejected_quantity,
            "defect_flag": (
                "True" if rejected_quantity > 0 else "False"
            )
        })


machine_logs_df = pd.DataFrame(machine_logs)

machine_logs_df.to_csv(
    MES_PATH / "machine_logs.csv",
    index=False
)

print("machine_logs.csv created successfully")
print("Shape:", machine_logs_df.shape)
print(machine_logs_df.head())


# ------------------------------------------------------------
# 3. Generate downtime events linked to production orders
# ------------------------------------------------------------

downtime_events = []

selected_orders = production_orders_df.sample(
    n=min(NUM_DOWNTIME, len(production_orders_df)),
    random_state=42
)

for event_number, (_, order) in enumerate(
    selected_orders.iterrows(),
    start=1
):
    order_id = order["order_id"]
    machine_id = order["machine_id"]

    order_start = pd.Timestamp(order["start_time"])
    order_end = pd.Timestamp(order["end_time"])

    order_duration_minutes = max(
        1,
        int((order_end - order_start).total_seconds() / 60)
    )

    # Limit downtime to 30% of the production order duration.
    # This prevents a single downtime event from consuming the entire order.
    max_downtime_minutes = max(
        1,
        int(order_duration_minutes * 0.30)
    )

    duration_minutes = random.randint(
        1,
        min(240, max_downtime_minutes)
    )

    latest_start = (
        order_end - pd.Timedelta(minutes=duration_minutes)
    )

    available_seconds = max(
        0,
        int((latest_start - order_start).total_seconds())
    )

    random_seconds = random.randint(0, available_seconds)

    downtime_start = (
        order_start + pd.Timedelta(seconds=random_seconds)
    )
    downtime_end = (
        downtime_start + pd.Timedelta(minutes=duration_minutes)
    )

    downtime_events.append({
        "event_id": f"DT-{event_number:03d}",
        "production_order_id": order_id,
        "machine_id": machine_id,
        "start_time": downtime_start,
        "end_time": downtime_end,
        "reason_code": random.choice(reason_codes)
    })


downtime_df = pd.DataFrame(downtime_events)

downtime_df.to_csv(
    MES_PATH / "downtime_events.csv",
    index=False
)

print("downtime_events.csv created successfully")
print("Shape:", downtime_df.shape)
print(downtime_df.head())


# ------------------------------------------------------------
# 4. Validate generated MES relationships
# ------------------------------------------------------------

print("\\n========== MES DATA VALIDATION ==========")

order_ids = set(production_orders_df["order_id"])

# Every machine log and downtime event must reference an order.
assert set(machine_logs_df["production_order_id"]).issubset(order_ids)
assert set(downtime_df["production_order_id"]).issubset(order_ids)

# Machine-log machine IDs must match their linked production orders.
machine_check = machine_logs_df.merge(
    production_orders_df[["order_id", "machine_id"]],
    left_on="production_order_id",
    right_on="order_id",
    suffixes=("_log", "_order")
)

assert (
    machine_check["machine_id_log"]
    == machine_check["machine_id_order"]
).all()

# Downtime machine IDs must match their linked production orders.
downtime_check = downtime_df.merge(
    production_orders_df[["order_id", "machine_id"]],
    left_on="production_order_id",
    right_on="order_id",
    suffixes=("_downtime", "_order")
)

assert (
    downtime_check["machine_id_downtime"]
    == downtime_check["machine_id_order"]
).all()

# Total machine-log output must equal actual quantity for every order.
output_by_order = (
    machine_logs_df
    .groupby("production_order_id")["output_count"]
    .sum()
    .sort_index()
)

actual_by_order = (
    production_orders_df
    .set_index("order_id")["actual_qty"]
    .sort_index()
)

assert output_by_order.equals(actual_by_order), (
    "Machine-log output does not match production-order actual quantity."
)

# Rejected quantity must be valid and cannot exceed output.
assert (machine_logs_df["rejected_quantity"] >= 0).all()
assert (
    machine_logs_df["rejected_quantity"]
    <= machine_logs_df["output_count"]
).all()

# Confirm that the requested number of records was generated.
assert len(production_orders_df) == NUM_ORDERS
assert len(machine_logs_df) == NUM_MACHINE_LOGS

print("All MES relationship validations passed.")
print("Production orders:", len(production_orders_df))
print("Machine logs:", len(machine_logs_df))
print("Downtime events:", len(downtime_df))
print(
    "Total actual quantity:",
    int(production_orders_df["actual_qty"].sum())
)
print(
    "Total machine-log output:",
    int(machine_logs_df["output_count"].sum())
)
print(
    "Total rejected quantity:",
    int(machine_logs_df["rejected_quantity"].sum())
)
print("=========================================")
