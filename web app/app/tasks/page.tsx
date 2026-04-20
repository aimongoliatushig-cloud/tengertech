import Link from "next/link";

import { AppMenu } from "@/app/_components/app-menu";
import dashboardStyles from "@/app/page.module.css";
import shellStyles from "@/app/workspace.module.css";
import { getRoleLabel, hasCapability, isWorkerOnly, requireSession } from "@/lib/auth";
import { loadMunicipalSnapshot } from "@/lib/odoo";

import styles from "./tasks.module.css";

type FilterKey = "all" | "working" | "review" | "problem" | "verified";

type PageProps = {
  searchParams?: Promise<{
    department?: string | string[];
    filter?: string | string[];
  }>;
};

const FILTERS: Array<{ key: FilterKey; label: string }> = [
  { key: "all", label: "Бүгд" },
  { key: "working", label: "Ажиллаж байна" },
  { key: "review", label: "Хянагдаж байна" },
  { key: "problem", label: "Асуудалтай" },
  { key: "verified", label: "Баталгаажсан" },
];

function getParam(value?: string | string[]) {
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
}

function normalizeFilter(value: string): FilterKey {
  return FILTERS.some((item) => item.key === value) ? (value as FilterKey) : "all";
}

function StatusBadge({
  statusKey,
  statusLabel,
}: {
  statusKey: "planned" | "working" | "review" | "verified" | "problem";
  statusLabel: string;
}) {
  return (
    <span className={`${dashboardStyles.statusBadge} ${dashboardStyles[`status${statusKey}`]}`}>
      {statusLabel}
    </span>
  );
}

export const dynamic = "force-dynamic";

