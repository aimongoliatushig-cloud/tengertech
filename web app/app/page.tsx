import Image from "next/image";
import Link from "next/link";

import { AppMenu } from "@/app/_components/app-menu";
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
          <div className={styles.brandMark}>
            <Image
              src="/logo.png"
              alt="Хан-Уул дүүргийн тохижилт үйлчилгээний төв онөаатүг лого"
              width={180}
              height={60}
              className={styles.brandLogo}
              priority
              unoptimized
            />
          </div>
          <div>
            <p className={styles.kicker}>Municipal Operations Platform</p>
            <h1>Хот тохижилтын удирдлагын төв</h1>
          </div>
        </div>

        <div className={styles.topbarActions}>
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

      <AppMenu active="dashboard" canCreateProject={canCreateProject} />

      <section className={styles.hero}>
        <div className={styles.heroCopy}>
          <span className={styles.eyebrow}>
            {snapshot.source === "live" ? "Live Odoo Sync" : "Demo Fallback"}
          </span>
          <h2>Хяналтын самбар</h2>
          <p>
            Энэ нүүр дээр зөвхөн ерөнхий dashboard харагдана. Төсөл нэмэх, төсөл
            хянах, шалгах ажлууд, тайлан харах үйлдлүүдийг дээд menu-гээс тус тусад нь нээнэ.
          </p>
          <div className={styles.heroActions}>
            <Link className={styles.primaryAction} href="/projects">
              Төсөл хянах
            </Link>
            <Link className={styles.secondaryAction} href="/review">
              Шалгах ажлууд
            </Link>
            {canCreateProject ? (
              <Link className={styles.secondaryAction} href="/projects/new">
                Төсөл нэмэх
              </Link>
            ) : null}
            <Link className={styles.secondaryAction} href="/reports">
              Тайлан харах
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
              <span>Алба нэгж</span>
              <b>{snapshot.departments.length}</b>
            </li>
          </ul>
        </aside>
      </section>

      <section className={styles.metricsGrid}>
        {snapshot.metrics.map((metric) => (
          <MetricCard key={metric.label} {...metric} />
        ))}
      </section>

      <section className={styles.dualGrid}>
        <section className={styles.panel}>
          <div className={styles.sectionHeader}>
            <div>
              <span className={styles.kicker}>Шуурхай цэс</span>
              <h2>Үндсэн үйлдлүүд</h2>
              <small className={styles.sectionNote}>
                Дэлгэрэнгүй жагсаалтууд menu-гийн тусдаа хуудсанд байна
              </small>
            </div>
          </div>

          <div className={styles.quickActions}>
            <Link href="/projects" className={styles.quickAction}>
              <strong>{snapshot.projects.length}</strong>
              <span>Төслүүдийн хяналтын самбар</span>
            </Link>
            <Link href="/review" className={styles.quickAction}>
              <strong>{snapshot.reviewQueue.length}</strong>
              <span>Шалгалт хүлээж буй ажил</span>
            </Link>
            <Link href="/reports" className={styles.quickAction}>
              <strong>{snapshot.reports.length}</strong>
              <span>Тайлангийн урсгал</span>
            </Link>
            {canCreateProject ? (
              <Link href="/projects/new" className={styles.quickAction}>
                <strong>+</strong>
                <span>Шинэ төсөл бүртгэх</span>
              </Link>
            ) : (
              <Link href="/projects" className={styles.quickAction}>
                <strong>{snapshot.liveTasks.length}</strong>
                <span>Явагдаж буй task харах</span>
              </Link>
            )}
          </div>
        </section>

        <section className={styles.panel}>
          <div className={styles.sectionHeader}>
            <div>
              <span className={styles.kicker}>Өнөөдрийн төлөв</span>
              <h2>Хяналтын товч зураглал</h2>
            </div>
          </div>

          <div className={styles.statusList}>
            <div className={styles.statusItem}>
              <span>Идэвхтэй төсөл</span>
              <strong>{snapshot.projects.length}</strong>
              <small>Алба нэгжээр ангилсан</small>
            </div>
            <div className={styles.statusItem}>
              <span>Талбарын ажил</span>
              <strong>{snapshot.liveTasks.length}</strong>
              <small>Явагдаж буй task</small>
            </div>
            <div className={styles.statusItem}>
              <span>Шалгалтын мөр</span>
              <strong>{snapshot.reviewQueue.length}</strong>
              <small>Баталгаажуулалт хүлээж байна</small>
            </div>
            <div className={styles.statusItem}>
              <span>Тайлангийн урсгал</span>
              <strong>{snapshot.reports.length}</strong>
              <small>Сүүлийн proof of work</small>
            </div>
          </div>
        </section>
      </section>

      <section className={styles.departmentsSection}>
        <div className={styles.sectionHeader}>
          <div>
            <span className={styles.kicker}>Алба нэгжийн зураглал</span>
            <h2>5 үндсэн нэгжийн dashboard</h2>
            <small className={styles.sectionNote}>
              Алба нэгж бүрийн нээлттэй ажил ба гүйцэтгэлийн товч төлөв
            </small>
          </div>
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

      <nav className={styles.mobileDock} aria-label="Mobile quick navigation">
        <Link href="/" className={styles.mobileDockLink}>
          <span>Самбар</span>
          <strong>{snapshot.projects.length}</strong>
        </Link>
        <Link href="/projects" className={styles.mobileDockLink}>
          <span>Төсөл</span>
          <strong>{snapshot.liveTasks.length}</strong>
        </Link>
        <Link href="/review" className={styles.mobileDockLink}>
          <span>Шалгах</span>
          <strong>{snapshot.reviewQueue.length}</strong>
        </Link>
        <Link href="/reports" className={styles.mobileDockLink}>
          <span>Тайлан</span>
          <strong>{snapshot.reports.length}</strong>
        </Link>
        {canCreateProject ? (
          <Link
            href="/projects/new"
            className={`${styles.mobileDockLink} ${styles.mobileDockPrimary}`}
          >
            <span>Шинэ</span>
            <strong>+</strong>
          </Link>
        ) : null}
      </nav>
    </main>
  );
}
