from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
import os
import glob

# 检查所有 runs
base_dir = os.path.expanduser('~/ultralytics/runs/detect')
run_dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]

print(f"Found {len(run_dirs)} runs in {base_dir}\n")

for run_dir in sorted(run_dirs):
    run_path = os.path.join(base_dir, run_dir)
    event_files = glob.glob(os.path.join(run_path, 'events.out.tfevents.*'))
    
    if not event_files:
        print(f"[{run_dir}] No event files")
        continue
    
    try:
        ea = EventAccumulator(event_files[0])
        ea.Reload()
        scalars = ea.Tags()['scalars']
        
        has_train_loss = any('train/' in s and 'loss' in s for s in scalars)
        has_val_loss = any('val/' in s and 'loss' in s for s in scalars)
        
        print(f"[{run_dir}] {len(scalars)} scalars, train_loss={has_train_loss}, val_loss={has_val_loss}")
        if not has_train_loss:
            print(f"  Available: {scalars}")
    except Exception as e:
        print(f"[{run_dir}] Error: {e}")
