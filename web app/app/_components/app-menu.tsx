import Link from "next/link";

import styles from "./app-menu.module.css";

type MenuKey =
  | "dashboard"
  | "field"
  | "projects"
  | "review"
  | "new-project"
  | "reports"
  | "data-download";

type AppMenuProps = {
  active: MenuKey;
  canCreateProject?: boolean;
};

type MenuItem = {
  key: MenuKey;
  href: string;
  label: string;
};

export function AppMenu({ active, canCreateProject = false }: AppMenuProps) {
  const items: MenuItem[] = [
    { key: "field", href: "/field", label: "Today route" },
    { key: "dashboard", href: "/", label: "Хяналтын самбар" },
    { key: "projects", href: "/projects", label: "Төсөл хянах" },
    { key: "review", href: "/review", label: "Шалгах ажлууд" },
    ...(canCreateProject
      ? [{ key: "new-project", href: "/projects/new", label: "Төсөл нэмэх" } satisfies MenuItem]
      : []),
    { key: "reports", href: "/reports", label: "Тайлан" },
    { key: "data-download", href: "/data-download", label: "Дата татах" },
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
