from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
import os

log_dir = os.path.expanduser('~/ultralytics/runs/detect/exp_1775568244')
events_file = [f for f in os.listdir(log_dir) if f.startswith('events.out.tfevents')][0]
events_path = os.path.join(log_dir, events_file)

print(f'Reading: {events_path}')
ea = EventAccumulator(events_path)
ea.Reload()

scalars = ea.Tags()['scalars']
print(f'Total scalar tags: {len(scalars)}')
for tag in sorted(scalars):
    print(f'  - {tag}')
