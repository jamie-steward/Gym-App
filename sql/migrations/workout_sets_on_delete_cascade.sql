-- Ensure workout_sets are automatically deleted when their workout is deleted.
-- Run this in the Supabase SQL Editor.
-- This migration does not delete existing data. If orphaned workout_sets exist,
-- it stops and reports the problem so you can inspect them first.

do $$
declare
    orphan_count bigint;
    existing_fk record;
begin
    select count(*)
    into orphan_count
    from public.workout_sets ws
    left join public.workouts w on w.id = ws.workout_id
    where ws.workout_id is not null
      and w.id is null;

    if orphan_count > 0 then
        raise exception
            'Cannot add workout_sets -> workouts foreign key: % orphaned workout_sets rows exist.',
            orphan_count;
    end if;

    alter table public.workout_sets
    drop constraint if exists fk_workout_sets_workout;

    for existing_fk in
        select c.conname
        from pg_constraint c
        join pg_class child_table on child_table.oid = c.conrelid
        join pg_namespace child_schema on child_schema.oid = child_table.relnamespace
        join pg_class parent_table on parent_table.oid = c.confrelid
        join pg_namespace parent_schema on parent_schema.oid = parent_table.relnamespace
        where c.contype = 'f'
          and child_schema.nspname = 'public'
          and child_table.relname = 'workout_sets'
          and parent_schema.nspname = 'public'
          and parent_table.relname = 'workouts'
          and pg_get_constraintdef(c.oid) like '%FOREIGN KEY (workout_id)%'
    loop
        execute format(
            'alter table public.workout_sets drop constraint %I',
            existing_fk.conname
        );
    end loop;

    alter table public.workout_sets
    add constraint fk_workout_sets_workout
    foreign key (workout_id)
    references public.workouts(id)
    on delete cascade;
end $$;

-- Optional verification after running the migration:
select
    c.conname,
    pg_get_constraintdef(c.oid) as constraint_definition
from pg_constraint c
join pg_class child_table on child_table.oid = c.conrelid
join pg_namespace child_schema on child_schema.oid = child_table.relnamespace
where child_schema.nspname = 'public'
  and child_table.relname = 'workout_sets'
  and c.conname = 'fk_workout_sets_workout';
