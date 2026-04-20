import Link from "next/link";
import { redirect } from "next/navigation";

import { AppMenu } from "@/app/_components/app-menu";
import dashboardStyles from "@/app/page.module.css";
import styles from "@/app/workspace.module.css";
import {
  getRoleLabel,
  hasCapability,
  isMasterRole,
  isWorkerOnly,
  requireSession,
} from "@/lib/auth";
import { filterByDepartment, pickPrimaryDepartmentName } from "@/lib/dashboard-scope";
import {
  DEPARTMENT_GROUPS,
  findDepartmentGroupByName,
  findDepartmentGroupByUnit,
  getAvailableUnits,
  matchesDepartmentGroup,
} from "@/lib/department-groups";
import { loadMunicipalSnapshot } from "@/lib/odoo";

type PageProps = {
  searchParams?: Promise<{
    department?: string | string[];
    category?: string | string[];
    unit?: string | string[];
  }>;
};

type ProjectFilterKey = "all" | "progress" | "planned";
const PROJECT_FILTERS: Array<{ key: ProjectFilterKey; label: string }> = [
  { key: "all", label: "Бүгд" },
  { key: "progress", label: "Явагдаж буй ажил" },
  { key: "planned", label: "Төлөвлөж буй ажил" },
];

/* legacy department groups kept commented during shared helper migration
  {
    name: "Авто бааз, хог тээвэрлэлтийн хэлтэс",
    units: ["Авто бааз", "Хог тээвэрлэлт"],
    icon: "🚚",
  },
  {
    name: "Ногоон байгууламж, цэвэрлэгээ үйлчилгээний хэлтэс",
    units: ["Ногоон байгууламж", "Зам талбайн цэвэрлэгээ"],
    icon: "🌿",
  },
  {
    name: "Тохижилтын хэлтэс",
    units: ["Тохижилт үйлчилгээ"],
    icon: "🏙️",
  },
*/

function getDepartmentParam(value?: string | string[]) {
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
}

function normalizeProjectFilter(value: string): ProjectFilterKey {
  return PROJECT_FILTERS.some((item) => item.key === value) ? (value as ProjectFilterKey) : "all";
}

/* local group helpers removed in favor of shared lib helpers */

function StagePill({
  label,
  bucket,
}: {
  label: string;
  bucket: "todo" | "progress" | "review" | "done" | "unknown";
}) {
  const tone =
    bucket === "done"
      ? dashboardStyles.stageDone
      : bucket === "review"
        ? dashboardStyles.stageReview
        : bucket === "progress"
          ? dashboardStyles.stageProgress
          : dashboardStyles.stageTodo;

  return <span className={`${dashboardStyles.stagePill} ${tone}`}>{label}</span>;
}

export const dynamic = "force-dynamic";

