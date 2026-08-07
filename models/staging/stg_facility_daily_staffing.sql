select
    facility_ccn,
    facility_name,
    state,
    calendar_quarter,
    work_date,
    resident_census,
    certified_beds,
    rn_hours,
    lpn_hours,
    cna_hours,
    employee_nursing_hours,
    contract_nursing_hours,
    total_nursing_hours,
    staffing_hours_per_resident_day,
    rn_hours_per_resident_day,
    occupancy_rate_proxy
from {{ source('healthcare_raw', 'FACILITY_DAILY_STAFFING') }}
where facility_ccn is not null
