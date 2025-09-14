# Scheduled Runs Implementation

This document describes the implementation of scheduled/automated runs for the llms.txt crawler system.

## Overview

The system now supports automated scheduling of runs based on cron expressions, allowing projects to automatically check for changes and update their llms.txt files on a regular schedule.

## Key Components

### 1. Database Schema Updates

The `project_configs` table now includes:
- `cron_expression`: Cron expression for scheduling (e.g., "0 2 * * *" for daily at 2 AM)
- `last_run_at`: Timestamp of the last completed run
- `next_run_at`: Timestamp of the next scheduled run
- `is_enabled`: Boolean flag to enable/disable scheduled runs

### 2. Frontend Updates

#### Project Creation Dialog
- Added "Schedule" dropdown with options: Daily, Weekly, Custom (disabled)
- Added "Enable Scheduled Runs" checkbox
- Schedule options are converted to proper cron expressions:
  - Daily: "0 2 * * *" (runs at 2 AM daily)
  - Weekly: "0 2 * * 0" (runs at 2 AM on Sundays)

#### Project List Page
- Displays schedule information (Daily/Weekly/Custom/None)
- Shows "Auto-enabled" status for projects with scheduling enabled
- Shows last run timestamp if available

#### Project Detail Page
- Shows detailed schedule information
- Displays last run and next run timestamps
- Shows auto-runs enabled/disabled status

### 3. Redis Scheduler System

#### Sorted Sets for Scheduling
- Uses Redis sorted sets (`scheduled:jobs`) with timestamps as scores
- Jobs are automatically moved to the immediate queue when their scheduled time arrives
- Supports both immediate and scheduled job processing

#### Scheduler Service
- `apps/worker/scheduler.py`: Standalone service that processes scheduled jobs
- Runs every 30 seconds to check for ready jobs
- Moves ready jobs from `scheduled:jobs` to `generate:queue`
- Includes health check endpoint on port 8081

### 4. API Updates

#### Project Creation
- Automatically creates and enqueues an initial run when a project is created (if scheduling is enabled)
- Calculates and stores `next_run_at` timestamp based on cron expression

#### Run Completion
- After a run completes successfully, automatically schedules the next run
- Updates `last_run_at` and `next_run_at` timestamps
- Creates a new scheduled job in Redis for the next execution

### 5. Worker Updates

#### Enhanced Storage Module
- `calculate_next_run_time()`: Calculates next run time from cron expressions
- `schedule_next_run()`: Schedules the next run after completion
- `update_run_status()`: Enhanced to trigger next run scheduling

## Usage

### Creating a Scheduled Project

1. Create a new project through the web interface
2. Select "Daily" or "Weekly" from the Schedule dropdown
3. Ensure "Enable Scheduled Runs" is checked
4. The system will:
   - Create the project with appropriate cron expression
   - Immediately run the first generation
   - Schedule subsequent runs based on the selected frequency

### Monitoring Scheduled Runs

- View project list to see schedule status and last run times
- Check project detail page for next run information
- Use `/api/scheduler/jobs` to view all scheduled jobs
- Use `/api/scheduler/process` to manually trigger scheduled job processing

### Running the Scheduler

The scheduler service should be run alongside the main worker:

```bash
# In the worker directory
python scheduler.py
```

Or in production with proper process management (PM2, systemd, etc.).

## Technical Details

### Cron Expression Support

Currently supports:
- Daily: `0 2 * * *` (2 AM daily)
- Weekly: `0 2 * * 0` (2 AM on Sundays)

Future versions can be extended to support more complex cron expressions.

### Redis Keys

- `scheduled:jobs`: Sorted set containing scheduled jobs
- `generate:queue`: List containing immediate jobs
- `job:{job_id}`: Hash containing job metadata

### Error Handling

- Failed runs do not trigger next run scheduling
- Only successful runs (`COMPLETE_NO_DIFFS` or `COMPLETE_WITH_DIFFS`) schedule the next run
- Scheduler errors are logged but don't affect the main worker
- Database errors during scheduling are logged but don't fail the current run

## Testing

### Manual Testing

1. Create a project with daily scheduling
2. Check that an initial run is created and queued
3. Wait for the run to complete
4. Verify that a new scheduled job appears in Redis
5. Use the scheduler API to manually process jobs
6. Verify that the next run is scheduled correctly

### API Endpoints for Testing

- `GET /api/scheduler/jobs`: View all scheduled jobs
- `POST /api/scheduler/process`: Manually trigger scheduled job processing

## Future Enhancements

1. Support for more complex cron expressions
2. Timezone support for scheduling
3. Pause/resume scheduling for individual projects
4. Email notifications for scheduled run results
5. Webhook support for external integrations
6. Metrics and monitoring for scheduled runs
