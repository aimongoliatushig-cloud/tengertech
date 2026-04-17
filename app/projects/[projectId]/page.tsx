import Link from "next/link";

import { createTaskAction, logoutAction } from "@/app/actions";
import styles from "@/app/workspace.module.css";
import { getRoleLabel, requireSession } from "@/lib/auth";
import { loadProjectDetail } from "@/lib/workspace";

type PageProps = {
  params: Promise<{
    projectId: string;
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

export default async function ProjectDetailPage({ params, searchParams }: PageProps) {
  const session = await requireSession();
  const resolvedParams = await params;
  const projectId = Number(resolvedParams.projectId);
  const query = (await searchParams) ?? {};
  const errorMessage = getMessage(query.error);
  const noticeMessage = getMessage(query.notice);

  let project;
  try {
    project = await loadProjectDetail(projectId, {
      login: session.login,
      password: session.password,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Төслийг уншихад алдаа гарлаа.";
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
            <h2>Төсөл нээгдсэнгүй</h2>
            <p>{message}</p>
          </section>
        </div>
      </main>
    );
  }

  const canCreateTask =
    session.role === "general_manager" ||
    session.role === "system_admin" ||
    session.role === "project_manager";

  return (
    <main className={styles.shell}>
      <div className={styles.container}>
        <header className={styles.navBar}>
          <div className={styles.navLinks}>
            <Link href="/" className={styles.backLink}>
              Самбар руу буцах
            </Link>
            <span>{project.name}</span>
            <span>{getRoleLabel(session.role)}</span>
          </div>

          <div className={styles.navActions}>
            <Link href="/projects/new" className={styles.smallLink}>
              Шинэ төсөл
            </Link>
            <form action={logoutAction}>
              <button type="submit" className={styles.secondaryButton}>
                Гарах
              </button>
            </form>
          </div>
        </header>

        <section className={styles.heroCard}>
          <span className={styles.eyebrow}>Project Workspace</span>
          <h1>{project.name}</h1>
          <p>
            Энэ дэлгэцээс төслийн task-уудыг дотроос нь хянаж, шинэ task үүсгээд, дараагийн
            алхамд task detail рүү орж workflow-ийг удирдана.
          </p>

          <div className={styles.statsGrid}>
            <article className={styles.statCard}>
              <span>Алба нэгж</span>
              <strong>{project.departmentName}</strong>
            </article>
            <article className={styles.statCard}>
              <span>Төслийн удирдагч</span>
              <strong>{project.managerName}</strong>
            </article>
            <article className={styles.statCard}>
              <span>Нийт task</span>
              <strong>{project.taskCount}</strong>
            </article>
            <article className={styles.statCard}>
              <span>Шалгалтад байгаа</span>
              <strong>{project.reviewCount}</strong>
            </article>
          </div>
        </section>

        {errorMessage ? (
          <div className={`${styles.message} ${styles.errorMessage}`}>{errorMessage}</div>
        ) : null}
        {noticeMessage ? (
          <div className={`${styles.message} ${styles.noticeMessage}`}>{noticeMessage}</div>
        ) : null}

        <section className={styles.panelGrid}>
          <section className={styles.panel}>
            <div className={styles.sectionHeader}>
              <div>
                <span className={styles.eyebrow}>Task Board</span>
                <h2>Төслийн task-ууд</h2>
              </div>
              <p>Доорх task дээр дарж status, тайлан, гүйцэтгэлийг web app-аас удирдана.</p>
            </div>

            {project.tasks.length ? (
              <div className={styles.taskGrid}>
                {project.tasks.map((task) => (
                  <Link key={task.id} href={task.href} className={styles.taskItem}>
                    <div className={styles.taskItemTop}>
                      <div>
                        <h3>{task.name}</h3>
                        <p>Багийн ахлагч: {task.teamLeaderName}</p>
                      </div>
                      <StagePill label={task.stageLabel} bucket={task.stageBucket} />
                    </div>

                    <div className={styles.metaRow}>
                      <span>
                        Хэмжээ: {task.completedQuantity}/{task.plannedQuantity}{" "}
                        {task.measurementUnit}
                      </span>
                      <span>Deadline: {task.deadline}</span>
                    </div>

                    <div className={styles.progressTrack}>
                      <span style={{ width: `${task.progress}%` }} />
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className={styles.emptyState}>
                <h2>Task алга</h2>
                <p>Энэ төсөл дээр одоогоор task бүртгэгдээгүй байна.</p>
              </div>
            )}
          </section>

          <aside className={styles.formCard}>
            <div className={styles.sectionHeader}>
              <div>
                <span className={styles.eyebrow}>Task Create</span>
                <h2>Шинэ task</h2>
              </div>
            </div>

            {!canCreateTask ? (
              <p>Энэ role дээр шинэ task үүсгэх form харагдахгүй.</p>
            ) : (
              <form action={createTaskAction} className={styles.form}>
                <input type="hidden" name="project_id" value={project.id} />

                <div className={styles.field}>
                  <label htmlFor="name">Task нэр</label>
                  <input
                    id="name"
                    name="name"
                    type="text"
                    placeholder="Жишээ: 3-р хорооны мод хэлбэржүүлэлт"
                    required
                  />
                </div>

                <div className={styles.field}>
                  <label htmlFor="team_leader_id">Багийн ахлагч</label>
                  <select id="team_leader_id" name="team_leader_id" defaultValue="">
                    <option value="">Одоохондоо сонгохгүй</option>
                    {project.teamLeaderOptions.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.name} ({option.login})
                      </option>
                    ))}
                  </select>
                </div>

                <div className={styles.fieldRow}>
                  <div className={styles.field}>
                    <label htmlFor="planned_quantity">Төлөвлөсөн хэмжээ</label>
                    <input
                      id="planned_quantity"
                      name="planned_quantity"
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="48"
                    />
                  </div>
                  <div className={styles.field}>
                    <label htmlFor="measurement_unit">Хэмжих нэгж</label>
                    <input
                      id="measurement_unit"
                      name="measurement_unit"
                      type="text"
                      placeholder="мод"
                    />
                  </div>
                </div>

                <div className={styles.field}>
                  <label htmlFor="deadline">Deadline</label>
                  <input id="deadline" name="deadline" type="date" defaultValue={project.deadline} />
                </div>

                <div className={styles.field}>
                  <label htmlFor="description">Тайлбар</label>
                  <textarea
                    id="description"
                    name="description"
                    placeholder="Байршил, ажлын нөхцөл, нэмэлт тайлбар"
                  />
                </div>

                <div className={styles.buttonRow}>
                  <button type="submit" className={styles.primaryButton}>
                    Task үүсгэх
                  </button>
                </div>
              </form>
            )}
          </aside>
        </section>
      </div>
    </main>
  );
}
