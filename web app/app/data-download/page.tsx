import Link from "next/link";

import { AppMenu } from "@/app/_components/app-menu";
import { logoutAction } from "@/app/actions";
import { DataDownloadClient } from "@/app/data-download/data-download-client";
import styles from "@/app/workspace.module.css";
import { getRoleLabel, requireSession } from "@/lib/auth";

export const dynamic = "force-dynamic";

export default async function DataDownloadPage() {
  const session = await requireSession();
  const canCreateProject =
    session.role === "general_manager" || session.role === "system_admin";

  return (
    <main className={styles.shell}>
      <div className={styles.container}>
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

        <AppMenu active="data-download" canCreateProject={canCreateProject} />

        <section className={styles.heroCard}>
          <span className={styles.eyebrow}>Дата татах</span>
          <h1>WRS-ээс өдрийн тайлан татах</h1>
          <p>
            Нэг өдрийн огноо сонгоод `Data татах` товч дарахад WRS тайлан автоматаар
            нээгдэж, логин хийгээд, гарсан тайлан нь HTML preview байдлаар энэ дэлгэцэн дээр
            харагдана.
          </p>
        </section>

        <DataDownloadClient />
      </div>
    </main>
  );
}
