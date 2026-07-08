with source as (
    select * from {{ source('raw', 'events') }}
),

deduped as (
    select
        event_id,
        user_id,
        event_type,
        ts,
        row_number() over (partition by event_id order by ts desc) as rn
    from source
)

select
    event_id,
    user_id,
    event_type,
    ts
from deduped
where rn = 1
