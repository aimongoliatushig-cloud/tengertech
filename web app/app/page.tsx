import Image from "next/image";
import Link from "next/link";

import { AppMenu } from "@/app/_components/app-menu";
import { logoutAction } from "@/app/actions";
import { getRoleLabel, hasCapability, requireSession } from "@/lib/auth";
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

  const featuredProjects = snapshot.projects.slice(0, 6);
  const reviewQueue = snapshot.reviewQueue.slice(0, 5);
  const qualityAlerts = snapshot.qualityAlerts.slice(0, 5);
  const recentReports = snapshot.reports.slice(0, 4);
  const teamLeaders = snapshot.teamLeaders.slice(0, 4);

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

          <section className={styles.departmentsSection}>
            <div className={styles.sectionHeader}>
              <div>
                <span className={styles.kicker}>Алба нэгжүүд</span>
                <h2>Алба нэгжийн товч зураглал</h2>
              </div>
            </div>

            <div className={styles.departmentGrid}>
              {snapshot.departments.map((department) => (
                <article key={department.name} className={styles.departmentCard}>
                  <Link
                    href={`/projects?department=${encodeURIComponent(department.name)}`}
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
                          <span>Нээлттэй</span>
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

          <section className={styles.dualGrid}>
            <section className={styles.panel}>
              <div className={styles.sectionHeader}>
                <div>
                  <span className={styles.kicker}>Шалгалт</span>
                  <h2>Шалгалтын мөр</h2>
                </div>
                <p>Баталгаажуулалт хүлээж буй ажлуудыг priority дарааллаар харуулна.</p>
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
                <div className={styles.emptyColumnState}>
                  Одоогоор шалгалт хүлээж буй ажил алга.
                </div>
              )}
            </section>

            <section className={styles.panel}>
              <div className={styles.sectionHeader}>
                <div>
                  <span className={styles.kicker}>Анхаарах зүйлс</span>
                  <h2>Чанарын анхааруулга</h2>
                </div>
                <p>Зураг, маршрут, синк, нээлттэй цэгтэй холбоотой асуудлууд.</p>
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
                        <span>
                          {alert.hasWeightWarning
                            ? "Жингийн синк шалгана"
                            : "Чанарын мөр"}
                        </span>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className={styles.emptyColumnState}>
                  Одоогоор чанарын анхааруулга алга.
                </div>
              )}
            </section>
          </section>

          <section className={styles.projectsSection}>
            <div className={styles.sectionHeader}>
              <div>
                <span className={styles.kicker}>Төслүүд</span>
                <h2>Сүүлийн төслүүд</h2>
              </div>
              <p>Бүх алба нэгжийн хамгийн идэвхтэй төслүүдийг эндээс нээнэ.</p>
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
                      <span>Нээлттэй ажил</span>
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
                    <span className={styles.cardLinkLabel}>Төслийг нээх</span>
                    <strong aria-hidden>→</strong>
                  </div>
                </Link>
              ))}
            </div>
          </section>

          <section className={styles.dualGrid}>
            <section className={styles.panel}>
              <div className={styles.sectionHeader}>
                <div>
                  <span className={styles.kicker}>Тайлан</span>
                  <h2>Сүүлийн тайлангууд</h2>
                </div>
                <p>Талбараас ирсэн хамгийн сүүлийн тайлангийн урсгалыг харуулна.</p>
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
                      <p className={styles.reportSummary}>
                        {report.summary}
                      </p>
                    </article>
                  ))}
                </div>
              ) : (
                <div className={styles.emptyColumnState}>
                  Одоогоор сүүлийн тайлангийн бүртгэл алга.
                </div>
              )}
            </section>

            <section className={styles.panel}>
              <div className={styles.sectionHeader}>
                <div>
                  <span className={styles.kicker}>Ахлагчид</span>
                  <h2>Багийн ахлагчдын зураглал</h2>
                </div>
                <p>Хэн дээр ачаалал төвлөрснийг хурдан харахад зориулав.</p>
              </div>

              {teamLeaders.length ? (
                <div className={styles.leaderGrid}>
                  {teamLeaders.map((leader) => (
                    <article key={leader.name} className={styles.leaderCard}>
                      <div className={styles.leaderBadge} aria-hidden>
                        {leader.name.charAt(0)}
                      </div>

                      <div className={styles.leaderContent}>
                        <h3>{leader.name}</h3>
                        <p>
                          {leader.activeTasks} идэвхтэй ажил, {leader.reviewTasks} шалгалтын
                          мөр
                        </p>
                        <div className={styles.leaderMeta}>
                          <strong>{leader.averageCompletion}%</strong>
                          <span>{leader.squadSize} хүний бүрэлдэхүүн</span>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className={styles.emptyColumnState}>
                  Одоогоор ахлагчийн нэгтгэсэн зураглал алга.
                </div>
              )}
            </section>
          </section>
        </div>
      </div>
    </main>
  );
}
