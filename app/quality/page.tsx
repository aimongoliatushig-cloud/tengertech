import Link from "next/link";

import { AppMenu } from "@/app/_components/app-menu";
import { logoutAction } from "@/app/actions";
import dashboardStyles from "@/app/page.module.css";
import styles from "@/app/workspace.module.css";
import { getRoleLabel, hasCapability, requireSession } from "@/lib/auth";
import { loadMunicipalSnapshot } from "@/lib/odoo";

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
    <article className={`${dashboardStyles.metricCard} ${dashboardStyles[`tone${tone}`]}`}>
      <p>{label}</p>
      <strong>{value}</strong>
      <span>{note}</span>
    </article>
  );
}

export default async function QualityPage() {
  const session = await requireSession();
  const canCreateProject = hasCapability(session, "create_projects");
  const canViewQualityCenter = hasCapability(session, "view_quality_center");
  const canUseFieldConsole = hasCapability(session, "use_field_console");
  const snapshot = await loadMunicipalSnapshot({
    login: session.login,
    password: session.password,
  });

  return (
    <main className={styles.shell}>
      <div className={styles.container} id="quality-top">
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
          active="quality"
          canCreateProject={canCreateProject}
          canViewQualityCenter={canViewQualityCenter}
          canUseFieldConsole={canUseFieldConsole}
        />

        {!canViewQualityCenter ? (
          <section className={styles.emptyState}>
            <h2>Чанарын төв рүү хандах эрх алга</h2>
            <p>Энэ хуудас нь удирдлага, диспетчер, хянагчийн чанарын хяналтад зориулагдсан.</p>
          </section>
        ) : (
          <>
            <section className={styles.heroCard}>
              <span className={styles.eyebrow}>Чанарын төв</span>
              <h1>Талбарын чанар ба зөрчлийн хяналтын самбар</h1>
              <p>
                Зургийн бүрэн байдал, маршрутын зөрүү, хаагдаагүй цэг, жингийн синкийн
                анхааруулгыг энд нэгтгэн харуулж, эрсдэлийг хурдан ангилан шийднэ.
              </p>

              <div className={styles.statsGrid}>
                <article className={styles.statCard}>
                  <span>Чанарын анхааруулга</span>
                  <strong>{snapshot.qualityAlerts.length}</strong>
                </article>
                <article className={styles.statCard}>
                  <span>Шалгалтын мөр</span>
                  <strong>{snapshot.reviewQueue.length}</strong>
                </article>
                <article className={styles.statCard}>
                  <span>Эх сурвалж</span>
                  <strong>{snapshot.source === "live" ? "Шууд" : "Жишээ"}</strong>
                </article>
                <article className={styles.statCard}>
                  <span>Шинэчлэгдсэн</span>
                  <strong>{snapshot.generatedAt}</strong>
                </article>
              </div>
            </section>

            <section className={dashboardStyles.metricsGrid}>
              {snapshot.qualityMetrics.map((metric) => (
                <MetricCard key={metric.label} {...metric} />
              ))}
            </section>

            <section className={styles.panel}>
              <div className={styles.sectionHeader}>
                <div>
                  <span className={styles.eyebrow}>Ажлын зөрчил</span>
                  <h2>Анхаарах ажил</h2>
                </div>
                <p>
                  Ажил бүрийг нээж зураг, маршрут, жингийн синк, хаагдаагүй цэгийн
                  дэлгэрэнгүйг шалгана.
                </p>
              </div>

              {snapshot.qualityAlerts.length ? (
                <div className={dashboardStyles.reviewList}>
                  {snapshot.qualityAlerts.map((alert) => (
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
                        <span>{alert.departmentName}</span>
                        <span>Дутуу зураг {alert.missingProofStopCount}</span>
                        <span>Хаагдаагүй {alert.unresolvedStopCount}</span>
                        {alert.hasWeightWarning ? <span>Жингийн синкийн анхааруулга</span> : null}
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className={styles.emptyState}>
                  <h2>Чанарын анхааруулга алга</h2>
                  <p>Энэ агшинд талбарын гүйцэтгэлийн зөрчил илрээгүй байна.</p>
                </div>
              )}
            </section>
          </>
        )}

        <nav className={styles.mobileDock} aria-label="Чанарын хуудасны гар утасны цэс">
          <Link href="/" className={styles.jumpLink}>
            Нүүр
          </Link>
          <Link href="/review" className={styles.jumpLink}>
            Шалгалт
          </Link>
          <a href="#quality-top" className={styles.jumpLink}>
            Дээш
          </a>
        </nav>
      </div>
    </main>
  );
}
