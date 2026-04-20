import Link from "next/link";
import { redirect } from "next/navigation";

import { AppMenu } from "@/app/_components/app-menu";
import { createTaskAction } from "@/app/actions";
import dashboardStyles from "@/app/page.module.css";
import styles from "@/app/workspace.module.css";
import {
  getRoleLabel,
  hasCapability,
  isMasterRole,
  isWorkerOnly,
  requireSession,
} from "@/lib/auth";
import { loadProjectDetail } from "@/lib/workspace";

type PageProps = {
  params: Promise<{
    projectId: string;
  }>;
  searchParams?: Promise<{
    status?: string | string[];
    error?: string | string[];
    notice?: string | string[];
  }>;
};

type TaskFilterKey = "all" | "todo" | "progress" | "review" | "done";

const TASK_FILTERS: Array<{ key: TaskFilterKey; label: string }> = [
  { key: "all", label: "Бүгд" },
  { key: "todo", label: "Хийх ажил" },
  { key: "progress", label: "Хийгдэж буй" },
  { key: "review", label: "Шалгаж буй" },
  { key: "done", label: "Дууссан" },
];

function getParam(value?: string | string[]) {
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
}

function normalizeFilter(value: string): TaskFilterKey {
  return TASK_FILTERS.some((item) => item.key === value) ? (value as TaskFilterKey) : "all";
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

export default async function ProjectDetailPage({ params, searchParams }: PageProps) {
  const session = await requireSession();
  if (isWorkerOnly(session)) {
    redirect("/");
  }
  const resolvedParams = await params;
  const projectId = Number(resolvedParams.projectId);
  const query = (await searchParams) ?? {};
  const activeFilter = normalizeFilter(getParam(query.status));
  const errorMessage = getParam(query.error);
  const noticeMessage = getParam(query.notice);
  const masterMode = isMasterRole(session.role);

  let project;
  try {
    project = await loadProjectDetail(projectId, {
      login: session.login,
      password: session.password,
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Ажлыг уншихад алдаа гарлаа.";
    return (
      <main className={styles.shell}>
        <div className={styles.container}>
          <section className={styles.emptyState}>
            <h2>Ажил нээгдсэнгүй</h2>
            <p>{message}</p>
          </section>
        </div>
      </main>
    );
  }

  const canCreateProject = hasCapability(session, "create_projects");
  const canCreateTasks = hasCapability(session, "create_tasks");
  const canViewQualityCenter = hasCapability(session, "view_quality_center");
  const canUseFieldConsole = hasCapability(session, "use_field_console");
  const taskCounts = {
    all: project.tasks.length,
    todo: project.tasks.filter((task) => task.stageBucket === "todo" || task.stageBucket === "unknown").length,
    progress: project.tasks.filter((task) => task.stageBucket === "progress").length,
    review: project.tasks.filter((task) => task.stageBucket === "review").length,
    done: project.tasks.filter((task) => task.stageBucket === "done").length,
  } satisfies Record<TaskFilterKey, number>;

  const visibleTasks = project.tasks.filter((task) => {
    if (activeFilter === "all") {
      return true;
    }

    if (activeFilter === "todo") {
      return task.stageBucket === "todo" || task.stageBucket === "unknown";
    }

    return task.stageBucket === activeFilter;
  });

  return (
    <main className={styles.shell}>
      <div className={styles.container} id="project-top">
        <div className={styles.contentWithMenu}>
          <aside className={styles.menuColumn}>
            <AppMenu
              active="projects"
              canCreateProject={canCreateProject}
              canViewQualityCenter={canViewQualityCenter}
              canUseFieldConsole={canUseFieldConsole}
              userName={session.name}
              roleLabel={getRoleLabel(session.role)}
              masterMode={masterMode}
            />
          </aside>

          <div className={styles.pageContent}>
            {errorMessage ? (
              <div className={`${styles.message} ${styles.errorMessage}`}>{errorMessage}</div>
            ) : null}
            {noticeMessage ? (
              <div className={`${styles.message} ${styles.noticeMessage}`}>{noticeMessage}</div>
            ) : null}

            <section className={styles.heroCard}>
              <span className={styles.eyebrow}>{masterMode ? "Ажил нэмэх урсгал" : "Ажлын ажилбар"}</span>
              <h1>{project.name}</h1>
              <p>
                {masterMode
                  ? "Мастер хэрэглэгч энэ ажлын хүрээнд шинэ ажилбар нээж, өнөөдрийн урсгалаа тайлантай нь хамт удирдана."
                  : "Энэ дэлгэц дээр зөвхөн тухайн ажлын ажилбарууд харагдана. Тухайн ажилбар дээр дарж дараагийн дэлгэрэнгүй рүү орно."}
              </p>

              <div className={styles.statsGrid}>
                <article className={styles.statCard}>
                  <span>Алба нэгж</span>
                  <strong>{project.departmentName}</strong>
                </article>
                <article className={styles.statCard}>
                  <span>Нийт ажилбар</span>
                  <strong>{project.taskCount}</strong>
                </article>
                <article className={styles.statCard}>
                  <span>Хянагдаж буй</span>
                  <strong>{project.reviewCount}</strong>
                </article>
                <article className={styles.statCard}>
                  <span>Гүйцэтгэл</span>
                  <strong>{project.completion}%</strong>
                </article>
              </div>

              <div className={styles.buttonRow}>
                <Link href="/projects" className={styles.smallLink}>
                  {masterMode ? "Ажил нэмэх жагсаалт руу буцах" : "Ажлууд руу буцах"}
                </Link>
              </div>
            </section>

            <section className={styles.panelGrid}>
              <section className={styles.panel}>
                <div className={styles.sectionHeader}>
                  <div>
                    <span className={styles.eyebrow}>Ажлын самбар</span>
                    <h2>{masterMode ? "Ажил дээрх өнөөдрийн урсгал" : "Ажлын ажилбарууд"}</h2>
                  </div>
                  <p>
                    {masterMode
                      ? "Доорх ажилбар бүр дээр дарж тайлангийн урсгал руу орно. Шинэ ажилбар нэмэх form баруун талд харагдана."
                      : "Доорх ажилбар бүр дээр дарахад тухайн ажилбарын дэлгэрэнгүй нээгдэнэ."}
                  </p>
                </div>

                <div className={styles.taskFilterRail}>
                  {TASK_FILTERS.map((filter) => {
                    const href =
                      filter.key === "all"
                        ? `/projects/${project.id}`
                        : `/projects/${project.id}?status=${filter.key}`;

                    return (
                      <Link
                        key={filter.key}
                        href={href}
                        className={`${styles.taskFilterChip} ${
                          activeFilter === filter.key ? styles.taskFilterChipActive : ""
                        }`}
                      >
                        <span>{filter.label}</span>
                        <strong>{taskCounts[filter.key]}</strong>
                      </Link>
                    );
                  })}
                </div>

                {visibleTasks.length ? (
                  <div className={styles.taskGrid}>
                    {visibleTasks.map((task) => (
                      <Link key={task.id} href={task.href} className={styles.taskItem}>
                        <div className={styles.taskItemTop}>
                          <div>
                            <h3>{task.name}</h3>
                            <p>Хариуцсан мастер: {task.teamLeaderName}</p>
                          </div>
                          <StagePill label={task.stageLabel} bucket={task.stageBucket} />
                        </div>

                        <div className={styles.metaRow}>
                          <span>
                            Хэмжээ: {task.completedQuantity}/{task.plannedQuantity}{" "}
                            {task.measurementUnit}
                          </span>
                          <span>Хугацаа: {task.deadline}</span>
                        </div>

                        <div className={styles.progressTrack}>
                          <span style={{ width: `${task.progress}%` }} />
                        </div>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <div className={styles.emptyState}>
                    <h2>Ажилбар алга</h2>
                    <p>Энэ төлөв дээр харагдах ажилбар одоогоор алга байна.</p>
                  </div>
                )}
              </section>

              {canCreateTasks ? (
                <aside className={styles.formCard} id="task-create-form">
                  <div className={styles.sectionHeader}>
                    <div>
                      <span className={styles.eyebrow}>Шинэ ажилбар</span>
                      <h2>{masterMode ? "Өнөөдрийн ажил нэмэх" : "Ажилбар үүсгэх"}</h2>
                    </div>
                  </div>

                  <form action={createTaskAction} className={styles.form}>
                    <input type="hidden" name="project_id" value={project.id} />

                    <div className={styles.field}>
                      <label htmlFor="task-name">Ажилбарын нэр</label>
                      <input
                        id="task-name"
                        name="name"
                        type="text"
                        placeholder="Жишээ: Хогийн савны тойргийн цэвэрлэгээ"
                        required
                      />
                    </div>

                    {!masterMode ? (
                      <div className={styles.field}>
                        <label htmlFor="task-team-leader">Хариуцсан мастер</label>
                        <select id="task-team-leader" name="team_leader_id" defaultValue="">
                          <option value="">Сонгоогүй</option>
                          {project.teamLeaderOptions.map((option) => (
                            <option key={option.id} value={option.id}>
                              {option.name}
                            </option>
                          ))}
                        </select>
                      </div>
                    ) : null}

                    <div className={styles.field}>
                      <label htmlFor="task-deadline">Хугацаа</label>
                      <input id="task-deadline" name="deadline" type="date" defaultValue={project.deadline} />
                    </div>

                    <div className={styles.field}>
                      <label htmlFor="task-planned-quantity">Төлөвлөсөн хэмжээ</label>
                      <input
                        id="task-planned-quantity"
                        name="planned_quantity"
                        type="number"
                        min="0"
                        step="0.01"
                        placeholder="0"
                      />
                    </div>

                    <div className={styles.field}>
                      <label htmlFor="task-measurement-unit">Хэмжих нэгж</label>
                      <input
                        id="task-measurement-unit"
                        name="measurement_unit"
                        type="text"
                        placeholder="ш, м.кв, рейс"
                      />
                    </div>

                    <div className={styles.field}>
                      <label htmlFor="task-description">Товч тайлбар</label>
                      <textarea
                        id="task-description"
                        name="description"
                        placeholder="Өнөөдөр хийх ажлын хүрээ, байршил, онцгой зааврыг товч бичнэ."
                      />
                    </div>

                    <div className={styles.buttonRow}>
                      <button type="submit" className={styles.primaryButton}>
                        {masterMode ? "Ажил нэмэх" : "Ажилбар үүсгэх"}
                      </button>
                    </div>
                  </form>
                </aside>
              ) : null}
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}
