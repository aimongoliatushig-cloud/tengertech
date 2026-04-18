import Image from "next/image";
import Link from "next/link";

import { AppMenu } from "@/app/_components/app-menu";
import { logoutAction } from "@/app/actions";
import dashboardStyles from "@/app/page.module.css";
import styles from "@/app/workspace.module.css";
import { getRoleLabel, requireSession } from "@/lib/auth";
import { loadMunicipalSnapshot } from "@/lib/odoo";

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

export default async function ReportsPage() {
  const session = await requireSession();
  const snapshot = await loadMunicipalSnapshot({
    login: session.login,
    password: session.password,
  });

  const canCreateProject =
    session.role === "general_manager" || session.role === "system_admin";

  return (
    <main className={styles.shell}>
      <div className={styles.container} id="reports-top">
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

        <AppMenu active="reports" canCreateProject={canCreateProject} />

        <section className={styles.heroCard}>
          <span className={styles.eyebrow}>Тайлан ба баталгаажуулалт</span>
          <h1>Шалгалтын дараалал ба proof of work</h1>
          <p>
            Ерөнхий менежер, төслийн удирдагч, багийн ахлагчийн review урсгал,
            тайлангийн feed, proof of work мэдээлэл энд төвлөрнө.
          </p>

          <div className={styles.statsGrid}>
            <article className={styles.statCard}>
              <span>Шалгалтын мөр</span>
              <strong>{snapshot.reviewQueue.length}</strong>
            </article>
            <article className={styles.statCard}>
              <span>Тайлангийн мөр</span>
              <strong>{snapshot.reports.length}</strong>
            </article>
            <article className={styles.statCard}>
              <span>Идэвхтэй багийн ахлагч</span>
              <strong>{snapshot.teamLeaders.length}</strong>
            </article>
            <article className={styles.statCard}>
              <span>Сүүлийн sync</span>
              <strong>{snapshot.generatedAt}</strong>
            </article>
          </div>
        </section>

        <section className={styles.panelGrid}>
          <section className={styles.panel}>
            <div className={styles.sectionHeader}>
              <div>
                <span className={styles.eyebrow}>Review queue</span>
                <h2>Шалгалт хүлээж буй ажил</h2>
              </div>
              <p>Task дээр дарж workflow болон тайланг нь дотроос нь нээнэ.</p>
            </div>

            {snapshot.reviewQueue.length ? (
              <div className={dashboardStyles.reviewList}>
                {snapshot.reviewQueue.map((item) => (
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
              <div className={styles.emptyState}>
                <h2>Шалгалтын мөр хоосон</h2>
                <p>Одоогоор баталгаажуулалт хүлээж буй ажил байхгүй байна.</p>
              </div>
            )}
          </section>

          <section className={styles.panel}>
            <div className={styles.sectionHeader}>
              <div>
                <span className={styles.eyebrow}>Reports feed</span>
                <h2>Тайлангийн урсгал</h2>
              </div>
              <p>Field report-оос орж ирсэн хамгийн сүүлийн мөрүүд.</p>
            </div>

            {snapshot.reports.length ? (
              <div className={dashboardStyles.reportFeed}>
                {snapshot.reports.map((report) => (
                  <article key={report.id} className={dashboardStyles.reportCard}>
                    <div className={dashboardStyles.reportTop}>
                      <div>
                        <h3>{report.taskName}</h3>
                        <p>
                          {report.projectName} • {report.reporter}
                        </p>
                      </div>
                      <strong>{report.submittedAt}</strong>
                    </div>
                    <div className={dashboardStyles.reportMeta}>
                      <span>{report.reportedQuantity} нэгж</span>
                      <span>{report.imageCount} зураг</span>
                      <span>{report.audioCount} аудио</span>
                    </div>
                    <p className={dashboardStyles.reportSummary}>{report.summary}</p>

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
                              alt={`${report.taskName} - ${image.name}`}
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
                <p>Одоогоор тайлангийн feed хоосон байна.</p>
              </div>
            )}
          </section>
        </section>

        <section className={styles.panel} style={{ marginTop: 22 }}>
          <div className={styles.sectionHeader}>
            <div>
              <span className={styles.eyebrow}>Team leaders</span>
              <h2>Багийн ахлагчдын товч зураглал</h2>
            </div>
          </div>

          {snapshot.teamLeaders.length ? (
            <div className={dashboardStyles.leaderGrid}>
              {snapshot.teamLeaders.map((leader) => (
                <article key={leader.name} className={dashboardStyles.leaderCard}>
                  <div className={dashboardStyles.leaderBadge}>
                    {leader.name.slice(0, 1).toUpperCase()}
                  </div>
                  <div className={dashboardStyles.leaderContent}>
                    <h3>{leader.name}</h3>
                    <div className={dashboardStyles.leaderMeta}>
                      <span>Идэвхтэй {leader.activeTasks}</span>
                      <span>Review {leader.reviewTasks}</span>
                      <span>Баг {leader.squadSize}</span>
                      <strong>{leader.averageCompletion}%</strong>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className={styles.emptyState}>
              <h2>Багийн ахлагчийн өгөгдөл алга</h2>
              <p>Тайлан орж ирэх үед энд ахлагчдын summary харагдана.</p>
            </div>
          )}
        </section>

        <nav className={styles.mobileDock} aria-label="Reports mobile quick navigation">
          <Link href="/" className={styles.jumpLink}>
            Нүүр
          </Link>
          <a href="#reports-top" className={styles.jumpLink}>
            Дээш
          </a>
          <Link href="/projects" className={styles.jumpLink}>
            Төсөл
          </Link>
        </nav>
      </div>
    </main>
  );
}
