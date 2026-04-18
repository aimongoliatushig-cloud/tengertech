import Link from "next/link";

import { AppMenu } from "@/app/_components/app-menu";
import { createProjectAction, logoutAction } from "@/app/actions";
import styles from "@/app/workspace.module.css";
import { getRoleLabel, requireSession } from "@/lib/auth";
import { loadDepartmentOptions, loadProjectManagerOptions } from "@/lib/workspace";

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

  const [managerOptions, departmentOptions] = await Promise.all([
    loadProjectManagerOptions({
      login: session.login,
      password: session.password,
    }),
    loadDepartmentOptions({
      login: session.login,
      password: session.password,
    }),
  ]);

  const canCreateProject =
    session.role === "general_manager" || session.role === "system_admin";

  return (
    <main className={styles.shell}>
      <div className={styles.container} id="create-project-top">
        <header className={styles.navBar}>
          <div className={styles.navLinks}>
            <Link href="/" className={styles.backLink}>
              Хяналтын самбар
            </Link>
            <span>{getRoleLabel(session.role)}</span>
          </div>

          <div className={styles.navActions}>
            <form action={logoutAction}>
              <button type="submit" className={styles.secondaryButton}>
                Гарах
              </button>
            </form>
          </div>
        </header>

        <AppMenu active="new-project" canCreateProject={canCreateProject} />

        <section className={styles.heroCard}>
          <span className={styles.eyebrow}>Төсөл бүртгэх</span>
          <h1>Шинэ төсөл нэмэх</h1>
          <p>
            Алба нэгжийг нь сонгоод шинэ төсөл бүртгэнэ. Алба нэгж дээр төслийн
            удирдагч урьдчилан тохируулагдсан бол төсөл үүсэх үед автоматаар
            бөглөгдөнө.
          </p>
        </section>

        <nav className={styles.jumpRail} aria-label="Create project quick navigation">
          <a href="#project-form" className={styles.jumpLink}>
            Form
          </a>
          <a href="#create-project-top" className={styles.jumpLink}>
            Дээш
          </a>
        </nav>

        {errorMessage ? (
          <div className={`${styles.message} ${styles.errorMessage}`}>{errorMessage}</div>
        ) : null}
        {noticeMessage ? (
          <div className={`${styles.message} ${styles.noticeMessage}`}>{noticeMessage}</div>
        ) : null}

        {!canCreateProject ? (
          <section className={styles.emptyState}>
            <h2>Төсөл бүртгэх эрх алга</h2>
            <p>
              Шинэ төсөл нэмэх боломж одоогоор зөвхөн ерөнхий менежер болон
              системийн админ хэрэглэгч дээр нээлттэй байна.
            </p>
          </section>
        ) : (
          <section className={styles.formCard} id="project-form">
            <form action={createProjectAction} className={styles.form}>
              <div className={styles.field}>
                <label htmlFor="name">Төслийн нэр</label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  placeholder="Жишээ: Хан-Уулын хаврын тохижилтын ажил"
                  required
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="department_id">Алба нэгж</label>
                <select id="department_id" name="department_id" defaultValue="" required>
                  <option value="">Алба нэгж сонгоно уу</option>
                  {departmentOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className={styles.fieldRow}>
                <div className={styles.field}>
                  <label htmlFor="manager_id">Төслийн удирдагч</label>
                  <select id="manager_id" name="manager_id" defaultValue="">
                    <option value="">Автоматаар эсвэл дараа нь сонгоно</option>
                    {managerOptions.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.name} ({option.login})
                      </option>
                    ))}
                  </select>
                </div>

                <div className={styles.field}>
                  <label htmlFor="start_date">Эхлэх огноо</label>
                  <input id="start_date" name="start_date" type="date" />
                </div>

                <div className={styles.field}>
                  <label htmlFor="deadline">Дуусах огноо</label>
                  <input id="deadline" name="deadline" type="date" />
                </div>
              </div>

              <div className={styles.optionalSection}>
                <input
                  id="track_quantity"
                  name="track_quantity"
                  type="checkbox"
                  value="1"
                  className={styles.optionalCheckbox}
                />
                <label htmlFor="track_quantity" className={styles.optionalToggle}>
                  <span className={styles.optionalToggleTitle}>
                    Төлөвлөсөн хэмжээ авах
                  </span>
                  <span className={styles.optionalToggleText}>
                    Чек хийсэн үед төсөл дээр төлөвлөсөн хэмжээ болон хэмжих нэгжийг
                    бүртгэнэ.
                  </span>
                </label>

                <div className={styles.optionalFields}>
                  <div className={styles.field}>
                    <label htmlFor="planned_quantity">Төлөвлөсөн хэмжээ</label>
                    <input
                      id="planned_quantity"
                      name="planned_quantity"
                      type="number"
                      min="0"
                      step="0.01"
                      placeholder="48"
                    />
                  </div>

                  <div className={styles.field}>
                    <label htmlFor="measurement_unit">Хэмжих нэгж</label>
                    <input
                      id="measurement_unit"
                      name="measurement_unit"
                      type="text"
                      placeholder="мод"
                    />
                  </div>
                </div>
              </div>

              <div className={styles.buttonRow}>
                <button type="submit" className={styles.primaryButton}>
                  Төсөл үүсгэх
                </button>
                <Link href="/projects" className={styles.smallLink}>
                  Төслүүд рүү очих
                </Link>
              </div>
            </form>
          </section>
        )}

        <nav className={styles.mobileDock} aria-label="Create project mobile navigation">
          <a href="#project-form" className={styles.jumpLink}>
            Form
          </a>
          <Link href="/" className={styles.jumpLink}>
            Нүүр
          </Link>
          <a href="#create-project-top" className={styles.jumpLink}>
            Дээш
          </a>
        </nav>
      </div>
    </main>
  );
}
