import Image from "next/image";
import Link from "next/link";
import { redirect } from "next/navigation";

import { AppMenu } from "@/app/_components/app-menu";
import dashboardStyles from "@/app/page.module.css";
import shellStyles from "@/app/workspace.module.css";
import {
  getRoleLabel,
  hasCapability,
  isMasterRole,
  isWorkerOnly,
  requireSession,
} from "@/lib/auth";
import {
  filterByDepartment,
  filterTasksToDate,
  getTodayDateKey,
  pickPrimaryDepartmentName,
} from "@/lib/dashboard-scope";
import {
  DEPARTMENT_GROUPS,
  findDepartmentGroupByName,
  findDepartmentGroupByUnit,
  getAvailableUnits,
  matchesDepartmentGroup,
} from "@/lib/department-groups";
import { loadMunicipalSnapshot } from "@/lib/odoo";

import styles from "./reports.module.css";

type PageProps = {
  searchParams?: Promise<{
    department?: string | string[];
    unit?: string | string[];
  }>;
};

type FeedReport = {
  id: number;
  reporter: string;
  taskName: string;
  departmentName: string;
  projectName: string;
  summary: string;
  reportedQuantity: number;
  imageCount: number;
  audioCount: number;
  submittedAt: string;
  images: {
    id: number;
    name: string;
    mimetype: string;
    url: string;
  }[];
  audios: {
    id: number;
    name: string;
    mimetype: string;
    url: string;
  }[];
};

type ReportGroup = {
  projectName: string;
  departmentName: string;
  reports: FeedReport[];
  latestSubmittedAt: string;
};

function getDepartmentParam(value?: string | string[]) {
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
}

function countReportsByUnits(unitNames: string[], reports: Array<{ departmentName: string }>) {
  return reports.filter((report) => unitNames.includes(report.departmentName)).length;
}

function countReportsByGroup(
  group: (typeof DEPARTMENT_GROUPS)[number],
  reports: Array<{ departmentName: string }>,
) {
  return reports.filter((report) => matchesDepartmentGroup(group, report.departmentName)).length;
}

function formatQuantity(value: number, unit: string) {
  if (!value) {
    return `0 ${unit}`;
  }

  return `${value} ${unit}`.trim();
}

export const dynamic = "force-dynamic";

