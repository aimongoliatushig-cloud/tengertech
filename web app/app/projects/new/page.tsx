import { AppMenu } from "@/app/_components/app-menu";
import { createProjectAction } from "@/app/actions";
import styles from "@/app/workspace.module.css";
import { getRoleLabel, hasCapability, requireSession } from "@/lib/auth";
import {
  loadDepartmentOptions,
  loadGarbageRouteOptions,
  loadGarbageVehicleOptions,
  loadProjectManagerOptions,
} from "@/lib/workspace";

import { NewWorkForm } from "@/app/projects/new/new-work-form";

type PageProps = {
  searchParams?: Promise<{
    error?: string | string[];
    notice?: string | string[];
  }>;
};

function getMessage(value?: string | string[]) {
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }

  return value ?? "";
}

export default async function NewProjectPage({ searchParams }: PageProps) {
  const session = await requireSession();
  const params = (await searchParams) ?? {};
  const errorMessage = getMessage(params.error);
  const noticeMessage = getMessage(params.notice);

  const [managerOptions, departmentOptions, garbageVehicleOptions, garbageRouteOptions] =
    await Promise.all([
      loadProjectManagerOptions({
        login: session.login,
        password: session.password,
      }),
      loadDepartmentOptions({
        login: session.login,
        password: session.password,
      }),
      loadGarbageVehicleOptions({
        login: session.login,
        password: session.password,
      }),
      loadGarbageRouteOptions({
        login: session.login,
        password: session.password,
      }),
    ]);

  const canCreateProject = hasCapability(session, "create_projects");
  const canViewQualityCenter = hasCapability(session, "view_quality_center");
  const canUseFieldConsole = hasCapability(session, "use_field_console");

  return (
    <main className={styles.shell}>
      <div className={styles.container} id="create-project-top">
        <div className={styles.contentWithMenu}>
          <aside className={styles.menuColumn}>
            <AppMenu
              active="new-project"
              canCreateProject={canCreateProject}
              canViewQualityCenter={canViewQualityCenter}
              canUseFieldConsole={canUseFieldConsole}
              userName={session.name}
              roleLabel={getRoleLabel(session.role)}
            />
          </aside>

          <div className={styles.pageContent}>
            <section className={styles.heroCard}>
              <span className={styles.eyebrow}>Ажил бүртгэх</span>
              <h1>Шинэ ажил нэмэх</h1>
              <p>
                Энгийн ажил дээр нэрээ гараар оруулна. Харин хог тээвэрлэлтийн
                үед машины дугаар, маршрут, огноо сонгоход нэг ажил автоматаар
                үүсэж, тухайн маршрутын хог ачих цэг бүр тусдаа ажилбар болж нэмэгдэнэ.
              </p>
            </section>

            {errorMessage ? (
              <div className={`${styles.message} ${styles.errorMessage}`}>{errorMessage}</div>
            ) : null}

            {noticeMessage ? (
              <div className={`${styles.message} ${styles.noticeMessage}`}>
                {noticeMessage}
              </div>
            ) : null}

            {!canCreateProject ? (
              <section className={styles.emptyState}>
                <h2>Ажил бүртгэх эрх алга</h2>
                <p>
                  Шинэ ажил нэмэх боломж одоогоор зөвхөн ерөнхий менежер болон
                  системийн админ дээр нээлттэй байна.
                </p>
              </section>
            ) : (
              <section className={styles.formCard} id="project-form">
                <NewWorkForm
                  action={createProjectAction}
                  departmentOptions={departmentOptions}
                  managerOptions={managerOptions}
                  garbageVehicleOptions={garbageVehicleOptions}
                  garbageRouteOptions={garbageRouteOptions}
                />
              </section>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
