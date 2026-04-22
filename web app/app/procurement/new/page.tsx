import { ProcurementShell } from "@/app/procurement/_components/procurement-shell";
import { createProcurementRequestAction } from "@/app/procurement/actions";
import { requireSession } from "@/lib/auth";
import { loadProcurementMe, loadProcurementMeta } from "@/lib/procurement";

import styles from "../procurement.module.css";

type PageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

function getValue(value?: string | string[]) {
  return Array.isArray(value) ? value[0] || "" : value || "";
}

export const dynamic = "force-dynamic";

export default async function NewProcurementPage({ searchParams }: PageProps) {
  const session = await requireSession();
  const params = (await searchParams) || {};
  const notice = getValue(params.notice);
  const error = getValue(params.error);
  const connectionOverrides = {
    login: session.login,
    password: session.password,
  };
  const [procurementUser, meta] = await Promise.all([
    loadProcurementMe(connectionOverrides),
    loadProcurementMeta(connectionOverrides),
  ]);

  return (
    <ProcurementShell
      session={session}
      procurementUser={procurementUser}
      title="Шинэ худалдан авалтын хүсэлт"
      description="Төсөл эсвэл ажилбартай шууд холбож, шаардлагатай бараа, үйлчилгээ, сэлбэгийн хэрэгцээг хурдан бүртгэнэ."
      activeTab="new"
    >
      {notice ? <section className={styles.cardSection}>{notice}</section> : null}
      {error ? <section className={styles.cardSection}>{error}</section> : null}

      {!procurementUser.flags.requester && !procurementUser.flags.admin ? (
        <section className={styles.cardSection}>
          <div className={styles.emptyState}>Танд шинэ худалдан авалтын хүсэлт үүсгэх эрх алга.</div>
        </section>
      ) : (
        <section className={styles.cardSection}>
          <div className={styles.sectionHeader}>
            <div>
              <h2>Хүсэлтийн маягт</h2>
              <p>Гарчиг, төсөл, нярав, хэрэгцээний мөрүүдийг бөглөөд хүсэлтээ ноорог хэлбэрээр үүсгэнэ.</p>
            </div>
          </div>
          <form action={createProcurementRequestAction} className={styles.quoteForm}>
            <div className={styles.filterRow}>
              <label className={styles.fieldLabel}>
                Гарчиг
                <input name="title" placeholder="Жишээ: Замын материалын худалдан авалт" required />
              </label>
              <label className={styles.fieldLabel}>
                Төсөл
                <select name="project_id" defaultValue="">
                  <option value="">Сонгох</option>
                  {meta.projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className={styles.fieldLabel}>
                Ажилбар
                <select name="task_id" defaultValue="">
                  <option value="">Сонгох</option>
                  {meta.tasks.map((task) => (
                    <option key={task.id} value={task.id}>
                      {task.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className={styles.fieldLabel}>
                Алба нэгж
                <select name="department_id" defaultValue="">
                  <option value="">Сонгох</option>
                  {meta.departments.map((department) => (
                    <option key={department.id} value={department.id}>
                      {department.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className={styles.fieldLabel}>
                Хариуцсан нярав
                <select name="responsible_storekeeper_user_id" required defaultValue="">
                  <option value="">Сонгох</option>
                  {meta.storekeepers.map((storekeeper) => (
                    <option key={storekeeper.id} value={storekeeper.id}>
                      {storekeeper.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className={styles.fieldLabel}>
                Хэрэгцээний төрөл
                <select name="procurement_type" defaultValue="goods">
                  <option value="goods">Бараа</option>
                  <option value="service">Үйлчилгээ</option>
                  <option value="spare_part">Сэлбэг</option>
                  <option value="other">Бусад</option>
                </select>
              </label>
              <label className={styles.fieldLabel}>
                Яаралтай түвшин
                <select name="urgency" defaultValue="medium">
                  <option value="low">Бага</option>
                  <option value="medium">Дунд</option>
                  <option value="high">Өндөр</option>
                  <option value="critical">Яаралтай</option>
                </select>
              </label>
              <label className={styles.fieldLabel}>
                Шаардлагатай огноо
                <input type="date" name="required_date" />
              </label>
            </div>

            <label className={styles.fieldLabel}>
              Тайлбар / зорилго
              <textarea
                name="description"
                placeholder="Юунд зориулж, ямар хэрэгцээтэй байгааг дэлгэрэнгүй бичнэ үү."
              />
            </label>

            <section className={styles.cardSection}>
              <div className={styles.sectionHeader}>
                <div>
                  <h3>Хүсэлтийн мөрүүд</h3>
                  <p>Доорх мөрүүдээс хэрэгтэй хэсгээ бөглөнө. Хоосон мөрүүд автоматаар алгасагдана.</p>
                </div>
              </div>
              <div className={styles.quoteGrid}>
                {[1, 2, 3, 4].map((index) => (
                  <article key={index} className={styles.quoteCard}>
                    <h3>Мөр {index}</h3>
                    <label>
                      Нэр
                      <input name="line_name" placeholder="Бараа / үйлчилгээний нэр" />
                    </label>
                    <label>
                      Тодорхойлолт
                      <textarea name="line_specification" placeholder="Техникийн шаардлага, тайлбар" />
                    </label>
                    <label>
                      Тоо хэмжээ
                      <input type="number" step="0.01" min="0" name="line_quantity" />
                    </label>
                    <label>
                      Хэмжих нэгж
                      <select name="line_uom_id" defaultValue="">
                        <option value="">Сонгох</option>
                        {meta.uoms.map((uom) => (
                          <option key={uom.id} value={uom.id}>
                            {uom.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Ойролцоох нэгж үнэ
                      <input type="number" step="0.01" min="0" name="line_approx_unit_price" />
                    </label>
                  </article>
                ))}
              </div>
            </section>

            <label className={styles.fieldLabel}>
              Хэрэглэгчийн тэмдэглэл
              <textarea name="notes_user" placeholder="Нэмэлт нөхцөл, ажлын онцлог" />
            </label>

            <label className={styles.fieldLabel}>
              Хавсралт
              <input type="file" name="request_files" multiple />
            </label>

            <div className={styles.buttonRow}>
              <button type="submit" className={styles.primaryButton}>
                Хүсэлт үүсгэх
              </button>
            </div>
          </form>
        </section>
      )}
    </ProcurementShell>
  );
}
