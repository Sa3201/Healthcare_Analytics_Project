select
    state,
    calendar_quarter,
    count(distinct facility_ccn) as facility_count,
    round(avg(average_daily_census), 2) as average_daily_census,
    round(avg(average_staffing_hprd), 2) as average_staffing_hprd,
    round(avg(average_rn_hprd), 2) as average_rn_hprd,
    round(avg(average_occupancy_rate) * 100, 2) as average_occupancy_percent,
    round(avg(contract_hour_percentage) * 100, 2) as average_contract_hour_percent
from {{ ref('stg_facility_quarterly_summary') }}
where state is not null
group by state, calendar_quarter
