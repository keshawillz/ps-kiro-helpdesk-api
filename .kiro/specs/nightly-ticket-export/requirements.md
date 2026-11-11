# Requirements Document

## Introduction

Finance calculates SLA credits from closed support tickets. This feature adds a job that runs once a day at 06:00 UTC and exports the tickets that were closed during the previous UTC day to a CSV file in the Finance exports bucket. The job runs before Finance's 3 AM Eastern job. It only reads the ticket table, and it writes only under the `ticket-exports/` prefix of the bucket. A file is written every day, including days with no matching tickets.

## Glossary

- **Export_Job**: The function `helpdesk-nightly-export` that builds and uploads the CSV file.
- **Export_Schedule**: The rule `helpdesk-nightly-export-schedule` that starts the Export_Job.
- **Export_Role**: The role `helpdesk-nightly-export-role` that the Export_Job runs under.
- **Ticket_Table**: The table `helpdesk-tickets`.
- **Finance_Bucket**: The bucket `helpdesk-finance-exports-<account-id>`.
- **Export_Prefix**: The key prefix `ticket-exports/` in the Finance_Bucket.
- **Run_Date**: The UTC date on which the Export_Job runs, in the format YYYY-MM-DD.
- **Export_Window**: The UTC calendar day before the Run_Date, from 00:00:00 to 23:59:59 inclusive.
- **Export_File**: The CSV file produced by one run of the Export_Job.

## Requirements

### Requirement 1: Schedule

**User Story:** As a Finance analyst, I want the export to run once a day before our 3 AM Eastern job, so that the file is ready when the job needs it.

#### Acceptance Criteria

1. THE Export_Schedule SHALL start the Export_Job once daily at 06:00 UTC.
2. THE Export_Schedule SHALL start the Export_Job at 1 AM Eastern Standard Time and at 2 AM Eastern Daylight Time.

### Requirement 2: Ticket selection

**User Story:** As a Finance analyst, I want the export to contain the tickets closed the previous day, so that I can calculate SLA credits from them.

#### Acceptance Criteria

1. WHEN the Export_Job runs, THE Export_Job SHALL include in the Export_File each ticket in the Ticket_Table whose status equals CLOSED and whose closedAt falls within the Export_Window.
2. WHEN the Export_Job runs, THE Export_Job SHALL exclude from the Export_File each ticket whose closedAt falls outside the Export_Window.

### Requirement 3: File contents

**User Story:** As a Finance analyst, I want a predictable CSV layout, so that my report can read the file without special handling.

#### Acceptance Criteria

1. THE Export_Job SHALL write a header row followed by the columns ticketId, requester, priority, createdAt, and closedAt, in that order.
2. THE Export_Job SHALL quote values in the Export_File according to RFC 4180.

### Requirement 4: Destination

**User Story:** As a Finance analyst, I want each day's file at a predictable location, so that my report can find it by date.

#### Acceptance Criteria

1. THE Export_Job SHALL write the Export_File to `s3://helpdesk-finance-exports-<account-id>/ticket-exports/closed-tickets-YYYY-MM-DD.csv`, where YYYY-MM-DD is the Run_Date.
2. WHEN an object already exists at the destination key, THE Export_Job SHALL overwrite the object with the new Export_File.

### Requirement 5: Least access

**User Story:** As a platform owner, I want the export to hold only the access it needs, so that it cannot affect anything beyond its one job.

#### Acceptance Criteria

1. THE Export_Role SHALL be limited to reading the Ticket_Table and writing objects under the Export_Prefix of the Finance_Bucket.
2. THE Export_Job SHALL be named `helpdesk-nightly-export`, THE Export_Role SHALL be named `helpdesk-nightly-export-role`, and THE Export_Schedule SHALL be named `helpdesk-nightly-export-schedule`.

### Requirement 6: Empty days

**User Story:** As a Finance analyst, I want a file even when no tickets match, so that I can tell an empty day from a failed export.

#### Acceptance Criteria

1. IF no tickets match the selection, THEN THE Export_Job SHALL write an Export_File that contains only the header row.
