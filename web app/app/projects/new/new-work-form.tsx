"use client";

import { useMemo, useState } from "react";

import styles from "@/app/workspace.module.css";
import type {
  DepartmentOption,
  GarbageRouteOption,
  GarbageVehicleOption,
  SelectOption,
} from "@/lib/workspace";

const COMBINED_DEPARTMENT_NAME = "Авто бааз, хог тээвэрлэлтийн хэлтэс";

type Props = {
  action: (formData: FormData) => void | Promise<void>;
  departmentOptions: DepartmentOption[];
  managerOptions: SelectOption[];
  garbageVehicleOptions: GarbageVehicleOption[];
  garbageRouteOptions: GarbageRouteOption[];
  lockedDepartmentId?: string;
  lockedDepartmentLabel?: string;
};

function getTodayValue() {
  return new Date().toISOString().slice(0, 10);
}

function formatShiftLabel(shiftType: string) {
  switch (shiftType) {
    case "morning":
      return "Өглөө";
    case "day":
      return "Өдөр";
    case "evening":
      return "Орой";
    case "night":
      return "Шөнө";
    default:
      return "Тодорхойгүй";
  }
}

function formatDateLabel(value: string) {
  if (!value) {
    return "Огноо сонгоно уу";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("mn-MN", {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(parsed);
}

export function NewWorkForm({
  action,
  departmentOptions,
  managerOptions,
  garbageVehicleOptions,
  garbageRouteOptions,
  lockedDepartmentId,
  lockedDepartmentLabel,
}: Props) {
  const [departmentId, setDepartmentId] = useState(lockedDepartmentId ?? "");
  const [operationUnit, setOperationUnit] = useState(() => {
    const initialDepartment = departmentOptions.find(
      (option) => String(option.id) === (lockedDepartmentId ?? ""),
    );

    return initialDepartment?.name === COMBINED_DEPARTMENT_NAME
      ? "garbage_transport"
      : "standard";
  });
  const [vehicleId, setVehicleId] = useState("");
  const [routeId, setRouteId] = useState("");
  const [shiftDate, setShiftDate] = useState(getTodayValue());

  const selectedDepartment = useMemo(
    () => departmentOptions.find((option) => String(option.id) === departmentId) ?? null,
    [departmentId, departmentOptions],
  );
  const selectedVehicle = useMemo(
    () => garbageVehicleOptions.find((option) => String(option.id) === vehicleId) ?? null,
    [garbageVehicleOptions, vehicleId],
  );
  const selectedRoute = useMemo(
    () => garbageRouteOptions.find((option) => String(option.id) === routeId) ?? null,
    [garbageRouteOptions, routeId],
  );

  const isCombinedDepartment = selectedDepartment?.name === COMBINED_DEPARTMENT_NAME;
  const isGarbageTransport = isCombinedDepartment && operationUnit === "garbage_transport";
  const isDepartmentLocked = Boolean(lockedDepartmentId);

  const generatedName = useMemo(() => {
    if (!isGarbageTransport) {
      return "";
    }

    const vehicleLabel = selectedVehicle?.plate || "Машины дугаар";
    const routeLabel = selectedRoute?.code || selectedRoute?.name || "Маршрут";
    return `${vehicleLabel} - ${routeLabel} / ${shiftDate}`;
  }, [isGarbageTransport, selectedRoute, selectedVehicle, shiftDate]);

  const handleDepartmentChange = (nextDepartmentId: string) => {
    setDepartmentId(nextDepartmentId);
    const nextDepartment = departmentOptions.find(
      (option) => String(option.id) === nextDepartmentId,
    );

    if (nextDepartment?.name === COMBINED_DEPARTMENT_NAME) {
      setOperationUnit("garbage_transport");
      return;
    }

    setOperationUnit("standard");
  };

  return (
    <form action={action} className={styles.form}>
      {isDepartmentLocked ? (
        <div className={styles.field}>
          <label>Хэлтэс</label>
          <div className={styles.lockedFieldValue}>
            {lockedDepartmentLabel ?? selectedDepartment?.label ?? selectedDepartment?.name}
          </div>
          <input type="hidden" name="department_id" value={departmentId} />
        </div>
      ) : (
        <div className={styles.field}>
          <label htmlFor="department_id">Хэлтэс</label>
          <select
            id="department_id"
            name="department_id"
            value={departmentId}
            onChange={(event) => handleDepartmentChange(event.target.value)}
            required
          >
            <option value="">Хэлтэс сонгоно уу</option>
            {departmentOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      )}

      {isCombinedDepartment ? (
        <div className={styles.optionalSection}>
          <div className={styles.field}>
            <label>Хэлтэс доторх ажил</label>
            <div className={styles.modeRail}>
              <button
                type="button"
                className={`${styles.modeChip} ${
                  operationUnit === "auto_base" ? styles.modeChipActive : ""
                }`}
                onClick={() => setOperationUnit("auto_base")}
              >
                <span>Авто бааз</span>
                <small>Техник, засвар, бэлэн байдал</small>
              </button>
              <button
                type="button"
                className={`${styles.modeChip} ${
                  operationUnit === "garbage_transport" ? styles.modeChipActive : ""
                }`}
                onClick={() => setOperationUnit("garbage_transport")}
              >
                <span>Хог тээвэрлэлт</span>
                <small>Машин, маршрут, цэгийн ажилбар</small>
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <input type="hidden" name="operation_unit" value={operationUnit} />

      {isGarbageTransport ? (
        <>
          <div className={styles.fieldRow}>
            <div className={styles.field}>
              <label htmlFor="garbage_vehicle_id">Машины дугаар</label>
              <select
                id="garbage_vehicle_id"
                name="garbage_vehicle_id"
                value={vehicleId}
                onChange={(event) => setVehicleId(event.target.value)}
                required={isGarbageTransport}
              >
                <option value="">Машин сонгоно уу</option>
                {garbageVehicleOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.field}>
              <label htmlFor="garbage_route_id">Маршрут</label>
              <select
                id="garbage_route_id"
                name="garbage_route_id"
                value={routeId}
                onChange={(event) => setRouteId(event.target.value)}
                required={isGarbageTransport}
              >
                <option value="">Маршрут сонгоно уу</option>
                {garbageRouteOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.field}>
              <label htmlFor="start_date">Огноо</label>
              <input
                id="start_date"
                name="start_date"
                type="date"
                value={shiftDate}
                onChange={(event) => setShiftDate(event.target.value)}
                required={isGarbageTransport}
              />
            </div>
          </div>

          <input type="hidden" name="name" value={generatedName} />

          <div className={styles.previewCard}>
            <div className={styles.previewHeader}>
              <span className={styles.eyebrow}>Хог тээвэрлэлтийн ажил</span>
              <strong>
                {generatedName ||
                  "Машин, маршрут сонгоход нэр автоматаар үүснэ"}
              </strong>
            </div>

            <div className={styles.previewGrid}>
              <div className={styles.previewMeta}>
                <span>Сонгосон машин</span>
                <strong>{selectedVehicle?.plate || "Сонгоогүй"}</strong>
              </div>
              <div className={styles.previewMeta}>
                <span>Маршрут</span>
                <strong>{selectedRoute?.label || "Сонгоогүй"}</strong>
              </div>
              <div className={styles.previewMeta}>
                <span>Цэгийн тоо</span>
                <strong>{selectedRoute ? `${selectedRoute.pointCount} цэг` : "—"}</strong>
              </div>
              <div className={styles.previewMeta}>
                <span>Ээлж</span>
                <strong>{selectedRoute ? formatShiftLabel(selectedRoute.shiftType) : "—"}</strong>
              </div>
            </div>

            <p className={styles.helperNote}>
              Сонгосон машин, маршрут, огноогоор нэг ажил үүснэ. Тухайн маршрутын
              хог ачих цэг бүр ажил дотор тусдаа ажилбар болж автоматаар үүснэ.
            </p>
            <p className={styles.helperNote}>
              Огноо: <strong>{formatDateLabel(shiftDate)}</strong>
            </p>
          </div>
        </>
      ) : (
        <>
          <div className={styles.field}>
            <label htmlFor="name">Ажлын нэр</label>
            <input
              id="name"
              name="name"
              type="text"
              placeholder="Жишээ: Хаврын тохижилтын ажил"
              required
            />
          </div>

          <div className={styles.fieldRow}>
            <div className={styles.field}>
              <label htmlFor="manager_id">Хариуцах ажилтан</label>
              <select id="manager_id" name="manager_id" defaultValue="">
                <option value="">Дараа нь сонгоно</option>
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
              <span className={styles.optionalToggleTitle}>Төлөвлөсөн хэмжээ ашиглах</span>
              <span className={styles.optionalToggleText}>
                Шаардлагатай үед төлөвлөсөн хэмжээ болон хэмжих нэгжийг нэмж бүртгэнэ.
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
        </>
      )}

      <div className={styles.buttonRow}>
        <button type="submit" className={styles.primaryButton}>
          {isGarbageTransport ? "Хог тээвэрлэлтийн ажил үүсгэх" : "Ажил үүсгэх"}
        </button>
      </div>
    </form>
  );
}
