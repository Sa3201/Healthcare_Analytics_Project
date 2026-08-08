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
from {{ ref('stg_staffing_quality_analysis') }}
where measure_score is not null
  and (
      lower(measure_name) like '%rehospital%'
      or lower(measure_name) like '%readmission%'
  )
