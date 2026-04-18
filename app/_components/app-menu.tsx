import Link from "next/link";

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
};

type MenuItem = {
  key: MenuKey;
  href: string;
  label: string;
};

export function AppMenu({
  active,
  canCreateProject = false,
  canViewQualityCenter = false,
  canUseFieldConsole = false,
  variant = "default",
}: AppMenuProps) {
  const items: MenuItem[] =
    variant === "executive"
      ? [
          { key: "dashboard", href: "/", label: "Хяналтын самбар" },
          { key: "tasks", href: "/tasks", label: "Өнөөдрийн ажил" },
          { key: "reports", href: "/reports", label: "Тайлан" },
        ]
      : [
          ...(canUseFieldConsole
            ? [
                {
                  key: "field",
                  href: "/field",
                  label: "Өнөөдрийн маршрут",
                } satisfies MenuItem,
              ]
            : []),
          { key: "dashboard", href: "/", label: "Хяналтын самбар" },
          { key: "projects", href: "/projects", label: "Төслүүд" },
          { key: "review", href: "/review", label: "Шалгалт" },
          ...(canViewQualityCenter
            ? [{ key: "quality", href: "/quality", label: "Чанар" } satisfies MenuItem]
            : []),
          ...(canCreateProject
            ? [
                {
                  key: "new-project",
                  href: "/projects/new",
                  label: "Шинэ төсөл",
                } satisfies MenuItem,
              ]
            : []),
          { key: "reports", href: "/reports", label: "Тайлан" },
          { key: "data-download", href: "/data-download", label: "Өгөгдөл татах" },
        ];

  return (
    <nav className={styles.menuBar} aria-label="Үндсэн цэс">
      <div className={styles.menuInner}>
        {items.map((item) => (
          <Link
            key={item.key}
            href={item.href}
            className={`${styles.menuLink} ${active === item.key ? styles.menuLinkActive : ""}`}
            aria-current={active === item.key ? "page" : undefined}
          >
            {item.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
