import { ProcurementShell } from "@/app/procurement/_components/procurement-shell";
import { requireSession } from "@/lib/auth";
import { loadProcurementDashboard, loadProcurementMe } from "@/lib/procurement";

import styles from "../procurement.module.css";

export const dynamic = "force-dynamic";

export default async function ProcurementDashboardPage() {
  const session = await requireSession();
  const connectionOverrides = {
    login: session.login,
    password: session.password,
  };
  const [procurementUser, dashboard] = await Promise.all([
    loadProcurementMe(connectionOverrides),
    loadProcurementDashboard({}, connectionOverrides),
  ]);

  return (
    <ProcurementShell
      session={session}
      procurementUser={procurementUser}
      title="Ерөнхий менежерийн хяналтын самбар"
      description="Төслүүдийн худалдан авалтын явц, няравын ачаалал, нийлүүлэгчийн сонголт, шийдвэрлэх хугацааг төвлөрүүлэн харуулна."
      activeTab="dashboard"
    >
      <section className={styles.metricsGrid}>
        <article className={styles.metricCard}>
          <span>Нийт хүсэлт</span>
          <strong>{dashboard.metrics.total}</strong>
          <small>Системийн бүх урсгал</small>
        </article>
        <article className={styles.metricCard}>
          <span>Төлбөр хүлээгдэж буй</span>
          <strong>{dashboard.metrics.payment_pending}</strong>
          <small>Санхүүгийн дараагийн алхамтай</small>
        </article>
        <article className={styles.metricCard}>
          <span>Хүлээн авалт хүлээгдэж буй</span>
          <strong>{dashboard.metrics.receipt_pending}</strong>
          <small>Няравын баталгаажуулалт дутуу</small>
        </article>
        <article className={styles.metricCard}>
          <span>Дундаж хугацаа</span>
          <strong>{dashboard.metrics.average_resolution_days}</strong>
          <small>өдөр</small>
        </article>
      </section>

      <section className={styles.dashboardGrid}>
        <article className={styles.dashboardCard}>
          <div className={styles.sectionHeader}>
            <div>
              <h3>Нярав тус бүрийн ачаалал</h3>
              <p>Идэвхтэй урсгалын тоо</p>
            </div>
          </div>
          {dashboard.storekeeper_load.length ? (
            <div className={styles.tableList}>
              {dashboard.storekeeper_load.map((item) => (
                <div key={item.id} className={styles.tableRow}>
                  <div className={styles.tableRowHeader}>
                    <strong>{item.name}</strong>
                    <span className={styles.badge}>{item.count} хүсэлт</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className={styles.emptyState}>Одоогоор ачааллын мэдээлэл алга байна.</div>
          )}
        </article>

        <article className={styles.dashboardCard}>
          <div className={styles.sectionHeader}>
            <div>
              <h3>Төсөл тус бүрийн явц</h3>
              <p>Төсөл дээр хэдэн хүсэлт нээлттэй байгааг харуулна.</p>
            </div>
          </div>
          {dashboard.project_progress.length ? (
            <div className={styles.tableList}>
              {dashboard.project_progress.map((item) => (
                <div key={item.id} className={styles.tableRow}>
                  <div className={styles.tableRowHeader}>
                    <strong>{item.name}</strong>
                    <span className={styles.badgeOutline}>{item.count} хүсэлт</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className={styles.emptyState}>Төслийн явцын мэдээлэл олдсонгүй.</div>
          )}
        </article>

        <article className={styles.dashboardCard}>
          <div className={styles.sectionHeader}>
            <div>
              <h3>Нийлүүлэгчийн сонголт</h3>
              <p>Хамгийн олон сонгогдсон нийлүүлэгчид</p>
            </div>
          </div>
          {dashboard.supplier_counts.length ? (
            <div className={styles.tableList}>
              {dashboard.supplier_counts.map((item) => (
                <div key={item.id} className={styles.tableRow}>
                  <div className={styles.tableRowHeader}>
                    <strong>{item.name}</strong>
                    <span className={styles.badgeOutline}>{item.count} удаа</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className={styles.emptyState}>Сонгогдсон нийлүүлэгчийн статистик алга байна.</div>
          )}
        </article>
      </section>
    </ProcurementShell>
  );
}