export default async function ReportsPage({ searchParams }: PageProps) {
  const session = await requireSession();
  if (isWorkerOnly(session)) {
    redirect("/");
  }
  const snapshot = await loadMunicipalSnapshot({
    login: session.login,
    password: session.password,
  });

  const canCreateProject = hasCapability(session, "create_projects");
  const canViewQualityCenter = hasCapability(session, "view_quality_center");
  const canUseFieldConsole = hasCapability(session, "use_field_console");
  const masterMode = isMasterRole(session.role);

  const params = (await searchParams) ?? {};
  const requestedDepartment = getDepartmentParam(params.department);
  const requestedUnit = getDepartmentParam(params.unit);
  const allReportUnits = Array.from(new Set(snapshot.reports.map((report) => report.departmentName)));
  const masterDepartmentName = masterMode
    ? pickPrimaryDepartmentName({
        taskDirectory: snapshot.taskDirectory,
        reports: snapshot.reports,
        projects: snapshot.projects,
        departments: snapshot.departments,
      })
    : null;

  const selectedGroup =
    !masterMode && requestedDepartment && requestedDepartment !== "all"
      ? findDepartmentGroupByName(requestedDepartment) ??
        findDepartmentGroupByUnit(requestedDepartment)
      : null;
  const availableUnits = selectedGroup
    ? getAvailableUnits(selectedGroup, allReportUnits)
    : [];
  const selectedUnit =
    requestedUnit && availableUnits.includes(requestedUnit)
      ? requestedUnit
      : requestedDepartment && availableUnits.includes(requestedDepartment)
        ? requestedDepartment
        : availableUnits.length === 1
          ? (availableUnits[0] ?? "")
          : "";
  const matchesSelectedDepartment = (departmentName: string) =>
    selectedUnit
      ? departmentName === selectedUnit
      : selectedGroup
        ? matchesDepartmentGroup(selectedGroup, departmentName)
        : true;
  const todayDateKey = getTodayDateKey();

  const filteredReports = masterMode
    ? filterByDepartment(snapshot.reports, masterDepartmentName)
    : snapshot.reports.filter((report) => matchesSelectedDepartment(report.departmentName));

  const filteredReviewQueue = masterMode
    ? filterByDepartment(snapshot.reviewQueue, masterDepartmentName)
    : snapshot.reviewQueue.filter((item) => matchesSelectedDepartment(item.departmentName));
  const filteredTaskDirectory = masterMode
    ? filterByDepartment(snapshot.taskDirectory, masterDepartmentName)
    : snapshot.taskDirectory.filter((task) => matchesSelectedDepartment(task.departmentName));
  const todayScopedTasks = filterTasksToDate(filteredTaskDirectory, todayDateKey);
  const todayActiveTasks = todayScopedTasks.filter(
    (task) => task.stageBucket === "todo" || task.stageBucket === "progress",
  );
  const todayReviewTasks = todayScopedTasks.filter((task) => task.stageBucket === "review");
  const todayDoneTasks = todayScopedTasks.filter((task) => task.stageBucket === "done");
  const todayAverageProgress = todayActiveTasks.length
    ? Math.round(
        todayActiveTasks.reduce((sum, task) => sum + task.progress, 0) /
          todayActiveTasks.length,
      )
    : 0;

  const groupedReports = Array.from(
    filteredReports.reduce<Map<string, ReportGroup>>((accumulator, report) => {
      const groupKey = `${report.departmentName}::${report.projectName}`;
      const existing = accumulator.get(groupKey);
      if (existing) {
        existing.reports.push(report);
        return accumulator;
      }

      accumulator.set(groupKey, {
        projectName: report.projectName,
        departmentName: report.departmentName,
        reports: [report],
        latestSubmittedAt: report.submittedAt,
      });
      return accumulator;
    }, new Map()),
  )
    .map(([, group]) => ({
      ...group,
      reports: group.reports.sort((left, right) => right.id - left.id),
    }))
    .sort((left, right) => right.reports[0].id - left.reports[0].id);

  const selectedDepartmentName = masterMode
    ? masterDepartmentName ?? "Миний алба нэгж"
    : selectedUnit || selectedGroup?.name || "Бүх хэлтэс";
  const totalImages = filteredReports.reduce((sum, report) => sum + report.imageCount, 0);
  const totalAudios = filteredReports.reduce((sum, report) => sum + report.audioCount, 0);

  return (
    <main className={shellStyles.shell}>
      <div className={shellStyles.container} id="reports-top">
        <div className={shellStyles.contentWithMenu}>
          <aside className={shellStyles.menuColumn}>
            <AppMenu
              active="reports"
              canCreateProject={canCreateProject}
              canViewQualityCenter={canViewQualityCenter}
              canUseFieldConsole={canUseFieldConsole}
              userName={session.name}
              roleLabel={getRoleLabel(session.role)}
              masterMode={masterMode}
            />
          </aside>

          <div className={shellStyles.pageContent}>
            <header className={styles.pageHeader}>
              <div className={styles.titleBlock}>
                <span className={styles.kicker}>Тайлан</span>
                <h1>{masterMode ? "Нэгжийн тайлангийн урсгал" : "Хэлтсийн тайлан"}</h1>
                <p>
                  {masterMode
                    ? "Мастер хэрэглэгчид зөвхөн өөрийн алба нэгжийн илгээсэн тайлан энд харагдана. Ажлаар нь бүлэглэж, зураг аудио хавсралтыг нэг дороос харуулна."
                    : "Эхлээд хэлтсээ сонгоно. Дараа нь доторх нэгжээ сонгоод, тухайн нэгжийн ажлуудаар тайланг бүлэглэж харуулна."}
                </p>
              </div>

              <div className={styles.pageAside}>
                <div className={styles.dateMeta}>
                  <span>Сүүлд шинэчлэгдсэн</span>
                  <strong>{snapshot.generatedAt}</strong>
                  <small>{masterMode ? selectedDepartmentName : getRoleLabel(session.role)}</small>
                </div>
              </div>
            </header>

            {!masterMode ? (
              <section className={styles.sectionCard}>
                <div className={dashboardStyles.sectionHeader}>
                  <div>
                    <span className={dashboardStyles.kicker}>Хэлтсийн шүүлт</span>
                    <h2>Тайлан харах хэлтэс</h2>
                    <small className={dashboardStyles.sectionNote}>
                      Тайланг эхлээд хэлтсээр, дараа нь хэлтэс доторх нэгжээр шүүнэ
                    </small>
                  </div>
                </div>

                <nav className={styles.departmentFilterGrid} aria-label="Хэлтэс сонгох">
                  <div className={styles.departmentFilterInner}>
                    <Link
                      href="/reports"
                      className={`${styles.departmentFilterCard} ${
                        !selectedGroup ? styles.departmentFilterCardActive : ""
                      }`}
                      aria-current={!selectedGroup ? "page" : undefined}
                    >
                      <span className={styles.departmentFilterLabel}>
                        <span className={styles.departmentFilterIcon} aria-hidden>
                          🏢
                        </span>
                        <span>Бүгд</span>
                      </span>
                      <strong>{snapshot.reports.length}</strong>
                    </Link>

                    {DEPARTMENT_GROUPS.map((group) => {
                      const isActive = selectedGroup?.name === group.name;
                      const reportCount = countReportsByGroup(group, snapshot.reports);
                      const groupUnits = getAvailableUnits(group, allReportUnits);
                      const hrefParams = new URLSearchParams();
                      hrefParams.set("department", group.name);
                      if (groupUnits[0]) {
                        hrefParams.set("unit", groupUnits[0]);
                      }

                      return (
                        <Link
                          key={group.name}
                          href={`/reports?${hrefParams.toString()}`}
                          className={`${styles.departmentFilterCard} ${
                            isActive ? styles.departmentFilterCardActive : ""
                          }`}
                          aria-current={isActive ? "page" : undefined}
                        >
                          <span className={styles.departmentFilterLabel}>
                            <span className={styles.departmentFilterIcon} aria-hidden>
                              {group.icon}
                            </span>
                            <span>{group.name}</span>
                          </span>
                          <strong>{reportCount}</strong>
                        </Link>
                      );
                    })}
                  </div>
                </nav>
              </section>
            ) : null}

            {selectedGroup && availableUnits.length > 1 ? (
              <section className={styles.sectionCard}>
                <div className={dashboardStyles.sectionHeader}>
                  <div>
                    <span className={dashboardStyles.kicker}>Доторх нэгж</span>
                    <h2>{selectedGroup.name}</h2>
                    <small className={dashboardStyles.sectionNote}>
                      Энэ хэлтэс доторх тайланг нэгж тус бүрээр нь харуулна
                    </small>
                  </div>
                </div>

                <div className={shellStyles.taskFilterRail}>
                  {availableUnits.map((unit) => {
                    const hrefParams = new URLSearchParams();
                    hrefParams.set("department", selectedGroup.name);
                    hrefParams.set("unit", unit);

                    return (
                      <Link
                        key={unit}
                        href={`/reports?${hrefParams.toString()}`}
                        className={`${shellStyles.taskFilterChip} ${
                          selectedUnit === unit ? shellStyles.taskFilterChipActive : ""
                        }`}
                      >
                        <span>{unit}</span>
                        <strong>{countReportsByUnits([unit], snapshot.reports)}</strong>
                      </Link>
                    );
                  })}
                </div>
              </section>
            ) : null}

            <section className={styles.summaryStrip}>
              <article className={styles.summaryCard}>
                <span>{masterMode ? "Алба нэгж" : "Сонгосон хүрээ"}</span>
                <strong>{selectedDepartmentName}</strong>
                <small>
                  {masterMode
                    ? "Зөвхөн энэ нэгжийн тайлангийн урсгал харагдаж байна"
                    : "Одоо харагдаж буй тайлангийн багц"}
                </small>
              </article>
              <article className={styles.summaryCard}>
                <span>Ажил</span>
                <strong>{groupedReports.length}</strong>
                <small>Тайлан орсон ажлууд</small>
              </article>
              <article className={styles.summaryCard}>
                <span>Орсон тайлан</span>
                <strong>{filteredReports.length}</strong>
                <small>Бүртгэгдсэн нийт тайлан</small>
              </article>
              {!masterMode ? (
                <article className={styles.summaryCard}>
                  <span>Хянах ажилбар</span>
                  <strong>{filteredReviewQueue.length}</strong>
                  <small>Хяналт хүлээж буй ажилбар</small>
                </article>
              ) : null}
              <article className={styles.summaryCard}>
                <span>Зураг</span>
                <strong>{totalImages}</strong>
                <small>Хавсаргасан зураг</small>
              </article>
              <article className={styles.summaryCard}>
                <span>Аудио</span>
                <strong>{totalAudios}</strong>
                <small>Хавсаргасан аудио</small>
              </article>
            </section>

            <section className={styles.sectionCard}>
              <div className={styles.workflowHeader}>
                <div>
                  <span className={styles.kicker}>Өнөөдрийн явц</span>
                  <h2>Өнөөдөр явагдаж буй ажил</h2>
                  <p>
                    Ерөнхий менежерийн шалгалтад орохоос өмнөх явц, шалгалт
                    хүлээж буй ажил, бүрэн баталгаажсан ажлыг тусад нь харуулна.
                  </p>
                </div>
                <div className={styles.workflowMetaCard}>
                  <span>Өнөөдрийн дундаж явц</span>
                  <strong>{todayAverageProgress}%</strong>
                  <small>{todayScopedTasks.length} ажилбарын нийлбэр төлөв</small>
                </div>
              </div>

              <div className={styles.workflowSummaryGrid}>
                <article className={styles.workflowSummaryCard}>
                  <span>Өнөөдрийн ажил</span>
                  <strong>{todayScopedTasks.length}</strong>
                  <small>Өнөөдрийн огноонд төлөвлөгдсөн нийт ажилбар</small>
                </article>
                <article className={styles.workflowSummaryCard}>
                  <span>Явж буй</span>
                  <strong>{todayActiveTasks.length}</strong>
                  <small>Шалгалтад хараахан ороогүй ажилбар</small>
                </article>
                <article className={styles.workflowSummaryCard}>
                  <span>Шалгалт хүлээж буй</span>
                  <strong>{todayReviewTasks.length}</strong>
                  <small>Ерөнхий менежерийн шийдвэр хүлээж буй ажилбар</small>
                </article>
                <article className={styles.workflowSummaryCard}>
                  <span>Бүрэн дууссан</span>
                  <strong>{todayDoneTasks.length}</strong>
                  <small>Баталгаажиж хаагдсан ажилбар</small>
                </article>
              </div>

              <div className={styles.workflowColumns}>
                <article className={styles.workflowColumn}>
                  <div className={styles.workflowColumnHeader}>
                    <div>
                      <span className={styles.kicker}>Явж буй</span>
                      <h3>Шалгалтаас өмнөх явц</h3>
                    </div>
                    <strong>{todayActiveTasks.length}</strong>
                  </div>
                  {todayActiveTasks.length ? (
                    <div className={styles.workflowList}>
                      {todayActiveTasks.map((task) => (
                        <article key={task.id} className={styles.workflowItem}>
                          <div className={styles.workflowItemTop}>
                            <div>
                              <strong>{task.name}</strong>
                              <p>{task.projectName}</p>
                            </div>
                            <span className={styles.workflowItemBadge}>{task.progress}%</span>
                          </div>
                          <div className={styles.workflowItemMeta}>
                            <span>{task.leaderName || "Хариуцагчгүй"}</span>
                            <span>
                              {formatQuantity(task.completedQuantity, task.measurementUnit)}
                            </span>
                          </div>
                          <div className={styles.workflowTrack} aria-hidden>
                            <span style={{ width: `${Math.max(task.progress, 4)}%` }} />
                          </div>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <div className={styles.workflowEmpty}>
                      Өнөөдрийн явж буй ажил одоогоор алга байна.
                    </div>
                  )}
                </article>

                <article className={styles.workflowColumn}>
                  <div className={styles.workflowColumnHeader}>
                    <div>
                      <span className={styles.kicker}>Шалгалт</span>
                      <h3>Ерөнхий менежер хүлээж буй</h3>
                    </div>
                    <strong>{todayReviewTasks.length}</strong>
                  </div>
                  {todayReviewTasks.length ? (
                    <div className={styles.workflowList}>
                      {todayReviewTasks.map((task) => (
                        <article key={task.id} className={styles.workflowItem}>
                          <div className={styles.workflowItemTop}>
                            <div>
                              <strong>{task.name}</strong>
                              <p>{task.projectName}</p>
                            </div>
                            <span className={styles.workflowItemBadge}>Шалгалт</span>
                          </div>
                          <div className={styles.workflowItemMeta}>
                            <span>{task.leaderName || "Хариуцагчгүй"}</span>
                            <span>{task.stageLabel}</span>
                          </div>
                          <div className={styles.workflowTrack} aria-hidden>
                            <span style={{ width: "100%" }} />
                          </div>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <div className={styles.workflowEmpty}>
                      Ерөнхий менежерийн шалгалт хүлээж буй ажил алга байна.
                    </div>
                  )}
                </article>

                <article className={styles.workflowColumn}>
                  <div className={styles.workflowColumnHeader}>
                    <div>
                      <span className={styles.kicker}>Дууссан</span>
                      <h3>Бүрэн баталгаажсан</h3>
                    </div>
                    <strong>{todayDoneTasks.length}</strong>
                  </div>
                  {todayDoneTasks.length ? (
                    <div className={styles.workflowList}>
                      {todayDoneTasks.map((task) => (
                        <article key={task.id} className={styles.workflowItem}>
                          <div className={styles.workflowItemTop}>
                            <div>
                              <strong>{task.name}</strong>
                              <p>{task.projectName}</p>
                            </div>
                            <span className={styles.workflowItemBadge}>100%</span>
                          </div>
                          <div className={styles.workflowItemMeta}>
                            <span>{task.leaderName || "Хариуцагчгүй"}</span>
                            <span>{task.stageLabel}</span>
                          </div>
                          <div className={styles.workflowTrack} aria-hidden>
                            <span style={{ width: "100%" }} />
                          </div>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <div className={styles.workflowEmpty}>
                      Өнөөдрийн баталгаажсан ажил одоогоор алга байна.
                    </div>
                  )}
                </article>
              </div>
            </section>

            {groupedReports.length ? (
              <section className={styles.projectStack}>
                {groupedReports.map((group) => (
                  <article key={`${group.departmentName}-${group.projectName}`} className={styles.projectSection}>
                    <div className={styles.projectHeader}>
                      <div>
                        <span className={styles.kicker}>{group.departmentName}</span>
                        <h2>{group.projectName}</h2>
                        <p>{group.reports.length} тайлан орсон ажил</p>
                      </div>
                      <div className={styles.projectMeta}>
                        <div>
                          <span>Сүүлд орсон</span>
                          <strong>{group.latestSubmittedAt}</strong>
                        </div>
                        <div>
                          <span>Тайлан</span>
                          <strong>{group.reports.length}</strong>
                        </div>
                      </div>
                    </div>

                    <div className={styles.reportList}>
                      {group.reports.map((report) => (
                        <article key={report.id} className={styles.reportCard}>
                          <div className={styles.reportTop}>
                            <div>
                              <strong>{report.taskName}</strong>
                              <p>{report.submittedAt}</p>
                            </div>
                            <span className={styles.reportStamp}>Тайлан орсон</span>
                          </div>

                          <div className={styles.reportMeta}>
                            <span>Илгээгч: {report.reporter}</span>
                            <span>Хэмжээ: {report.reportedQuantity} нэгж</span>
                            <span>Зураг: {report.imageCount}</span>
                            <span>Аудио: {report.audioCount}</span>
                          </div>

                          <div className={styles.summaryBox}>{report.summary}</div>

                          {report.images.length ? (
                            <div className={dashboardStyles.reportImageGrid}>
                              {report.images.map((image) => (
                                <a
                                  key={image.id}
                                  href={image.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className={dashboardStyles.reportImageLink}
                                >
                                  <Image
                                    src={image.url}
                                    alt={`${report.taskName} - ${image.name}`}
                                    className={dashboardStyles.reportImage}
                                    width={320}
                                    height={240}
                                    unoptimized
                                  />
                                </a>
                              ))}
                            </div>
                          ) : null}

                          {report.audios.length ? (
                            <div className={dashboardStyles.reportAudioList}>
                              {report.audios.map((audio) => (
                                <div key={audio.id} className={dashboardStyles.reportAudioCard}>
                                  <strong>{audio.name}</strong>
                                  <audio
                                    controls
                                    preload="none"
                                    src={audio.url}
                                    className={dashboardStyles.reportAudioPlayer}
                                  />
                                </div>
                              ))}
                            </div>
                          ) : null}
                        </article>
                      ))}
                    </div>
                  </article>
                ))}
              </section>
            ) : (
              <section className={styles.emptyState}>
                <span className={styles.kicker}>Хоосон төлөв</span>
                <h2>Энэ хүрээнд тайлан алга</h2>
                <p>Өөр хэлтэс эсвэл доторх нэгж сонгож үзнэ үү.</p>
              </section>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
