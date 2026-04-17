import Link from "next/link";

import {
  createTaskReportAction,
  logoutAction,
  markTaskDoneAction,
  returnTaskForChangesAction,
  submitTaskForReviewAction,
} from "@/app/actions";
import styles from "@/app/workspace.module.css";
import { getRoleLabel, requireSession } from "@/lib/auth";
import { loadTaskDetail } from "@/lib/workspace";

type PageProps = {
  params: Promise<{
    taskId: string;
  }>;
  searchParams?: Promise<{
    error?: string | string[];
    notice?: string | string[];
  }>;
};

function getMessage(value?: string | string[]) {
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
}

function StagePill({ label, bucket }: { label: string; bucket: string }) {
  const tone =
    bucket === "done"
      ? styles.stageDone
      : bucket === "review"
        ? styles.stageReview
        : bucket === "progress"
          ? styles.stageProgress
          : styles.stageTodo;

  return <span className={`${styles.stagePill} ${tone}`}>{label}</span>;
}

export default async function TaskDetailPage({ params, searchParams }: PageProps) {
  const session = await requireSession();
  const resolvedParams = await params;
  const taskId = Number(resolvedParams.taskId);
  const query = (await searchParams) ?? {};
  const errorMessage = getMessage(query.error);
  const noticeMessage = getMessage(query.notice);

  let task;
  try {
    task = await loadTaskDetail(taskId, {
      login: session.login,
      password: session.password,
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Даалгавар уншихад алдаа гарлаа.";
    return (
      <main className={styles.shell}>
        <div className={styles.container}>
          <header className={styles.navBar}>
            <div className={styles.navLinks}>
              <Link href="/" className={styles.backLink}>
                Самбар руу буцах
              </Link>
            </div>
          </header>
          <section className={styles.emptyState}>
            <h2>Task нээгдсэнгүй</h2>
            <p>{message}</p>
          </section>
        </div>
      </main>
    );
  }

  const canWriteReport =
    !task.reportsLocked &&
    (session.role === "team_leader" || session.role === "system_admin");

  return (
    <main className={styles.shell}>
      <div className={styles.container} id="task-top">
        <header className={styles.navBar}>
          <div className={styles.navLinks}>
            <Link
              href={task.projectId ? `/projects/${task.projectId}` : "/"}
              className={styles.backLink}
            >
              Төсөл рүү буцах
            </Link>
            <span>{task.projectName}</span>
            <span>{getRoleLabel(session.role)}</span>
          </div>

          <div className={styles.navActions}>
            <form action={logoutAction}>
              <button type="submit" className={styles.secondaryButton}>
                Гарах
              </button>
            </form>
          </div>
        </header>

        <section className={styles.heroCard}>
          <span className={styles.eyebrow}>Task Workspace</span>
          <h1>{task.name}</h1>
          <p>
            Энэ дэлгэц дээр тайлан нэмэх, шалгалтад илгээх, дуусгах, засвар нэхэж
            буцаах зэрэг workflow-ийг web app дотроос удирдана.
          </p>

          <div className={styles.statsGrid}>
            <article className={styles.statCard}>
              <span>Төлөв</span>
              <strong>{task.stageLabel}</strong>
            </article>
            <article className={styles.statCard}>
              <span>Гүйцэтгэл</span>
              <strong>{task.progress}%</strong>
            </article>
            <article className={styles.statCard}>
              <span>Deadline</span>
              <strong>{task.deadline}</strong>
            </article>
            <article className={styles.statCard}>
              <span>Priority</span>
              <strong>{task.priorityLabel}</strong>
            </article>
          </div>
        </section>

        <nav className={styles.jumpRail} aria-label="Task quick navigation">
          <a href="#task-detail" className={styles.jumpLink}>
            Дэлгэрэнгүй
          </a>
          <a href="#workflow" className={styles.jumpLink}>
            Үйлдэл
          </a>
          <a href="#reports" className={styles.jumpLink}>
            Тайлан
          </a>
          {canWriteReport ? (
            <a href="#report-form" className={styles.jumpLink}>
              Шинэ тайлан
            </a>
          ) : null}
        </nav>

        {errorMessage ? (
          <div className={`${styles.message} ${styles.errorMessage}`}>{errorMessage}</div>
        ) : null}
        {noticeMessage ? (
          <div className={`${styles.message} ${styles.noticeMessage}`}>{noticeMessage}</div>
        ) : null}

        <section className={styles.panelGrid}>
          <section className={styles.panel} id="task-detail">
            <div className={styles.sectionHeader}>
              <div>
                <span className={styles.eyebrow}>Task Detail</span>
                <h2>Ажлын мэдээлэл</h2>
              </div>
              <StagePill label={task.stageLabel} bucket={task.stageBucket} />
            </div>

            <div className={styles.metaList}>
              <div>
                <span>Төсөл</span>
                <strong>{task.projectName}</strong>
              </div>
              <div>
                <span>Багийн ахлагч</span>
                <strong>{task.teamLeaderName}</strong>
              </div>
              <div>
                <span>Хэмжээ</span>
                <strong>
                  {task.completedQuantity}/{task.plannedQuantity} {task.measurementUnit}
                </strong>
              </div>
              <div>
                <span>Үлдэгдэл</span>
                <strong>
                  {task.remainingQuantity} {task.measurementUnit}
                </strong>
              </div>
            </div>

            <div className={styles.progressTrack}>
              <span style={{ width: `${task.progress}%` }} />
            </div>

            <div className={styles.sectionHeader} style={{ marginTop: 20 }}>
              <div>
                <span className={styles.eyebrow}>Assignees</span>
                <h2>Хариуцсан хүмүүс</h2>
              </div>
            </div>
            <div className={styles.chipRow}>
              {task.assignees.map((name) => (
                <span key={name} className={styles.chip}>
                  {name}
                </span>
              ))}
            </div>

            {task.description ? (
              <>
                <div className={styles.sectionHeader} style={{ marginTop: 20 }}>
                  <div>
                    <span className={styles.eyebrow}>Description</span>
                    <h2>Тайлбар</h2>
                  </div>
                </div>
                <p>{task.description}</p>
              </>
            ) : null}
          </section>

          <aside
            className={`${styles.formCard} ${styles.stickyAside}`}
            id="workflow"
          >
            <div className={styles.sectionHeader}>
              <div>
                <span className={styles.eyebrow}>Workflow</span>
                <h2>Үйлдлүүд</h2>
              </div>
            </div>

            <div className={styles.form}>
              {task.canSubmitForReview ? (
                <form action={submitTaskForReviewAction} className={styles.form}>
                  <input type="hidden" name="task_id" value={task.id} />
                  <button type="submit" className={styles.secondaryButton}>
                    Шалгалтад илгээх
                  </button>
                </form>
              ) : null}

              {task.canMarkDone ? (
                <form action={markTaskDoneAction} className={styles.form}>
                  <input type="hidden" name="task_id" value={task.id} />
                  <button type="submit" className={styles.primaryButton}>
                    Дууссан төлөвт оруулах
                  </button>
                </form>
              ) : null}

              {task.canReturnForChanges ? (
                <form action={returnTaskForChangesAction} className={styles.form}>
                  <input type="hidden" name="task_id" value={task.id} />
                  <div className={styles.field}>
                    <label htmlFor="return_reason">Буцаах шалтгаан</label>
                    <textarea
                      id="return_reason"
                      name="return_reason"
                      placeholder="Ямар засвар шаардлагатайг бичнэ үү"
                      required
                    />
                  </div>
                  <button type="submit" className={styles.dangerButton}>
                    Засвар нэхэж буцаах
                  </button>
                </form>
              ) : null}

              {!task.canSubmitForReview &&
              !task.canMarkDone &&
              !task.canReturnForChanges ? (
                <p>Энэ task дээр одоогоор таны role-д тохирсон workflow action алга.</p>
              ) : null}
            </div>
          </aside>
        </section>

        <section className={styles.panelGrid} style={{ marginTop: 22 }}>
          <section className={styles.panel} id="reports">
            <div className={styles.sectionHeader}>
              <div>
                <span className={styles.eyebrow}>Field Reports</span>
                <h2>Тайлангийн урсгал</h2>
              </div>
              <p>
                Зураг, аудио upload-ийг дараагийн шатанд нэмнэ. Одоогоор текст ба
                хэмжээнй тайлан орно.
              </p>
            </div>

            {task.reports.length ? (
              <div className={styles.reportGrid}>
                {task.reports.map((report) => (
                  <article key={report.id} className={styles.reportCard}>
                    <div className={styles.reportTop}>
                      <div>
                        <h3>{report.reporter}</h3>
                        <p>{report.submittedAt}</p>
                      </div>
                      <strong>
                        {report.quantity} {task.measurementUnit}
                      </strong>
                    </div>
                    <p>{report.summary}</p>
                    <div className={styles.chipRow}>
                      <span className={styles.chip}>{report.imageCount} зураг</span>
                      <span className={styles.chip}>{report.audioCount} аудио</span>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className={styles.emptyState}>
                <h2>Тайлан алга</h2>
                <p>Энэ task дээр одоогоор тайлан бүртгэгдээгүй байна.</p>
              </div>
            )}
          </section>

          <aside
            className={`${styles.formCard} ${styles.stickyAside}`}
            id="report-form"
          >
            <div className={styles.sectionHeader}>
              <div>
                <span className={styles.eyebrow}>Add Report</span>
                <h2>Шинэ тайлан</h2>
              </div>
            </div>

            {!canWriteReport ? (
              <p>
                Тайлан нэмэх form нь одоогоор багийн ахлагч дээр, мөн түгжигдээгүй
                task дээр нээлттэй.
              </p>
            ) : (
              <form action={createTaskReportAction} className={styles.form}>
                <input type="hidden" name="task_id" value={task.id} />

                <div className={styles.field}>
                  <label htmlFor="reported_quantity">Энэ тайлангаар хийсэн хэмжээ</label>
                  <input
                    id="reported_quantity"
                    name="reported_quantity"
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="12"
                    required
                  />
                </div>

                <div className={styles.field}>
                  <label htmlFor="report_text">Тайлангийн текст</label>
                  <textarea
                    id="report_text"
                    name="report_text"
                    placeholder="Өнөөдөр хэдийг хийсэн, ямар нөхцөлтэй байсан, юу үлдсэн гэх мэт"
                    required
                  />
                </div>

                <div className={styles.buttonRow}>
                  <button type="submit" className={styles.primaryButton}>
                    Тайлан хадгалах
                  </button>
                </div>
              </form>
            )}
          </aside>
        </section>

        <nav className={styles.mobileDock} aria-label="Task mobile quick navigation">
          <a href="#workflow" className={styles.jumpLink}>
            Үйлдэл
          </a>
          <a href="#reports" className={styles.jumpLink}>
            Тайлан
          </a>
          {canWriteReport ? (
            <a href="#report-form" className={styles.jumpLink}>
              Нэмэх
            </a>
          ) : (
            <a href="#task-top" className={styles.jumpLink}>
              Дээш
            </a>
          )}
        </nav>
      </div>
    </main>
  );
}
