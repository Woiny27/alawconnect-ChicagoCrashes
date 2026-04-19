# Chicago Crash Data Relationships

This document describes how the three related Chicago traffic crash datasets link together.

## The Three Datasets

### 1. Crashes Dataset
- **Portal ID:** `85ca-t3if`
- **API:** https://data.cityofchicago.org/api/views/85ca-t3if
- **Primary Key:** `crash_record_id`
- **Description:** High-level crash records with location, conditions, and injury summaries

### 2. Vehicles Dataset  
- **Portal ID:** `68nd-jvt3`
- **API:** https://data.cityofchicago.org/api/views/68nd-jvt3
- **Primary Key:** `crash_unit_id`
- **Foreign Key:** `crash_record_id` (links to Crashes)
- **Description:** Details about each vehicle/unit involved in a crash

### 3. People Dataset
- **Portal ID:** `u6fk-qq6r`
- **API:** https://data.cityofchicago.org/api/views/u6fk-qq6r
- **Primary Key:** `person_id`
- **Foreign Keys:** `crash_record_id` (links to Crashes), `crash_unit_id` (links to Vehicles)
- **Description:** Details about people (drivers, passengers, pedestrians) involved in crashes

## Entity Relationship Diagram

```
┌─────────────────────────────────────────┐
│           CRASHES                       │
├─────────────────────────────────────────┤
│ crash_record_id (PK)                    │
│ crash_date                              │
│ latitude, longitude                     │
│ crash_type                              │
│ most_severe_injury                      │
│ injuries_total                          │
│ ... (45 other fields)                   │
└────────────────┬────────────────────────┘
                 │ (1:N)
                 │ crash_record_id
                 │
         ┌───────▼───────┐
         │   VEHICLES    │
         ├───────────────┤
         │ crash_unit_id │ (PK)
         │ crash_record_ │
         │   id (FK)     │
         │ unit_no       │
         │ vehicle_id    │
         │ make, model   │
         │ num_passengers│
         │ ... (20+ more)│
         └───────┬───────┘
                 │ (1:N)
                 │ crash_unit_id
                 │
         ┌───────▼──────────┐
         │     PEOPLE       │
         ├──────────────────┤
         │ person_id (PK)   │
         │ crash_record_id  │
         │   (FK)           │
         │ crash_unit_id    │
         │   (FK)           │
         │ person_type      │
         │ age, gender      │
         │ injury_type      │
         │ ... (20+ more)   │
         └──────────────────┘
```

## Linking Examples

### Example 1: Get all vehicles in a specific crash
```sql
SELECT c.crash_record_id, c.crash_date, v.*
FROM crashes c
JOIN vehicles v ON c.crash_record_id = v.crash_record_id
WHERE c.crash_record_id = 'abc123...';
```

### Example 2: Get all people involved in a specific vehicle
```sql
SELECT v.crash_unit_id, v.vehicle_id, p.*
FROM vehicles v
JOIN people p ON v.crash_unit_id = p.crash_unit_id
WHERE v.crash_unit_id = 'xyz789...';
```

### Example 3: Full crash with all vehicles and people
```sql
SELECT c.*, v.*, p.*
FROM crashes c
LEFT JOIN vehicles v ON c.crash_record_id = v.crash_record_id
LEFT JOIN people p ON v.crash_unit_id = p.crash_unit_id
WHERE c.crash_record_id = 'abc123...';
```

## Key Fields for Joining

### Crashes ↔ Vehicles
- **Join Key:** `crashes.crash_record_id = vehicles.crash_record_id`
- **Cardinality:** 1:N (one crash can have multiple vehicles)

### Vehicles ↔ People
- **Join Key:** `vehicles.crash_unit_id = people.crash_unit_id`
- **Cardinality:** 1:N (one vehicle can have multiple people)

### Crashes ↔ People (direct)
- **Join Key:** `crashes.crash_record_id = people.crash_record_id`
- **Cardinality:** 1:N (one crash can have multiple people)
- **Note:** People can also be joined via vehicles for more detailed info

## Data Aggregation Examples

### Count vehicles per crash
```sql
SELECT crash_record_id, COUNT(*) as vehicle_count
FROM vehicles
GROUP BY crash_record_id;
```

### Count people per vehicle
```sql
SELECT crash_unit_id, COUNT(*) as person_count
FROM people
GROUP BY crash_unit_id;
```

### Injury summary including vehicle details
```sql
SELECT 
  c.crash_record_id,
  c.crash_date,
  v.unit_no,
  v.make,
  v.model,
  COUNT(p.person_id) as occupant_count,
  COUNT(CASE WHEN p.injury_type = 'FATAL INJURY' THEN 1 END) as fatalities
FROM crashes c
JOIN vehicles v ON c.crash_record_id = v.crash_record_id
LEFT JOIN people p ON v.crash_unit_id = p.crash_unit_id
GROUP BY c.crash_record_id, v.crash_unit_id;
```

## Schema Files

- [crashes_schema.json](crashes_schema.json) - JSON Schema for crash records
- [vehicles_schema.json](vehicles_schema.json) - JSON Schema for vehicle records
- [socrata_columns_api.json](socrata_columns_api.json) - Official Crashes columns from Socrata API
- [socrata_vehicles_api.json](socrata_vehicles_api.json) - Official Vehicles columns from Socrata API

## Notes

- Not all crashes have vehicles (e.g., pedestrian incidents)
- Not all vehicles have people records (e.g., parked cars hit)
- Some people records may have missing vehicle/unit assignments
- Foreign keys may be null in some edge cases
- The `person_type` field distinguishes between driver, passenger, pedestrian, etc.
