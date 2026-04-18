import Link from "next/link";

import { AppMenu } from "@/app/_components/app-menu";
import { logoutAction } from "@/app/actions";
import dashboardStyles from "@/app/page.module.css";
import styles from "@/app/workspace.module.css";
import { getRoleLabel, requireSession } from "@/lib/auth";
import { loadMunicipalSnapshot } from "@/lib/odoo";

type PageProps = {
  searchParams?: Promise<{
    department?: string | string[];
  }>;
};

function getDepartmentParam(value?: string | string[]) {
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
}

function StagePill({
  label,
  bucket,
}: {
  label: string;
  bucket: "todo" | "progress" | "review" | "done" | "unknown";
}) {
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

export const dynamic = "force-dynamic";

export default async function ProjectsPage({ searchParams }: PageProps) {
  const session = await requireSession();
  const snapshot = await loadMunicipalSnapshot({
    login: session.login,
    password: session.password,
  });

  const canCreateProject =
    session.role === "general_manager" || session.role === "system_admin";

  const params = (await searchParams) ?? {};
  const requestedDepartment = getDepartmentParam(params.department);

  const selectedDepartment =
    snapshot.departments.find((department) => department.name === requestedDepartment) ??
    snapshot.departments.find((department) =>
      snapshot.projects.some((project) => project.departmentName === department.name),
    ) ??
    snapshot.departments[0];

  const visibleProjects = snapshot.projects
    .filter((project) => project.departmentName === selectedDepartment?.name)
    .sort((left, right) => right.completion - left.completion);

  return (
    <main className={styles.shell}>
      <div className={styles.container} id="projects-top">
        <header className={styles.navBar}>
          <div className={styles.navLinks}>
            <Link href="/" className={styles.backLink}>
              Хяналтын самбар
            </Link>
            <span>{getRoleLabel(session.role)}</span>
          </div>

          <div className={styles.navActions}>
            {canCreateProject ? (
              <Link href="/projects/new" className={styles.smallLink}>
                Шинэ төсөл
              </Link>
            ) : null}
            <form action={logoutAction}>
              <button type="submit" className={styles.secondaryButton}>
                Гарах
              </button>
            </form>
          </div>
        </header>

        <AppMenu active="projects" canCreateProject={canCreateProject} />

        <section className={styles.heroCard}>
          <span className={styles.eyebrow}>Төсөл хянах</span>
          <h1>Алба нэгжээр сонгож төслүүдээ харах</h1>
          <p>
            Доорх алба нэгжийн цэснээс нэгийг нь сонгоод тухайн нэгжийн төслүүдийг
            төвлөрүүлж харна. Ингэснээр олон багана дундаас хайхгүй, нэгж тус
            бүрээ нэг нэгээр нь хянах боломжтой.
          </p>

          <div className={styles.statsGrid}>
            <article className={styles.statCard}>
              <span>Сонгосон алба нэгж</span>
              <strong>{selectedDepartment?.name ?? "Тодорхойгүй"}</strong>
            </article>
            <article className={styles.statCard}>
              <span>Тухайн нэгжийн төсөл</span>
              <strong>{visibleProjects.length}</strong>
            </article>
            <article className={styles.statCard}>
              <span>Нээлттэй ажил</span>
              <strong>{selectedDepartment?.openTasks ?? 0}</strong>
            </article>
            <article className={styles.statCard}>
              <span>Шалгалтын мөр</span>
              <strong>{selectedDepartment?.reviewTasks ?? 0}</strong>
            </article>
          </div>
        </section>

        <section className={dashboardStyles.projectsSection}>
          <div className={dashboardStyles.sectionHeader}>
            <div>
              <span className={dashboardStyles.kicker}>Department menu</span>
              <h2>Алба нэгж сонгох</h2>
              <small className={dashboardStyles.sectionNote}>
                Нэг удаад нэг алба нэгжийн төслүүдийг харуулна
              </small>
            </div>
          </div>

          <nav className={dashboardStyles.departmentSelector} aria-label="Алба нэгж сонгох цэс">
            <div className={dashboardStyles.departmentTabBar}>
              {snapshot.departments.map((department) => {
                const isActive = department.name === selectedDepartment?.name;

                return (
                  <Link
                    key={department.name}
                    href={`/projects?department=${encodeURIComponent(department.name)}`}
                    className={`${dashboardStyles.departmentTab} ${
                      isActive ? dashboardStyles.departmentTabActive : ""
                    }`}
                    aria-current={isActive ? "page" : undefined}
                  >
                    <span>{department.name}</span>
                    <strong>{department.openTasks}</strong>
                  </Link>
                );
              })}
            </div>
          </nav>
        </section>

        {selectedDepartment ? (
          <section className={dashboardStyles.projectsSection}>
            <div className={dashboardStyles.selectedDepartmentHeader}>
              <div>
                <span
                  className={dashboardStyles.departmentAccentBadge}
                  style={{ background: selectedDepartment.accent }}
                />
                <h2>{selectedDepartment.name}</h2>
                <p className={dashboardStyles.selectedDepartmentNote}>
                  {selectedDepartment.label}
                </p>
              </div>

              <div className={dashboardStyles.projectMetaSummary}>
                <div>
                  <span>Төсөл</span>
                  <strong>{visibleProjects.length}</strong>
                </div>
                <div>
                  <span>Нээлттэй</span>
                  <strong>{selectedDepartment.openTasks}</strong>
                </div>
                <div>
                  <span>Гүйцэтгэл</span>
                  <strong>{selectedDepartment.completion}%</strong>
                </div>
              </div>
            </div>

            {visibleProjects.length ? (
              <div className={dashboardStyles.projectRail}>
                {visibleProjects.map((project) => (
                  <Link
                    key={project.id}
                    href={project.href}
                    className={dashboardStyles.projectCard}
                  >
                    <div className={dashboardStyles.projectCardTop}>
                      <span>{project.deadline}</span>
                      <StagePill label={project.stageLabel} bucket={project.stageBucket} />
                    </div>

                    <h3>{project.name}</h3>
                    <p>Менежер: {project.manager}</p>

                    <div className={dashboardStyles.projectMeta}>
                      <div>
                        <span>Нээлттэй task</span>
                        <strong>{project.openTasks}</strong>
                      </div>
                      <div>
                        <span>Гүйцэтгэл</span>
                        <strong>{project.completion}%</strong>
                      </div>
                    </div>

                    <div className={dashboardStyles.progressTrack}>
                      <span style={{ width: `${project.completion}%` }} />
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className={dashboardStyles.emptyColumnState}>
                Одоогоор {selectedDepartment.name} дээр бүртгэгдсэн төсөл алга.
              </div>
            )}
          </section>
        ) : null}

        <nav className={styles.mobileDock} aria-label="Project board mobile quick navigation">
          <Link href="/" className={styles.jumpLink}>
            Нүүр
          </Link>
          <a href="#projects-top" className={styles.jumpLink}>
            Дээш
          </a>
          {canCreateProject ? (
            <Link href="/projects/new" className={styles.jumpLink}>
              Шинэ
            </Link>
          ) : (
            <Link href="/reports" className={styles.jumpLink}>
              Тайлан
            </Link>
          )}
        </nav>
      </div>
    </main>
  );
}
