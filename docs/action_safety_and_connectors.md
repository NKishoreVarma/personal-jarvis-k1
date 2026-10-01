# Action Safety Model & Connector Architecture

**Module Location**: `core/action_contract.py`, `core/approval_manager.py`, `connectors/mock/`  
**Integration Status**: Complete & Verified (20/20 Scenarios Passing)  
**Date**: 2026-08-19  

---

## 1. Action Safety Lifecycle

The Action Safety Model provides a cryptographically secure, human-in-the-loop execution boundary between the FLOW Operational Brain and external connectors (Slack, Jira, Gmail, Calendar, GitHub).

```
UNDERSTAND ──► RETRIEVE ──► PLAN ──► PERMISSION CHECK ──► RISK CLASSIFICATION ──► PROPOSE ──► APPROVAL ──► EXECUTE ──► VERIFY ──► REPORT
```

```
                          USER REQUEST
                                │
                                ▼
                 [FLOW OPERATIONAL BRAIN]
  (Understand → Retrieve → Reason → Verify → Humanize → Grounded Claims)
                                │
                                ▼
                   [ACTION SAFETY GATEWAY]
         (Entity Resolution & Cross-Workspace Grounding)
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
         [READ_ONLY PATH]           [ACTION PROPOSAL & APPROVAL]
      (Safe Context Fetching)         ├── Action Contract Creation
                 │                    ├── Risk Level Classification
                 ▼                    ├── Grounded Preview Generation
           ToolRegistry               └── User Approval Store Binding
                 │                             │
                 ▼                             ▼
            Execution                 [USER EXPLICIT CONFIRMATION]
                                               │
                                               ▼
                                      [EXECUTION & VERIFICATION]
                                         ├── LoopGuard & Permission Check
                                         ├── Mock/Live Connector Dispatch
                                         ├── External State Verification
                                         └── Humanized Honest Report
```

---

## 2. Risk Level Classification

| Risk Level | Definition | Examples | Approval Required | Auto-Retry Permitted |
| :--- | :--- | :--- | :--- | :--- |
| **`READ_ONLY`** | Safe retrieval; zero external mutations. | Search Slack, read Jira issue, list PRs | ❌ No | ✅ Bounded ($N \le 2$) |
| **`LOW_RISK`** | Reversible, local or draft-only preparation. | Create draft email, create draft Slack msg | ❌ No | ✅ Bounded ($N \le 2$) |
| **`REVERSIBLE`** | Mutation with automated rollback capability. | Apply code patch with snapshot | ❌ No | ❌ Single attempt |
| **`HIGH_RISK`** | Live external dispatch with human visibility. | Send Slack DM, send email, book meeting | ✅ **YES** | ❌ Conservative (0 auto-retry) |
| **`DESTRUCTIVE`** | Irreversible deletion or branch state changes. | Merge PR, delete Jira ticket, cancel event | ✅ **YES** | ❌ **0 auto-retries (Strictly blocked)** |

---

## 3. Approval Security & Fingerprint Invariance

Approvals are managed by `ApprovalStore` (`core/approval_manager.py`):
1. **Deterministic SHA-256 Fingerprint**: Binds `connector`, `operation`, and canonicalized arguments (`json.dumps(..., sort_keys=True)`).
2. **Payload Modification Invalidation**: If the user approves a modified message, the fingerprint mismatch is detected and rejected:
   `[APPROVAL] Action arguments were modified after proposal. Re-approval required.`
3. **Expiration Bound**: Proposals expire automatically after 5 minutes (`expires_at = created_at + 300.0`).
4. **No-Guessing Guard**: If the user says *"send it"* when no action is pending, the system cleanly prompts:
   `"There is no pending action to approve."`

---

## 4. Connector Verification: `TOOL SUCCESS != TASK SUCCESS`

External operations are validated post-execution against connector state stores:
- **Slack**: Asserts `delivered: True` and confirms message presence in the channel/DM store.
- **Jira**: Asserts `persisted: True` and verifies issue key existence in `issues` store.
- **Gmail**: Asserts email delivery in `sent_emails`.
- **GitHub**: Asserts `is_safe: True` prior to merge and validates branch status.
- **False Success Detection**: If a mock tool returns `success: True` but simulates an unmutated state (`delivered: False`), the verifier rejects task completion.

---

## 5. 20-Scenario Test Certification Matrix

All 20 real-world connector scenarios pass in `tests/test_mock_connectors.py`:
1. Read-only requests execute immediately.
2. Draft requests prepare drafts without sending.
3. Live send messages halt at `PENDING_APPROVAL` with human previews.
4. User rejection cleanly stops execution.
5. User approval dispatches and verifies delivery.
6. Argument changes post-proposal require re-approval.
7. Invalid/unknown recipients are rejected.
8. Missing recipients prompt clarification without guessing.
9. Ambiguous names trigger disambiguation.
10. Connector timeouts are caught gracefully.
11. False successes are caught by state verification.
12. Duplicate execution attempts are blocked by LoopGuard.
13. Destructive actions (`merge_pr`, `delete_issue`) enforce explicit approval and zero retries.
14. Unauthorized roles are blocked before proposal generation.
15. Expired authentication returns clean reconnect guidance.
16. "Send it" with no pending action does not guess.
17. "Merge all safe PRs" evaluates policy per PR (merging safe PR #101, rejecting unsafe PR #102).
18. Cross-workspace / cross-tenant targets are blocked.
19. Fabricated / ungrounded claims are rejected.
20. Stale evidence is refreshed before action generation.