export default async function ProjectsPage({ searchParams }: PageProps) {
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
  const activeFilter = normalizeProjectFilter(getDepartmentParam(params.category));
  const masterDepartmentName = masterMode
    ? pickPrimaryDepartmentName({
        taskDirectory: snapshot.taskDirectory,
        reports: snapshot.reports,
        projects: snapshot.projects,
        departments: snapshot.departments,
      })
    : null;

  const detectedGroup =
    !masterMode && requestedDepartment && requestedDepartment !== "all"
      ? findDepartmentGroupByName(requestedDepartment) ??
        findDepartmentGroupByUnit(requestedDepartment)
      : null;

  const selectedGroup = detectedGroup;
  const allProjectUnits = Array.from(
    new Set(snapshot.projects.map((project) => project.departmentName)),
  );
  const availableUnits = selectedGroup
    ? getAvailableUnits(selectedGroup, allProjectUnits)
    : [];

  const selectedUnit =
    requestedUnit && availableUnits.includes(requestedUnit)
      ? requestedUnit
      : requestedDepartment && availableUnits.includes(requestedDepartment)
        ? requestedDepartment
        : selectedGroup && availableUnits.length > 1
          ? (availableUnits[0] ?? "")
          : "";

  const scopedProjects = (masterMode
    ? filterByDepartment(snapshot.projects, masterDepartmentName)
    : snapshot.projects.filter((project) => {
        if (selectedUnit) {
          return project.departmentName === selectedUnit;
        }
        if (selectedGroup) {
          return matchesDepartmentGroup(selectedGroup, project.departmentName);
        }
        return true;
      })
  ).sort((left, right) => right.completion - left.completion);

  const activeProjects = scopedProjects.filter((project) => {
    if (activeFilter === "all") {
      return true;
    }

    if (activeFilter === "progress") {
      return project.stageBucket === "progress" || project.stageBucket === "review";
    }

    return project.stageBucket === "todo" || project.stageBucket === "unknown";
  });

  const selectedDepartmentName = masterMode
    ? masterDepartmentName ?? "Миний алба нэгж"
    : selectedUnit || selectedGroup?.name || "Бүх хэлтэс";

  const projectCounts = {
    all: scopedProjects.length,
    progress: scopedProjects.filter(
      (project) => project.stageBucket === "progress" || project.stageBucket === "review",
    ).length,
    planned: scopedProjects.filter(
      (project) => project.stageBucket === "todo" || project.stageBucket === "unknown",
    ).length,
  } satisfies Record<ProjectFilterKey, number>;

  const reviewProjectsCount = scopedProjects.filter(
    (project) => project.stageBucket === "review",
  ).length;
  const totalOpenTaskCount = scopedProjects.reduce(
    (sum, project) => sum + project.openTasks,
    0,
  );
  const weightedCompletion = scopedProjects.length
    ? Math.round(
        totalOpenTaskCount > 0
          ? scopedProjects.reduce(
              (sum, project) => sum + project.completion * project.openTasks,
              0,
            ) / totalOpenTaskCount
          : scopedProjects.reduce((sum, project) => sum + project.completion, 0) /
              scopedProjects.length,
      )
    : 0;
  const summaryCards = [
    {
      label: "Нийт ажил",
      value: String(scopedProjects.length),
      note: "Энэ нэгж дээр бүртгэлтэй бүх ажил",
      icon: "📦",
      tone: styles.summaryCardSoft,
    },
    {
      label: "Идэвхтэй ажил",
      value: String(projectCounts.progress),
      note: "Яг одоо явж байгаа болон хяналтын шаттай ажил",
      icon: "🟢",
      tone: styles.summaryCardActive,
    },
    {
      label: "Хяналтад буй ажил",
      value: String(reviewProjectsCount),
      note: "Баталгаажуулалт хүлээж буй ажил",
      icon: "🛡️",
      tone: styles.summaryCardReview,
    },
    {
      label: "Нийт гүйцэтгэл",
      value: `${weightedCompletion}%`,
      note: `${totalOpenTaskCount} нээлттэй ажилбарт тулгуурлан тооцсон`,
      icon: "📈",
      tone: styles.summaryCardPrimary,
    },
  ] as const;
  const visibleSummaryCards = masterMode
    ? [summaryCards[0], summaryCards[1], summaryCards[3]]
    : summaryCards;

  const filterTitle =
    activeFilter === "progress"
      ? "Явагдаж буй ажил"
      : activeFilter === "planned"
        ? "Төлөвлөж буй ажил"
        : "Бүх ажил";

  const filterNote =
    activeFilter === "progress"
      ? "Одоо хэрэгжиж байгаа болон хяналтын шатанд явж буй ажлуудыг харуулна"
      : activeFilter === "planned"
        ? "Одоогоор эхлээгүй, төлөвлөсөн шатанд байгаа ажлуудыг харуулна"
        : "Сонгосон алба нэгжийн бүх ажлыг нэг дор харуулна";

  return (
    <main className={styles.shell}>
      <div className={styles.container} id="projects-top">
        <div className={styles.contentWithMenu}>
          <aside className={styles.menuColumn}>
            <AppMenu
              active="projects"
              canCreateProject={canCreateProject}
              canViewQualityCenter={canViewQualityCenter}
              canUseFieldConsole={canUseFieldConsole}
              userName={session.name}
              roleLabel={getRoleLabel(session.role)}
              masterMode={masterMode}
            />
          </aside>

          <div className={styles.pageContent}>
            {!masterMode ? (
              <section className={dashboardStyles.projectsSection}>
                <div className={dashboardStyles.sectionHeader}>
                  <div>
                    <span className={dashboardStyles.kicker}>Хэлтсийн цэс</span>
                    <h2>Хэлтэс сонгох</h2>
                    <small className={dashboardStyles.sectionNote}>
                      Эхлээд хэлтэс сонгоно. Дараа нь тухайн хэлтэс доторх ажлыг тусад нь шүүж харуулна.
                    </small>
                  </div>
                </div>

                <nav
                  className={dashboardStyles.departmentSelector}
                  aria-label="Хэлтэс сонгох цэс"
                >
                  <div className={dashboardStyles.departmentTabBar}>
                    <Link
                      href={activeFilter === "all" ? "/projects" : `/projects?category=${activeFilter}`}
                      className={`${dashboardStyles.departmentTab} ${
                        !selectedGroup ? dashboardStyles.departmentTabActive : ""
                      }`}
                      aria-current={!selectedGroup ? "page" : undefined}
                    >
                      <span className={dashboardStyles.departmentTabLabel}>
                        <span className={dashboardStyles.departmentTabIcon} aria-hidden>
                          🏢
                        </span>
                        <span>Бүгд</span>
                      </span>
                      <strong>{snapshot.projects.length}</strong>
                    </Link>

                    {DEPARTMENT_GROUPS.map((group) => {
                      const isActive = group.name === selectedGroup?.name;
                      const departmentProjects = snapshot.projects.filter(
                        (project) => matchesDepartmentGroup(group, project.departmentName),
                      );
                      const groupUnits = getAvailableUnits(group, allProjectUnits);
                      const hrefParams = new URLSearchParams();
                      hrefParams.set("department", group.name);
                      if (activeFilter !== "all") {
                        hrefParams.set("category", activeFilter);
                      }

                      return (
                        <Link
                          key={group.name}
                          href={`/projects?${
                            (() => {
                              const params = new URLSearchParams(hrefParams);
                              const defaultUnit = groupUnits[0] ?? "";
                              if (defaultUnit) {
                                params.set("unit", defaultUnit);
                              }
                              return params.toString();
                            })()
                          }`}
                          className={`${dashboardStyles.departmentTab} ${
                            isActive ? dashboardStyles.departmentTabActive : ""
                          }`}
                          aria-current={isActive ? "page" : undefined}
                        >
                          <span className={dashboardStyles.departmentTabLabel}>
                            <span className={dashboardStyles.departmentTabIcon} aria-hidden>
                              {group.icon}
                            </span>
                            <span>{group.name}</span>
                          </span>
                          <strong>{departmentProjects.length}</strong>
                        </Link>
                      );
                    })}
                  </div>
                </nav>
              </section>
            ) : null}

            {selectedGroup && availableUnits.length > 1 ? (
              <section className={dashboardStyles.projectsSection}>
                <div className={dashboardStyles.sectionHeader}>
                  <div>
                    <span className={dashboardStyles.kicker}>Доторх нэгж</span>
                    <h2>{selectedGroup.name}</h2>
                    <small className={dashboardStyles.sectionNote}>
                      Энэ хэлтэс доторх ажлыг нэгжээр нь салгаж харуулна.
                    </small>
                  </div>
                </div>

                <div className={styles.taskFilterRail}>
                  {availableUnits.map((unit) => {
                    const hrefParams = new URLSearchParams();
                    hrefParams.set("department", selectedGroup.name);
                    hrefParams.set("unit", unit);
                    if (activeFilter !== "all") {
                      hrefParams.set("category", activeFilter);
                    }

                    return (
                      <Link
                        key={unit}
                        href={`/projects?${hrefParams.toString()}`}
                        className={`${styles.taskFilterChip} ${
                          selectedUnit === unit
                            ? styles.taskFilterChipActive
                            : ""
                        }`}
                      >
                        <span>{unit}</span>
                        <strong>
                          {
                            snapshot.projects.filter((project) => project.departmentName === unit)
                              .length
                          }
                        </strong>
                      </Link>
                    );
                  })}
                </div>
              </section>
            ) : null}

            <section className={dashboardStyles.projectsSection}>
              <div className={dashboardStyles.sectionHeader}>
                <div>
                  <span className={dashboardStyles.kicker}>
                    {masterMode ? "Нэгжийн ажил" : "Хэлтсийн ангилал"}
                  </span>
                  <h2>{selectedDepartmentName}</h2>
                  <small className={dashboardStyles.sectionNote}>
                    {masterMode
                      ? "Ажил дээр дарахад тухайн ажлаас шинэ ажилбар нээх болон өнөөдрийн урсгал руу орно."
                      : "Ажил дээр дарахад тухайн ажлын ажилбарууд нээгдэнэ"}
                  </small>
                </div>
              </div>

              <div className={styles.summaryShowcaseGrid}>
                {visibleSummaryCards.map((card) => (
                  <article key={card.label} className={`${styles.summaryShowcaseCard} ${card.tone}`}>
                    <div className={styles.summaryShowcaseTop}>
                      <span className={styles.summaryShowcaseIcon} aria-hidden>
                        {card.icon}
                      </span>
                      <span className={styles.summaryShowcaseLabel}>{card.label}</span>
                    </div>
                    <strong className={styles.summaryShowcaseValue}>{card.value}</strong>
                    <small className={styles.summaryShowcaseNote}>{card.note}</small>
                    {card.label === "Нийт гүйцэтгэл" ? (
                      <div className={styles.summaryShowcaseTrack} aria-hidden>
                        <span
                          className={styles.summaryShowcaseFill}
                          style={{ width: `${Math.max(weightedCompletion, 6)}%` }}
                        />
                      </div>
                    ) : null}
                  </article>
                ))}
              </div>

              <div className={styles.taskFilterRail}>
                {PROJECT_FILTERS.map((filter) => {
                  const hrefParams = new URLSearchParams();
                  if (selectedGroup?.name) {
                    hrefParams.set("department", selectedGroup.name);
                  }
                  if (selectedUnit) {
                    hrefParams.set("unit", selectedUnit);
                  }
                  if (filter.key !== "all") {
                    hrefParams.set("category", filter.key);
                  }

                  return (
                    <Link
                      key={filter.key}
                      href={`/projects${hrefParams.toString() ? `?${hrefParams.toString()}` : ""}`}
                      className={`${styles.taskFilterChip} ${
                        activeFilter === filter.key ? styles.taskFilterChipActive : ""
                      }`}
                    >
                      <span>{filter.label}</span>
                      <strong>{projectCounts[filter.key]}</strong>
                    </Link>
                  );
                })}
              </div>

              {activeProjects.length ? (
                <>
                  <div className={dashboardStyles.sectionHeader}>
                    <div>
                      <span className={dashboardStyles.kicker}>{filterTitle}</span>
                      <h2>{selectedDepartmentName}</h2>
                      <small className={dashboardStyles.sectionNote}>{filterNote}</small>
                    </div>
                  </div>

                  <div className={dashboardStyles.projectRail}>
                  {activeProjects.map((project) => (
                    <Link key={project.id} href={project.href} className={dashboardStyles.projectCard}>
                      <div className={dashboardStyles.projectCardTop}>
                        <span>{project.deadline}</span>
                        <StagePill label={project.stageLabel} bucket={project.stageBucket} />
                      </div>

                      <h3>{project.name}</h3>
                      <p>Менежер: {project.manager}</p>

                      <div className={dashboardStyles.projectMeta}>
                        <div>
                          <span>Нээлттэй ажил</span>
                          <strong>{project.openTasks}</strong>
                        </div>
                        <div>
                          <span>Гүйцэтгэл</span>
                          <strong>{project.completion}%</strong>
                        </div>
                      </div>

                      <div className={dashboardStyles.progressTrack}>
                        <span style={{ width: `${project.completion}%` }} />
                      </div>

                      <div className={dashboardStyles.cardFooter}>
                        <span className={dashboardStyles.cardLinkLabel}>Ажлын ажилбар харах</span>
                        <strong aria-hidden>→</strong>
                      </div>
                    </Link>
                  ))}
                  </div>
                </>
              ) : (
                <div className={dashboardStyles.emptyColumnState}>
                  Одоогоор {selectedDepartmentName} дээр энэ ангиллын ажил алга байна.
                </div>
              )}
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}
