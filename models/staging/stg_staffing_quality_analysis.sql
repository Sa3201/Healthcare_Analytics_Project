select
    facility_ccn,
    facility_name,
    state,
    calendar_quarter,
    average_daily_census,
    average_staffing_hprd,
    average_rn_hprd,
    average_occupancy_rate,
    contract_hour_percentage,
    quality_source,
    measure_code,
    measure_name,
    measure_score,
    measure_period
from {{ source('healthcare_raw', 'STAFFING_QUALITY_ANALYSIS') }}
where facility_ccn is not null
