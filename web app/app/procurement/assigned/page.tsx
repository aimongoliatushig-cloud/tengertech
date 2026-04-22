import Link from "next/link";

import { ProcurementShell } from "@/app/procurement/_components/procurement-shell";
import { requireSession } from "@/lib/auth";
import { loadProcurementMe, loadProcurementRequests } from "@/lib/procurement";

import styles from "../procurement.module.css";

export const dynamic = "force-dynamic";

export default async function AssignedProcurementPage() {
  const session = await requireSession();
  const connectionOverrides = {
    login: session.login,
    password: session.password,
  };
  const [procurementUser, requestBundle] = await Promise.all([
    loadProcurementMe(connectionOverrides),
    loadProcurementRequests({ scope: "assigned", limit: 20 }, connectionOverrides),
  ]);

  return (
    <ProcurementShell
      session={session}
      procurementUser={procurementUser}
      title="Хариуцсан хүсэлтүүд"
      description="Нярав, санхүү, бичиг хэрэг, гэрээний ажилтан, удирдлагад оноогдсон ажлуудыг шууд дарааллаар нь харуулна."
      activeTab="assigned"
    >
      <section className={styles.cardSection}>
        <div className={styles.sectionHeader}>
          <div>
            <h2>Миний хариуцсан урсгал</h2>
            <p>Одоогоор {requestBundle.items.length} хүсэлт таны харагдацад байна.</p>
          </div>
        </div>
        {requestBundle.items.length ? (
          <div className={styles.requestGrid}>
            {requestBundle.items.map((item) => (
              <Link key={item.id} href={`/procurement/${item.id}`} className={styles.requestCard}>
                <div className={styles.requestCardTop}>
                  <div>
                    <strong>{item.name}</strong>
                    <p>{item.title}</p>
                  </div>
                  <span className={item.is_delayed ? styles.badgeDanger : styles.badge}>
                    {item.state.label}
                  </span>
                </div>
                <div className={styles.metaList}>
                  <span><strong>Төсөл:</strong> {item.project?.name || "Сонгоогүй"}</span>
                  <span><strong>Хариуцагч:</strong> {item.current_responsible?.name || "Тодорхойгүй"}</span>
                  <span><strong>Одоогийн шат:</strong> {item.current_stage_age_days} өдөр</span>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className={styles.emptyState}>Одоогоор танд оноогдсон худалдан авалтын хүсэлт алга байна.</div>
        )}
      </section>
    </ProcurementShell>
  );
}
