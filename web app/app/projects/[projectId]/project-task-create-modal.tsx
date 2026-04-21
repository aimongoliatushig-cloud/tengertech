"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

import styles from "@/app/workspace.module.css";
import type { SelectOption } from "@/lib/workspace";

type Props = {
  action: (formData: FormData) => void | Promise<void>;
  projectId: number;
  deadline: string;
  masterMode: boolean;
  teamLeaderOptions: SelectOption[];
  defaultOpen?: boolean;
};

export function ProjectTaskCreateModal({
  action,
  projectId,
  deadline,
  masterMode,
  teamLeaderOptions,
  defaultOpen = false,
}: Props) {
  const [isOpen, setIsOpen] = useState(() => {
    if (typeof window === "undefined") {
      return defaultOpen;
    }

    return defaultOpen || window.location.hash === "#task-create-form";
  });

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const previousBodyOverflow = document.body.style.overflow;
    const previousHtmlOverflow = document.documentElement.style.overflow;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };

    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousBodyOverflow;
      document.documentElement.style.overflow = previousHtmlOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const portalTarget = typeof document === "undefined" ? null : document.body;

  const modalContent =
    portalTarget && isOpen
      ? createPortal(
          <div
            className={styles.modalOverlay}
            role="presentation"
            onClick={() => setIsOpen(false)}
          >
            <div
              className={styles.modalDialog}
              role="dialog"
              aria-modal="true"
              aria-labelledby="project-task-create-title"
              onClick={(event) => event.stopPropagation()}
            >
              <div className={styles.modalHeader}>
                <div className={styles.modalTitleGroup}>
                  <span className={styles.eyebrow}>Шинэ ажилбар</span>
                  <strong className={styles.modalTitle} id="project-task-create-title">
                    {masterMode ? "Өнөөдрийн ажил нэмэх" : "Ажилбар үүсгэх"}
                  </strong>
                  <p className={styles.modalLead}>
                    Товч мэдээллээ оруулаад энэ ажлын дотор шинэ ажилбар нээнэ.
                  </p>
                </div>

                <button
                  type="button"
                  className={styles.modalCloseButton}
                  aria-label="Цонх хаах"
                  onClick={() => setIsOpen(false)}
                >
                  Хаах
                </button>
              </div>

              <form action={action} className={styles.modalForm}>
                <input type="hidden" name="project_id" value={projectId} />

                <div className={styles.field}>
                  <label htmlFor="task-name">Ажилбарын нэр</label>
                  <input
                    id="task-name"
                    name="name"
                    type="text"
                    placeholder="Жишээ: Хогийн савны тойргийн цэвэрлэгээ"
                    required
                  />
                </div>

                {!masterMode ? (
                  <div className={styles.field}>
                    <label htmlFor="task-team-leader">Хариуцсан мастер</label>
                    <select id="task-team-leader" name="team_leader_id" defaultValue="">
                      <option value="">Сонгоогүй</option>
                      {teamLeaderOptions.map((option) => (
                        <option key={option.id} value={option.id}>
                          {option.name}
                        </option>
                      ))}
                    </select>
                  </div>
                ) : null}

                <div className={styles.field}>
                  <label htmlFor="task-deadline">Хугацаа</label>
                  <input
                    id="task-deadline"
                    name="deadline"
                    type="date"
                    defaultValue={deadline}
                  />
                </div>

                <div className={styles.field}>
                  <label htmlFor="task-planned-quantity">Төлөвлөсөн хэмжээ</label>
                  <input
                    id="task-planned-quantity"
                    name="planned_quantity"
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="0"
                  />
                </div>

                <div className={styles.field}>
                  <label htmlFor="task-measurement-unit">Хэмжих нэгж</label>
                  <input
                    id="task-measurement-unit"
                    name="measurement_unit"
                    type="text"
                    placeholder="ш, м.кв, рейс"
                  />
                </div>

                <div className={styles.field}>
                  <label htmlFor="task-description">Товч тайлбар</label>
                  <textarea
                    id="task-description"
                    name="description"
                    placeholder="Өнөөдөр хийх ажлын хүрээ, байршил, онцгой зааврыг товч бичнэ."
                  />
                </div>

                <div className={styles.modalActions}>
                  <button
                    type="button"
                    className={styles.secondaryButton}
                    onClick={() => setIsOpen(false)}
                  >
                    Болих
                  </button>
                  <button type="submit" className={styles.primaryButton}>
                    {masterMode ? "Ажил нэмэх" : "Ажилбар үүсгэх"}
                  </button>
                </div>
              </form>
            </div>
          </div>,
          portalTarget,
        )
      : null;

  return (
    <>
      <div id="task-create-form" className={styles.createTaskTriggerWrap}>
        <button
          type="button"
          className={`${styles.primaryButton} ${styles.createTaskTrigger}`}
          onClick={() => setIsOpen(true)}
        >
          Ажил нэмэх
        </button>
      </div>
      {modalContent}
    </>
  );
}
