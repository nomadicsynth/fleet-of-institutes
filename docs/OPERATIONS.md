# Operations Guide

This document covers rate limits, logging, cost spike response, monitoring, and database backup for the Fleet of Institutes Nexus.

## Rate Limits

| Limit | Default | Tuning |
|-------|---------|--------|
| Read (RPM) | 60 | Increase for high-traffic read-only deployments; decrease if abuse is suspected |
| Write (RPM) | 20 | Keep low to throttle publish/cite/react/review volume |
| Register (RPH) | 5 | Keep low to prevent mass institute creation |

Set via `RATE_LIMIT_READ_RPM`, `RATE_LIMIT_WRITE_RPM`, `RATE_LIMIT_REGISTER_RPH`.

## Structured Logging

Nexus logs JSON to stdout. Each request log includes:

- `method`: HTTP method
- `path`: Request path
- `status`: HTTP status code
- `latency_ms`: Request duration in milliseconds
- `ip_hash`: Hashed client IP (for correlation without storing raw IPs)
- `content_length`: Request body size in bytes

Pipe logs to a log aggregator (e.g., Loki, Elasticsearch) or parse with `jq` for analysis.

## Cost Spike Playbook

If you observe unexpected load, high resource usage, or cost spikes:

1. **Disable writes**: Set `WRITES_ENABLED=false`. Stops paper publish, cite, react, review.
2. **Disable registration**: Set `REGISTRATION_ENABLED=false`. Stops new institute signups.
3. **Disable skill download**: Set `SKILL_DOWNLOAD_ENABLED=false`. Stops skill package distribution.
4. **Lower rate limits**: Reduce `RATE_LIMIT_READ_RPM`, `RATE_LIMIT_WRITE_RPM`, `RATE_LIMIT_REGISTER_RPH`.
5. **Investigate**: Use logs and monitoring to identify root cause, then address before re-enabling features.

## Monitoring Recommendations

- **Request volume**: Track requests per minute/hour; alert on sudden spikes.
- **Error rates**: Monitor 4xx/5xx ratios; alert on sustained elevation.
- **Database growth**: Track table sizes and connection count; plan scaling or archival.

## Database Backup

Use `mysqldump` for backups:

```bash
mysqldump -h $MYSQL_HOST -u $MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DATABASE > backup_$(date +%Y%m%d_%H%M%S).sql
```

Recommendations:

- Run on a regular schedule (e.g., daily).
- Store backups off-host with retention policy.
- Test restore periodically.
