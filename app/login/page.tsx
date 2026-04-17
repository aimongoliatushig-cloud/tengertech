import { redirect } from "next/navigation";

import { loginAction } from "@/app/actions";
import { getSession } from "@/lib/auth";

import styles from "./page.module.css";

type LoginPageProps = {
  searchParams?: Promise<{
    error?: string | string[];
  }>;
};

function getErrorMessage(code?: string) {
  switch (code) {
    case "missing":
      return "Нэвтрэх нэр болон нууц үгээ бөглөнө үү.";
    case "invalid":
      return "Нэвтрэх мэдээлэл буруу байна. Odoo дээрх хэрэглэгчийн нэр, нууц үгээ шалгана уу.";
    case "connection":
      return "Odoo сервертэй холбогдож чадсангүй. Odoo ажиллаж байгаа эсэхийг шалгана уу.";
    default:
      return "";
  }
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const session = await getSession();
  if (session) {
    redirect("/");
  }

  const params = (await searchParams) ?? {};
  const errorCode = Array.isArray(params.error) ? params.error[0] : params.error;
  const errorMessage = getErrorMessage(errorCode);

  return (
    <main className={styles.shell}>
      <section className={styles.infoPanel}>
        <span className={styles.eyebrow}>Municipal Operations Platform</span>
        <h1>Хот тохижилтын веб апп</h1>
        <p>
          Odoo ERP дээрх төслийн урсгал, талбарын тайлан, review queue, багийн
          бүтэц, хэмжээг нэг дэлгэц дээр нэгтгэсэн mobile-friendly web app.
        </p>

        <div className={styles.featureGrid}>
          <article className={styles.featureCard}>
            <strong>Ерөнхий менежер</strong>
            <span>Review queue, KPI, live progress, proof of work feed</span>
          </article>
          <article className={styles.featureCard}>
            <strong>Багийн ахлагч</strong>
            <span>Task, тайлан, зураг, аудио, хэмжээг нэг урсгалаар удирдана</span>
          </article>
          <article className={styles.featureCard}>
            <strong>Mobile ready</strong>
            <span>Утсан дээр нэг гараар ашиглахад эвтэйхэн layout-тай</span>
          </article>
        </div>
      </section>

      <section className={styles.formPanel}>
        <div className={styles.formHeader}>
          <span className={styles.formBadge}>Odoo Login</span>
          <h2>Нэвтрэх</h2>
          <p>
            Odoo дээрх одоогийн хэрэглэгчийн нэр, нууц үгээрээ шууд орно.
            Odoo ERP рүү тусдаа нэвтрэх шаардлагагүй.
          </p>
        </div>

        <form action={loginAction} className={styles.form}>
          <label className={styles.field}>
            <span>Нэвтрэх нэр</span>
            <input
              name="login"
              type="text"
              placeholder="Жишээ нь: admin эсвэл suldee@gmail.com"
              autoComplete="username"
              required
            />
          </label>

          <label className={styles.field}>
            <span>Нууц үг</span>
            <input
              name="password"
              type="password"
              placeholder="Нууц үгээ оруулна уу"
              autoComplete="current-password"
              required
            />
          </label>

          {errorMessage ? <p className={styles.errorBox}>{errorMessage}</p> : null}

          <button type="submit" className={styles.submitButton}>
            Дашбоард руу нэвтрэх
          </button>
        </form>

        <div className={styles.footerHint}>
          <span>Default demo access</span>
          <strong>`admin / admin`</strong>
        </div>
      </section>
    </main>
  );
}
