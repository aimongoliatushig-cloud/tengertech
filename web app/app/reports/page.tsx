import Image from "next/image";
import Link from "next/link";

import { AppMenu } from "@/app/_components/app-menu";
import dashboardStyles from "@/app/page.module.css";
import shellStyles from "@/app/workspace.module.css";
import { getRoleLabel, hasCapability, requireSession } from "@/lib/auth";
import { loadMunicipalSnapshot } from "@/lib/odoo";

import styles from "./reports.module.css";

type PageProps = {
  searchParams?: Promise<{
    department?: string | string[];
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

function countReportsByDepartment(
  departmentName: string | null,
  reports: Array<{ departmentName: string }>,
) {
  if (!departmentName) {
    return reports.length;
  }

  return reports.filter((report) => report.departmentName === departmentName).length;
}

export const dynamic = "force-dynamic";

export default async function ReportsPage({ searchParams }: PageProps) {
  const session = await requireSession();
  const snapshot = await loadMunicipalSnapshot({
    login: session.login,
    password: session.password,
  });

  const canCreateProject = hasCapability(session, "create_projects");
  const canViewQualityCenter = hasCapability(session, "view_quality_center");
  const canUseFieldConsole = hasCapability(session, "use_field_console");

  const params = (await searchParams) ?? {};
  const requestedDepartment = getDepartmentParam(params.department);

  const selectedDepartment =
    requestedDepartment && requestedDepartment !== "all"
      ? snapshot.departments.find((department) => department.name === requestedDepartment) ?? null
      : null;

  const filteredReports = snapshot.reports.filter(
    (report) => !selectedDepartment || report.departmentName === selectedDepartment.name,
  );

  const filteredReviewQueue = snapshot.reviewQueue.filter(
    (item) => !selectedDepartment || item.departmentName === selectedDepartment.name,
  );

  const groupedReports = Array.from(
    filteredReports.reduce<Map<string, ReportGroup>>((accumulator, report) => {
      const existing = accumulator.get(report.projectName);
      if (existing) {
        existing.reports.push(report);
        return accumulator;
      }

      accumulator.set(report.projectName, {
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

  const selectedDepartmentName = selectedDepartment?.name ?? "Бүх алба нэгж";
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
            />
          </aside>

          <div className={shellStyles.pageContent}>
            <header className={styles.pageHeader}>
              <div className={styles.titleBlock}>
                <span className={styles.kicker}>Тайлан</span>
                <h1>Алба нэгжийн тайлан</h1>
                <p>
                  Нэг дэлгэц дээр алба нэгжээ сонгоод, тухайн албаны ажлуудаар тайланг бүлэглэж
                  харуулна.
                </p>
              </div>

              <div className={styles.pageAside}>
                <div className={styles.dateMeta}>
                  <span>Сүүлд шинэчлэгдсэн</span>
                  <strong>{snapshot.generatedAt}</strong>
                  <small>{getRoleLabel(session.role)}</small>
                </div>
              </div>
            </header>

            <section className={styles.sectionCard}>
              <div className={dashboardStyles.sectionHeader}>
                <div>
                  <span className={dashboardStyles.kicker}>Алба нэгжийн шүүлт</span>
                  <h2>Тайлан харах алба нэгж</h2>
                  <small className={dashboardStyles.sectionNote}>
                    Тусдаа сонголтын мөр биш, нэг урсгалтай сонголтоор тайлангаа шүүнэ
                  </small>
                </div>
              </div>

              <nav className={styles.departmentFilterGrid} aria-label="Алба нэгж сонгох">
                <Link
                  href="/reports"
                  className={`${styles.departmentFilterCard} ${
                    !selectedDepartment ? styles.departmentFilterCardActive : ""
                  }`}
                  aria-current={!selectedDepartment ? "page" : undefined}
                >
                  <span className={styles.departmentFilterLabel}>
                    <span className={styles.departmentFilterIcon} aria-hidden>
                      🏢
                    </span>
                    <span>Бүгд</span>
                  </span>
                  <strong>{snapshot.reports.length}</strong>
                </Link>

                {snapshot.departments.map((department) => {
                  const isActive = selectedDepartment?.name === department.name;
                  const reportCount = countReportsByDepartment(department.name, snapshot.reports);

                  return (
                    <Link
                      key={department.name}
                      href={`/reports?department=${encodeURIComponent(department.name)}`}
                      className={`${styles.departmentFilterCard} ${
                        isActive ? styles.departmentFilterCardActive : ""
                      }`}
                      aria-current={isActive ? "page" : undefined}
                    >
                      <span className={styles.departmentFilterLabel}>
                        <span className={styles.departmentFilterIcon} aria-hidden>
                          {department.icon}
                        </span>
                        <span>{department.name}</span>
                      </span>
                      <strong>{reportCount}</strong>
                    </Link>
                  );
                })}
              </nav>
            </section>

            <section className={styles.summaryStrip}>
              <article className={styles.summaryCard}>
                <span>Сонгосон алба</span>
                <strong>{selectedDepartmentName}</strong>
                <small>Одоо харагдаж буй тайлангийн хүрээ</small>
              </article>
              <article className={styles.summaryCard}>
                <span>Ажил</span>
                <strong>{groupedReports.length}</strong>
                <small>Тайлан орсон ажлууд</small>
              </article>
              <article className={styles.summaryCard}>
                <span>Орсон тайлан</span>
                <strong>{filteredReports.length}</strong>
                <small>Сүүлд бүртгэгдсэн урсгал</small>
              </article>
              <article className={styles.summaryCard}>
                <span>Хянах ажилбар</span>
                <strong>{filteredReviewQueue.length}</strong>
                <small>Хүлээгдэж буй баталгаажуулалт</small>
              </article>
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

            {groupedReports.length ? (
              <section className={styles.projectStack}>
                {groupedReports.map((group) => (
                  <article key={group.projectName} className={styles.projectSection}>
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
                <h2>Тайлан алга</h2>
                <p>{selectedDepartmentName} дээр одоогоор харагдах тайлан бүртгэгдээгүй байна.</p>
              </section>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
