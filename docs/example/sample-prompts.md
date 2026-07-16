# Sample Prompts

This document provides readable, task-oriented sample prompts for the IBM Storage Protect MCP Server. Use these prompts as starting points and adapt names, server identifiers, dates, and scope to your environment.

## How to Use These Prompts

When writing prompts:

- keep the scope narrow
- prefer exact object names when known
- ask for one task at a time
- avoid broad log searches unless necessary
- ask for summaries first, then drill into details

---

## 1. Discover Available Capabilities

Use these prompts to understand what servers and tools are available before starting operational work.

### List available MCP servers and tools

```text
What micro-MCP servers and tools are available in sp-mcp-server-remote-tumbleweed?
```

### Map tools to IBM Storage Protect commands

```text
List all IBM Storage Protect commands called by the tools available in sp-mcp-server-remote-tumbleweed.
```

---

## 2. Basic Information Requests

Use these prompts for quick operational visibility.

### Check database status

```text
What is the database status?
```

### List active clients

```text
Show me all active clients.
```

### Review failed operations

```text
Show me all failed operations from the last 24 hours.
```

### Check running threads

```text
How many threads are running?
```

---

## 3. Configuration and Provisioning Tasks

Use these prompts for common administrative changes.

### Create a device class

```text
Create a devclass named foo_devclass1.
```

### Create a primary storage pool

```text
Create a PRIMARY storage pool named my_container_pool using the DISK devclass with description "My storage pool".
```

---

## 4. How-To and Concept Questions

Use these prompts when you want explanation plus an example.

### Tier data from container storage to cloud storage

```text
What are the steps to tier data from a container-type storage pool to a cloud-type storage pool? Show me an example of how to do this.
```

### Understand retention concepts

```text
What is retset and how is it related to a retention pool?
```

---

## 5. Monitoring and Diagnostics

Use these prompts for health checks and issue investigation.

### Run server monitoring

```text
Run the tool run_servermon.
```

### Check thread count and database condition

```text
How many threads are running, and what is the DB status? Tell me whether it is almost full or locked.
```

### Analyze servermon output

```text
Analyze the servermon logs for customer issues and summarize the most important findings.
```

---

## 6. Solution-Oriented Scenario Prompts

These prompts are longer because they describe a role, objective, and expected outcome.

### Cloud Architect: validate tiering efficiency

```text
On sp-mcp-server-remote-tumbleweed, I am a Cloud Architect managing data movement to object storage. I want to validate tiering efficiency. Analyze the age of data residing on high-performance disk versus the cloud tier. Identify data that meets cold criteria but has not moved, and recommend migration threshold adjustments to optimize storage cost.
```

### Capacity Planner: forecast storage sustainability

```text
On sp-mcp-server-remote-tumbleweed, I am a Capacity Planner managing IBM Storage Protect storage pools. Retrieve storage utilization trends for the last 90 days, including deduplication savings, compression ratios, and daily data ingest rates across disk and cloud tiers. Forecast capacity exhaustion timelines and recommend repository expansion or policy adjustments.
```

### Platform Owner: assess database health

```text
On sp-mcp-server-remote-tumbleweed, I am a Platform Owner monitoring system stability. Analyze database growth trends, reorganization status, and maintenance job success over the last 30 days. Identify performance risks caused by fragmentation and recommend optimization steps to prevent service latency.
```

---

## 7. Prompt Design for Large Investigations

Large prompts can fail if they trigger overly broad queries. The example below shows how to refine a troubleshooting request so it stays constrained and readable.

### Broad prompt that can exhaust context

```text
I am a Backup Engineer looking to reduce manual troubleshooting. Identify all failed or missed backup schedules in the last 24 hours. Categorize failures by root cause such as communication errors, locked files, or out-of-space conditions.
```

### Refined prompt with execution constraints

```text
You are assisting a Backup Engineer to reduce manual troubleshooting in IBM Storage Protect.

Goal:
Identify all failed or missed client backup schedules in the last 24 hours and categorize each by likely root cause.

Query success rules:
1. Prefer the most constrained query possible before expanding scope.
2. Never call query_scheduled_event without first discovering a valid policy domain and relevant schedule names.
3. Never call query_activity_log without both:
   - a specific search term
   - a narrow date/time window
4. If a query fails, retry once with a simpler but still constrained parameter set.
5. If a query still fails, state the exact failed query pattern and move to the next best constrained query.

Required execution sequence:

Step 1 - Discover valid scope
- Use query_policy_group first to identify valid policy domains.
- Use query_schedule with domain_name and type="client" to list candidate backup schedules.
- Focus only on schedules whose start times fall within the last 24 hours or whose period indicates daily execution.

Step 2 - Query scheduled events using narrow scope
- Run query_scheduled_event only after identifying:
  - one valid policy_group
  - one or more exact schedule_name values
- Query one schedule at a time.
- Use date filters in MM/DD/YYYY format.
- If supported, add start and end times only in exact HH-SS format.
- Do not issue broad, all-domain event queries.

Step 3 - Keep only abnormal events
- Retain only events with status Failed, Missed, Incomplete, or abnormal non-success result codes.

Step 4 - Validate each abnormal event with targeted log search
- Use query_activity_log only for one failed event at a time.
- Search using the most specific available discriminator, in this order:
  1. exact node name
  2. exact schedule name
  3. specific IBM message code, if already known
- Always include a narrow time window around the scheduled or actual event time.
- Start with a window of plus or minus 60 minutes.
- Expand only once to plus or minus 180 minutes if no evidence is found.
- Never run broad searches such as all ANR*, all VMWARE_*, or unbounded 24-hour log scans.

Step 5 - Root cause classification
Classify each event as one of the following:
- Communication error
- Locked file or file in use
- Out of space or storage pool full
- Authentication, node locked, or password issue
- Schedule window, timeout, or missed window
- Other or unknown

Step 6 - If query_scheduled_event fails
- Retry once using a simpler valid call:
  - exact policy_group
  - exact schedule_name
  - date only, no time filters
- If it still fails, continue schedule-by-schedule using:
  - query_schedule
  - query_client
  - query_active_session
  - query_storage_container
- Mark findings as Likely instead of Confirmed.

Step 7 - If query_activity_log fails
- Retry once with:
  - a single exact node or schedule search term
  - a smaller time window
- If it still fails, do not broaden the query.
- Use operational evidence from:
  - query_client
  - query_active_session
  - query_storage_container

Output format:
- Executive Summary
- Confirmed Failed or Missed Schedules Table
- Likely Failed or Abnormal Schedules Table
- Top Recurring Failure Patterns
- Environmental Risks
- Items Requiring Immediate Attention
- Limitations

Constraints:
- Limit analysis to the last 24 hours only.
- Use query_policy_group and query_schedule to discover valid inputs before query_scheduled_event.
- Use query_activity_log only with exact search terms and narrow time windows.
- Query one schedule at a time rather than all schedules at once.
- Query one failed event at a time rather than all logs at once.
- Do not include raw log dumps unless a single short message is essential as evidence.
- Clearly distinguish Confirmed from Likely findings.
```

---

## 8. Tips for Better Results

- Replace placeholder server names with your actual MCP server name.
- Prefer exact object names such as node names, schedule names, and pool names.
- Ask for summaries before requesting raw details.
- For troubleshooting, constrain by time window, object name, and failure type.
- For change operations, clearly state the desired object name and configuration values.