export default async function TasksPage({ searchParams }: PageProps) {
  const session = await requireSession();
  const params = (await searchParams) ?? {};
  const activeFilter = normalizeFilter(getParam(params.filter));
  const requestedDepartment = getParam(params.department);

  const snapshot = await loadMunicipalSnapshot({
    login: session.login,
    password: session.password,
  });

  const canCreateProject = hasCapability(session, "create_projects");
  const canViewQualityCenter = hasCapability(session, "view_quality_center");
  const canUseFieldConsole = hasCapability(session, "use_field_console");
  const workerMode = isWorkerOnly(session);
  const workerTasks = workerMode
    ? snapshot.taskDirectory.filter((task) => task.assigneeIds?.includes(session.uid))
    : [];

  const selectedDepartment =
    !workerMode && requestedDepartment && requestedDepartment !== "all"
      ? snapshot.departments.find((department) => department.name === requestedDepartment) ?? null
      : null;

  const scopedProjects = workerMode
    ? Array.from(new Set(workerTasks.map((task) => task.projectName)))
    : snapshot.projects.filter(
        (project) => !selectedDepartment || project.departmentName === selectedDepartment.name,
      );
  const scopedTasks = workerMode
    ? workerTasks
    : snapshot.taskDirectory.filter(
        (task) => !selectedDepartment || task.departmentName === selectedDepartment.name,
      );

  const counts = {
    all: scopedTasks.length,
    working: scopedTasks.filter((task) => task.statusKey === "working").length,
    review: scopedTasks.filter((task) => task.statusKey === "review").length,
    problem: scopedTasks.filter((task) => task.statusKey === "problem").length,
    verified: scopedTasks.filter((task) => task.statusKey === "verified").length,
  } satisfies Record<FilterKey, number>;

  const visibleTasks = scopedTasks.filter((task) => {
    if (activeFilter === "all") {
      return true;
    }
    return task.statusKey === activeFilter;
  });

  const selectedDepartmentLabel = workerMode
    ? "Надад оноогдсон ажилбар"
    : selectedDepartment?.name ?? "Бүх алба нэгж";

  return (
    <main className={shellStyles.shell}>
      <div className={shellStyles.container}>
        <div className={shellStyles.contentWithMenu}>
          <aside className={shellStyles.menuColumn}>
            <AppMenu
              active="tasks"
              variant={session.role === "general_manager" ? "executive" : "default"}
              canCreateProject={canCreateProject}
              canViewQualityCenter={canViewQualityCenter}
              canUseFieldConsole={canUseFieldConsole}
              userName={session.name}
              roleLabel={getRoleLabel(session.role)}
              workerMode={workerMode}
            />
          </aside>

          <div className={shellStyles.pageContent}>
            <header className={styles.pageHeader}>
              <div className={styles.pageHeaderMain}>
                <div className={styles.titleBlock}>
                  <span className={styles.pageKicker}>
                    {workerMode ? "Миний урсгал" : "Бүх урсгал"}
                  </span>
                  <h1>{workerMode ? "Надад оноогдсон ажилбар" : "Бүх ажилбар"}</h1>
                  <p>
                    {workerMode
                      ? "Зөвхөн танд хамаарах ажилбаруудыг эндээс харна. Төлөвөөр нь хурдан шүүж, дэлгэрэнгүй рүү шууд орж ажлаа үргэлжлүүлнэ."
                      : "Odoo ERP дээр бүртгэгдсэн бүх ажилбарыг алба нэгж, ажил, төлөвөөр нь нэг дороос харуулна. Асуудалтай болон хяналт хүлээж буй ажилбаруудыг эхэнд нь ялгаж, дэлгэрэнгүй рүү шууд нээнэ."}
                  </p>
                </div>

                <div className={styles.userBlock}>
                  <span>Сүүлд шинэчлэгдсэн</span>
                  <strong>{snapshot.generatedAt}</strong>
                  <small>{selectedDepartmentLabel}</small>
                </div>
              </div>

              <div className={styles.pageHeaderAside}>
                {workerMode ? (
                  <div className={styles.userBlock}>
                    <span>Өнөөдрийн ажил</span>
                    <strong>{canUseFieldConsole ? "Маршрут нээх" : "Маршрутгүй"}</strong>
                    <small>
                      {canUseFieldConsole
                        ? "Өнөөдөрт оноогдсон маршрут, талбайн урсгал руу шууд орно."
                        : "Энэ хэрэглэгч дээр талбайн маршрут харах эрх идэвхгүй байна."}
                    </small>
                    {canUseFieldConsole ? (
                      <Link href="/field" className={styles.dateButton}>
                        Өнөөдрийн ажил
                      </Link>
                    ) : null}
                  </div>
                ) : (
                  <form className={styles.dateFilterForm} method="get">
                    <label htmlFor="tasks-department">Алба нэгж</label>
                    <div className={styles.dateRow}>
                      <select
                        id="tasks-department"
                        name="department"
                        defaultValue={selectedDepartment?.name ?? "all"}
                        className={styles.dateInput}
                      >
                        <option value="all">Бүх алба нэгж</option>
                        {snapshot.departments.map((department) => (
                          <option key={department.name} value={department.name}>
                            {department.name}
                          </option>
                        ))}
                      </select>
                      <input type="hidden" name="filter" value={activeFilter} />
                      <button type="submit" className={styles.dateButton}>
                        Харах
                      </button>
                    </div>
                  </form>
                )}
              </div>
            </header>

            <section className={styles.summaryStrip}>
              <article className={styles.summaryCard}>
                <span>{workerMode ? "Харагдах хүрээ" : "Сонгосон алба нэгж"}</span>
                <strong>{selectedDepartmentLabel}</strong>
                <small>
                  {workerMode
                    ? "Зөвхөн танд оноогдсон ажилбаруудыг харуулж байна"
                    : `${snapshot.departments.length} алба нэгжээс шүүж байна`}
                </small>
              </article>
              <article className={styles.summaryCard}>
                <span>{workerMode ? "Надад оноогдсон ажилбар" : "Нийт ажилбар"}</span>
                <strong>{counts.all}</strong>
                <small>
                  {workerMode
                    ? "Тухайн хэрэглэгчид оноогдсон нийт ажилбар"
                    : "Odoo ERP-ээс орж ирсэн бүх ажилбар"}
                </small>
              </article>
              <article className={styles.summaryCard}>
                <span>{workerMode ? "Холбогдсон ажил" : "Нийт ажил"}</span>
                <strong>{scopedProjects.length}</strong>
                <small>
                  {workerMode
                    ? "Эдгээр ажилд таны ажилбарууд багтаж байна"
                    : "Энэ шүүлтэд хамаарах ажлууд"}
                </small>
              </article>
            </section>

            <section className={styles.filterPanel}>
              <div className={styles.filterHeader}>
                <div>
                  <span className={styles.filterKicker}>Төлөвийн шүүлт</span>
                  <h2>{workerMode ? "Миний ажилбарын төлөв" : "Ажлыг хурдан ангилж харах"}</h2>
                </div>
                <p>
                  {workerMode
                    ? "Асуудалтай, хяналт хүлээж буй, баталгаажсан ажилбараа нэг товшилтоор ялгаж харна."
                    : "Эхлээд асуудалтай, дараа нь хяналт хүлээж буй ажилбаруудыг ялгаж харахад тохиромжтой."}
                </p>
              </div>

              <div className={styles.filterScroller}>
                {FILTERS.map((item) => {
                  const hrefParams = new URLSearchParams();
                  if (!workerMode && selectedDepartment?.name) {
                    hrefParams.set("department", selectedDepartment.name);
                  }
                  if (item.key !== "all") {
                    hrefParams.set("filter", item.key);
                  }

                  return (
                    <Link
                      key={item.key}
                      href={`/tasks?${hrefParams.toString()}`}
                      className={`${styles.filterChip} ${
                        activeFilter === item.key ? styles.filterChipActive : ""
                      }`}
                    >
                      <span>{item.label}</span>
                      <strong>{counts[item.key]}</strong>
                    </Link>
                  );
                })}
              </div>
            </section>

            <section className={styles.taskSection}>
              <div className={styles.sectionHeader}>
                <div>
                  <span className={styles.filterKicker}>
                    {workerMode ? "Миний жагсаалт" : "Ажлын жагсаалт"}
                  </span>
                  <h2>{workerMode ? "Надад хамаарах ажилбар" : "Odoo-оос татсан бүх ажилбар"}</h2>
                </div>
                <p>
                  {workerMode
                    ? `${visibleTasks.length} ажилбар танд одоогоор харагдаж байна`
                    : `${visibleTasks.length} ажилбар одоогоор дэлгэц дээр харагдаж байна`}
                </p>
              </div>

              {visibleTasks.length ? (
                <>
                  <div className={styles.taskCardList}>
                    {visibleTasks.map((task) => (
                      <article key={task.id} className={styles.taskCard}>
                        <div className={styles.taskCardTop}>
                          <div className={styles.taskIdentity}>
                            <strong>{task.name}</strong>
                            <span>{task.projectName}</span>
                          </div>
                          <StatusBadge statusKey={task.statusKey} statusLabel={task.statusLabel} />
                        </div>

                        <p className={styles.taskRoute}>{task.departmentName}</p>

                        <div className={styles.taskInfoGrid}>
                          <div className={styles.taskInfoItem}>
                            <span>Ахлагч</span>
                            <strong>{task.leaderName}</strong>
                          </div>
                          <div className={styles.taskInfoItem}>
                            <span>Хугацаа</span>
                            <strong>{task.deadline}</strong>
                          </div>
                          <div className={styles.taskInfoItem}>
                            <span>Ангилал</span>
                            <strong>{task.operationTypeLabel}</strong>
                          </div>
                        </div>

                        <div className={styles.progressRow}>
                          <div className={styles.progressLabel}>
                            <span>Ажлын явц</span>
                            <strong>{task.progress}%</strong>
                          </div>
                          <div className={styles.progressTrack}>
                            <span style={{ width: `${task.progress}%` }} />
                          </div>
                        </div>

                        <div className={styles.cardActions}>
                          <Link href={task.href} className={styles.primaryLink}>
                            Дэлгэрэнгүй харах
                          </Link>
                          <span className={styles.subtleNote}>
                            {task.completedQuantity}/{task.plannedQuantity} {task.measurementUnit} •{" "}
                            {task.priorityLabel}
                          </span>
                        </div>
                      </article>
                    ))}
                  </div>

                  <div className={styles.tableShell}>
                    <table className={styles.taskTable}>
                      <thead>
                        <tr>
                          <th>Ажилбар</th>
                          <th>Алба нэгж</th>
                          <th>Ажил</th>
                          <th>Төлөв</th>
                          <th>Ахлагч</th>
                          <th>Явц</th>
                          <th>Дэлгэрэнгүй</th>
                        </tr>
                      </thead>
                      <tbody>
                        {visibleTasks.map((task) => (
                          <tr key={task.id}>
                            <td>
                              <strong>{task.name}</strong>
                            </td>
                            <td>{task.departmentName}</td>
                            <td>{task.projectName}</td>
                            <td>
                              <StatusBadge
                                statusKey={task.statusKey}
                                statusLabel={task.statusLabel}
                              />
                            </td>
                            <td>{task.leaderName}</td>
                            <td>
                              <div className={styles.tableProgress}>
                                <span>{task.progress}%</span>
                                <div className={styles.progressTrack}>
                                  <span style={{ width: `${task.progress}%` }} />
                                </div>
                              </div>
                            </td>
                            <td>
                              <Link href={task.href} className={styles.inlineLink}>
                                Нээх
                              </Link>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : (
                <div className={styles.emptyState}>
                  <h3>
                    {workerMode
                      ? "Танд тохирох ажилбар энэ шүүлтээр олдсонгүй"
                      : "Энэ шүүлтээр ажил олдсонгүй"}
                  </h3>
                  <p>
                    {workerMode
                      ? "Өөр төлөв сонгоод дахин шүүж үзнэ үү."
                      : "Өөр алба нэгж эсвэл өөр төлөв сонгоод дахин шүүж үзнэ үү."}
                  </p>
                </div>
              )}
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}
