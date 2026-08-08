with ranked_facilities as (
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
        row_number() over (
            partition by calendar_quarter
            order by average_staffing_hprd
        ) as staffing_rank
    from {{ ref('stg_facility_quarterly_summary') }}
    where average_staffing_hprd is not null
)

select *
from ranked_facilities
where staffing_rank <= 10
