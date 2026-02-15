# Deploy Freeze & Dress Rehearsal Plan

ClassBridge March 6, 2026 pilot launch.

## Timeline

| Date | Milestone |
|------|-----------|
| **Mar 3 (Mon)** | Deploy freeze begins — announce to all contributors |
| **Mar 4 (Tue)** | Dress rehearsal — full end-to-end walkthrough |
| **Mar 5 (Wed)** | Final smoke tests, pre-launch backup, last checks |
| **Mar 6 (Thu)** | Pilot launch day |

## Deploy Freeze Rules (Mar 3-6)

- **No code merges to `master`** unless classified as a critical hotfix (P1)
- All in-progress feature branches stay unmerged until after the pilot
- CI/CD pipeline remains active — pushing to `master` still triggers deploy
- The freeze ensures production stability during final testing and launch

### What Qualifies as a Critical Hotfix

A hotfix is allowed during the freeze only if:
- The app is down or returning 500 errors (P1)
- Users cannot log in (P1)
- Data loss is occurring (P1)

Everything else (UI glitches, cosmetic issues, minor bugs) waits until after launch.

## Deploy Freeze Announcement

Send to all contributors on **Mar 3**:

> **Subject: Deploy freeze in effect — ClassBridge pilot**
>
> Team,
>
> The deploy freeze for the March 6 pilot launch is now in effect.
>
> - **No merges to `master`** until after the pilot (March 6)
> - If you find a critical bug (service down, login broken, data loss), contact the project owner immediately
> - All other issues should be logged in GitHub Issues for post-pilot fixes
>
> Thanks for your help getting us to launch!

## Dress Rehearsal (Mar 4)

Walk through the entire pilot experience end-to-end, simulating what each role will do on launch day.

### Web App — All Roles

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Visit https://www.classbridge.ca | Landing page loads |
| 2 | Log in as **parent** | Parent dashboard shows children, assignments, messages |
| 3 | Navigate to child overview | Courses, assignments, and tasks display correctly |
| 4 | Open Messages, reply to a conversation | Message sends and appears in thread |
| 5 | Check Notifications | Notifications display and can be marked read |
| 6 | Check Calendar | Assignments appear on correct dates |
| 7 | Log out, log in as **student** | Student dashboard loads with courses and study tools |
| 8 | Generate a study guide or quiz | AI tool produces output |
| 9 | Log out, log in as **teacher** | Teacher dashboard shows courses, messages, assignments |
| 10 | Reply to a parent message | Message sends successfully |
| 11 | Log out, log in as **admin** | Admin dashboard loads with system overview |

### Mobile App — Parent

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Open ClassBridge in Expo Go (iOS) | App loads, login screen appears |
| 2 | Log in with parent credentials | Dashboard shows children, due items, unread count |
| 3 | Tap a child's name | Child overview: courses, assignments, tasks |
| 4 | Toggle a task checkbox | Task status updates |
| 5 | Open Calendar tab | Monthly view with assignment dots |
| 6 | Open Messages tab, reply to a conversation | Message sends |
| 7 | Open Notifications tab, mark one as read | Notification clears |
| 8 | Open Profile tab | Account info displays correctly |
| 9 | Repeat steps 1-8 on **Android** | Same results |

### Cross-Platform Verification

- [ ] Mobile app connects to production API (not localhost)
- [ ] Data created on web appears in mobile (and vice versa)
- [ ] Unread message badges update across both platforms

## Pilot Account Verification (Mar 4-5)

Verify every pilot participant can log in:

```bash
# List all active users with their roles
gcloud sql connect emai-db --user=emai-user --database=emai --project=emai-dev-01 \
  -c "SELECT u.email, u.role, u.is_active FROM users u WHERE u.is_active = true ORDER BY u.role, u.email;"
```

For each pilot account:
- [ ] Login works on web (https://www.classbridge.ca)
- [ ] Parent accounts also work on mobile (Expo Go)
- [ ] Correct children linked to correct parents
- [ ] Teachers have correct course assignments
- [ ] Demo data (assignments, messages) is in place

## Final Smoke Test (Mar 5)

Quick pass to confirm nothing broke since the dress rehearsal:

```bash
# Health check
curl -s https://www.classbridge.ca/health

# Check for recent errors
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=classbridge AND severity>=ERROR" \
  --project=emai-dev-01 --limit=10 --format="table(timestamp,severity,textPayload)"

# Verify Cloud SQL is healthy
gcloud sql instances describe emai-db --project=emai-dev-01 --format="value(state)"
```

- [ ] Health endpoint returns 200
- [ ] No unexpected errors in logs
- [ ] Database is RUNNABLE
- [ ] All pilot accounts still log in
- [ ] Pre-launch backup taken: `./scripts/backup/manual-backup.sh pre-launch`

## Hotfix Plan

If a critical issue is discovered during or after launch:

1. **Assess severity** using levels in [INCIDENT_RESPONSE.md](../INCIDENT_RESPONSE.md)
2. **P1 only:** Fix directly on `master` and push (CI runs tests, then deploys)
3. **Verify:** After deploy, run smoke test on production
4. **Rollback** if the fix makes things worse:
   ```bash
   # List revisions, route traffic to previous working one
   gcloud run revisions list --service=classbridge --region=us-central1 --project=emai-dev-01 --limit=5
   gcloud run services update-traffic classbridge \
     --to-revisions=<GOOD_REVISION>=100 \
     --region=us-central1 --project=emai-dev-01
   ```
5. **Log** the incident in GitHub Issues with `incident` label

Full procedures: [docs/INCIDENT_RESPONSE.md](../INCIDENT_RESPONSE.md)

## Support Contact

| Role | Contact | Availability |
|------|---------|--------------|
| **Primary support** | support@classbridge.ca | Mar 3-6, responsive within 1 hour |
| **Escalation** | Project owner (direct contact) | Mar 6 launch day, immediate for P1/P2 |

## Related Documents

- [Go-Live Checklist](go-live-checklist.md) — Launch day procedures
- [Incident Response](../INCIDENT_RESPONSE.md) — Monitoring and incident handling
- [Disaster Recovery](../DISASTER_RECOVERY.md) — Backup and restore procedures
- [Quick-Start Guide](quick-start-guide.md) — Parent-facing setup instructions
