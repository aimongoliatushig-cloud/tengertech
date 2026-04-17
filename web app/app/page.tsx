import Link from "next/link";

import { logoutAction } from "@/app/actions";
import { getRoleLabel, requireSession } from "@/lib/auth";
import { loadMunicipalSnapshot } from "@/lib/odoo";

import styles from "./page.module.css";

export const dynamic = "force-dynamic";

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
    <article className={`${styles.metricCard} ${styles[`tone${tone}`]}`}>
      <p>{label}</p>
      <strong>{value}</strong>
      <span>{note}</span>
    </article>
  );
}

function StagePill({ label, bucket }: { label: string; bucket: string }) {
  const stageTone =
    bucket === "done"
      ? styles.stageDone
      : bucket === "review"
        ? styles.stageReview
        : bucket === "progress"
          ? styles.stageProgress
          : styles.stageTodo;

  return <span className={`${styles.stagePill} ${stageTone}`}>{label}</span>;
}

export default async function Home() {
  const session = await requireSession();
  const snapshot = await loadMunicipalSnapshot({
    login: session.login,
    password: session.password,
  });
  const canCreateProject =
    session.role === "general_manager" || session.role === "system_admin";

  return (
    <main className={styles.shell}>
      <header className={styles.topbar}>
        <div className={styles.brandBlock}>
          <span className={styles.brandBadge}>MOP</span>
          <div>
            <p className={styles.kicker}>Municipal Operations Platform</p>
            <h1>Хот тохижилтын удирдлагын төв</h1>
          </div>
        </div>

        <div className={styles.topbarActions}>
          {canCreateProject ? (
            <Link href="/projects/new" className={styles.logoutButton}>
              Шинэ төсөл
            </Link>
          ) : null}

          <div className={styles.userPanel}>
            <span>{getRoleLabel(session.role)}</span>
            <strong>{session.name}</strong>
            <small>{session.login}</small>
          </div>

          <form action={logoutAction}>
            <button type="submit" className={styles.logoutButton}>
              Гарах
            </button>
          </form>
        </div>
      </header>

      <section className={styles.hero}>
        <div className={styles.heroCopy}>
          <span className={styles.eyebrow}>
            {snapshot.source === "live" ? "Live Odoo Sync" : "Demo Fallback"}
          </span>
          <h2>Хот тохижилтын удирдлагын төв</h2>
          <p>
            Odoo ERP-ийн project, task, field report, team leader мэдээллийг нэг
            дэлгэц дээр нэгтгээд ерөнхий менежер, төслийн удирдагч, багийн ахлагч
            нарт зориулсан ажиллагааны зураглалыг үзүүлнэ.
          </p>
          <div className={styles.heroActions}>
            <Link className={styles.primaryAction} href="#projects">
              Төслийн самбар
            </Link>
            <Link className={styles.secondaryAction} href="#review">
              Шалгалтын дараалал
            </Link>
          </div>
        </div>

        <aside className={styles.syncPanel}>
          <div className={styles.syncTopline}>
            <span className={styles.syncDot} />
            <p>Сүүлд шинэчилсэн</p>
          </div>
          <strong>{snapshot.generatedAt}</strong>
          <ul className={styles.syncFacts}>
            <li>
              <span>Эх үүсвэр</span>
              <b>{snapshot.source === "live" ? "Odoo 19 JSON-RPC" : "Demo snapshot"}</b>
            </li>
            <li>
              <span>Нийт task</span>
              <b>{snapshot.totalTasks}</b>
            </li>
            <li>
              <span>Backend</span>
              <b>Odoo service</b>
            </li>
          </ul>
        </aside>
      </section>

      <section className={styles.metricsGrid}>
        {snapshot.metrics.map((metric) => (
          <MetricCard key={metric.label} {...metric} />
        ))}
      </section>

      <section className={styles.projectsSection} id="projects">
        <div className={styles.sectionHeader}>
          <div>
            <span className={styles.kicker}>Төслийн хяналт</span>
            <h2>Идэвхтэй кампанит ажил</h2>
          </div>
          <p>Ерөнхий менежерийн түвшний priority, хугацаа, гүйцэтгэлийн зураглал.</p>
        </div>
        <div className={styles.projectRail}>
          {snapshot.projects.map((project) => (
            <Link key={project.id} className={styles.projectCard} href={project.href}>
              <div className={styles.projectCardTop}>
                <StagePill label={project.stageLabel} bucket={project.stageBucket} />
                <span>{project.deadline}</span>
              </div>
              <h3>{project.name}</h3>
              <p>Алба нэгж: {project.departmentName}</p>
              <p>Менежер: {project.manager}</p>
              <div className={styles.projectMeta}>
                <div>
                  <span>Нээлттэй task</span>
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
            </Link>
          ))}
        </div>
      </section>

      <section className={styles.dualGrid}>
        <div className={styles.panel} id="review">
          <div className={styles.sectionHeader}>
            <div>
              <span className={styles.kicker}>Амьд ажиллагаа</span>
              <h2>Талбар дээр явагдаж буй ажил</h2>
            </div>
            <p>Багийн ахлагчийн түвшнээс харагддаг active workload.</p>
          </div>
          <div className={styles.taskList}>
            {snapshot.liveTasks.map((task) => (
              <Link key={task.id} className={styles.taskCard} href={task.href}>
                <div className={styles.taskCardTop}>
                  <div>
                    <h3>{task.name}</h3>
                    <p>{task.projectName}</p>
                  </div>
                  <StagePill label={task.stageLabel} bucket={task.stageBucket} />
                </div>
                <div className={styles.taskStats}>
                  <span>Ахлагч: {task.leaderName}</span>
                  <span>Priority: {task.priorityLabel}</span>
                  <span>Deadline: {task.deadline}</span>
                </div>
                <div className={styles.taskQuantities}>
                  <b>
                    {task.completedQuantity}/{task.plannedQuantity} {task.measurementUnit}
                  </b>
                  <span>
                    Үлдэгдэл: {task.remainingQuantity} {task.measurementUnit}
                  </span>
                </div>
                <div className={styles.progressTrack}>
                  <span style={{ width: `${task.progress}%` }} />
                </div>
              </Link>
            ))}
          </div>
        </div>

        <div className={styles.panel}>
          <div className={styles.sectionHeader}>
            <div>
              <span className={styles.kicker}>Review Queue</span>
              <h2>Ерөнхий менежерийн шалгалт</h2>
            </div>
            <p>`Шалгалтад илгээх` дарсан ажил энд төвлөрч орж ирнэ.</p>
          </div>
          <div className={styles.reviewList}>
            {snapshot.reviewQueue.map((item) => (
              <Link key={item.id} className={styles.reviewItem} href={item.href}>
                <div>
                  <h3>{item.name}</h3>
                  <p>
                    {item.projectName} - {item.leaderName}
                  </p>
                </div>
                <div className={styles.reviewMeta}>
                  <StagePill label={item.stageLabel} bucket="review" />
                  <strong>{item.progress}%</strong>
                  <span>{item.deadline}</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className={styles.departmentsSection}>
        <div className={styles.sectionHeader}>
          <div>
            <span className={styles.kicker}>Хэлтсийн ачаалал</span>
            <h2>5 үндсэн нэгжийн зураглал</h2>
          </div>
          <p>Танай байгууллагын operational department-уудаар live workload-ийг харуулна.</p>
        </div>
        <div className={styles.departmentGrid}>
          {snapshot.departments.map((department) => (
            <article key={department.name} className={styles.departmentCard}>
              <span
                className={styles.departmentAccent}
                style={{ background: department.accent }}
              />
              <div className={styles.departmentBody}>
                <h3>{department.name}</h3>
                <p>{department.label}</p>
                <div className={styles.departmentMeta}>
                  <span>{department.openTasks} нээлттэй</span>
                  <span>{department.reviewTasks} review</span>
                  <strong>{department.completion}%</strong>
                </div>
                <div className={styles.progressTrack}>
                  <span style={{ width: `${department.completion}%` }} />
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className={styles.dualGrid}>
        <div className={styles.panel}>
          <div className={styles.sectionHeader}>
            <div>
              <span className={styles.kicker}>Багийн ахлагч</span>
              <h2>Гүйцэтгэлийн жижиг cockpit</h2>
            </div>
            <p>Team leader сонгогдоход ямар squad, ямар backlog-той явж байгааг харуулна.</p>
          </div>
          <div className={styles.leaderGrid}>
            {snapshot.teamLeaders.map((leader) => (
              <article key={leader.name} className={styles.leaderCard}>
                <div className={styles.leaderBadge}>{leader.name.slice(0, 1).toUpperCase()}</div>
                <div className={styles.leaderContent}>
                  <h3>{leader.name}</h3>
                  <p>{leader.squadSize} ажилтан бүхий баг</p>
                  <div className={styles.leaderMeta}>
                    <span>{leader.activeTasks} active</span>
                    <span>{leader.reviewTasks} review</span>
                    <strong>{leader.averageCompletion}%</strong>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>

        <div className={styles.panel}>
          <div className={styles.sectionHeader}>
            <div>
              <span className={styles.kicker}>Proof Of Work</span>
              <h2>Сүүлийн field report feed</h2>
            </div>
            <p>Зураг, аудио, текст тайлангийн сүүлийн урсгал.</p>
          </div>
          <div className={styles.reportFeed}>
            {snapshot.reports.map((report) => (
              <article key={report.id} className={styles.reportCard}>
                <div className={styles.reportTop}>
                  <div>
                    <h3>{report.taskName}</h3>
                    <p>
                      {report.projectName} - {report.reporter}
                    </p>
                  </div>
                  <strong>{report.submittedAt}</strong>
                </div>
                <p className={styles.reportSummary}>{report.summary}</p>
                <div className={styles.reportMeta}>
                  <span>{report.reportedQuantity} нэгж</span>
                  <span>{report.imageCount} зураг</span>
                  <span>{report.audioCount} аудио</span>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
