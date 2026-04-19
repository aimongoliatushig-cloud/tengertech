import Link from "next/link";

import { AppMenu } from "@/app/_components/app-menu";
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

function matchesDepartment(departmentName: string, ...values: string[]) {
  const haystack = values.join(" ").toLowerCase();

  if (haystack.includes(departmentName.toLowerCase())) {
    return true;
  }

  if (departmentName === "Авто бааз") {
    return haystack.includes("авто") || haystack.includes("техник") || haystack.includes("машин");
  }

  if (departmentName === "Хог тээвэрлэлт") {
    return haystack.includes("хог") || haystack.includes("ачилт") || haystack.includes("маршрут");
  }

  if (departmentName === "Ногоон байгууламж") {
    return haystack.includes("ногоон") || haystack.includes("мод") || haystack.includes("зүлэг");
  }

  if (departmentName === "Зам талбайн цэвэрлэгээ") {
    return haystack.includes("зам") || haystack.includes("цэвэрлэгээ") || haystack.includes("гудамж");
  }

  if (departmentName === "Тохижилт үйлчилгээ") {
    return (
      haystack.includes("тохижилт") ||
      haystack.includes("үйлчилгээ") ||
      haystack.includes("засвар")
    );
  }

  return false;
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

  const canCreateProject = hasCapability(session, "create_projects");
  const canViewQualityCenter = hasCapability(session, "view_quality_center");
  const canUseFieldConsole = hasCapability(session, "use_field_console");

  const params = (await searchParams) ?? {};
  const requestedDepartment = getDepartmentParam(params.department);

  const selectedDepartment =
    requestedDepartment && requestedDepartment !== "all"
      ? snapshot.departments.find((department) => department.name === requestedDepartment) ?? null
      : null;

  const displayDepartment = selectedDepartment ?? {
    name: "Бүх алба нэгж",
    label: "Odoo ERP дээрх бүх алба нэгжийн төсөл, ажил, тайланг нэг дор харуулна.",
    icon: "🏢",
    accent: "var(--tone-slate)",
    openTasks: snapshot.taskDirectory.filter((task) => task.statusKey !== "verified").length,
    reviewTasks: snapshot.taskDirectory.filter((task) => task.statusKey === "review").length,
    completion: snapshot.totalTasks
      ? Math.round(
          (snapshot.taskDirectory.filter((task) => task.statusKey === "verified").length /
            snapshot.totalTasks) *
            100,
        )
      : 0,
  };

  const selectedDepartmentName = displayDepartment.name;

  const visibleProjects = snapshot.projects
    .filter((project) => !selectedDepartment || project.departmentName === selectedDepartment.name)
    .sort((left, right) => right.completion - left.completion);

  const visibleProjectNames = new Set(visibleProjects.map((project) => project.name));

  const visibleLiveTasks = snapshot.liveTasks
    .filter(
      (task) =>
        (!selectedDepartment ||
          matchesDepartment(selectedDepartment.name, task.departmentName, task.projectName, task.name)) ||
        visibleProjectNames.has(task.projectName),
    )
    .sort((left, right) => right.progress - left.progress);

  const visibleReviewQueue = snapshot.reviewQueue
    .filter(
      (task) =>
        !selectedDepartment ||
        matchesDepartment(selectedDepartment.name, task.departmentName, task.projectName, task.name),
    )
    .sort((left, right) => right.progress - left.progress);

  const visibleQualityAlerts = snapshot.qualityAlerts
    .filter(
      (alert) =>
        !selectedDepartment ||
        matchesDepartment(selectedDepartment.name, alert.departmentName, alert.projectName, alert.name),
    )
    .sort((left, right) => right.exceptionCount - left.exceptionCount);

  const visibleReports = snapshot.reports
    .filter(
      (report) =>
        (!selectedDepartment ||
          matchesDepartment(
            selectedDepartment.name,
            report.departmentName,
            report.projectName,
            report.taskName,
          )) ||
        visibleProjectNames.has(report.projectName),
    )
    .slice(0, 6);

  const activeProjectCount = visibleProjects.filter((project) => project.stageBucket !== "done").length;
  const averageTaskProgress = visibleLiveTasks.length
    ? Math.round(
        visibleLiveTasks.reduce((sum, task) => sum + task.progress, 0) / visibleLiveTasks.length,
      )
    : displayDepartment.completion;

  return (
    <main className={styles.shell}>
      <div className={styles.container} id="projects-top">
        <div className={styles.contentWithMenu}>
          <aside className={styles.menuColumn}>
            <AppMenu
              active="projects"
              canCreateProject={canCreateProject}
              canViewQualityCenter={canViewQualityCenter}
              canUseFieldConsole={canUseFieldConsole}
              userName={session.name}
              roleLabel={getRoleLabel(session.role)}
            />
          </aside>

          <div className={styles.pageContent}>
            <section className={dashboardStyles.projectsSection}>
              <div className={dashboardStyles.sectionHeader}>
                <div>
                  <span className={dashboardStyles.kicker}>Алба нэгжийн цэс</span>
                  <h2>Алба нэгж сонгох</h2>
                  <small className={dashboardStyles.sectionNote}>
                    Сонголт бүр тухайн албаны самбарыг нээнэ
                  </small>
                </div>
              </div>

              <nav className={dashboardStyles.departmentSelector} aria-label="Алба нэгж сонгох цэс">
                <div className={dashboardStyles.departmentTabBar}>
                  <Link
                    href="/projects"
                    className={`${dashboardStyles.departmentTab} ${
                      !selectedDepartment ? dashboardStyles.departmentTabActive : ""
                    }`}
                    aria-current={!selectedDepartment ? "page" : undefined}
                  >
                    <span className={dashboardStyles.departmentTabLabel}>
                      <span className={dashboardStyles.departmentTabIcon} aria-hidden>
                        🏢
                      </span>
                      <span>Бүгд</span>
                    </span>
                    <strong>{snapshot.totalTasks}</strong>
                  </Link>
                  {snapshot.departments.map((department) => {
                    const isActive = department.name === selectedDepartmentName;

                    return (
                      <Link
                        key={department.name}
                        href={`/projects?department=${encodeURIComponent(department.name)}`}
                        className={`${dashboardStyles.departmentTab} ${
                          isActive ? dashboardStyles.departmentTabActive : ""
                        }`}
                        aria-current={isActive ? "page" : undefined}
                      >
                        <span className={dashboardStyles.departmentTabLabel}>
                          <span className={dashboardStyles.departmentTabIcon} aria-hidden>
                            {department.icon}
                          </span>
                          <span>{department.name}</span>
                        </span>
                        <strong>{department.openTasks}</strong>
                      </Link>
                    );
                  })}
                </div>
              </nav>
            </section>

            <section className={styles.heroCard}>
              <span className={styles.eyebrow}>Алба нэгжийн самбар</span>
              <h1>Албаны нэгдсэн самбар</h1>
              <p>Сонгосон албаны төсөл, ажил, шалгалт, тайланг нэг дороос харуулна.</p>

              <div className={styles.statsGrid}>
                <article className={styles.statCard}>
                  <span>Сонгосон алба</span>
                  <strong>{selectedDepartmentName}</strong>
                </article>
                <article className={styles.statCard}>
                  <span>Нийт төсөл</span>
                  <strong>{visibleProjects.length}</strong>
                </article>
                <article className={styles.statCard}>
                  <span>Идэвхтэй ажил</span>
                  <strong>{visibleLiveTasks.length}</strong>
                </article>
                <article className={styles.statCard}>
                  <span>Анхаарах ажил</span>
                  <strong>{visibleQualityAlerts.length}</strong>
                </article>
              </div>
            </section>

          <>
            <section className={dashboardStyles.projectsSection}>
              <div className={dashboardStyles.selectedDepartmentHeader}>
                <div>
                  <span
                    className={dashboardStyles.departmentAccentBadge}
                    style={{ background: displayDepartment.accent }}
                  />
                  <div className={dashboardStyles.selectedDepartmentTitle}>
                    <span className={dashboardStyles.departmentHeroIcon} aria-hidden>
                      {displayDepartment.icon}
                    </span>
                    <h2>{displayDepartment.name}</h2>
                  </div>
                  <p className={dashboardStyles.selectedDepartmentNote}>
                    {displayDepartment.label}
                  </p>
                </div>

                <div className={dashboardStyles.projectMetaSummary}>
                  <div>
                    <span>Төсөл</span>
                    <strong>{visibleProjects.length}</strong>
                  </div>
                  <div>
                    <span>Идэвхтэй төсөл</span>
                    <strong>{activeProjectCount}</strong>
                  </div>
                  <div>
                    <span>Шалгалт</span>
                    <strong>{visibleReviewQueue.length}</strong>
                  </div>
                  <div>
                    <span>Дундаж явц</span>
                    <strong>{averageTaskProgress}%</strong>
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
                          <span>Нээлттэй ажил</span>
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

                      <div className={dashboardStyles.cardFooter}>
                        <span className={dashboardStyles.cardLinkLabel}>Төслийг нээх</span>
                        <strong aria-hidden>→</strong>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className={dashboardStyles.emptyColumnState}>
                  Одоогоор {displayDepartment.name} дээр бүртгэгдсэн төсөл алга.
                </div>
              )}
            </section>

            <section className={styles.panelGrid}>
              <section className={styles.panel}>
                <div className={styles.sectionHeader}>
                  <div>
                    <h2>Идэвхтэй ажил</h2>
                    <p>Одоогоор явж буй ажлуудыг товч зураглалаар харуулна.</p>
                  </div>
                </div>

                {visibleLiveTasks.length ? (
                  <div className={dashboardStyles.taskList}>
                    {visibleLiveTasks.map((task) => (
                      <Link key={task.id} href={task.href} className={dashboardStyles.taskCard}>
                        <div className={dashboardStyles.taskCardTop}>
                          <span>{task.deadline}</span>
                          <StagePill label={task.stageLabel} bucket={task.stageBucket} />
                        </div>

                        <h3>{task.name}</h3>
                        <p>{task.projectName}</p>

                        <div className={dashboardStyles.taskStats}>
                          <span>Ахлагч: {task.leaderName}</span>
                          <span>Төлөв: {task.priorityLabel}</span>
                          <span>Үлдэгдэл: {task.remainingQuantity} {task.measurementUnit}</span>
                        </div>

                        <div className={dashboardStyles.taskQuantities}>
                          <span>
                            {task.completedQuantity} / {task.plannedQuantity} {task.measurementUnit}
                          </span>
                          <b>{task.progress}%</b>
                        </div>

                        <div className={dashboardStyles.progressTrack}>
                          <span style={{ width: `${task.progress}%` }} />
                        </div>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <div className={dashboardStyles.emptyColumnState}>
                    Энэ алба нэгж дээр одоогоор идэвхтэй ажил алга.
                  </div>
                )}
              </section>

              <section className={styles.panel}>
                <div className={styles.sectionHeader}>
                  <div>
                    <h2>Товч төлөв</h2>
                    <p>Алба нэгжийн гол үзүүлэлтүүдийг executive түвшинд харуулна.</p>
                  </div>
                </div>

                <div className={dashboardStyles.statusList}>
                  <div className={dashboardStyles.statusItem}>
                    <span>Нээлттэй ажил</span>
                    <strong>{displayDepartment.openTasks}</strong>
                    <small>Тухайн алба нэгжийн одоо хаагдаагүй ажил</small>
                  </div>
                  <div className={dashboardStyles.statusItem}>
                    <span>Шалгалтын мөр</span>
                    <strong>{visibleReviewQueue.length}</strong>
                    <small>Баталгаажуулалт хүлээж буй ажил</small>
                  </div>
                  <div className={dashboardStyles.statusItem}>
                    <span>Анхаарах зүйл</span>
                    <strong>{visibleQualityAlerts.length}</strong>
                    <small>Чанар эсвэл синкийн зөрүүтэй ажил</small>
                  </div>
                  <div className={dashboardStyles.statusItem}>
                    <span>Сүүлийн тайлан</span>
                    <strong>{visibleReports.length}</strong>
                    <small>Хамгийн сүүлийн тайлангийн бүртгэл</small>
                  </div>
                </div>
              </section>
            </section>

            <section className={styles.panelGrid}>
              <section className={styles.panel}>
                <div className={styles.sectionHeader}>
                  <div>
                    <h2>Шалгалтын мөр</h2>
                    <p>Шалгалт хүлээж буй ажлуудыг priority дагуу харуулна.</p>
                  </div>
                </div>

                {visibleReviewQueue.length ? (
                  <div className={dashboardStyles.reviewList}>
                    {visibleReviewQueue.map((task) => (
                      <Link key={task.id} href={task.href} className={dashboardStyles.reviewItem}>
                        <div>
                          <h3>{task.name}</h3>
                          <p>
                            {task.projectName} / {task.leaderName}
                          </p>
                        </div>

                        <div className={dashboardStyles.reviewMeta}>
                          <strong>{task.progress}%</strong>
                          <span>{task.stageLabel}</span>
                          <span>{task.deadline}</span>
                        </div>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <div className={dashboardStyles.emptyColumnState}>
                    Энэ алба нэгж дээр одоогоор шалгалтын мөр алга.
                  </div>
                )}
              </section>

              <section className={styles.panel}>
                <div className={styles.sectionHeader}>
                  <div>
                    <h2>Анхаарах зүйлс</h2>
                    <p>Чанар, зураг, маршрут, жингийн синктэй холбоотой ажлууд.</p>
                  </div>
                </div>

                {visibleQualityAlerts.length ? (
                  <div className={dashboardStyles.reviewList}>
                    {visibleQualityAlerts.map((alert) => (
                      <Link key={alert.id} href={alert.href} className={dashboardStyles.reviewItem}>
                        <div>
                          <h3>{alert.name}</h3>
                          <p>
                            {alert.projectName} / {alert.routeName}
                          </p>
                        </div>

                        <div className={dashboardStyles.reviewMeta}>
                          <strong>{alert.exceptionCount} анхааруулга</strong>
                          <span>{alert.operationTypeLabel}</span>
                          <span>{alert.hasWeightWarning ? "Жингийн синк шалгах" : "Чанарын мөр"}</span>
                        </div>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <div className={dashboardStyles.emptyColumnState}>
                    Одоогоор энэ алба нэгж дээр чанарын анхааруулга алга.
                  </div>
                )}
              </section>
            </section>

            <section className={dashboardStyles.projectsSection}>
              <div className={dashboardStyles.sectionHeader}>
                <div>
                  <span className={dashboardStyles.kicker}>Сүүлийн урсгал</span>
                  <h2>Тайлангийн самбар</h2>
                  <small className={dashboardStyles.sectionNote}>
                    Тухайн алба нэгжийн хамгийн сүүлийн тайлангуудыг харуулна
                  </small>
                </div>
                <Link href="/reports" className={styles.smallLink}>
                  Бүх тайлан харах
                </Link>
              </div>

              {visibleReports.length ? (
                <div className={dashboardStyles.reportFeed}>
                  {visibleReports.map((report) => (
                    <article key={report.id} className={dashboardStyles.reportCard}>
                      <div className={dashboardStyles.reportTop}>
                        <strong>{report.submittedAt}</strong>
                        <StagePill label="Тайлан орсон" bucket="review" />
                      </div>

                      <h3>{report.taskName}</h3>
                      <p>{report.projectName}</p>

                      <div className={dashboardStyles.reportMeta}>
                        <span>Илгээсэн: {report.reporter}</span>
                        <span>Зураг: {report.imageCount}</span>
                        <span>Аудио: {report.audioCount}</span>
                      </div>

                      <div className={dashboardStyles.reportSummary}>{report.summary}</div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className={dashboardStyles.emptyColumnState}>
                  Энэ алба нэгж дээр харагдах тайлан одоогоор алга.
                </div>
              )}
            </section>
        </>

        <nav className={styles.mobileDock} aria-label="Алба нэгжийн самбарын гар утасны цэс">
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
        </div>
      </div>
    </main>
  );
}
