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
import shellStyles from "@/app/workspace.module.css";
import { getRoleLabel, hasCapability, requireSession } from "@/lib/auth";
import { loadTaskDetail } from "@/lib/workspace";

import styles from "./task-detail.module.css";

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
  const backLabel = useExecutiveLayout ? "Өнөөдрийн ажил руу буцах" : "Төсөл рүү буцах";

  let task;
  try {
    task = await loadTaskDetail(taskId, {
      login: session.login,
      password: session.password,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Ажлын мэдээлэл уншихад алдаа гарлаа.";
    return (
      <main className={shellStyles.shell}>
        <div className={shellStyles.container}>
          <header className={shellStyles.navBar}>
            <div className={shellStyles.navLinks}>
              <Link href={backHref} className={shellStyles.backLink}>
                {backLabel}
              </Link>
            </div>
          </header>
          <section className={styles.emptyState}>
            <h2>Ажлыг нээж чадсангүй</h2>
            <p>{message}</p>
          </section>
        </div>
      </main>
    );
  }

  const canWriteReport = !task.reportsLocked && hasCapability(session, "write_workspace_reports");
  const canCreateProject = hasCapability(session, "create_projects");
  const canViewQualityCenter = hasCapability(session, "view_quality_center");
  const canUseFieldConsole = hasCapability(session, "use_field_console");
  const primaryActionLabel = task.canMarkDone
    ? "Ажлыг дуусгах"
    : task.canSubmitForReview
      ? "Шалгалтад илгээх"
      : canWriteReport
        ? "Тайлан оруулах"
        : "Мэдээлэл харах";

  return (
    <main className={shellStyles.shell}>
      <div className={shellStyles.container} id="task-top">
        <header className={shellStyles.navBar}>
          <div className={shellStyles.navLinks}>
            <Link href={backHref} className={shellStyles.backLink}>
              {backLabel}
            </Link>
            <span>{task.projectName}</span>
            <span>{getRoleLabel(session.role)}</span>
          </div>

          <div className={shellStyles.navActions}>
            <form action={logoutAction}>
              <button type="submit" className={shellStyles.secondaryButton}>
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
          userName={session.name}
          roleLabel={getRoleLabel(session.role)}
        />

        {errorMessage ? (
          <div className={`${shellStyles.message} ${shellStyles.errorMessage}`}>{errorMessage}</div>
        ) : null}
        {noticeMessage ? (
          <div className={`${shellStyles.message} ${shellStyles.noticeMessage}`}>{noticeMessage}</div>
        ) : null}

        <section className={styles.summaryCard}>
          <div className={styles.summaryTop}>
            <div className={styles.titleBlock}>
              <span className={styles.kicker}>Ажлын дэлгэрэнгүй</span>
              <h1>{task.name}</h1>
              <p className={styles.lead}>
                {task.projectName} төслийн энэ ажлын явц, тайлан, дараагийн гол үйлдлийг
                нэг дэлгэцээс ойлгомжтой харуулж байна.
              </p>
            </div>
            <StagePill label={task.stageLabel} bucket={task.stageBucket} />
          </div>

          <div className={styles.anchorRow}>
            <a href="#task-info" className={styles.anchorLink}>
              Товч мэдээлэл
            </a>
            <a href="#task-actions" className={styles.anchorLink}>
              Үндсэн үйлдэл
            </a>
            <a href="#task-reports" className={styles.anchorLink}>
              Тайлан
            </a>
            {canWriteReport ? (
              <a href="#report-form" className={styles.anchorLink}>
                {primaryActionLabel}
              </a>
            ) : null}
          </div>

          <div className={styles.heroStats}>
            <article className={styles.heroStatCard}>
              <span>Төлөв</span>
              <strong>{task.stageLabel}</strong>
            </article>
            <article className={styles.heroStatCard}>
              <span>Явц</span>
              <strong>{task.progress}%</strong>
            </article>
            <article className={styles.heroStatCard}>
              <span>Хугацаа</span>
              <strong>{task.deadline}</strong>
            </article>
            <article className={styles.heroStatCard}>
              <span>Эрэмбэ</span>
              <strong>{task.priorityLabel}</strong>
            </article>
          </div>
        </section>

        <section className={styles.pageGrid}>
          <div className={styles.mainColumn}>
            <section className={styles.sectionCard} id="task-info">
              <div className={styles.sectionHead}>
                <div>
                  <span className={styles.kicker}>Товч мэдээлэл</span>
                  <h2>Ажлын гол мэдээлэл</h2>
                </div>
                <p>Уншихад хялбар байдлаар зөвхөн хамгийн хэрэгтэй мэдээллийг гаргав.</p>
              </div>

              <div className={styles.infoGrid}>
                <article className={styles.infoCard}>
                  <span>Төсөл</span>
                  <strong>{task.projectName}</strong>
                </article>
                <article className={styles.infoCard}>
                  <span>Багийн ахлагч</span>
                  <strong>{task.teamLeaderName}</strong>
                </article>
                <article className={styles.infoCard}>
                  <span>Төлөвлөсөн хэмжээ</span>
                  <strong>
                    {task.plannedQuantity} {task.measurementUnit}
                  </strong>
                </article>
                <article className={styles.infoCard}>
                  <span>Гүйцэтгэсэн хэмжээ</span>
                  <strong>
                    {task.completedQuantity} {task.measurementUnit}
                  </strong>
                </article>
                <article className={styles.infoCard}>
                  <span>Үлдэгдэл</span>
                  <strong>
                    {task.remainingQuantity} {task.measurementUnit}
                  </strong>
                </article>
                <article className={styles.infoCard}>
                  <span>Үндсэн үйлдэл</span>
                  <strong>{primaryActionLabel}</strong>
                </article>
              </div>
            </section>

            <section className={styles.sectionCard}>
              <div className={styles.sectionHead}>
                <div>
                  <span className={styles.kicker}>Хариуцсан хүмүүс</span>
                  <h2>Багийн бүрэлдэхүүн</h2>
                </div>
              </div>

              <div className={styles.chipRow}>
                {task.assignees.length ? (
                  task.assignees.map((name) => (
                    <span key={name} className={styles.chip}>
                      {name}
                    </span>
                  ))
                ) : (
                  <span className={styles.chip}>Хүн оноогдоогүй</span>
                )}
              </div>
            </section>

            {task.description ? (
              <section className={styles.sectionCard}>
                <div className={styles.sectionHead}>
                  <div>
                    <span className={styles.kicker}>Тайлбар</span>
                    <h2>Ажлын тайлбар</h2>
                  </div>
                </div>

                <div className={styles.descriptionCard}>{task.description}</div>
              </section>
            ) : null}

            <section className={styles.sectionCard} id="task-reports">
              <div className={styles.sectionHead}>
                <div>
                  <span className={styles.kicker}>Тайлангийн урсгал</span>
                  <h2>Оруулсан тайлангууд</h2>
                </div>
                <p>Сүүлийн тайлангуудыг эхэнд нь харуулж, зураг болон аудиог шууд нээнэ.</p>
              </div>

              {task.reports.length ? (
                <div className={styles.reportList}>
                  {task.reports.map((report) => (
                    <article key={report.id} className={styles.reportCard}>
                      <div className={styles.reportCardTop}>
                        <div className={styles.metaGroup}>
                          <strong>{report.reporter}</strong>
                          <small>{report.submittedAt}</small>
                        </div>
                        <StagePill label={`${report.quantity} ${task.measurementUnit}`} bucket="progress" />
                      </div>

                      <p>{report.summary}</p>

                      <div className={styles.reportMediaMeta}>
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
                  <p>Одоогоор энэ ажил дээр тайлан бүртгэгдээгүй байна.</p>
                </div>
              )}
            </section>
          </div>

          <div className={styles.sideColumn}>
            <aside className={`${styles.actionCard} ${styles.stickyCard}`} id="task-actions">
              <span className={styles.kicker}>Үндсэн үйлдэл</span>
              <strong className={styles.actionTitle}>{primaryActionLabel}</strong>
              <p className={styles.actionLead}>
                Аль шатанд байгаа ажлыг дараагийн зөв алхам руу шилжүүлэхэд энэ хэсгийг ашиглана.
              </p>

              <div className={styles.actionStack}>
                {task.canMarkDone ? (
                  <form action={markTaskDoneAction}>
                    <input type="hidden" name="task_id" value={task.id} />
                    <button type="submit" className={styles.actionButton}>
                      Ажлыг дуусгах
                    </button>
                  </form>
                ) : null}

                {task.canSubmitForReview ? (
                  <form action={submitTaskForReviewAction}>
                    <input type="hidden" name="task_id" value={task.id} />
                    <button type="submit" className={task.canMarkDone ? styles.secondaryButton : styles.actionButton}>
                      Шалгалтад илгээх
                    </button>
                  </form>
                ) : null}

                {!task.canMarkDone && !task.canSubmitForReview && canWriteReport ? (
                  <a href="#report-form" className={styles.actionButton}>
                    Тайлан оруулах
                  </a>
                ) : null}
              </div>

              <div className={styles.helperPanel}>
                <small>Төлөв: {task.stageLabel}</small>
                <small>Явц: {task.progress}%</small>
                <small>
                  Хэмжээ: {task.completedQuantity}/{task.plannedQuantity} {task.measurementUnit}
                </small>
              </div>

              {task.canReturnForChanges ? (
                <form action={returnTaskForChangesAction} className={styles.returnBox}>
                  <input type="hidden" name="task_id" value={task.id} />
                  <label htmlFor="return_reason">
                    Засвар шаардах шалтгаан
                  </label>
                  <textarea
                    id="return_reason"
                    name="return_reason"
                    placeholder="Ямар зүйлийг засах ёстойг товч тодорхой бичнэ үү"
                    required
                  />
                  <button type="submit" className={styles.warningButton}>
                    Засвар нэхэж буцаах
                  </button>
                </form>
              ) : null}
            </aside>

            <aside className={styles.reportComposer} id="report-form">
              <div className={styles.reportComposerHeader}>
                <span className={styles.kicker}>Тайлан оруулах</span>
                <strong className={styles.actionTitle}>Хурдан тайлан</strong>
                <p className={styles.actionLead}>
                  Хамгийн хэрэгтэй хоёр мэдээлэл болох хэмжээ ба тайлбарыг түрүүлж авна.
                </p>
              </div>

              {!canWriteReport ? (
                <div className={styles.helperPanel}>
                  <small>Одоогоор тайлан оруулах эрх нээлттэй биш байна.</small>
                </div>
              ) : (
                <form action={createTaskReportAction} className={styles.composerFields}>
                  <input type="hidden" name="task_id" value={task.id} />

                  <div className={styles.composerHighlight}>
                    <strong>Товч тайлан</strong>
                    <p className={styles.composerHint}>
                      Хийсэн хэмжээгээ оруулаад 2-3 өгүүлбэрээр өнөөдрийн ажлаа товч бичнэ.
                    </p>
                  </div>

                  <label htmlFor="reported_quantity">
                    Хийсэн хэмжээ
                    <input
                      id="reported_quantity"
                      name="reported_quantity"
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="12"
                      required
                    />
                  </label>

                  <label htmlFor="report_text">
                    Тайлангийн тайлбар
                    <textarea
                      id="report_text"
                      name="report_text"
                      placeholder="Юу хийсэн, ямар саад гарсан, дараагийн алхам юу болохыг товч бичнэ үү"
                      required
                    />
                  </label>

                  <button type="submit" className={styles.actionButton}>
                    Тайлан хадгалах
                  </button>
                </form>
              )}
            </aside>
          </div>
        </section>

        <nav className={shellStyles.mobileDock} aria-label="Ажлын гар утасны хурдан цэс">
          <a href="#task-info" className={shellStyles.jumpLink}>
            Товч
          </a>
          <a href="#task-actions" className={shellStyles.jumpLink}>
            Үйлдэл
          </a>
          <a href="#task-reports" className={shellStyles.jumpLink}>
            Тайлан
          </a>
        </nav>
      </div>
    </main>
  );
}
