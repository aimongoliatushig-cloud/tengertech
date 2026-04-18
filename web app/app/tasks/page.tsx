import Link from "next/link";

import { AppMenu } from "@/app/_components/app-menu";
import { logoutAction } from "@/app/actions";
import dashboardStyles from "@/app/page.module.css";
import shellStyles from "@/app/workspace.module.css";
import styles from "@/app/tasks/tasks.module.css";
import { getRoleLabel, requireSession } from "@/lib/auth";
import { loadGarbageExecutiveSnapshot } from "@/lib/garbage-executive";

type PageProps = {
  searchParams?: Promise<{
    date?: string | string[];
    filter?: string | string[];
  }>;
};

function getParam(value?: string | string[]) {
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
}

function createFilterHref(date: string, filter: string) {
  const params = new URLSearchParams({ date });
  if (filter !== "all") {
    params.set("filter", filter);
  }
  return `/tasks?${params.toString()}`;
}

export const dynamic = "force-dynamic";

export default async function TasksPage({ searchParams }: PageProps) {
  const session = await requireSession();
  const params = (await searchParams) ?? {};
  const selectedDate = getParam(params.date);
  const selectedFilter = getParam(params.filter) || "all";

  const snapshot = await loadGarbageExecutiveSnapshot(
    {
      login: session.login,
      password: session.password,
    },
    selectedDate,
  );

  const filterItems = [
    { key: "all", label: "Бүгд", count: snapshot.todayTasks.length },
    {
      key: "working",
      label: "Ажиллаж байна",
      count: snapshot.todayTasks.filter((task) => task.statusKey === "working").length,
    },
    {
      key: "review",
      label: "Шалгаж байна",
      count: snapshot.todayTasks.filter((task) => task.statusKey === "review").length,
    },
    {
      key: "problem",
      label: "Асуудалтай",
      count: snapshot.todayTasks.filter((task) => task.statusKey === "problem").length,
    },
    {
      key: "verified",
      label: "Баталгаажсан",
      count: snapshot.todayTasks.filter((task) => task.statusKey === "verified").length,
    },
  ];

  const visibleTasks =
    selectedFilter === "all"
      ? snapshot.todayTasks
      : snapshot.todayTasks.filter((task) => task.statusKey === selectedFilter);
  const returnTo = createFilterHref(snapshot.selectedDateInput, selectedFilter);

  return (
    <main className={shellStyles.shell}>
      <div className={shellStyles.container}>
        <header className={shellStyles.navBar}>
          <div className={shellStyles.navLinks}>
            <Link href="/" className={shellStyles.backLink}>
              Хяналтын самбар
            </Link>
            <span>{getRoleLabel(session.role)}</span>
          </div>

          <div className={shellStyles.navActions}>
            <form action={logoutAction}>
              <button type="submit" className={shellStyles.secondaryButton}>
                Гарах
              </button>
            </form>
          </div>
        </header>

        <AppMenu active="tasks" variant="executive" />

        <section className={shellStyles.heroCard}>
          <span className={shellStyles.eyebrow}>Өдрийн жагсаалт</span>
          <h1>Өнөөдрийн ажил</h1>
          <p>
            {snapshot.selectedDateLabel}-ний хог тээвэрлэлтийн ажлын жагсаалт. Төлөвөөр
            шүүгээд асуудалтай эсвэл шалгалт хүлээж буй ажлууд руу шууд орж болно.
          </p>
        </section>

        <section className={styles.toolbar}>
          <form className={styles.dateFilterForm} method="get">
            <label htmlFor="task-date">Огноо</label>
            <div className={styles.dateRow}>
              <input
                id="task-date"
                type="date"
                name="date"
                defaultValue={snapshot.selectedDateInput}
                className={styles.dateInput}
              />
              <button type="submit" className={styles.dateButton}>
                Харах
              </button>
            </div>
          </form>

          <div className={styles.filterTabs} aria-label="Төлөвийн шүүлтүүр">
            {filterItems.map((item) => (
              <Link
                key={item.key}
                href={createFilterHref(snapshot.selectedDateInput, item.key)}
                className={`${styles.filterTab} ${
                  selectedFilter === item.key ? styles.filterTabActive : ""
                }`}
                aria-current={selectedFilter === item.key ? "page" : undefined}
              >
                <span>{item.label}</span>
                <strong>{item.count}</strong>
              </Link>
            ))}
          </div>
        </section>

        <section className={styles.tableShell}>
          <table className={styles.taskTable}>
            <thead>
              <tr>
                <th>Машин</th>
                <th>Жолооч</th>
                <th>Маршрут</th>
                <th>Төлөв</th>
                <th>Явц</th>
                <th>Өдрийн эцсийн жин</th>
                <th>Дэлгэрэнгүй</th>
              </tr>
            </thead>
            <tbody>
              {visibleTasks.map((task) => (
                <tr key={task.id}>
                  <td>{task.vehicleName}</td>
                  <td>{task.driverName}</td>
                  <td>{task.routeName}</td>
                  <td>
                    <span
                      className={`${dashboardStyles.statusBadge} ${
                        dashboardStyles[`status${task.statusKey}`]
                      }`}
                    >
                      {task.statusLabel}
                    </span>
                  </td>
                  <td>
                    <div className={styles.progressCell}>
                      <span>{task.progress}%</span>
                      <div className={styles.progressTrack}>
                        <span style={{ width: `${task.progress}%` }} />
                      </div>
                    </div>
                  </td>
                  <td>{task.finalWeightLabel}</td>
                  <td>
                    <Link
                      href={`/tasks/${task.id}?returnTo=${encodeURIComponent(returnTo)}`}
                      className={styles.detailLink}
                    >
                      Харах
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {!visibleTasks.length ? (
            <div className={shellStyles.emptyState}>
              <h2>Ажил олдсонгүй</h2>
              <p>Сонгосон төлөвөөр харагдах хог тээвэрлэлтийн ажил алга.</p>
            </div>
          ) : null}
        </section>
      </div>
    </main>
  );
}
