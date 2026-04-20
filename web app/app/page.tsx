import Image from "next/image";
import Link from "next/link";

import { AppMenu } from "@/app/_components/app-menu";
import { logoutAction } from "@/app/actions";
import { getRoleLabel, hasCapability, requireSession } from "@/lib/auth";
import { DEPARTMENT_GROUPS, getAvailableUnits } from "@/lib/department-groups";
import { loadMunicipalSnapshot } from "@/lib/odoo";

import styles from "./page.module.css";

function MetricCard({
  label,
  value,
  note,
  tone,
}: {
  label: string;
  value: string;
  note: string;
  tone: "amber" | "teal" | "red" | "slate";
}) {
  return (
    <article className={`${styles.commandCard} ${styles[`tone${tone}`]}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </article>
  );
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
      ? styles.stageDone
      : bucket === "review"
        ? styles.stageReview
        : bucket === "progress"
          ? styles.stageProgress
          : styles.stageTodo;

  return <span className={`${styles.stagePill} ${tone}`}>{label}</span>;
}

export const dynamic = "force-dynamic";

export default async function Home() {
  const session = await requireSession();
  const snapshot = await loadMunicipalSnapshot({
    login: session.login,
    password: session.password,
  });

  const canCreateProject = hasCapability(session, "create_projects");
  const canViewQualityCenter = hasCapability(session, "view_quality_center");
  const canUseFieldConsole = hasCapability(session, "use_field_console");

  const featuredProjects = snapshot.projects.slice(0, 4);
  const activeTasks = snapshot.liveTasks.slice(0, 4);
  const reviewQueue = snapshot.reviewQueue.slice(0, 5);
  const qualityAlerts = snapshot.qualityAlerts.slice(0, 5);
  const recentReports = snapshot.reports.slice(0, 5);
  const availableDepartmentNames = Array.from(
    new Set([
      ...snapshot.departments.map((department) => department.name),
      ...snapshot.projects.map((project) => project.departmentName),
    ]),
  );
  const departmentCards = DEPARTMENT_GROUPS.map((group) => {
    const availableUnits = getAvailableUnits(group, availableDepartmentNames);
    if (!availableUnits.length) {
      return null;
    }

    const relatedDepartments = snapshot.departments.filter((department) =>
      availableUnits.includes(department.name),
    );
    const openTasks = relatedDepartments.reduce(
      (sum, department) => sum + department.openTasks,
      0,
    );
    const reviewTasks = relatedDepartments.reduce(
      (sum, department) => sum + department.reviewTasks,
      0,
    );
    const completionWeight = relatedDepartments.reduce(
      (sum, department) => sum + Math.max(department.openTasks + department.reviewTasks, 1),
      0,
    );
    const completion = completionWeight
      ? Math.round(
          relatedDepartments.reduce(
            (sum, department) =>
              sum +
              department.completion *
                Math.max(department.openTasks + department.reviewTasks, 1),
            0,
          ) / completionWeight,
        )
      : 0;

    const hrefParams = new URLSearchParams();
    hrefParams.set("department", group.name);
    if (availableUnits[0]) {
      hrefParams.set("unit", availableUnits[0]);
    }

    return {
      name: group.name,
      label: availableUnits.join(" • "),
      icon: group.icon,
      accent: group.accent,
      openTasks,
      reviewTasks,
      completion,
      href: `/projects?${hrefParams.toString()}`,
    };
  }).filter(
    (
      card,
    ): card is {
      name: string;
      label: string;
      icon: string;
      accent: string;
      openTasks: number;
      reviewTasks: number;
      completion: number;
      href: string;
    } => Boolean(card),
  );

  return (
    <main className={styles.shell}>
      <div className={styles.layoutGrid}>
        <aside className={styles.sideRail}>
          <AppMenu
            active="dashboard"
            canCreateProject={canCreateProject}
            canViewQualityCenter={canViewQualityCenter}
            canUseFieldConsole={canUseFieldConsole}
            userName={session.name}
            roleLabel={getRoleLabel(session.role)}
          />
        </aside>

        <div className={styles.mainColumn}>
          <header className={styles.topbar}>
            <div className={styles.brandBlock}>
              <div className={styles.brandMark}>
                <Image
                  src="/logo.png"
                  alt="Хот тохижилтын удирдлагын төвийн лого"
                  width={180}
                  height={56}
                  className={styles.brandLogo}
                  priority
                  unoptimized
                />
              </div>

              <div>
                <span className={styles.kicker}>Нэгдсэн хяналт</span>
                <h1>Хот тохижилтын нэгдсэн хяналтын самбар</h1>
              </div>
            </div>

            <div className={styles.topbarActions}>
              <div className={styles.userPanel}>
                <span>{getRoleLabel(session.role)}</span>
                <strong>{session.name}</strong>
                <small>Сүүлд шинэчлэгдсэн: {snapshot.generatedAt}</small>
              </div>

              <form action={logoutAction}>
                <button type="submit" className={styles.logoutButton}>
                  Гарах
                </button>
              </form>
            </div>
          </header>

          {snapshot.source === "demo" ? (
            <section className={styles.sourceNotice}>
              <div>
                <strong>Odoo-оос бүх өгөгдөл бүрэн ирээгүй байна.</strong>
                <p>Түр нөөц мэдээлэл харуулж байгаа тул ажилбар, тайлангийн холбоосыг дахин шалгана уу.</p>
              </div>
              <Link href="/data-download" className={styles.sectionLink}>
                Өгөгдөл шалгах
              </Link>
            </section>
          ) : null}

          <section className={styles.departmentsSection}>
            <div className={styles.sectionHeader}>
              <div>
                <span className={styles.kicker}>Алба нэгжүүд</span>
                <h2>Алба нэгжийн товч зураглал</h2>
              </div>
            </div>

            <div className={styles.departmentGrid}>
              {departmentCards.map((department) => (
                <article key={department.name} className={styles.departmentCard}>
                  <Link
                    href={department.href}
                    className={styles.departmentCardLink}
                  >
                    <span
                      className={styles.departmentAccent}
                      style={{ background: department.accent }}
                    />

                    <div className={styles.departmentBody}>
                      <div className={styles.departmentTitleRow}>
                        <span className={styles.departmentCardIcon} aria-hidden>
                          {department.icon}
                        </span>
                        <h3>{department.name}</h3>
                      </div>

                      <p>{department.label}</p>

                      <div className={styles.departmentMeta}>
                        <div>
                          <span>Нээлттэй ажилбар</span>
                          <strong>{department.openTasks}</strong>
                        </div>
                        <div>
                          <span>Шалгалт</span>
                          <strong>{department.reviewTasks}</strong>
                        </div>
                        <div>
                          <span>Гүйцэтгэл</span>
                          <strong>{department.completion}%</strong>
                        </div>
                      </div>

                      <div className={styles.cardFooter}>
                        <span className={styles.cardLinkLabel}>Самбарыг нээх</span>
                        <strong aria-hidden>→</strong>
                      </div>
                    </div>
                  </Link>
                </article>
              ))}
            </div>
          </section>

          <section className={styles.commandStrip}>
            {snapshot.metrics.map((metric) => (
              <MetricCard key={metric.label} {...metric} />
            ))}
          </section>

          <section className={styles.metricsGrid}>
            {snapshot.qualityMetrics.map((metric) => (
              <article
                key={metric.label}
                className={`${styles.metricCard} ${styles[`tone${metric.tone}`]}`}
              >
                <p>{metric.label}</p>
                <strong>{metric.value}</strong>
                <span>{metric.note}</span>
              </article>
            ))}
          </section>

          <section className={styles.projectsSection}>
            <div className={styles.sectionHeader}>
              <div>
                <span className={styles.kicker}>Өнөөдрийн урсгал</span>
                <h2>Идэвхтэй ажилбар</h2>
              </div>
              <Link href="/tasks" className={styles.sectionLink}>
                Бүгдийг харах
              </Link>
            </div>

            {activeTasks.length ? (
              <div className={styles.taskList}>
                {activeTasks.map((task) => (
                  <Link key={task.id} href={task.href} className={styles.taskCard}>
                    <div className={styles.taskCardTop}>
                      <span>{task.deadline}</span>
                      <StagePill label={task.stageLabel} bucket={task.stageBucket} />
                    </div>

                    <h3>{task.name}</h3>
                    <p>{task.projectName}</p>

                    <div className={styles.taskStats}>
                      <span>Ахлагч: {task.leaderName}</span>
                      <span>Төлөв: {task.priorityLabel}</span>
                      <span>
                        Үлдэгдэл: {task.remainingQuantity} {task.measurementUnit}
                      </span>
                    </div>

                    <div className={styles.taskQuantities}>
                      <b>
                        {task.completedQuantity} / {task.plannedQuantity} {task.measurementUnit}
                      </b>
                      <strong>{task.progress}%</strong>
                    </div>

                    <div className={styles.progressTrack}>
                      <span style={{ width: `${task.progress}%` }} />
                    </div>

                    <div className={styles.cardFooter}>
                      <span className={styles.cardLinkLabel}>Ажилбарыг нээх</span>
                      <strong aria-hidden>→</strong>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className={styles.emptyColumnState}>Одоогоор идэвхтэй ажилбар олдсонгүй.</div>
            )}
          </section>

          <section className={styles.dualGrid}>
            <section className={styles.panel}>
              <div className={styles.sectionHeader}>
                <div>
                  <span className={styles.kicker}>Хяналт</span>
                  <h2>Хяналтын мөр</h2>
                </div>
                <Link href="/review" className={styles.sectionLink}>
                  Мөрийг нээх
                </Link>
              </div>

              {reviewQueue.length ? (
                <div className={styles.reviewList}>
                  {reviewQueue.map((task) => (
                    <Link key={task.id} href={task.href} className={styles.reviewItem}>
                      <div>
                        <h3>{task.name}</h3>
                        <p>
                          {task.departmentName} / {task.projectName}
                        </p>
                      </div>

                      <div className={styles.reviewMeta}>
                        <strong>{task.progress}%</strong>
                        <span>{task.stageLabel}</span>
                        <span>{task.deadline}</span>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className={styles.emptyColumnState}>Одоогоор хяналт хүлээж буй ажилбар алга.</div>
              )}
            </section>

            <section className={styles.panel}>
              <div className={styles.sectionHeader}>
                <div>
                  <span className={styles.kicker}>Анхаарах зүйлс</span>
                  <h2>Чанарын анхааруулга</h2>
                </div>
                <Link href="/quality" className={styles.sectionLink}>
                  Чанар руу орох
                </Link>
              </div>

              {qualityAlerts.length ? (
                <div className={styles.reviewList}>
                  {qualityAlerts.map((alert) => (
                    <Link key={alert.id} href={alert.href} className={styles.reviewItem}>
                      <div>
                        <h3>{alert.name}</h3>
                        <p>
                          {alert.departmentName} / {alert.routeName}
                        </p>
                      </div>

                      <div className={styles.reviewMeta}>
                        <strong>{alert.exceptionCount}</strong>
                        <span>{alert.operationTypeLabel}</span>
                        <span>{alert.hasWeightWarning ? "Жингийн синк шалгана" : "Чанарын мөр"}</span>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className={styles.emptyColumnState}>Одоогоор чанарын анхааруулга алга.</div>
              )}
            </section>
          </section>

          <section className={styles.dualGrid}>
            <section className={styles.panel}>
              <div className={styles.sectionHeader}>
                <div>
                  <span className={styles.kicker}>Тайлан</span>
                  <h2>Сүүлийн тайлангууд</h2>
                </div>
                <Link href="/reports" className={styles.sectionLink}>
                  Тайлан руу орох
                </Link>
              </div>

              {recentReports.length ? (
                <div className={styles.reportFeed}>
                  {recentReports.map((report) => (
                    <article key={report.id} className={styles.reportCard}>
                      <div className={styles.reportTop}>
                        <div>
                          <strong>{report.reporter}</strong>
                          <h3>{report.taskName}</h3>
                        </div>
                        <span>{report.submittedAt}</span>
                      </div>

                      <p>{report.departmentName}</p>

                      <div className={styles.reportMeta}>
                        <span>Тоо хэмжээ: {report.reportedQuantity}</span>
                        <span>Зураг: {report.imageCount}</span>
                        <span>Аудио: {report.audioCount}</span>
                      </div>

                      <p className={styles.reportSummary}>{report.summary}</p>
                    </article>
                  ))}
                </div>
              ) : (
                <div className={styles.emptyColumnState}>
                  Одоогоор сүүлийн тайлангийн бүртгэл харагдахгүй байна.
                </div>
              )}
            </section>

            <section className={styles.panel}>
              <div className={styles.sectionHeader}>
                <div>
                  <span className={styles.kicker}>Ажил</span>
                  <h2>Сүүлийн ажлууд</h2>
                </div>
                <Link href="/projects" className={styles.sectionLink}>
                  Ажил руу орох
                </Link>
              </div>

              <div className={styles.projectRail}>
                {featuredProjects.map((project) => (
                  <Link key={project.id} href={project.href} className={styles.projectCard}>
                    <div className={styles.projectCardTop}>
                      <span>{project.deadline}</span>
                      <StagePill label={project.stageLabel} bucket={project.stageBucket} />
                    </div>

                    <h3>{project.name}</h3>
                    <p>
                      {project.departmentName} / Менежер: {project.manager}
                    </p>

                    <div className={styles.projectMeta}>
                      <div>
                        <span>Нээлттэй ажилбар</span>
                        <strong>{project.openTasks}</strong>
                      </div>
                      <div>
                        <span>Гүйцэтгэл</span>
                        <strong>{project.completion}%</strong>
                      </div>
                    </div>

                    <div className={styles.progressTrack}>
                      <span style={{ width: `${project.completion}%` }} />
                    </div>

                    <div className={styles.cardFooter}>
                      <span className={styles.cardLinkLabel}>Ажлыг нээх</span>
                      <strong aria-hidden>→</strong>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          </section>

          <section className={styles.projectsSection}>
            <div className={styles.sectionHeader}>
              <div>
                <span className={styles.kicker}>Шуурхай гарц</span>
                <h2>Ерөнхий менежерийн гол урсгал</h2>
              </div>
              <p>Өдөр тутмын шийдвэр гаргалтад хамгийн хэрэгтэй хуудсууд.</p>
            </div>

            <div className={styles.quickActions}>
              <Link href="/tasks?filter=problem" className={styles.quickAction}>
                <span>Асуудалтай ажилбар</span>
                <strong>{qualityAlerts.length}</strong>
                <small>Шуурхай анхаарах шаардлагатай ажилбарууд</small>
              </Link>
              <Link href="/review" className={styles.quickAction}>
                <span>Шалгалтын мөр</span>
                <strong>{reviewQueue.length}</strong>
                <small>Хяналт хүлээж буй ажилбарууд</small>
              </Link>
              <Link href="/reports" className={styles.quickAction}>
                <span>Тайлангийн урсгал</span>
                <strong>{recentReports.length}</strong>
                <small>Өдөр тутмын тайлан, зураг, дууны бүртгэл</small>
              </Link>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
