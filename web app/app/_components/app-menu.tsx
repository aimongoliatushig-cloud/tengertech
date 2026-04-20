import Image from "next/image";
import Link from "next/link";

import { logoutAction } from "@/app/actions";

import styles from "./app-menu.module.css";

type MenuKey =
  | "dashboard"
  | "tasks"
  | "field"
  | "projects"
  | "review"
  | "quality"
  | "new-project"
  | "reports"
  | "data-download";

type AppMenuProps = {
  active: MenuKey;
  canCreateProject?: boolean;
  canViewQualityCenter?: boolean;
  canUseFieldConsole?: boolean;
  variant?: "default" | "executive";
  userName?: string;
  roleLabel?: string;
};

type MenuItem = {
  key: MenuKey;
  href: string;
  label: string;
  note: string;
  icon: string;
};

export function AppMenu({
  active,
  canCreateProject = false,
  canViewQualityCenter = false,
  canUseFieldConsole = false,
  variant = "default",
  userName = "Хэрэглэгч",
  roleLabel = "Систем",
}: AppMenuProps) {
  void canViewQualityCenter;

  const items: MenuItem[] =
    variant === "executive"
      ? [
          {
            key: "dashboard",
            href: "/",
            label: "Хяналтын самбар",
            note: "Ерөнхий төлөв",
            icon: "⌂",
          },
          {
            key: "tasks",
            href: "/tasks",
            label: "Өнөөдрийн ажил",
            note: "Ажилбарын жагсаалт",
            icon: "≣",
          },
          {
            key: "reports",
            href: "/reports",
            label: "Тайлан",
            note: "Хяналт ба тайлан",
            icon: "◫",
          },
        ]
      : [
          ...(canUseFieldConsole
            ? [
                {
                  key: "field",
                  href: "/field",
                  label: "Өнөөдрийн маршрут",
                  note: "Талбайн ажил",
                  icon: "◎",
                } satisfies MenuItem,
              ]
            : []),
          {
            key: "dashboard",
            href: "/",
            label: "Хяналтын самбар",
            note: "Нүүр хуудас",
            icon: "⌂",
          },
          {
            key: "projects",
            href: "/projects",
            label: "Ажил",
            note: "Ажлын жагсаалт",
            icon: "▣",
          },
          {
            key: "review",
            href: "/review",
            label: "Хяналт",
            note: "Баталгаажуулалт",
            icon: "✓",
          },
          ...(canCreateProject
            ? [
                {
                  key: "new-project",
                  href: "/projects/new",
                  label: "Шинэ ажил",
                  note: "Шууд үүсгэх",
                  icon: "+",
                } satisfies MenuItem,
              ]
            : []),
          {
            key: "reports",
            href: "/reports",
            label: "Тайлан",
            note: "Өдрийн урсгал",
            icon: "◫",
          },
          {
            key: "data-download",
            href: "/data-download",
            label: "Өгөгдөл татах",
            note: "Файл ба тайлан",
            icon: "↓",
          },
        ];

  const toggleId = variant === "executive" ? "executive-menu-toggle" : "default-menu-toggle";
  const menuTitle = variant === "executive" ? "Ерөнхий цэс" : "Ажлын цэс";
  const activeItem = items.find((item) => item.key === active) ?? items[0];

  return (
    <nav
      className={`${styles.menuShell} ${
        variant === "executive" ? styles.menuShellExecutive : ""
      }`}
      aria-label="Үндсэн цэс"
    >
      <input id={toggleId} type="checkbox" className={styles.menuToggleInput} />

      <div className={styles.menuMobileSpacer} />

      <div className={styles.menuMobileBar}>
        <label htmlFor={toggleId} className={styles.menuToggleButton}>
          <span className={styles.menuToggleIcon} aria-hidden>
            ☰
          </span>
        </label>

        <div className={styles.menuMobileBrand}>
          <Image
            src="/logo.png"
            alt="Хот тохижилтын удирдлагын төв"
            width={94}
            height={30}
            className={styles.menuMobileLogo}
            unoptimized
          />
          <span>{activeItem?.label ?? menuTitle}</span>
        </div>
      </div>

      <label htmlFor={toggleId} className={styles.menuOverlay} />

      <aside
        className={`${styles.menuBar} ${
          variant === "executive" ? styles.menuBarExecutive : ""
        }`}
      >
        <div className={styles.menuHeader}>
          <div className={styles.menuBrand}>
            <div className={styles.menuBrandLogo}>
              <Image
                src="/logo.png"
                alt="Хот тохижилтын удирдлагын төв"
                width={108}
                height={34}
                className={styles.menuLogo}
                unoptimized
              />
            </div>
            <div className={styles.menuBrandText}>
              <span className={styles.menuKicker}>Навигаци</span>
              <strong>{menuTitle}</strong>
            </div>
          </div>

          <label htmlFor={toggleId} className={styles.menuCloseButton}>
            ×
          </label>
        </div>

        <div className={styles.menuUserCard}>
          <span>Нэвтэрсэн хэрэглэгч</span>
          <strong>{userName}</strong>
          <div className={styles.menuUserMeta}>
            <small>{roleLabel}</small>
          </div>
        </div>

        <div className={styles.menuScrollArea}>
          <div className={styles.menuInner}>
            {items.map((item) => (
              <Link
                key={item.key}
                href={item.href}
                className={`${styles.menuLink} ${active === item.key ? styles.menuLinkActive : ""}`}
                aria-current={active === item.key ? "page" : undefined}
              >
                <span className={styles.menuLinkIcon} aria-hidden>
                  {item.icon}
                </span>
                <span className={styles.menuLinkBody}>
                  <span className={styles.menuLabel}>{item.label}</span>
                  <small className={styles.menuNote}>{item.note}</small>
                </span>
              </Link>
            ))}
          </div>
        </div>

        <div className={styles.menuFooter}>
          <form action={logoutAction}>
            <button type="submit" className={styles.menuLogoutButton}>
              Гарах
            </button>
          </form>
        </div>
      </aside>
    </nav>
  );
}
