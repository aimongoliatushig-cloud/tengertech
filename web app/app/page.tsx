import Image from "next/image";
import Link from "next/link";

import { AppMenu } from "@/app/_components/app-menu";
import { logoutAction } from "@/app/actions";
import { getRoleLabel, requireSession } from "@/lib/auth";
import { loadGarbageExecutiveSnapshot } from "@/lib/garbage-executive";

import styles from "./page.module.css";

type PageProps = {
  searchParams?: Promise<{
    date?: string | string[];
  }>;
};

function getParam(value?: string | string[]) {
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
}

function KpiCard({
  label,
  value,
  note,
  tone,
}: {
  label: string;
  value: string;
  note: string;
  tone: "normal" | "warning" | "critical" | "weight";
}) {
  return (
    <article className={`${styles.executiveKpiCard} ${styles[`kpi${tone}`]}`}>
      <span className={styles.executiveKpiLabel}>{label}</span>
      <strong className={styles.executiveKpiValue}>{value}</strong>
      <p className={styles.executiveKpiNote}>{note}</p>
    </article>
  );
}

function StatusBadge({
  statusKey,
  statusLabel,
}: {
  statusKey: "planned" | "working" | "review" | "verified" | "problem";
  statusLabel: string;
}) {
  return (
    <span className={`${styles.statusBadge} ${styles[`status${statusKey}`]}`}>
      {statusLabel}
    </span>
  );
}

export const dynamic = "force-dynamic";

