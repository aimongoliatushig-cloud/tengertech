import Link from "next/link";

import { AppMenu } from "@/app/_components/app-menu";
import { logoutAction } from "@/app/actions";
import dashboardStyles from "@/app/page.module.css";
import styles from "@/app/workspace.module.css";
import { getRoleLabel, hasCapability, requireSession } from "@/lib/auth";
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

export default async function ReviewPage({ searchParams }: PageProps) {
  const session = await requireSession();
  const snapshot = await loadMunicipalSnapshot({
    login: session.login,
    password: session.password,
  });

  const canCreateProject = hasCapability(session, "create_projects");
  const canViewQualityCenter = hasCapability(session, "view_quality_center");
  const canUseFieldConsole = hasCapability(session, "use_field_console");

  const params = (await searchParams) ?? {};
  const requestedDepartment = getDepartmentParam(params.department);

  const selectedDepartment =
    snapshot.departments.find((department) => department.name === requestedDepartment) ??
    snapshot.departments.find((department) =>
      snapshot.reviewQueue.some((item) => item.departmentName === department.name),
    ) ??
    snapshot.departments[0];

  const visibleReviewTasks = snapshot.reviewQueue.filter(
    (item) => item.departmentName === selectedDepartment?.name,
  );

  const departmentProjectCount = snapshot.projects.filter(
    (project) => project.departmentName === selectedDepartment?.name,
  ).length;

  return (
    <main className={styles.shell}>
      <div className={styles.container} id="review-top">
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

        <AppMenu
          active="review"
          canCreateProject={canCreateProject}
          canViewQualityCenter={canViewQualityCenter}
          canUseFieldConsole={canUseFieldConsole}
        />

        <section className={styles.heroCard}>
          <span className={styles.eyebrow}>Шалгах ажлууд</span>
          <h1>Алба нэгжээр нь сонгож шалгалтын ажлуудаа хянах</h1>
          <p>
            Ерөнхий менежер шалгалтад ирсэн ажлуудыг алба нэгжээр нь ялгаж харна.
            Доорх цэснээс нэг алба нэгж сонгоход зөвхөн тухайн нэгжийн
            `Шалгагдаж буй ажил`-ууд харагдана.
          </p>

          <div className={styles.statsGrid}>
            <article className={styles.statCard}>
              <span>Сонгосон алба нэгж</span>
              <strong>{selectedDepartment?.name ?? "Тодорхойгүй"}</strong>
            </article>
            <article className={styles.statCard}>
              <span>Шалгах ажил</span>
              <strong>{visibleReviewTasks.length}</strong>
            </article>
            <article className={styles.statCard}>
              <span>Тухайн нэгжийн төсөл</span>
              <strong>{departmentProjectCount}</strong>
            </article>
            <article className={styles.statCard}>
              <span>Нээлттэй ажил</span>
              <strong>{selectedDepartment?.openTasks ?? 0}</strong>
            </article>
          </div>
        </section>

        <section className={dashboardStyles.projectsSection}>
          <div className={dashboardStyles.sectionHeader}>
            <div>
              <span className={dashboardStyles.kicker}>Алба нэгжийн цэс</span>
              <h2>Алба нэгж сонгох</h2>
              <small className={dashboardStyles.sectionNote}>
                Нэг дор бүх нэгжийг биш, сонгосон нэгжийн шалгалтын ажлуудыг харуулна
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
                    href={`/review?department=${encodeURIComponent(department.name)}`}
                    className={`${dashboardStyles.departmentTab} ${
                      isActive ? dashboardStyles.departmentTabActive : ""
                    }`}
                    aria-current={isActive ? "page" : undefined}
                  >
                    <span>{department.name}</span>
                    <strong>{department.reviewTasks}</strong>
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
                  <span>Шалгах</span>
                  <strong>{visibleReviewTasks.length}</strong>
                </div>
                <div>
                  <span>Шалгалтын мөр</span>
                  <strong>{selectedDepartment.reviewTasks}</strong>
                </div>
                <div>
                  <span>Гүйцэтгэл</span>
                  <strong>{selectedDepartment.completion}%</strong>
                </div>
              </div>
            </div>

            {visibleReviewTasks.length ? (
              <div className={dashboardStyles.reviewList}>
                {visibleReviewTasks.map((item) => (
                  <Link key={item.id} href={item.href} className={dashboardStyles.reviewItem}>
                    <div>
                      <h3>{item.name}</h3>
                      <p>{item.projectName}</p>
                    </div>
                    <div className={dashboardStyles.reviewMeta}>
                      <StagePill label={item.stageLabel} bucket="review" />
                      <strong>{item.progress}%</strong>
                      <span>{item.deadline}</span>
                      <span>{item.leaderName}</span>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className={dashboardStyles.emptyColumnState}>
                Одоогоор {selectedDepartment.name} дээр шалгах ажил алга байна.
              </div>
            )}
          </section>
        ) : null}

        <nav className={styles.mobileDock} aria-label="Шалгалтын хуудасны гар утасны цэс">
          <Link href="/" className={styles.jumpLink}>
            Нүүр
          </Link>
          <Link href="/projects" className={styles.jumpLink}>
            Төсөл
          </Link>
          <a href="#review-top" className={styles.jumpLink}>
            Дээш
          </a>
        </nav>
      </div>
    </main>
  );
}
