import Link from "next/link";

import { AppMenu } from "@/app/_components/app-menu";
import {
  createFieldStopIssueAction,
  logoutAction,
  markFieldStopArrivedAction,
  markFieldStopDoneAction,
  markFieldStopSkippedAction,
  saveFieldStopNoteAction,
  startFieldShiftAction,
  submitFieldShiftAction,
  uploadFieldStopProofAction,
} from "@/app/actions";
import { BestEffortGpsFields } from "@/app/field/best-effort-gps-fields";
import fieldStyles from "@/app/field/field.module.css";
import workspaceStyles from "@/app/workspace.module.css";
import { getRoleLabel, requireSession } from "@/lib/auth";
import { loadAssignedGarbageTasks, type FieldStop } from "@/lib/field-ops";

export const dynamic = "force-dynamic";

const ISSUE_TYPE_OPTIONS = [
  { value: "route", label: "Route issue" },
  { value: "vehicle", label: "Vehicle issue" },
  { value: "crew", label: "Crew issue" },
  { value: "safety", label: "Safety risk" },
  { value: "citizen", label: "Citizen complaint" },
  { value: "other", label: "Other" },
];

const ISSUE_SEVERITY_OPTIONS = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];

type PageProps = {
  searchParams?: Promise<{
    error?: string | string[];
    notice?: string | string[];
    taskId?: string | string[];
  }>;
};

function getMessage(value?: string | string[]) {
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
}

function parseTaskId(value?: string | string[]) {
  const raw = getMessage(value);
  const numeric = Number(raw);
  return Number.isFinite(numeric) && numeric > 0 ? numeric : null;
}

function statusTone(stop: FieldStop) {
  if (stop.status === "done") {
    return fieldStyles.stopDone;
  }
  if (stop.status === "skipped") {
    return fieldStyles.stopSkipped;
  }
  if (stop.status === "arrived") {
    return fieldStyles.stopArrived;
  }
  return fieldStyles.stopDraft;
}

