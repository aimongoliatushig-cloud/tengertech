"use client";

import { useState } from "react";

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
  canCreateTasks?: boolean;
  canWriteReports?: boolean;
  canViewQualityCenter?: boolean;
  canUseFieldConsole?: boolean;
  variant?: "default" | "executive";
  userName?: string;
  roleLabel?: string;
  masterMode?: boolean;
  workerMode?: boolean;
};

type MenuItem = {
  key: MenuKey;
  href: string;
  label: string;
  note: string;
  icon: string;
};

function ProfileGlyph({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden
    >
      <path
        d="M12 12C14.2091 12 16 10.2091 16 8C16 5.79086 14.2091 4 12 4C9.79086 4 8 5.79086 8 8C8 10.2091 9.79086 12 12 12Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M5.5 19.5C6.9 16.9 9.1 15.5 12 15.5C14.9 15.5 17.1 16.9 18.5 19.5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function AppMenu({
  active,
  canCreateProject = false,
  canCreateTasks = false,
  canWriteReports = false,
  canViewQualityCenter = false,
  canUseFieldConsole = false,
  variant = "default",
  userName = "Хэрэглэгч",
  roleLabel = "Систем",
  masterMode = false,
  workerMode = false,
}: AppMenuProps) {
  void canViewQualityCenter;

  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const createHubHref = "/create";
  const canOpenCreateHub = canCreateProject || canCreateTasks || canWriteReports;

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
            icon: "○",
          },
        ]
      : workerMode
        ? [
            {
              key: "dashboard",
              href: "/",
              label: "Миний ажил",
              note: "Надад хамаарах ажил",
              icon: "⌂",
            },
            ...(canUseFieldConsole
              ? [
                  {
                    key: "field",
                    href: "/field",
                    label: "Өнөөдрийн ажил",
                    note: "Тухайн өдрийн маршрут",
                    icon: "◎",
                  } satisfies MenuItem,
                ]
              : []),
            {
              key: "tasks",
              href: "/tasks",
              label: "Ажилбар",
              note: "Надад оноогдсон жагсаалт",
              icon: "≣",
            },
          ]
        : masterMode
          ? [
              {
                key: "dashboard",
                href: "/",
                label: "Нэгжийн самбар",
                note: "Өнөөдрийн хураангуй",
                icon: "⌂",
              },
              {
                key: "tasks",
                href: "/tasks",
                label: "Өнөөдрийн ажил",
                note: "Зөвхөн өнөөдөр харагдана",
                icon: "≣",
              },
              {
                key: "new-project",
                href: createHubHref,
                label: "Ажил нэмэх",
                note: "Өөрийн нэгжийн ажил үүсгэх",
                icon: "+",
              },
              {
                key: "reports",
                href: "/reports",
                label: "Тайлан",
                note: "Илгээсэн тайлан",
                icon: "○",
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
                      href: createHubHref,
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
                icon: "○",
              },
              {
                key: "data-download",
                href: "/data-download",
                label: "Өгөгдөл татах",
                note: "Файл ба тайлан",
                icon: "↓",
              },
            ];

  const menuTitle =
    variant === "executive"
      ? "Ерөнхий цэс"
      : masterMode
        ? "Мастерын цэс"
        : "Ажлын цэс";
  const activeItem =
    items.find((item) => item.key === active) ??
    (active === "new-project" && canOpenCreateHub
      ? {
          key: "new-project",
          href: createHubHref,
          label: "Нэмэх",
          note: "Шинэ үйлдэл сонгох",
          icon: "+",
        }
      : items[0]);
  const mobileItems = items.filter((item) => item.key !== "new-project");
  const mobileLeadingItems = mobileItems.slice(0, 2);
  const mobileTrailingItems = mobileItems.slice(2);

  function closeMobileSheets() {
    setIsProfileOpen(false);
  }

  function toggleProfile() {
    setIsProfileOpen((current) => !current);
  }

  return (
    <nav
      className={`${styles.menuShell} ${
        variant === "executive" ? styles.menuShellExecutive : ""
      }`}
      aria-label="Үндсэн цэс"
    >
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

      {isProfileOpen ? (
        <button
          type="button"
          className={styles.menuMobileBackdrop}
          aria-label="Хаах"
          onClick={closeMobileSheets}
        />
      ) : null}

      <div className={styles.menuMobileDock} aria-label="Хурдан цэс">
        {mobileLeadingItems.map((item) => (
          <Link
            key={`mobile-${item.key}`}
            href={item.href}
            className={`${styles.menuDockLink} ${
              active === item.key ? styles.menuDockLinkActive : ""
            }`}
            aria-current={active === item.key ? "page" : undefined}
            onClick={closeMobileSheets}
          >
            <span className={styles.menuDockIcon} aria-hidden>
              {item.icon}
            </span>
            <span className={styles.menuDockLabel}>{item.label}</span>
          </Link>
        ))}

        {canOpenCreateHub ? (
          <div className={styles.menuMobileQuickAdd}>
            <Link
              href={createHubHref}
              className={`${styles.menuDockAddTrigger} ${
                active === "new-project" ? styles.menuDockAddTriggerActive : ""
              }`}
              aria-label="Нэмэх цэс"
              onClick={closeMobileSheets}
            >
              <span className={styles.menuDockAddIcon} aria-hidden>
                +
              </span>
              <span className={styles.srOnly}>Нэмэх</span>
            </Link>
          </div>
        ) : null}

        {mobileTrailingItems.map((item) => (
          <Link
            key={`mobile-${item.key}`}
            href={item.href}
            className={`${styles.menuDockLink} ${
              active === item.key ? styles.menuDockLinkActive : ""
            }`}
            aria-current={active === item.key ? "page" : undefined}
            onClick={closeMobileSheets}
          >
            <span className={styles.menuDockIcon} aria-hidden>
              {item.icon}
            </span>
            <span className={styles.menuDockLabel}>{item.label}</span>
          </Link>
        ))}

        <div className={styles.menuMobileProfile}>
          <button
            type="button"
            className={styles.menuDockProfileTrigger}
            aria-expanded={isProfileOpen}
            onClick={toggleProfile}
          >
            <span
              className={`${styles.menuDockIcon} ${styles.menuDockProfileIcon}`}
              aria-hidden
            >
              <ProfileGlyph className={styles.menuDockProfileSvg} />
            </span>
            <span className={styles.menuDockLabel}>Профайл</span>
          </button>

          {isProfileOpen ? (
            <div className={styles.menuProfileSheet}>
              <div className={styles.menuProfileCard}>
                <div className={styles.menuProfileAvatar} aria-hidden>
                  <ProfileGlyph className={styles.menuProfileAvatarSvg} />
                </div>
                <div className={styles.menuProfileBody}>
                  <span>Профайл</span>
                  <strong>{userName}</strong>
                  <small>{roleLabel}</small>
                </div>
              </div>

              <div className={styles.menuProfileMeta}>
                <span>Одоогийн хэсэг</span>
                <strong>{activeItem?.label ?? menuTitle}</strong>
              </div>

              <form action={logoutAction}>
                <button type="submit" className={styles.menuProfileLogoutButton}>
                  Гарах
                </button>
              </form>
            </div>
          ) : null}
        </div>
      </div>

      <div className={styles.menuMobileCurrent}>
        <span>{activeItem?.label ?? menuTitle}</span>
      </div>
    </nav>
  );
}
