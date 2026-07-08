with events as (
    select * from {{ ref('stg_events') }}
)

select
    user_id,
    event_type,
    date_trunc('hour', ts) as event_hour,
    count(*) as event_count
from events
group by user_id, event_type, date_trunc('hour', ts)