export default async function Home({ searchParams }: PageProps) {
  const session = await requireSession();
  const params = (await searchParams) ?? {};
  const selectedDate = getParam(params.date);

  const snapshot = await loadGarbageExecutiveSnapshot(
    {
      login: session.login,
      password: session.password,
    },
    selectedDate,
  );

  return (
    <main className={styles.shell}>
      <header className={styles.executiveHeader}>
        <div className={styles.executiveBrand}>
          <div className={styles.executiveBrandMark}>
            <Image
              src="/logo.png"
              alt="Хот тохижилтын удирдлагын төвийн лого"
              width={164}
              height={56}
              className={styles.brandLogo}
              priority
              unoptimized
            />
          </div>

          <div className={styles.executiveTitleBlock}>
            <span className={styles.executiveKicker}>Хог тээвэрлэлт</span>
            <h1>Хог тээвэрлэлт - Ерөнхий хяналт</h1>
            <p>
              Өнөөдрийн хог тээвэрлэлтийн явц, анхаарах асуудал, баталгаажсан
              жингийн мэдээлэл
            </p>
          </div>
        </div>

        <div className={styles.executiveHeaderAside}>
          <form className={styles.dateFilterForm} method="get">
            <label htmlFor="dashboard-date" className={styles.dateFilterLabel}>
              Огноо
            </label>
            <div className={styles.dateFilterRow}>
              <input
                id="dashboard-date"
                name="date"
                type="date"
                defaultValue={snapshot.selectedDateInput}
                className={styles.dateFilterInput}
              />
              <button type="submit" className={styles.dateFilterButton}>
                Харах
              </button>
            </div>
          </form>

          <div className={styles.executiveMeta}>
            <Link
              href="#alerts-section"
              className={styles.notificationButton}
              aria-label="Анхаарах асуудал руу очих"
            >
              <span aria-hidden>🔔</span>
              <strong>{snapshot.notificationCount}</strong>
            </Link>

            <div className={styles.executiveUserCard}>
              <span>{getRoleLabel(session.role)}</span>
              <strong>{session.name}</strong>
              <small>Сүүлд шинэчлэгдсэн: {snapshot.generatedAtLabel}</small>
            </div>

            <form action={logoutAction}>
              <button type="submit" className={styles.logoutButton}>
                Гарах
              </button>
            </form>
          </div>
        </div>
      </header>

      <AppMenu active="dashboard" variant="executive" />

      <section className={styles.compactSummaryStrip}>
        <div>
          <span className={styles.summaryLabel}>Сонгосон огноо</span>
          <strong>{snapshot.selectedDateLabel}</strong>
        </div>
        <div>
          <span className={styles.summaryLabel}>Жингийн тайлан</span>
          <strong>{snapshot.previousDateLabel}</strong>
        </div>
        <div>
          <span className={styles.summaryLabel}>Жингийн шинэчлэл</span>
          <strong>Шөнийн таталтаар орно</strong>
        </div>
      </section>

      <section className={styles.executiveKpiGrid}>
        {snapshot.kpis.map((card) => (
          <KpiCard key={card.label} {...card} />
        ))}
      </section>

      <section className={styles.executiveSignalGrid}>
        <section className={styles.executivePanel} id="alerts-section">
          <div className={styles.executiveSectionHeader}>
            <div>
              <span className={styles.executiveSectionKicker}>Анхаарах хэсэг</span>
              <h2>Анхаарах асуудал</h2>
            </div>
          </div>

          {snapshot.alerts.length ? (
            <div className={styles.alertList}>
              {snapshot.alerts.map((alert) => (
                <Link key={alert.id} href={alert.href} className={styles.alertItem}>
                  <div className={styles.alertHeading}>
                    <span
                      className={`${styles.severityBadge} ${
                        alert.severity === "red"
                          ? styles.severityRed
                          : styles.severityAmber
                      }`}
                    >
                      {alert.severityLabel}
                    </span>
                    <strong>{alert.title}</strong>
                  </div>
                  <p>{alert.note}</p>
                </Link>
              ))}
            </div>
          ) : (
            <div className={styles.emptyStateBox}>
              Одоогоор анхаарах асуудал бүртгэгдээгүй байна.
            </div>
          )}
        </section>

        <aside className={`${styles.executivePanel} ${styles.signalPanel}`}>
          <div className={styles.executiveSectionHeader}>
            <div>
              <span className={styles.executiveSectionKicker}>Шуурхай дохио</span>
              <h2>Шуурхай төлөв</h2>
            </div>
          </div>

          <div className={styles.signalList}>
            {snapshot.signals.map((item) => (
              <article key={item.label} className={styles.signalItem}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.note}</small>
              </article>
            ))}
          </div>
        </aside>
      </section>

      <section className={styles.executivePanel}>
        <div className={styles.executiveSectionHeader}>
          <div>
            <span className={styles.executiveSectionKicker}>Өнөөдрийн урсгал</span>
            <h2>Өнөөдрийн ажил</h2>
          </div>
          <Link
            href={`/tasks?date=${encodeURIComponent(snapshot.selectedDateInput)}`}
            className={styles.inlineLink}
          >
            Бүгдийг харах
          </Link>
        </div>

        <div className={styles.taskTableWrap}>
          <table className={styles.taskTable}>
            <thead>
              <tr>
                <th>Машин</th>
                <th>Маршрут</th>
                <th>Төлөв</th>
                <th>Явц</th>
                <th>Жин</th>
                <th>Дэлгэрэнгүй</th>
              </tr>
            </thead>
            <tbody>
              {snapshot.todayTasks.slice(0, 8).map((task) => (
                <tr key={task.id}>
                  <td>
                    <strong>{task.vehicleName}</strong>
                    <span>{task.driverName}</span>
                  </td>
                  <td>{task.routeName}</td>
                  <td>
                    <StatusBadge
                      statusKey={task.statusKey}
                      statusLabel={task.statusLabel}
                    />
                  </td>
                  <td>
                    <div className={styles.inlineProgress}>
                      <span>{task.progress}%</span>
                      <div className={styles.inlineProgressTrack}>
                        <span style={{ width: `${task.progress}%` }} />
                      </div>
                    </div>
                  </td>
                  <td>{task.finalWeightLabel}</td>
                  <td>
                    <Link href={task.detailHref} className={styles.inlineLink}>
                      Харах
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className={styles.executiveWeightGrid}>
        <section className={styles.executivePanel}>
          <div className={styles.executiveSectionHeader}>
            <div>
              <span className={styles.executiveSectionKicker}>Шөнийн таталт</span>
              <h2>Өчигдрийн хог тээвэрлэлтийн тайлан</h2>
            </div>
          </div>

          <div className={styles.weightStatGrid}>
            <article className={styles.weightStatCard}>
              <span>Нийт жин</span>
              <strong>{snapshot.yesterdayWeight.totalLabel}</strong>
            </article>
            <article className={styles.weightStatCard}>
              <span>Хамгийн их жинтэй машин</span>
              <strong>{snapshot.yesterdayWeight.topVehicleName}</strong>
              <small>{snapshot.yesterdayWeight.topVehicleLabel}</small>
            </article>
            <article className={styles.weightStatCard}>
              <span>Дундаж жин / машин</span>
              <strong>{snapshot.yesterdayWeight.averageLabel}</strong>
            </article>
          </div>
        </section>

        <section className={styles.executivePanel}>
          <div className={styles.executiveSectionHeader}>
            <div>
              <span className={styles.executiveSectionKicker}>Сарын зураглал</span>
              <h2>Сарын гүйцэтгэл</h2>
            </div>
          </div>

          <div className={styles.weightStatGrid}>
            <article className={styles.weightStatCard}>
              <span>Энэ сарын нийт жин</span>
              <strong>{snapshot.monthlyWeight.totalLabel}</strong>
            </article>
            <article className={styles.weightStatCard}>
              <span>Өчигдөр нэмэгдсэн жин</span>
              <strong>{snapshot.monthlyWeight.addedYesterdayLabel}</strong>
            </article>
          </div>

          <div className={styles.trendChart}>
            {snapshot.monthlyWeight.trend.map((point) => (
              <div key={point.dateKey} className={styles.trendColumn}>
                <span className={styles.trendValue}>{point.totalLabel}</span>
                <div className={styles.trendBarTrack}>
                  <span
                    className={styles.trendBar}
                    style={{ height: `${point.heightPercent}%` }}
                  />
                </div>
                <small>{point.dateLabel}</small>
              </div>
            ))}
          </div>
        </section>
      </section>

      <section className={styles.executivePanel}>
        <div className={styles.executiveSectionHeader}>
          <div>
            <span className={styles.executiveSectionKicker}>Шуурхай харах</span>
            <h2>Шуурхай холбоос</h2>
          </div>
        </div>

        <div className={styles.quickLinkGrid}>
          {snapshot.quickLinks.map((item) => (
            <Link key={item.label} href={item.href} className={styles.quickLinkCard}>
              <strong>{item.label}</strong>
              <span>{item.note}</span>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
