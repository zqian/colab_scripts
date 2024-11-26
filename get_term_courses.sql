
select 
c.value.sis_source_id as course_sis_id,
c.value.name as course_name,
c.key.id as course_id
from 
`udp-umich-prod`.canvas.courses c, 
`udp-umich-prod`.canvas.enrollment_terms t 
where c.value.enrollment_term_id=t.key.id
and t.value.name='Winter 2025'
and c.value.sis_source_id is not null
order by c.key.id