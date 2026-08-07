select
    facility_ccn,
    facility_name,
    state,
    calendar_quarter,
    days_reported,
    average_daily_census,
    average_staffing_hprd,
    average_rn_hprd,
    average_occupancy_rate,
    total_nursing_hours,
    employee_nursing_hours,
    contract_nursing_hours,
    contract_hour_percentage
from {{ source('healthcare_raw', 'FACILITY_QUARTERLY_SUMMARY') }}
where facility_ccn is not null
