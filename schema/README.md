# Chicago Crashes Data Schema

Complete documentation of the Chicago Traffic Crashes dataset from the City of Chicago Open Data Portal.

## Official Data Source

**Crashes Dataset:** https://data.cityofchicago.org/Transportation/Traffic-Crashes-Crashes/85ca-t3if

This dataset contains traffic crash records reported to the Chicago Police Department (CPD). Each crash record can be linked to corresponding vehicle and person/injury records using the `crash_record_id`.

## Schema Documentation

### Full Column Reference

See [chicago_crashes_crashes_schema.csv](chicago_crashes_crashes_schema.csv) for comprehensive column definitions including:
- Column names
- Data types
- Descriptions
- Nullability indicators
- Example values

### API Field Mapping

See [chicago_crashes_data_dictionary.csv](chicago_crashes_data_dictionary.csv) for API field names matched to column definitions.

### JSON Schema

See [chicago_crashes_schema.json](chicago_crashes_schema.json) for machine-readable JSON schema suitable for programmatic validation.

## Key Columns

### Identifiers
- `crash_record_id` - Unique crash identifier (links to Vehicles and People datasets)

### Temporal
- `crash_date` - Date and time of crash (Floating Timestamp)
- `crash_hour` - Hour of crash (0-23)
- `crash_day_of_week` - Day of week
- `crash_month` - Month (1-12)
- `date_police_notified` - When police were notified

### Location
- `latitude` - Approximate crash latitude
- `longitude` - Approximate crash longitude
- `location` - WKT POINT format
- `street_no`, `street_direction`, `street_name`
- `beat_of_occurrence` - Police beat number

### Crash Details
- `crash_type` - Classification of crash
- `first_crash_type` - Type of first collision
- `trafficway_type` - Road type (divided, not divided, etc.)
- `alignment` - Street alignment (straight, curved, etc.)
- `lane_cnt` - Number of lanes
- `posted_speed_limit` - Posted limit in mph

### Environmental Conditions
- `weather_condition` - RAIN, CLEAR, CLOUDY/OVERCAST, etc.
- `lighting_condition` - DARKNESS, DAYLIGHT, DUSK, etc.
- `roadway_surface_cond` - WET, DRY, UNKNOWN, etc.

### Traffic Control & Defects
- `traffic_control_device` - TRAFFIC SIGNAL, STOP SIGN, NO CONTROLS, etc.
- `device_condition` - Condition of control device
- `road_defect` - NO DEFECTS, WORN SURFACE, UNKNOWN, etc.

### Crash Characteristics
- `intersection_related_i` - Y/N if intersection-related
- `private_property_i` - Y/N if on private property
- `hit_and_run_i` - Y/N for hit-and-run
- `damage` - OVER $1,500, $501 - $1,500, $500 OR LESS

### Contributing Factors
- `prim_contributory_cause` - Primary cause (UNABLE TO DETERMINE, WEATHER, IMPROPER BACKING, etc.)
- `sec_contributory_cause` - Secondary cause

### Injury Data
- `most_severe_injury` - NO INDICATION, NONINCAPACITATING INJURY, INCAPACITATING INJURY, FATAL INJURY
- `injuries_total` - Total count
- `injuries_fatal` - Fatal count
- `injuries_incapacitating` - Incapacitating count
- `injuries_non_incapacitating` - Non-incapacitating count
- `injuries_reported_not_evident` - Reported injuries without visible signs
- `injuries_no_indication` - No indication of injury
- `injuries_unknown` - Unknown injury count

### Vehicle & Personnel
- `num_units` - Number of vehicles involved
- `photos_taken_i` - Y/N if photos taken
- `statements_taken_i` - Y/N if statements taken

### Work Zones
- `work_zone_i` - Y/N if in work zone
- `work_zone_type` - Type of work zone (CONSTRUCTION, etc.)
- `workers_present_i` - Y/N if workers present

### Administrative
- `report_type` - NOT ON SCENE (DESK REPORT), ON SCENE, AMENDED
- `crash_date_est_i` - Y if date was estimated

## Data Types

- **Text** - String/categorical data
- **Number** - Integer or decimal values
- **Floating Timestamp** - ISO 8601 format with milliseconds (e.g., `2026-04-18T01:45:00.000`)

## Linking to Related Data

The `crash_record_id` can be used to link records across three Chicago datasets:

1. **Crashes** (Primary) - This dataset
2. **Vehicles** - Vehicle details involved in each crash
3. **People** - People/injury information for each crash

## Data Quality Notes

- Some fields may be null or contain "UNKNOWN" values
- Location data is approximate
- Data is reported by officers and may contain estimation
- Hit-and-run crashes may have incomplete vehicle information
- Private property crashes may have limited data

## Updates

This dataset is continuously updated by the Chicago Police Department. Check the official portal for the latest data refresh status.

---

**Last Updated:** April 2026  
**Documentation Version:** 1.0
