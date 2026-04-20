export type DepartmentGroupDefinition = {
  name: string;
  units: string[];
  icon: string;
  accent: string;
};

export const DEPARTMENT_GROUPS: DepartmentGroupDefinition[] = [
  {
    name: "Авто бааз, хог тээвэрлэлтийн хэлтэс",
    units: ["Авто бааз", "Хог тээвэрлэлт"],
    icon: "🚚",
    accent: "var(--tone-amber)",
  },
  {
    name: "Ногоон байгууламж, цэвэрлэгээ үйлчилгээний хэлтэс",
    units: ["Ногоон байгууламж", "Зам талбайн цэвэрлэгээ"],
    icon: "🌿",
    accent: "var(--tone-teal)",
  },
  {
    name: "Тохижилтын хэлтэс",
    units: ["Тохижилт үйлчилгээ"],
    icon: "🏙️",
    accent: "var(--tone-slate)",
  },
];

export function findDepartmentGroupByName(groupName: string) {
  return DEPARTMENT_GROUPS.find((group) => group.name === groupName) ?? null;
}

export function findDepartmentGroupByUnit(unitName: string) {
  return DEPARTMENT_GROUPS.find((group) => group.units.includes(unitName)) ?? null;
}

export function getAvailableUnits(group: DepartmentGroupDefinition, availableNames: string[]) {
  return group.units.filter((unit) => availableNames.includes(unit));
}

export function getDepartmentGroupLabel(group: DepartmentGroupDefinition) {
  return group.units.join(" • ");
}
