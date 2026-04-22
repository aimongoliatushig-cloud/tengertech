import Link from "next/link";
import type { ReactNode } from "react";

import { AppMenu } from "@/app/_components/app-menu";
import {
  getRoleLabel,
  hasCapability,
  isMasterRole,
  isWorkerOnly,
  type AppSession,
} from "@/lib/auth";
import type { ProcurementUser } from "@/lib/procurement";

import styles from "../procurement.module.css";

type ProcurementShellProps = {
  session: AppSession;
  procurementUser: ProcurementUser;
  title: string;
  description: string;
  activeTab: "list" | "assigned" | "dashboard" | "new";
  children: ReactNode;
};

export function ProcurementShell({
  session,
  procurementUser,
  title,
  description,
  activeTab,
  children,
}: ProcurementShellProps) {
  const canCreateProject = hasCapability(session, "create_projects");
  const canCreateTasks = hasCapability(session, "create_tasks");
  const canWriteReports = hasCapability(session, "write_workspace_reports");
  const canViewQualityCenter = hasCapability(session, "view_quality_center");
  const canUseFieldConsole = hasCapability(session, "use_field_console");

  const showAssigned =
    procurementUser.flags.storekeeper ||
    procurementUser.flags.finance ||
    procurementUser.flags.office_clerk ||
    procurementUser.flags.contract_officer ||
    procurementUser.flags.director ||
    procurementUser.flags.admin;
  const showDashboard =
    procurementUser.flags.general_manager ||
    procurementUser.flags.director ||
    procurementUser.flags.finance ||
    procurementUser.flags.office_clerk ||
    procurementUser.flags.contract_officer ||
    procurementUser.flags.admin;
  const showCreate = procurementUser.flags.requester || procurementUser.flags.admin;

  return (
    <div className={styles.workspaceShell}>
      <AppMenu
        active="procurement"
        canCreateProject={canCreateProject}
        canCreateTasks={canCreateTasks}
        canWriteReports={canWriteReports}
        canViewQualityCenter={canViewQualityCenter}
        canUseFieldConsole={canUseFieldConsole}
        variant={procurementUser.flags.general_manager || procurementUser.flags.director ? "executive" : "default"}
        userName={session.name}
        roleLabel={getRoleLabel(session.role)}
        masterMode={isMasterRole(session.role)}
        workerMode={isWorkerOnly(session)}
      />

      <main className={styles.workspaceMain}>
        <section className={styles.heroCard}>
          <div className={styles.heroCopy}>
            <p className={styles.eyebrow}>Худалдан авалтын урсгал</p>
            <h1>{title}</h1>
            <p>{description}</p>
          </div>
          <div className={styles.heroMeta}>
            <span>Хэрэглэгч</span>
            <strong>{procurementUser.name}</strong>
            <small>{procurementUser.company}</small>
          </div>
        </section>

        <nav className={styles.subnav} aria-label="Худалдан авалтын хэсгүүд">
          <Link
            href="/procurement"
            className={`${styles.subnavLink} ${activeTab === "list" ? styles.subnavLinkActive : ""}`}
          >
            Миний худалдан авалт
          </Link>
          {showAssigned ? (
            <Link
              href="/procurement/assigned"
              className={`${styles.subnavLink} ${activeTab === "assigned" ? styles.subnavLinkActive : ""}`}
            >
              Хариуцсан хүсэлт
            </Link>
          ) : null}
          {showDashboard ? (
            <Link
              href="/procurement/dashboard"
              className={`${styles.subnavLink} ${activeTab === "dashboard" ? styles.subnavLinkActive : ""}`}
            >
              Хяналтын самбар
            </Link>
          ) : null}
          {showCreate ? (
            <Link
              href="/procurement/new"
              className={`${styles.subnavLink} ${activeTab === "new" ? styles.subnavLinkActive : ""}`}
            >
              Шинэ хүсэлт
            </Link>
          ) : null}
        </nav>

        {children}
      </main>
    </div>
  );
}
