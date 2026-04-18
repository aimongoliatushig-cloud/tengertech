import Image from "next/image";
import Link from "next/link";

import { AppMenu } from "@/app/_components/app-menu";
import {
  createTaskReportAction,
  logoutAction,
  markTaskDoneAction,
  returnTaskForChangesAction,
  submitTaskForReviewAction,
} from "@/app/actions";
import dashboardStyles from "@/app/page.module.css";
import styles from "@/app/workspace.module.css";
import { getRoleLabel, hasCapability, requireSession } from "@/lib/auth";
import { loadTaskDetail } from "@/lib/workspace";

type PageProps = {
  params: Promise<{
    taskId: string;
  }>;
  searchParams?: Promise<{
    error?: string | string[];
    notice?: string | string[];
    returnTo?: string | string[];
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
      ? dashboardStyles.stageDone
      : bucket === "review"
        ? dashboardStyles.stageReview
        : bucket === "progress"
          ? dashboardStyles.stageProgress
          : dashboardStyles.stageTodo;

  return <span className={`${dashboardStyles.stagePill} ${tone}`}>{label}</span>;
}

export default async function TaskDetailPage({ params, searchParams }: PageProps) {
  const session = await requireSession();
  const resolvedParams = await params;
  const taskId = Number(resolvedParams.taskId);
  const query = (await searchParams) ?? {};
  const errorMessage = getMessage(query.error);
  const noticeMessage = getMessage(query.notice);
  const returnTo = getMessage(query.returnTo);
  const safeReturnTo = returnTo.startsWith("/") ? returnTo : "";
  const useExecutiveLayout = safeReturnTo.startsWith("/tasks");
  const backHref = safeReturnTo || "/projects";
  const backLabel = useExecutiveLayout ? "Өнөөдрийн ажил руу буцах" : "Төслүүд рүү буцах";

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
              <Link href={backHref} className={styles.backLink}>
                {backLabel}
              </Link>
            </div>
          </header>
          <section className={styles.emptyState}>
            <h2>Ажил нээгдсэнгүй</h2>
            <p>{message}</p>
          </section>
        </div>
      </main>
    );
  }

  const canWriteReport =
    !task.reportsLocked && hasCapability(session, "write_workspace_reports");
  const canCreateProject = hasCapability(session, "create_projects");
  const canViewQualityCenter = hasCapability(session, "view_quality_center");
  const canUseFieldConsole = hasCapability(session, "use_field_console");
  const taskBackHref = safeReturnTo || (task.projectId ? `/projects/${task.projectId}` : "/projects");
  const taskBackLabel = useExecutiveLayout ? "Өнөөдрийн ажил руу буцах" : "Төсөл рүү буцах";

  return (
    <main className={styles.shell}>
      <div className={styles.container} id="task-top">
        <header className={styles.navBar}>
          <div className={styles.navLinks}>
            <Link href={taskBackHref} className={styles.backLink}>
              {taskBackLabel}
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

        <AppMenu
          active={useExecutiveLayout ? "tasks" : "projects"}
          variant={useExecutiveLayout ? "executive" : "default"}
          canCreateProject={canCreateProject}
          canViewQualityCenter={canViewQualityCenter}
          canUseFieldConsole={canUseFieldConsole}
        />

        <section className={styles.heroCard}>
          <span className={styles.eyebrow}>Ажлын орчин</span>
          <h1>{task.name}</h1>
          <p>
            Энэ дэлгэц дээр тайлан нэмэх, шалгалтад илгээх, дуусгах, засвар нэхэж
            буцаах зэрэг шатны урсгалыг веб апп дотроос удирдана.
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
              <span>Хугацаа</span>
              <strong>{task.deadline}</strong>
            </article>
            <article className={styles.statCard}>
              <span>Эрэмбэ</span>
              <strong>{task.priorityLabel}</strong>
            </article>
          </div>
        </section>

        <nav className={styles.jumpRail} aria-label="Ажлын хуудасны шуурхай цэс">
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
                <span className={styles.eyebrow}>Ажлын дэлгэрэнгүй</span>
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
                  <span className={styles.eyebrow}>Хуваарилагдсан хүмүүс</span>
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
                    <span className={styles.eyebrow}>Тайлбар</span>
                    <h2>Тайлбар</h2>
                  </div>
                </div>
                <p>{task.description}</p>
              </>
            ) : null}
          </section>

          <aside className={`${styles.formCard} ${styles.stickyAside}`} id="workflow">
            <div className={styles.sectionHeader}>
              <div>
                <span className={styles.eyebrow}>Шатны үйлдэл</span>
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
                <p>Энэ ажил дээр одоогоор танай эрхэд тохирсон үйлдэл алга.</p>
              ) : null}
            </div>
          </aside>
        </section>

        <section className={styles.panelGrid} style={{ marginTop: 22 }}>
          <section className={styles.panel} id="reports">
            <div className={styles.sectionHeader}>
              <div>
                <span className={styles.eyebrow}>Талбарын тайлан</span>
                <h2>Тайлангийн урсгал</h2>
              </div>
              <p>
                Зураг, аудио оруулах боломжийг дараагийн шатанд нэмнэ. Одоогоор текст ба
                хэмжээн дээр суурилсан тайлан оруулж байна.
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
                    <p className={styles.reportSummaryText}>{report.summary}</p>
                    <div className={styles.chipRow}>
                      <span className={styles.chip}>{report.imageCount} зураг</span>
                      <span className={styles.chip}>{report.audioCount} аудио</span>
                    </div>
                    {report.images.length ? (
                      <div className={dashboardStyles.reportImageGrid}>
                        {report.images.map((image) => (
                          <a
                            key={image.id}
                            href={image.url}
                            target="_blank"
                            rel="noreferrer"
                            className={dashboardStyles.reportImageLink}
                          >
                            <Image
                              src={image.url}
                              alt={`${task.name} - ${image.name}`}
                              className={dashboardStyles.reportImage}
                              width={320}
                              height={240}
                              unoptimized
                            />
                          </a>
                        ))}
                      </div>
                    ) : null}
                    {report.audios.length ? (
                      <div className={dashboardStyles.reportAudioList}>
                        {report.audios.map((audio) => (
                          <div key={audio.id} className={dashboardStyles.reportAudioCard}>
                            <strong>{audio.name}</strong>
                            <audio
                              controls
                              preload="none"
                              src={audio.url}
                              className={dashboardStyles.reportAudioPlayer}
                            />
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </article>
                ))}
              </div>
            ) : (
              <div className={styles.emptyState}>
                <h2>Тайлан алга</h2>
                <p>Энэ ажил дээр одоогоор тайлан бүртгэгдээгүй байна.</p>
              </div>
            )}
          </section>

          <aside className={`${styles.formCard} ${styles.stickyAside}`} id="report-form">
            <div className={styles.sectionHeader}>
              <div>
                <span className={styles.eyebrow}>Тайлан нэмэх</span>
                <h2>Шинэ тайлан</h2>
              </div>
            </div>

            {!canWriteReport ? (
              <p>
                Тайлан нэмэх маягт нь одоогоор багийн ахлагч дээр, мөн түгжигдээгүй
                ажил дээр нээлттэй байна.
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

        <nav className={styles.mobileDock} aria-label="Ажлын гар утасны шуурхай цэс">
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
