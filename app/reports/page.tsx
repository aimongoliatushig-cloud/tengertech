import Image from "next/image";
import Link from "next/link";

import { AppMenu } from "@/app/_components/app-menu";
import { logoutAction } from "@/app/actions";
import dashboardStyles from "@/app/page.module.css";
import shellStyles from "@/app/workspace.module.css";
import { getRoleLabel, hasCapability, requireSession } from "@/lib/auth";
import { loadMunicipalSnapshot } from "@/lib/odoo";

import styles from "./reports.module.css";

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

  const canCreateProject = hasCapability(session, "create_projects");
  const canViewQualityCenter = hasCapability(session, "view_quality_center");
  const canUseFieldConsole = hasCapability(session, "use_field_console");

  return (
    <main className={shellStyles.shell}>
      <div className={shellStyles.container} id="reports-top">
        <header className={styles.pageHeader}>
          <div className={styles.titleBlock}>
            <span className={styles.kicker}>Тайлан</span>
            <h1>Тайлан ба баталгаажуулалт</h1>
            <p>
              Шалгалт хүлээж буй ажил, талбайгаас ирсэн тайлан, багийн ахлагчдын гүйцэтгэлийг
              нэг урсгалаар цэгцтэй харуулна.
            </p>
          </div>

          <div className={styles.pageAside}>
            <div className={styles.dateMeta}>
              <span>Сүүлд шинэчлэгдсэн</span>
              <strong>{snapshot.generatedAt}</strong>
              <small>{getRoleLabel(session.role)}</small>
            </div>

            <div className={styles.userCard}>
              <span>Хэрэглэгч</span>
              <strong>{session.name}</strong>
            </div>

            <form action={logoutAction}>
              <button type="submit" className={shellStyles.secondaryButton}>
                Гарах
              </button>
            </form>
          </div>
        </header>

        <AppMenu
          active="reports"
          canCreateProject={canCreateProject}
          canViewQualityCenter={canViewQualityCenter}
          canUseFieldConsole={canUseFieldConsole}
          variant={session.role === "general_manager" ? "executive" : "default"}
          userName={session.name}
          roleLabel={getRoleLabel(session.role)}
        />

        <section className={styles.summaryStrip}>
          <article className={styles.summaryCard}>
            <span>Шалгалтын мөр</span>
            <strong>{snapshot.reviewQueue.length}</strong>
            <small>Хүлээгдэж буй ажил</small>
          </article>
          <article className={styles.summaryCard}>
            <span>Орсон тайлан</span>
            <strong>{snapshot.reports.length}</strong>
            <small>Сүүлийн тайлангийн урсгал</small>
          </article>
          <article className={styles.summaryCard}>
            <span>Багийн ахлагч</span>
            <strong>{snapshot.teamLeaders.length}</strong>
            <small>Идэвхтэй ахлагч</small>
          </article>
        </section>

        <section className={styles.pageGrid}>
          <div className={styles.mainColumn}>
            <section className={styles.sectionCard}>
              <div className={styles.sectionHead}>
                <div>
                  <span className={styles.kicker}>Шуурхай шийдэх</span>
                  <h2>Шалгалт хүлээж буй ажил</h2>
                </div>
                <p>Нэн түрүүнд шийдэх ажлуудыг дээд хэсэгт төвлөрүүлэв.</p>
              </div>

              {snapshot.reviewQueue.length ? (
                <div className={styles.reviewList}>
                  {snapshot.reviewQueue.map((item) => (
                    <Link key={item.id} href={item.href} className={styles.reviewCard}>
                      <div className={styles.reviewTop}>
                        <div>
                          <strong>{item.name}</strong>
                          <p>{item.projectName}</p>
                        </div>
                        <StagePill label={item.stageLabel} bucket="review" />
                      </div>

                      <div className={styles.reviewMeta}>
                        <span>Явц {item.progress}%</span>
                        <span>Хугацаа {item.deadline}</span>
                        <span>Багийн ахлагч {item.leaderName}</span>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className={styles.emptyState}>
                  <h2>Шалгалт хүлээж буй ажил алга</h2>
                  <p>Одоогоор баталгаажуулалт хүлээж буй ажил бүртгэгдээгүй байна.</p>
                </div>
              )}
            </section>

            <section className={styles.sectionCard}>
              <div className={styles.sectionHead}>
                <div>
                  <span className={styles.kicker}>Тайлангийн урсгал</span>
                  <h2>Сүүлийн тайлангууд</h2>
                </div>
                <p>Зураг, аудио, гол тайлбарыг нэг card дээр харагдуулна.</p>
              </div>

              {snapshot.reports.length ? (
                <div className={styles.reportList}>
                  {snapshot.reports.map((report) => (
                    <article key={report.id} className={styles.reportCard}>
                      <div className={styles.reportTop}>
                        <div>
                          <strong>{report.taskName}</strong>
                          <p>
                            {report.projectName} / {report.reporter}
                          </p>
                        </div>
                        <StagePill label={report.submittedAt} bucket="progress" />
                      </div>

                      <div className={styles.reportMeta}>
                        <span>{report.reportedQuantity} нэгж</span>
                        <span>{report.imageCount} зураг</span>
                        <span>{report.audioCount} аудио</span>
                      </div>

                      <p>{report.summary}</p>

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
                  <p>Одоогоор тайлангийн урсгал хоосон байна.</p>
                </div>
              )}
            </section>
          </div>

          <aside className={styles.sideColumn}>
            <section className={styles.sectionCard}>
              <div className={styles.sectionHead}>
                <div>
                  <span className={styles.kicker}>Багийн зураглал</span>
                  <h2>Багийн ахлагчдын товч үзүүлэлт</h2>
                </div>
              </div>

              {snapshot.teamLeaders.length ? (
                <div className={styles.leaderGrid}>
                  {snapshot.teamLeaders.map((leader) => (
                    <article key={leader.name} className={styles.leaderCard}>
                      <strong>{leader.name}</strong>
                      <div className={styles.leaderMeta}>
                        <span>Идэвхтэй {leader.activeTasks}</span>
                        <span>Шалгалт {leader.reviewTasks}</span>
                        <span>Баг {leader.squadSize}</span>
                        <span>Гүйцэтгэл {leader.averageCompletion}%</span>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className={styles.emptyState}>
                  <h2>Ахлагчийн мэдээлэл алга</h2>
                  <p>Тайлан орж ирэх үед энд багийн ахлагчдын зураглал гарна.</p>
                </div>
              )}
            </section>

            <section className={styles.sectionCard}>
              <div className={styles.sectionHead}>
                <div>
                  <span className={styles.kicker}>Шуурхай холбоос</span>
                  <h2>Дараагийн алхам</h2>
                </div>
              </div>

              <Link href="/" className={styles.pillLink}>
                Хяналтын самбар руу очих
              </Link>
              <Link href="/tasks" className={styles.pillLink}>
                Өнөөдрийн ажил харах
              </Link>
              <a href="#reports-top" className={styles.pillLink}>
                Дээш буцах
              </a>
            </section>
          </aside>
        </section>

        <nav className={shellStyles.mobileDock} aria-label="Тайлангийн гар утасны хурдан цэс">
          <Link href="/" className={shellStyles.jumpLink}>
            Нүүр
          </Link>
          <a href="#reports-top" className={shellStyles.jumpLink}>
            Дээш
          </a>
          <Link href="/tasks" className={shellStyles.jumpLink}>
            Ажил
          </Link>
        </nav>
      </div>
    </main>
  );
}
