import { redirect } from "next/navigation";

import { AppMenu } from "@/app/_components/app-menu";
import { WorkspaceHeader } from "@/app/_components/workspace-header";
import shellStyles from "@/app/workspace.module.css";
import { getRoleLabel, hasCapability, requireSession } from "@/lib/auth";
import { loadFleetVehicleBoard } from "@/lib/odoo";

import styles from "./page.module.css";

export const dynamic = "force-dynamic";

export default async function AutoBasePage() {
  const session = await requireSession();
  const allowedRoles = new Set(["system_admin", "director", "general_manager"]);

  if (!allowedRoles.has(String(session.role))) {
    redirect("/");
  }

  const canCreateProject = hasCapability(session, "create_projects");
  const canCreateTasks = hasCapability(session, "create_tasks");
  const canWriteReports = hasCapability(session, "write_workspace_reports");
  const canViewQualityCenter = hasCapability(session, "view_quality_center");
  const canUseFieldConsole = hasCapability(session, "use_field_console");

  let board = {
    activeVehicles: [],
    repairVehicles: [],
    totalVehicles: 0,
    activeCount: 0,
    repairCount: 0,
  } as Awaited<ReturnType<typeof loadFleetVehicleBoard>>;
  let loadError = "";

  try {
    board = await loadFleetVehicleBoard({
      login: session.login,
      password: session.password,
    });
  } catch (error) {
    console.error("Fleet vehicle board could not be loaded:", error);
    loadError =
      "Авто баазын машины төлөвийг Odoo-оос уншиж чадсангүй. Fleet эрх болон холболтын тохиргоог шалгана уу.";
  }

  return (
    <main className={shellStyles.shell}>
      <div className={shellStyles.container}>
        <div className={shellStyles.contentWithMenu}>
          <aside className={shellStyles.menuColumn}>
            <AppMenu
              active="auto-base"
              canCreateProject={canCreateProject}
              canCreateTasks={canCreateTasks}
              canWriteReports={canWriteReports}
              canViewQualityCenter={canViewQualityCenter}
              canUseFieldConsole={canUseFieldConsole}
              userName={session.name}
              roleLabel={getRoleLabel(session.role)}
            />
          </aside>

          <div className={shellStyles.pageContent}>
            <WorkspaceHeader
              title="Авто бааз"
              subtitle="Идэвхтэй болон засагдаж буй машинуудын бодит төлөв"
              userName={session.name}
              roleLabel={getRoleLabel(session.role)}
              notificationCount={board.totalVehicles}
              notificationNote={`${board.activeCount} идэвхтэй, ${board.repairCount} засагдаж буй машин байна`}
            />

            {loadError ? (
              <section className={styles.errorCard}>
                <h2>Авто баазын самбар ачаалсангүй</h2>
                <p>{loadError}</p>
              </section>
            ) : null}

            <section className={styles.boardCard}>
              <div className={styles.sectionHeader}>
                <div>
                  <span className={styles.eyebrow}>Машины төлөв</span>
                  <h1>Авто баазын chart</h1>
                </div>
                <p>Энэ хэсэгт зөвхөн идэвхтэй явж буй машин болон засагдаж буй машин л харагдана.</p>
              </div>

              <div className={styles.boardGrid}>
                <section className={`${styles.columnCard} ${styles.columnActive}`}>
                  <div className={styles.columnHeader}>
                    <div>
                      <span className={styles.columnLabel}>Идэвхтэй машин</span>
                      <strong>{board.activeCount}</strong>
                    </div>
                    <span className={styles.countBadge}>{board.activeCount}</span>
                  </div>

                  {board.activeVehicles.length ? (
                    <div className={styles.vehicleList}>
                      {board.activeVehicles.map((vehicle) => (
                        <article key={vehicle.id} className={styles.vehicleCard}>
                          <div className={styles.vehicleTop}>
                            <strong className={styles.vehiclePlate}>{vehicle.plate}</strong>
                            <span className={`${styles.vehicleState} ${styles.vehicleStateActive}`}>
                              {vehicle.stateLabel || "Идэвхтэй"}
                            </span>
                          </div>
                          <p className={styles.vehicleName}>{vehicle.name}</p>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <div className={styles.emptyState}>Одоогоор идэвхтэй машин алга.</div>
                  )}
                </section>

                <section className={`${styles.columnCard} ${styles.columnRepair}`}>
                  <div className={styles.columnHeader}>
                    <div>
                      <span className={styles.columnLabel}>Засагдаж буй машин</span>
                      <strong>{board.repairCount}</strong>
                    </div>
                    <span className={styles.countBadge}>{board.repairCount}</span>
                  </div>

                  {board.repairVehicles.length ? (
                    <div className={styles.vehicleList}>
                      {board.repairVehicles.map((vehicle) => (
                        <article key={vehicle.id} className={styles.vehicleCard}>
                          <div className={styles.vehicleTop}>
                            <strong className={styles.vehiclePlate}>{vehicle.plate}</strong>
                            <span className={`${styles.vehicleState} ${styles.vehicleStateRepair}`}>
                              {vehicle.latestRepairState || vehicle.stateLabel || "Засварт"}
                            </span>
                          </div>
                          <p className={styles.vehicleName}>{vehicle.name}</p>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <div className={styles.emptyState}>Одоогоор засагдаж буй машин алга.</div>
                  )}
                </section>
              </div>
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}