export default async function FieldPage({ searchParams }: PageProps) {
  const session = await requireSession();
  const query = (await searchParams) ?? {};
  const selectedTaskId = parseTaskId(query.taskId);
  const noticeMessage = getMessage(query.notice);
  const errorMessage = getMessage(query.error);
  const canCreateProject =
    session.role === "general_manager" || session.role === "system_admin";

  const bundle = await loadAssignedGarbageTasks(
    {
      userId: session.uid,
      selectedTaskId,
    },
    {
      login: session.login,
      password: session.password,
    },
  );

  const assignment = bundle.activeAssignment;

  return (
    <main className={workspaceStyles.shell}>
      <div className={workspaceStyles.container}>
        <header className={workspaceStyles.navBar}>
          <div className={workspaceStyles.navLinks}>
            <Link href="/" className={workspaceStyles.backLink}>
              Dashboard
            </Link>
            <span>{getRoleLabel(session.role)}</span>
            <span>{session.name}</span>
          </div>

          <div className={workspaceStyles.navActions}>
            <form action={logoutAction}>
              <button type="submit" className={workspaceStyles.secondaryButton}>
                Log out
              </button>
            </form>
          </div>
        </header>

        <AppMenu active="field" canCreateProject={canCreateProject} />

        <section className={`${workspaceStyles.heroCard} ${fieldStyles.heroCard}`}>
          <span className={workspaceStyles.eyebrow}>Mobile Field Flow</span>
          <h1>My Route Today</h1>
          <p>
            Drivers and inspectors can start the shift, work stop by stop, upload
            before and after proof photos, report issues, and submit the completed
            route for verification from this page.
          </p>

          <div className={fieldStyles.heroFacts}>
            <article className={workspaceStyles.statCard}>
              <span>Date</span>
              <strong>{bundle.requestedDateLabel}</strong>
            </article>
            <article className={workspaceStyles.statCard}>
              <span>Assigned routes</span>
              <strong>{bundle.assignments.length}</strong>
            </article>
            <article className={workspaceStyles.statCard}>
              <span>Role</span>
              <strong>{getRoleLabel(session.role)}</strong>
            </article>
          </div>
        </section>

        {errorMessage ? (
          <div className={`${workspaceStyles.message} ${workspaceStyles.errorMessage}`}>
            {errorMessage}
          </div>
        ) : null}
        {noticeMessage ? (
          <div className={`${workspaceStyles.message} ${workspaceStyles.noticeMessage}`}>
            {noticeMessage}
          </div>
        ) : null}

        {bundle.assignments.length > 1 ? (
          <section className={fieldStyles.routeSelector}>
            {bundle.assignments.map((item) => (
              <Link
                key={item.id}
                href={`/field?taskId=${item.id}`}
                className={`${fieldStyles.routeChip} ${
                  assignment?.id === item.id ? fieldStyles.routeChipActive : ""
                }`}
              >
                <span>{item.vehicleName}</span>
                <strong>{item.routeName}</strong>
                <small>
                  {item.completedStopCount}/{item.stopCount} stops
                </small>
              </Link>
            ))}
          </section>
        ) : null}

        {!assignment ? (
          <section className={workspaceStyles.emptyState}>
            <h2>No assigned garbage route for today</h2>
            <p>
              When a dispatcher assigns a garbage collection task to your driver or
              inspector account, it will appear here automatically.
            </p>
          </section>
        ) : (
          <>
            <section className={fieldStyles.summaryGrid}>
              <section className={workspaceStyles.panel}>
                <div className={workspaceStyles.sectionHeader}>
                  <div>
                    <span className={workspaceStyles.eyebrow}>Route Summary</span>
                    <h2>{assignment.routeName}</h2>
                  </div>
                  <span className={fieldStyles.statePill}>{assignment.stateLabel}</span>
                </div>

                <div className={fieldStyles.summaryFacts}>
                  <div>
                    <span>Vehicle</span>
                    <strong>{assignment.vehicleName}</strong>
                  </div>
                  <div>
                    <span>District</span>
                    <strong>{assignment.districtName}</strong>
                  </div>
                  <div>
                    <span>Driver</span>
                    <strong>{assignment.driverName}</strong>
                  </div>
                  <div>
                    <span>Inspector</span>
                    <strong>{assignment.inspectorName}</strong>
                  </div>
                  <div>
                    <span>Shift</span>
                    <strong>{assignment.shiftTypeLabel}</strong>
                  </div>
                  <div>
                    <span>Collected weight</span>
                    <strong>{assignment.totalNetWeightLabel}</strong>
                  </div>
                </div>

                <div className={workspaceStyles.progressTrack}>
                  <span style={{ width: `${assignment.progressPercent}%` }} />
                </div>

                <div className={fieldStyles.summaryStats}>
                  <div>
                    <span>Stops</span>
                    <strong>{assignment.stopCount}</strong>
                  </div>
                  <div>
                    <span>Completed</span>
                    <strong>{assignment.completedStopCount}</strong>
                  </div>
                  <div>
                    <span>Skipped</span>
                    <strong>{assignment.skippedStopCount}</strong>
                  </div>
                  <div>
                    <span>Open</span>
                    <strong>{assignment.unresolvedStopCount}</strong>
                  </div>
                  <div>
                    <span>Proof photos</span>
                    <strong>{assignment.proofCount}</strong>
                  </div>
                  <div>
                    <span>Issues</span>
                    <strong>{assignment.issueCount}</strong>
                  </div>
                </div>
              </section>

              <aside className={`${workspaceStyles.formCard} ${fieldStyles.stickySummary}`}>
                <div className={workspaceStyles.sectionHeader}>
                  <div>
                    <span className={workspaceStyles.eyebrow}>Shift Actions</span>
                    <h2>Ready to run</h2>
                  </div>
                </div>

                <div className={fieldStyles.timeline}>
                  <div>
                    <span>Dispatched</span>
                    <strong>{assignment.dispatchedAt}</strong>
                  </div>
                  <div>
                    <span>Started</span>
                    <strong>{assignment.startedAt}</strong>
                  </div>
                  <div>
                    <span>Submitted</span>
                    <strong>{assignment.endedAt}</strong>
                  </div>
                </div>

                {assignment.canStart ? (
                  <form action={startFieldShiftAction} className={workspaceStyles.form}>
                    <input type="hidden" name="task_id" value={assignment.id} />
                    <button type="submit" className={workspaceStyles.primaryButton}>
                      Start shift
                    </button>
                  </form>
                ) : null}

                <form action={submitFieldShiftAction} className={workspaceStyles.form}>
                  <input type="hidden" name="task_id" value={assignment.id} />
                  <div className={workspaceStyles.field}>
                    <label htmlFor="summary">End-of-shift summary</label>
                    <textarea
                      id="summary"
                      name="summary"
                      defaultValue={assignment.endShiftSummary}
                      placeholder="Write the shift summary before submitting for verification."
                      required
                    />
                  </div>
                  <button
                    type="submit"
                    className={workspaceStyles.secondaryButton}
                    disabled={!assignment.canSubmit}
                  >
                    Submit for verification
                  </button>
                </form>

                <div className={fieldStyles.alertList}>
                  <div className={fieldStyles.alertCard}>
                    <span>Unresolved stops</span>
                    <strong>{assignment.unresolvedStopCount}</strong>
                  </div>
                  <div className={fieldStyles.alertCard}>
                    <span>Completed stops missing proof</span>
                    <strong>{assignment.missingProofStopCount}</strong>
                  </div>
                </div>

                {assignment.weightTotals.length ? (
                  <div className={fieldStyles.weightList}>
                    {assignment.weightTotals.map((weight) => (
                      <article key={weight.id} className={fieldStyles.weightCard}>
                        <strong>{weight.netWeightTotal.toFixed(2)} t</strong>
                        <span>{weight.sourceLabel}</span>
                        {weight.externalReference ? <small>{weight.externalReference}</small> : null}
                      </article>
                    ))}
                  </div>
                ) : (
                  <p className={fieldStyles.helperText}>
                    Nightly WRS totals will appear here after the weighbridge sync runs.
                  </p>
                )}
              </aside>
            </section>

            <section className={fieldStyles.stopList}>
              {assignment.stops.map((stop) => (
                <article
                  key={stop.id}
                  id={`stop-${stop.id}`}
                  className={`${fieldStyles.stopCard} ${statusTone(stop)}`}
                >
                  <div className={fieldStyles.stopTop}>
                    <div>
                      <span className={fieldStyles.stopSequence}>Stop {stop.sequence}</span>
                      <h3>{stop.collectionPointName}</h3>
                      <p>
                        {stop.districtName}
                        {stop.subdistrictName ? ` / ${stop.subdistrictName}` : ""}
                      </p>
                    </div>
                    <span className={fieldStyles.stopStatus}>{stop.statusLabel}</span>
                  </div>

                  <div className={fieldStyles.stopMeta}>
                    <div>
                      <span>Planned arrival</span>
                      <strong>{stop.plannedArrivalLabel}</strong>
                    </div>
                    <div>
                      <span>Service time</span>
                      <strong>{stop.plannedServiceLabel}</strong>
                    </div>
                    <div>
                      <span>Arrived</span>
                      <strong>{stop.arrivalLabel}</strong>
                    </div>
                    <div>
                      <span>Departed</span>
                      <strong>{stop.departureLabel}</strong>
                    </div>
                  </div>

                  <div className={workspaceStyles.chipRow}>
                    <span className={workspaceStyles.chip}>{stop.proofCount} proof photos</span>
                    <span className={workspaceStyles.chip}>{stop.issueCount} issues</span>
                    {stop.missingProofTypes.length ? (
                      <span className={workspaceStyles.chip}>
                        Missing: {stop.missingProofTypes.join(", ")}
                      </span>
                    ) : null}
                    {stop.skipReason ? (
                      <span className={workspaceStyles.chip}>
                        Skip reason: {stop.skipReason}
                      </span>
                    ) : null}
                  </div>

                  <div className={fieldStyles.actionRow}>
                    {stop.status === "draft" ? (
                      <form action={markFieldStopArrivedAction}>
                        <input type="hidden" name="task_id" value={assignment.id} />
                        <input type="hidden" name="stop_line_id" value={stop.id} />
                        <button type="submit" className={workspaceStyles.secondaryButton}>
                          Mark arrived
                        </button>
                      </form>
                    ) : null}

                    {!["done", "skipped"].includes(stop.status) ? (
                      <form action={markFieldStopDoneAction}>
                        <input type="hidden" name="task_id" value={assignment.id} />
                        <input type="hidden" name="stop_line_id" value={stop.id} />
                        <button type="submit" className={workspaceStyles.primaryButton}>
                          Mark done
                        </button>
                      </form>
                    ) : null}
                  </div>

                  <div className={fieldStyles.detailsGrid}>
                    <details className={fieldStyles.detailCard} open={stop.status !== "done"}>
                      <summary>Proof photos</summary>
                      <form action={uploadFieldStopProofAction} className={workspaceStyles.form}>
                        <input type="hidden" name="task_id" value={assignment.id} />
                        <input type="hidden" name="stop_line_id" value={stop.id} />
                        <div className={workspaceStyles.field}>
                          <label htmlFor={`proof_type_${stop.id}`}>Photo type</label>
                          <select
                            id={`proof_type_${stop.id}`}
                            name="proof_type"
                            defaultValue="before"
                          >
                            <option value="before">Before</option>
                            <option value="after">After</option>
                          </select>
                        </div>
                        <div className={workspaceStyles.field}>
                          <label htmlFor={`image_${stop.id}`}>Photo</label>
                          <input
                            id={`image_${stop.id}`}
                            type="file"
                            name="image"
                            accept="image/*"
                            capture="environment"
                            required
                          />
                        </div>
                        <div className={workspaceStyles.field}>
                          <label htmlFor={`proof_description_${stop.id}`}>Note</label>
                          <input
                            id={`proof_description_${stop.id}`}
                            type="text"
                            name="description"
                            placeholder="Optional photo note"
                          />
                        </div>
                        <BestEffortGpsFields />
                        <button type="submit" className={workspaceStyles.secondaryButton}>
                          Upload proof photo
                        </button>
                      </form>

                      {stop.proofs.length ? (
                        <div className={fieldStyles.historyList}>
                          {stop.proofs.map((proof) => (
                            <article key={proof.id} className={fieldStyles.historyCard}>
                              <strong>{proof.proofTypeLabel}</strong>
                              <span>{proof.capturedAt}</span>
                              <small>{proof.uploader}</small>
                              {proof.description ? <p>{proof.description}</p> : null}
                              {proof.gpsLabel ? <small>{proof.gpsLabel}</small> : null}
                            </article>
                          ))}
                        </div>
                      ) : (
                        <p className={fieldStyles.helperText}>
                          Upload both before and after photos before marking the stop as done.
                        </p>
                      )}
                    </details>

                    <details className={fieldStyles.detailCard}>
                      <summary>Skip stop</summary>
                      <form action={markFieldStopSkippedAction} className={workspaceStyles.form}>
                        <input type="hidden" name="task_id" value={assignment.id} />
                        <input type="hidden" name="stop_line_id" value={stop.id} />
                        <div className={workspaceStyles.field}>
                          <label htmlFor={`skip_reason_${stop.id}`}>Reason</label>
                          <textarea
                            id={`skip_reason_${stop.id}`}
                            name="skip_reason"
                            defaultValue={stop.skipReason}
                            placeholder="Explain why this stop was skipped."
                            required
                          />
                        </div>
                        <button type="submit" className={workspaceStyles.dangerButton}>
                          Mark skipped
                        </button>
                      </form>
                    </details>

                    <details className={fieldStyles.detailCard}>
                      <summary>Notes and issue log</summary>
                      <form action={saveFieldStopNoteAction} className={workspaceStyles.form}>
                        <input type="hidden" name="task_id" value={assignment.id} />
                        <input type="hidden" name="stop_line_id" value={stop.id} />
                        <div className={workspaceStyles.field}>
                          <label htmlFor={`note_${stop.id}`}>Stop note</label>
                          <textarea
                            id={`note_${stop.id}`}
                            name="note"
                            defaultValue={stop.note}
                            placeholder="Save a note for this collection point."
                          />
                        </div>
                        <button type="submit" className={workspaceStyles.secondaryButton}>
                          Save note
                        </button>
                      </form>

                      <form action={createFieldStopIssueAction} className={workspaceStyles.form}>
                        <input type="hidden" name="task_id" value={assignment.id} />
                        <input type="hidden" name="stop_line_id" value={stop.id} />
                        <div className={workspaceStyles.field}>
                          <label htmlFor={`issue_title_${stop.id}`}>Issue title</label>
                          <input
                            id={`issue_title_${stop.id}`}
                            type="text"
                            name="title"
                            placeholder="Short issue title"
                            required
                          />
                        </div>
                        <div className={fieldStyles.inlineFields}>
                          <div className={workspaceStyles.field}>
                            <label htmlFor={`issue_type_${stop.id}`}>Issue type</label>
                            <select
                              id={`issue_type_${stop.id}`}
                              name="issue_type"
                              defaultValue="other"
                            >
                              {ISSUE_TYPE_OPTIONS.map((option) => (
                                <option key={option.value} value={option.value}>
                                  {option.label}
                                </option>
                              ))}
                            </select>
                          </div>
                          <div className={workspaceStyles.field}>
                            <label htmlFor={`severity_${stop.id}`}>Severity</label>
                            <select
                              id={`severity_${stop.id}`}
                              name="severity"
                              defaultValue="medium"
                            >
                              {ISSUE_SEVERITY_OPTIONS.map((option) => (
                                <option key={option.value} value={option.value}>
                                  {option.label}
                                </option>
                              ))}
                            </select>
                          </div>
                        </div>
                        <div className={workspaceStyles.field}>
                          <label htmlFor={`issue_description_${stop.id}`}>Description</label>
                          <textarea
                            id={`issue_description_${stop.id}`}
                            name="description"
                            placeholder="Describe the issue at this stop."
                            required
                          />
                        </div>
                        <button type="submit" className={workspaceStyles.secondaryButton}>
                          Create issue
                        </button>
                      </form>

                      {stop.issues.length ? (
                        <div className={fieldStyles.historyList}>
                          {stop.issues.map((issue) => (
                            <article key={issue.id} className={fieldStyles.historyCard}>
                              <strong>{issue.title}</strong>
                              <span>
                                {issue.typeLabel} / {issue.severityLabel}
                              </span>
                              <small>
                                {issue.stateLabel} / {issue.reportedAt}
                              </small>
                              <p>{issue.description}</p>
                            </article>
                          ))}
                        </div>
                      ) : (
                        <p className={fieldStyles.helperText}>
                          Use the issue log when a stop is blocked, unsafe, or needs follow-up.
                        </p>
                      )}
                    </details>
                  </div>
                </article>
              ))}
            </section>
          </>
        )}
      </div>
    </main>
  );
}
